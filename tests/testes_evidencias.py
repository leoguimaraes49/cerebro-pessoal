"""Regressões da integração 0.5 em fixtures e pelo coordenador real."""
import copy
import json
import unittest

from evidencias import inspect_response, read_receipt, safe_folder
from execucao import Engine, validate_citations
from nucleo import Conflict, Invalid
import testes_execucao
from testes_execucao import FakeModel


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = testes_execucao.EngineTests()
        self.fixture.setUp()
        self.store = self.fixture.sources
        self.one = self.store.apply('one', 'create', title='Dados fictícios', text=json.dumps({
            'state': 'planned', 'values': [1, 2], 'nested': [1],
            'edges': [['a', 'requires', 'b']],
        }))
        self.two = self.store.apply('two', 'create', title='Dependência fictícia',
                                    text=json.dumps({'edges': [['b', 'requires', 'c']]}))

    def tearDown(self):
        self.fixture.tearDown()

    def ref(self, record=None, path='/state'):
        return {'record_id': (record or self.one)['id'], 'revision': 1, 'path': path}

    def draft(self, value='planned', kind='field', refs=None, controlled=False):
        claim = {'id': 'c1', 'kind': kind, 'refs': refs or [self.ref()], 'value': value}
        answer = 'c1 = ' + json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        return {'answer': answer if controlled else 'Resposta natural fictícia.',
                'answer_format': 'controlled' if controlled else 'free_text', 'claims': [claim],
                'citations': [{'record_id': self.one['id'], 'revision': 1, 'quote': 'planned'}]}

    def test_free_text_claims_do_not_certify_the_narrative(self):
        result = inspect_response(self.store, 'free', self.draft())
        self.assertEqual(result['status'], 'claims_verified')
        self.assertFalse(result['answer_verified'])

    def test_controlled_answer_is_bound_to_verified_claims(self):
        draft = self.draft(controlled=True)
        result = inspect_response(self.store, 'controlled', draft)
        self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['answer_verified'])
        draft['answer'] += ' afirmação extra'
        self.assertEqual(inspect_response(self.store, 'changed', draft)['status'], 'rejected')

    def test_wrong_sum_with_valid_citation_is_rejected(self):
        draft = self.draft(4, 'sum', [self.ref(path='/values/0'), self.ref(path='/values/1')])
        self.assertEqual(inspect_response(self.store, 'wrong', draft)['status'], 'rejected')

    def test_nested_boolean_is_distinct_from_integer(self):
        draft = self.draft([True], refs=[self.ref(path='/nested')])
        self.assertEqual(inspect_response(self.store, 'types', draft)['status'], 'rejected')

    def test_reference_and_citation_revisions_are_strict(self):
        for bad in (True, 1.0, '1'):
            draft = self.draft()
            draft['claims'][0]['refs'][0]['revision'] = bad
            result = inspect_response(self.store, 'revision-' + type(bad).__name__, draft)
            self.assertEqual(result['status'], 'rejected')
            with self.assertRaises(Invalid):
                validate_citations(self.store, [{'record_id': self.one['id'], 'revision': bad, 'quote': 'planned'}])

    def test_selective_supplement_uses_current_sources_within_budget(self):
        draft = self.draft(['a', 'requires', 'c'], 'chain',
                           [self.ref(path='/edges/0'), self.ref(self.two, '/edges/0')])
        original = copy.deepcopy(draft)
        result = inspect_response(self.store, 'supplement', draft, [self.one['id']], 2)
        self.assertEqual(result['route'], 'supplemented')
        self.assertEqual(result['status'], 'claims_verified')
        self.assertEqual(result['context_after'], 2)
        self.assertEqual(draft, original)
        blocked = inspect_response(self.store, 'small', draft, [self.one['id']], 1)
        self.assertEqual(blocked['route'], 'context_budget_exceeded')
        self.assertEqual(blocked['status'], 'rejected')
        self.assertLessEqual(blocked['context_after'], 1)

    def test_valid_evidence_does_not_trigger_deepening(self):
        result = inspect_response(self.store, 'direct', self.draft(), [self.one['id']])
        self.assertEqual(result['route'], 'direct')

    def test_hypothesis_and_plain_source_remain_limited(self):
        draft = self.draft('Talvez haja uma preferência.', 'hypothesis', [self.ref()])
        self.assertEqual(inspect_response(self.store, 'hypothesis', draft)['status'], 'limited')
        self.store.apply('plain', 'correct', ident=self.one['id'], expected=1,
                         text='Um relato em linguagem natural.', reason='fixture')
        draft = self.draft()
        draft['claims'][0]['refs'][0]['revision'] = 2
        draft['citations'] = []
        self.assertEqual(inspect_response(self.store, 'plain-source', draft)['status'], 'limited')

    def test_receipt_is_stale_after_correction_and_after_unlinked_addition(self):
        checked = inspect_response(self.store, 'initial', self.draft())
        self.store.apply('unlinked', 'create', title='Nota nova fictícia', text='Informação fictícia nova.')
        self.assertEqual(read_receipt(self.store, checked['receipt_id'])['status'], 'stale')
        checked = inspect_response(self.store, 'current', self.draft())
        self.store.apply('correct', 'correct', ident=self.one['id'], expected=1,
                         text='{"state":"executed"}', reason='fixture')
        self.assertEqual(read_receipt(self.store, checked['receipt_id'])['status'], 'stale')

    def test_idempotency_survives_restart_and_conflicting_key_is_rejected(self):
        result = inspect_response(self.store, 'repeat', self.draft())
        self.assertEqual(inspect_response(self.store, 'repeat', self.draft()), result)
        with self.assertRaises(Conflict):
            inspect_response(self.store, 'repeat', self.draft('executed'))

    def test_checker_recalculates_and_does_not_trust_saved_verdict(self):
        result = inspect_response(self.store, 'tamper', self.draft(controlled=True))
        path = safe_folder(self.store, 'respostas') / (result['receipt_id'] + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        data['packet']['evidence'][self.one['id']]['payload']['content'] = '{"state":"executed"}'
        path.write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(read_receipt(self.store, result['receipt_id'])['status'], 'rejected')

    def test_legacy_answer_needs_no_receipt(self):
        result = inspect_response(self.store, 'legacy', {'answer': 'Texto livre.', 'citations': []})
        self.assertEqual(result['status'], 'not_requested')
        self.assertIsNone(result['receipt_id'])

    def test_changed_context_prevents_verification(self):
        with self.assertRaises(Conflict):
            inspect_response(self.store, 'obsolete-context', self.draft(), expected_generation='0' * 64)

    def test_rehashed_narrative_cannot_replace_a_controlled_answer(self):
        from verificador_evidencias import sha
        result = inspect_response(self.store, 'text-binding', self.draft(controlled=True))
        path = safe_folder(self.store, 'respostas') / (result['receipt_id'] + '.json')
        data = json.loads(path.read_text(encoding='utf-8'))
        data['packet']['response_text'] = 'Outra resposta sem comprovação.'
        data['packet']['receipt_sha256'] = sha({key: value for key, value in data['packet'].items() if key != 'receipt_sha256'})
        path.write_text(json.dumps(data), encoding='utf-8')
        checked = read_receipt(self.store, result['receipt_id'])
        self.assertEqual(checked['status'], 'rejected')
        self.assertFalse(checked['answer_verified'])

    def test_coordinator_blocks_rejected_claim_without_showing_wrong_answer(self):
        draft = self.draft(4, 'sum', [self.ref(path='/values/0'), self.ref(path='/values/1')])
        draft['answer'] = 'Resposta incorreta que não deve ser entregue.'
        model = FakeModel(lambda prompt: dict(draft, decision='answer'))
        engine = Engine(self.store, model_factory=lambda _: model)
        ident = engine.start('question', 'question', {'query': 'Dados fictícios'})
        outcome = engine.run(ident)
        self.assertEqual(outcome['status'], 'completed')
        response = json.loads(outcome['steps'][-1]['result'])
        self.assertEqual(response['quality'], 'limited')
        self.assertEqual(response['assurance']['status'], 'rejected')
        self.assertNotIn('Resposta incorreta', response['answer'])
        self.assertEqual(model.calls, 1)

    def test_coordinator_preserves_legacy_and_verifies_controlled_output(self):
        for controlled in (False, True):
            draft = self.draft(controlled=controlled)
            if not controlled:
                del draft['claims']
            model = FakeModel(lambda prompt: dict(draft, decision='answer'))
            engine = Engine(self.store, model_factory=lambda _: model)
            ident = engine.start('question-' + str(controlled), 'question', {'query': 'Dados fictícios'})
            outcome = engine.run(ident)
            self.assertEqual(outcome['status'], 'completed')
            response = json.loads(outcome['steps'][-1]['result'])
            self.assertEqual(response['answer'], draft['answer'])
            self.assertEqual(response['quality'], 'verified_as_recorded' if controlled else 'provisional')


if __name__ == '__main__':
    unittest.main(verbosity=2)
