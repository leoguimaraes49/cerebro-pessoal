"""Casos adversariais de identidade em fixtures; provedores reais proibidos."""
import copy,json,unittest
from unittest.mock import patch
from atribuicao import AttributionError,check_answer,validate_quote
import testes_execucao as fixtures
from testes_execucao import FakeModel
from autonomia import atomic_json
from evidencias import inspect_response,read_receipt
from nucleo import Invalid,Conflict


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.EngineTests();self.f.setUp()
        self.addCleanup(self.f.doCleanups);self.addCleanup(self.f.tearDown)
        self.s=self.f.sources;self.k=self.f.k
        source=self.s.apply('people-source','create',title='Pessoas fictícias',text='Ana fictícia e Beto fictício são pessoas distintas.')
        self.people=[]
        for i,name in enumerate(('Ana fictícia','Beto fictício')):
            result=self.k.apply('person-'+str(i),'entity',name,{'entity_kind':'person','display_name':name,
                'origin_refs':[{'record_id':source['id'],'revision':1}],'identity_status':'identified'})
            self.people.append(result)
        self.f.cfg['owner_person_id']=self.people[0]['id']
        atomic_json(self.s.root/'execucao.json',self.f.cfg)

    def item(self,subject=0,value='16h',quote='Beto fictício prefere estudar às 16h.'):
        return {'tipo':'assertion','titulo':'Preferência fictícia','evidence_quote':quote,
            'payload':{'subject_ref':{'record_id':self.people[subject]['id'],'revision':1},'predicate':'reports_preference',
                'value':{'type':'text','content':value},'nature':'user_report','asserted_by':'autora fictícia',
                'recorded_time':'2026-01-01T00:00:00+00:00','source_refs':[{'record_id':'$fonte','revision':1}],
                'context_description':'Cenário adversarial fictício','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}}

    def context(self,item=None,text='Ana fictícia prefere estudar às 09h. Beto fictício prefere estudar às 16h.'):
        return self.f.extraction_context([item] if item else None,text=text)

    def test_citation_about_beto_cannot_be_attributed_to_ana_before_writes(self):
        c=self.context(self.item());e=self.f.engine()
        with patch.object(e.k,'apply',side_effect=AssertionError('nenhum derivado deve ser gravado')):
            with self.assertRaises(AttributionError):e.extract(c)
            c['step_id']='apply_0'
            with self.assertRaises(AttributionError):e.apply_contribution(c)
        self.assertEqual(len([r for r in self.k.catalog()[0].values() if r['record_type']=='assertion']),0)
        self.assertEqual(self.s.read(c['input']['source_ref']['record_id'])['payload']['content'],c['input']['chunks'][0])

    def test_internal_model_repair_writes_correct_person_only(self):
        model=FakeModel(lambda prompt:{'extractions':[self.item(1 if 'CORRECAO_DE_FORMATO' in prompt else 0)]})
        e=self.f.engine(model)
        ident=e.start('repair-person','contribution',{'text':'Ana fictícia prefere estudar às 09h. Beto fictício prefere estudar às 16h.'})
        result=e.run(ident);self.assertEqual(result['status'],'completed');self.assertEqual(model.calls,2)
        record=next(r for r in self.k.catalog()[0].values() if r['record_type']=='assertion')
        self.assertEqual(record['payload']['subject_ref']['record_id'],self.people[1]['id'])
        self.assertEqual(e.run(ident)['status'],'completed');self.assertEqual(model.calls,2)

    def test_literal_numeric_value_from_other_person_is_rejected_even_without_quote(self):
        c=self.context();item=self.item();item.pop('evidence_quote')
        item['payload']['source_refs']=[c['input']['source_ref']]
        with self.assertRaises(AttributionError):self.k.apply('bad-direct','assertion','Valor trocado',item['payload'])

    def test_internal_repair_cannot_silently_drop_rejected_identity(self):
        model=FakeModel(lambda prompt:{'extractions':[] if 'CORRECAO_DE_FORMATO' in prompt else [self.item()]})
        e=self.f.engine(model)
        ident=e.start('do-not-drop','contribution',{'text':'Ana fictícia prefere estudar às 09h. Beto fictício prefere estudar às 16h.'})
        self.assertEqual(e.run(ident)['status'],'failed');self.assertEqual(model.calls,2)
        self.assertFalse(any(r['record_type']=='assertion' for r in self.k.catalog()[0].values()))

    def test_legacy_contribution_cannot_bypass_the_same_conflict(self):
        item=self.item();item.pop('evidence_quote')
        result=self.k.contribution('legacy-bad','Fonte fictícia',
            'Ana fictícia prefere estudar às 09h. Beto fictício prefere estudar às 16h.',[item])
        self.assertEqual(result['status'],'partial');self.assertEqual(result['completed'],[])
        self.assertEqual(self.s.read(result['source']['id'])['revision'],1)

    def test_broad_quote_uses_the_clause_for_the_literal_value(self):
        text='Ana fictícia prefere estudar às 09h. Beto fictício prefere estudar às 16h.'
        good=self.item(0,'09h',text);bad=self.item(0,'16h',text)
        self.f.engine().extract(self.context(good))
        with self.assertRaises(AttributionError):self.f.engine().extract(self.context(bad))

    def test_swapped_number_is_rejected_in_otherwise_correct_person_quote(self):
        with self.assertRaises(AttributionError):self.f.engine().extract(self.context(self.item(0,'16h','Ana fictícia prefere estudar às 09h.')))

    def test_first_person_is_bound_to_configured_owner_not_first_catalog_entry(self):
        c=self.context(self.item(0,'Sistemas de Informação','Eu estudo Sistemas de Informação.'),text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        self.f.engine().extract(c)
        c['input']['extractions'][0]['payload']['subject_ref']['record_id']=self.people[1]['id']
        with self.assertRaises(AttributionError):self.f.engine().extract(c)

    def test_pronoun_waits_and_resume_keeps_answer_as_separate_source(self):
        def output(prompt):
            if '"clarification":null' in prompt:
                return {'decision':'ask','question':'Você se refere a Ana fictícia ou Beto fictício?',
                        'evidence_quote':'Ele prefere estudar às 16h.'}
            item=self.item(1,'16h','Ele prefere estudar às 16h.')
            item['payload']['source_refs'].append({'record_id':'$resposta','revision':1})
            item['payload']['attribution_resolution_ref']={'record_id':'$resposta','revision':1}
            return {'extractions':[item]}
        e=self.f.engine(FakeModel(output))
        ident=e.start('ambiguous','contribution',{'text':'Ele prefere estudar às 16h.'})
        self.assertEqual(e.run(ident)['status'],'waiting_user')
        result=e.answer(ident,'Beto fictício');self.assertEqual(result['status'],'completed')
        record=next(r for r in self.k.catalog()[0].values() if r['record_type']=='assertion')
        bases=record['payload']['source_refs'];self.assertEqual(len(bases),2)
        self.assertNotEqual(bases[0]['record_id'],bases[1]['record_id'])
        self.assertEqual(self.s.read(bases[0]['record_id'])['payload']['content'],'Ele prefere estudar às 16h.')
        self.assertEqual(self.s.read(bases[1]['record_id'])['payload']['content'],'Beto fictício')
        self.assertEqual(e.answer(ident,'Beto fictício')['status'],'completed')

    def test_corrected_clarification_is_not_consumed_as_current(self):
        c=self.context();answer=self.s.apply('answer','create',title='Esclarecimento fictício',text='Beto fictício')
        c['answer']={'value':'Beto fictício','origin':{'record_id':answer['id'],'revision':1}}
        self.s.apply('correct-answer','correct',ident=answer['id'],expected=1,text='Ana fictícia',reason='Retificação fictícia')
        with self.assertRaises(Conflict):self.f.engine().extract(c)

    def test_answer_cannot_hide_beto_profession_behind_second_person(self):
        c=self.context(text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        citation=dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')
        records=self.k.catalog()[0]
        self.assertEqual(check_answer('Você está em transição de engenharia civil.',[citation],records,self.people[0]['id'])['status'],'rejected')
        self.assertNotEqual(check_answer('Beto fictício é engenheiro civil.',[citation],records,self.people[0]['id'])['status'],'rejected')

    def test_answer_endpoint_rejects_identity_conflict_without_optional_claims(self):
        c=self.context(text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        draft={'answer':'Você é engenheiro civil.','citations':[dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')]}
        verdict=inspect_response(self.s,'identity-check',draft)
        self.assertEqual(verdict['status'],'rejected');self.assertFalse(verdict['answer_verified'])

    def test_person_as_object_does_not_steal_subject_or_block_valid_relationship(self):
        c=self.context(text='Eu confio em Beto fictício.')
        citation=dict(c['input']['source_ref'],quote='Eu confio em Beto fictício.')
        records=self.k.catalog()[0];owner=self.people[0]['id']
        self.assertNotEqual(check_answer('Você confia em Beto fictício.',[citation],records,owner)['status'],'rejected')
        self.assertEqual(check_answer('Beto fictício confia em você.',[citation],records,owner)['status'],'rejected')
        item=self.item(0,'Beto fictício','Eu confio em Beto fictício.')
        self.f.engine().extract(self.context(item,text='Eu confio em Beto fictício.'))

    def test_unresolved_third_person_pronoun_cannot_become_you_in_answer(self):
        c=self.context(text='Ele é engenheiro civil. Eu estudo Sistemas de Informação.')
        citation=dict(c['input']['source_ref'],quote='Ele é engenheiro civil.')
        checked=check_answer('Você é engenheiro civil.',[citation],self.k.catalog()[0],self.people[0]['id'])
        self.assertEqual(checked['status'],'rejected')

    def test_first_person_in_publication_is_not_the_vault_owner(self):
        doc=self.s.apply('external-first-person','create',title='Publicação fictícia',text='Eu sou engenheiro civil.',
            source_metadata={'source_kind':'publication','publication_title':'Publicação inteiramente fictícia',
                             'reference_locator':'https://example.invalid/fixture'})
        citation={'record_id':doc['id'],'revision':1,'quote':'Eu sou engenheiro civil.'}
        checked=check_answer('Você é engenheiro civil.',[citation],self.k.catalog()[0],self.people[0]['id'])
        self.assertEqual(checked['status'],'rejected')
        payload=self.item(0,'engenheiro civil','Eu sou engenheiro civil.')['payload']
        payload['source_refs']=[{'record_id':doc['id'],'revision':1}]
        payload['attribution_evidence']={'source_ref':payload['source_refs'][0],'quote':citation['quote']}
        with self.assertRaises(AttributionError):self.k.apply('wrong-publication-person','assertion','Atribuição inválida',payload)

    def test_engine_suppresses_wrong_subject_answer(self):
        c=self.context(text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        citation=dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')
        model=FakeModel(lambda prompt:{'decision':'answer','answer':'Você é engenheiro civil.','citations':[citation]})
        e=self.f.engine(model);ident=e.start('profile','question',{'query':'Quem sou eu e qual minha formação?'})
        result=e.run(ident);self.assertEqual(result['status'],'completed')
        response=json.loads(next(s['result'] for s in result['steps'] if s['id']=='respond'))
        self.assertEqual(response['quality'],'limited')
        self.assertNotIn('Você é engenheiro civil.',response['answer'])

    def test_engine_repairs_answer_with_existing_evidence_within_same_budget(self):
        c=self.context(text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        bad=dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')
        good=dict(c['input']['source_ref'],quote='Eu estudo Sistemas de Informação.')
        model=FakeModel(lambda prompt:{'decision':'answer',
            'answer':'Você estuda Sistemas de Informação.' if 'CORRECAO_DE_ATRIBUICAO' in prompt else 'Você é engenheiro civil.',
            'citations':[good if 'CORRECAO_DE_ATRIBUICAO' in prompt else bad]})
        e=self.f.engine(model);ident=e.start('repair-answer','question',{'query':'Qual minha formação?'})
        result=e.run(ident);self.assertEqual(result['status'],'completed');self.assertEqual(model.calls,2)
        response=json.loads(next(s['result'] for s in result['steps'] if s['id']=='respond'))
        self.assertEqual(response['answer'],'Você estuda Sistemas de Informação.')
        self.assertEqual(response['quality'],'provisional')

    def test_legacy_receipt_is_rechecked_for_identity_before_reuse(self):
        c=self.context(text='Eu estudo Sistemas de Informação. Beto fictício é engenheiro civil.')
        number=self.s.apply('number-source','create',title='Número fictício',text='{"n":1}')
        draft={'answer':'Você é engenheiro civil.',
            'citations':[dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')],
            'claims':[{'id':'c1','kind':'field','refs':[{'record_id':number['id'],'revision':1,'path':'/n'}],'value':1}]}
        with patch('atribuicao.check_answer',return_value={'status':'checked_for_known_mentions'}):
            receipt=inspect_response(self.s,'old-receipt',draft)
        self.assertIsNotNone(receipt['receipt_id'])
        current=read_receipt(self.s,receipt['receipt_id'])
        self.assertEqual(current['status'],'rejected');self.assertFalse(current['answer_verified'])

    def test_answer_repair_does_not_expand_model_budget(self):
        c=self.context(text='Beto fictício é engenheiro civil.')
        citation=dict(c['input']['source_ref'],quote='Beto fictício é engenheiro civil.')
        def output(prompt):
            if 'CORRECAO_DE_ATRIBUICAO' in prompt:raise Invalid('orçamento do modelo esgotado')
            return {'decision':'answer','answer':'Você é engenheiro civil.','citations':[citation]}
        e=self.f.engine(FakeModel(output));ident=e.start('budget-limited','question',{'query':'Quem sou eu?'})
        result=e.run(ident);self.assertEqual(result['status'],'completed')
        response=json.loads(next(s['result'] for s in result['steps'] if s['id']=='respond'))
        self.assertEqual(response['quality'],'limited');self.assertNotIn('Você é engenheiro civil.',response['answer'])

    def test_homonymous_alias_does_not_select_by_catalog_order(self):
        records=copy.deepcopy(self.k.catalog()[0])
        for p in self.people:records[p['id']]['payload']['aliases']=['Dani']
        with self.assertRaises(AttributionError) as error:
            validate_quote(self.people[0]['id'],'Dani prefere estudar às 09h.',records,value='09h')
        self.assertTrue(error.exception.ambiguous)

    def test_new_person_placeholder_keeps_its_own_quote(self):
        first={'tipo':'entity','titulo':'Carla fictícia','payload':{'entity_kind':'person','display_name':'Carla fictícia',
               'origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'identified'},'evidence_quote':'Carla fictícia prefere estudar às 11h.'}
        item=self.item(0,'11h','Carla fictícia prefere estudar às 11h.')
        item['payload']['subject_ref']={'record_id':'$0','revision':1}
        c=self.f.extraction_context([first,item],key='new-person',text='Carla fictícia prefere estudar às 11h.')
        e=self.f.engine();result=e.extract(c);c.update(step_id='apply_0',previous={'extract_0':result})
        saved=e.apply_contribution(c)
        assertion=self.k.catalog()[0][saved['completed'][1]['id']]
        self.assertEqual(assertion['payload']['subject_ref']['record_id'],saved['completed'][0]['id'])


if __name__=='__main__':unittest.main(verbosity=2)
