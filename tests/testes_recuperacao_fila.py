import copy
import json
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from autonomia import Queue, DEFAULTS, atomic_json, code_hash
from execucao import Engine, DEFAULT as EXECUTION_DEFAULTS
from conhecimento import Knowledge
from nucleo import Store, REAL_SYSTEM, Invalid, sha
from recuperacao_fila import recover_expired, reconcile_lineage, retry_review
import recuperacao_fila


class RecoveryQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios')
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = Store(root/'sistema', root/'cofre')
        manual = self.store.vault/'00_Manual'
        manual.mkdir(exist_ok=True)
        data = b'# Manual exclusivamente ficticio para os testes de recuperacao.\n'
        (manual/'ficticio.md').write_bytes(data)
        atomic_json(self.store.root/'manual_manifest.json', {'ficticio.md': sha(data)})
        self.cfg = copy.deepcopy(EXECUTION_DEFAULTS)
        self.cfg.update(enabled=True, retrieval_policy='lexical', auto_adopt_config=False)
        self.cfg['model'] = {'enabled': False}
        self.cfg['embeddings'] = {'enabled': False}
        atomic_json(self.store.root/'execucao.json', self.cfg)
        self.engine = Engine(self.store)
        self.queue = Queue(self.store)
        atomic_json(self.queue.config_path, dict(DEFAULTS, enabled=True,
                    content_access='permitido', approved_code=code_hash()))

    def expired(self,key='original'):
        demand = self.engine.start(key,'contribution',{'text':'Relato fictício preservado.', 'title':'Origem fictícia'})
        job = self.queue.enqueue('demanda-'+key,'plan_demand',now=time.time()-2000,payload={'execution_id':demand})
        with self.engine.q.connect() as c:
            c.execute('UPDATE demands SET created=created-2000,deadline=deadline-2000 WHERE id=?', (demand,))
        with self.queue.connect() as c:
            self.queue.recover(c,time.time())
        return demand,job

    def test_expired_replans_once_and_reuses_original_source(self):
        old,job = self.expired()
        recovered = recover_expired(self.queue,self.engine)
        self.assertEqual(len(recovered),1)
        self.assertEqual(recover_expired(self.queue,self.engine),[])
        self.assertEqual(len(self.store.list()),1)
        with self.engine.q.connect() as c:
            before=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(old,)).fetchone()[0])
            after=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(recovered[0]['new_demand'],)).fetchone()[0])
        self.assertEqual(before['source_ref'],after['source_ref'])
        self.assertEqual(after['recovery_of'],old)
        self.assertEqual(self.queue.get(job['id'])['execution_status'],'failed')
        snapshot = self.engine.q.inspect(old)
        self.assertEqual(snapshot['demand']['status'], 'superseded')
        self.assertEqual(snapshot['demand']['superseded_by'], recovered[0]['new_demand'])
        self.assertTrue(all(step['status'] == 'queued' for step in snapshot['steps']))
        self.assertEqual(self.engine.q.run_until_pause(old), 'superseded')
        self.assertEqual(self.engine.q.cancel(old), 'superseded')

    def test_expired_failed_demand_is_superseded_without_renewing_old_budget(self):
        old, _ = self.expired()
        self.assertEqual(self.engine.q.run_one(old), 'failed')
        before = self.engine.q.inspect(old)['demand']
        self.assertEqual(before['error'], 'prazo total excedido')
        self.assertEqual(len(recover_expired(self.queue, self.engine)), 1)
        after = self.engine.q.inspect(old)['demand']
        self.assertEqual(after['status'], 'superseded')
        for field in ('deadline', 'actions', 'model_calls', 'limits_json'):
            self.assertEqual(after[field], before[field])
        self.assertEqual(self.engine.q.run_one(old), 'superseded')

    def test_interrupted_before_enqueue_reuses_new_demand(self):
        self.expired()
        with patch.object(self.queue,'enqueue',side_effect=OSError('interrupção fictícia')):
            with self.assertRaises(OSError): recover_expired(self.queue,self.engine)
        result=recover_expired(self.queue,self.engine)
        self.assertEqual(len(result),1)
        with self.engine.q.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM demands').fetchone()[0],2)
        self.assertEqual(recover_expired(self.queue,self.engine),[])

    def test_completed_failed_running_or_uncertain_effect_is_never_replayed(self):
        for status in ('completed', 'failed', 'running', 'uncertain'):
            with self.subTest(status=status):
                demand, job = self.expired('effect-' + status)
                with self.engine.q.connect() as c:
                    c.execute('UPDATE steps SET status=? WHERE demand_id=? AND capability=?',
                              (status, demand, 'apply_contribution'))
                self.assertEqual(recover_expired(self.queue, self.engine), [])
                with self.queue.connect() as c:
                    reason = c.execute('SELECT reason FROM recovery_review WHERE old_job=?', (job['id'],)).fetchone()[0]
                self.assertEqual(reason, 'efeito aplicado, falho ou incerto exige revisão')
                self.assertEqual(self.engine.q.inspect(demand)['demand']['status'], 'queued')

    def test_reference_errors_are_not_blindly_retried(self):
        demand,job=self.expired()
        with self.queue.connect() as c:
            c.execute("UPDATE executions SET error='referência inexistente' WHERE id=?",(job['id'],))
        self.assertEqual(recover_expired(self.queue,self.engine),[])

    def test_changed_source_does_not_replay_old_content(self):
        demand,job=self.expired()
        with self.engine.q.connect() as c:
            payload=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(demand,)).fetchone()[0])
        ref=payload['source_ref']
        with patch.object(self.store,'read',return_value={'revision':ref['revision']+1}):
            self.assertEqual(recover_expired(self.queue,self.engine),[])

    def test_existing_derivative_blocks_replay(self):
        demand,job=self.expired()
        with self.engine.q.connect() as c:
            payload=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(demand,)).fetchone()[0])
        Knowledge(self.store).apply('manual','entity','Tema fictício',{
            'entity_kind':'learning_topic','topic_description':'Origem já utilizada',
            'origin_refs':[payload['source_ref']],'identity_status':'provisional'})
        self.assertEqual(recover_expired(self.queue,self.engine),[])
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT reason FROM recovery_review WHERE old_job=?',(job['id'],)).fetchone()[0],
                             'origem já utilizada por outro registro')

    def test_expired_recovery_is_not_recovered_again(self):
        self.expired()
        first=recover_expired(self.queue,self.engine)[0]
        with self.queue.connect() as c:
            c.execute("UPDATE executions SET execution_status='failed',error='prazo total excedido' WHERE id=?",(first['new_job'],))
        self.assertEqual(recover_expired(self.queue,self.engine),[])

    def test_two_expired_demands_for_same_source_do_not_both_replay(self):
        first,_=self.expired('one')
        with self.engine.q.connect() as c:
            payload=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(first,)).fetchone()[0])
        second=self.engine.start('two','contribution',{'text':'Relato fictício preservado.',
            'title':'Origem fictícia','source_ref':payload['source_ref']})
        self.queue.enqueue('demanda-two','plan_demand',now=time.time()-2000,payload={'execution_id':second})
        with self.queue.connect() as c:self.queue.recover(c,time.time())
        self.assertEqual(len(recover_expired(self.queue,self.engine,limit=5)),1)
        self.assertEqual(recover_expired(self.queue,self.engine,limit=5),[])

    def test_scheduler_invokes_recovery_without_model_call(self):
        self.expired()
        cfg=copy.deepcopy(self.cfg)
        cfg['auto_process_sources']=True
        atomic_json(self.store.root/'execucao.json',cfg)
        self.queue.schedule_runtime()
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM recovery_links').fetchone()[0],1)
        self.queue.schedule_runtime()
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM recovery_links').fetchone()[0],1)

    def rows(self, *ids):
        with self.engine.q.connect() as c:
            return [dict(c.execute('SELECT id,status,created,deadline,actions,model_calls,error FROM demands WHERE id=?',
                                   (ident,)).fetchone()) for ident in ids]

    def legacy_recovery(self, key='legacy'):
        old, job = self.expired(key)
        with self.engine.q.connect() as c:
            payload = json.loads(c.execute('SELECT payload FROM demands WHERE id=?', (old,)).fetchone()[0])
        source = self.store.read(payload['source_ref']['record_id'])
        successor = self.engine.start('recuperar-' + job['id'].replace('-', ''), 'contribution',
            {'text': source['payload']['content'], 'title': source['title'], 'source_ref': payload['source_ref'],
             'query': payload['query'], 'recovery_of': old})
        successor_job = self.queue.enqueue('demand-' + successor, 'plan_demand', payload={'execution_id': successor})
        with self.queue.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS recovery_links(old_job TEXT PRIMARY KEY,new_demand TEXT NOT NULL,new_job TEXT NOT NULL)')
            c.execute('INSERT INTO recovery_links VALUES(?,?,?)', (job['id'], successor, successor_job['id']))
        return old, job, successor, successor_job

    def test_interrupted_handoff_is_durable_and_does_not_renew_budgets(self):
        old, job = self.expired()
        before = self.engine.q.inspect(old)
        with patch.object(self.queue, 'enqueue', side_effect=OSError('interrupção fictícia')):
            with self.assertRaises(OSError):
                recover_expired(self.queue, self.engine)
        staged = self.engine.q.inspect(old)
        self.assertEqual(staged['demand']['status'], 'superseded')
        successor = staged['demand']['superseded_by']
        self.assertTrue(successor)
        projected = reconcile_lineage(self.queue, self.engine, self.rows(old))[0]
        self.assertEqual(projected['status'], 'superseded')
        self.assertTrue(projected['lineage_verified']); self.assertTrue(projected['recovery_pending'])
        self.assertIsNone(projected['recovery_job_id'])
        successor_before = self.engine.q.inspect(successor)['demand']
        with patch.object(self.engine, 'start', side_effect=AssertionError('não recriar sucessora')):
            result = recover_expired(self.queue, self.engine)
        self.assertEqual(result, [{'old_job': job['id'], 'new_demand': successor, 'new_job': result[0]['new_job']}])
        after = self.engine.q.inspect(old)
        self.assertEqual(after['steps'], before['steps'])
        for field in ('actions', 'model_calls', 'deadline', 'limits_json', 'fingerprint', 'payload'):
            self.assertEqual(after['demand'][field], before['demand'][field])
            self.assertEqual(self.engine.q.inspect(successor)['demand'][field], successor_before[field])
        self.assertEqual(self.engine.q.run_one(old), 'superseded')
        self.assertEqual(recover_expired(self.queue, self.engine), [])

    def test_interrupted_before_supersession_reuses_unpublished_successor(self):
        old, _ = self.expired()
        with patch.object(self.engine.q, 'supersede', side_effect=OSError('interrupção fictícia antes da reserva')):
            with self.assertRaises(OSError):
                recover_expired(self.queue, self.engine)
        self.assertEqual(self.engine.q.inspect(old)['demand']['status'], 'queued')
        with self.engine.q.connect() as c:
            successor = dict(c.execute('SELECT * FROM demands WHERE id!=?', (old,)).fetchone())
        with patch.object(self.engine, 'start', side_effect=AssertionError('não renovar a demanda existente')):
            recovered = recover_expired(self.queue, self.engine)
        self.assertEqual(recovered[0]['new_demand'], successor['id'])
        self.assertEqual(self.engine.q.inspect(old)['demand']['status'], 'superseded')
        with self.engine.q.connect() as c:
            self.assertEqual(dict(c.execute('SELECT * FROM demands WHERE id=?', (successor['id'],)).fetchone()), successor)

    def test_interrupted_after_enqueue_relinks_completed_successor_without_replay(self):
        old, job = self.expired()
        event = self.queue.event
        def fail_link(c, ident, name, *args, **kwargs):
            if name == 'recovered':
                raise OSError('interrupção fictícia antes do commit do vínculo')
            return event(c, ident, name, *args, **kwargs)
        with patch.object(self.queue, 'event', side_effect=fail_link):
            with self.assertRaises(OSError):
                recover_expired(self.queue, self.engine)
        successor = self.engine.q.inspect(old)['demand']['superseded_by']
        with self.engine.q.connect() as c:
            payload = json.loads(c.execute('SELECT payload FROM demands WHERE id=?', (successor,)).fetchone()[0])
            c.execute("UPDATE demands SET status='completed' WHERE id=?", (successor,))
            c.execute("UPDATE steps SET status='completed' WHERE demand_id=?", (successor,))
        Knowledge(self.store).apply('successor-effect', 'entity', 'Derivação fictícia', {
            'entity_kind': 'learning_topic', 'topic_description': 'Efeito confirmado da sucessora',
            'origin_refs': [payload['source_ref']], 'identity_status': 'provisional'})
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM recovery_links').fetchone()[0], 0)
            new_job = c.execute('SELECT id FROM executions WHERE request_key=?', ('demand-' + successor,)).fetchone()[0]
        with patch.object(self.store, 'read', side_effect=AssertionError('não reler conteúdo para relink')), patch.object(self.engine.k, 'catalog', side_effect=AssertionError('não replanejar efeito concluído')):
            recovered = recover_expired(self.queue, self.engine)
        self.assertEqual(recovered, [{'old_job': job['id'], 'new_demand': successor, 'new_job': new_job}])
        self.assertEqual(self.engine.q.inspect(old)['demand']['status'], 'superseded')
        self.assertEqual(self.engine.q.inspect(successor)['demand']['status'], 'completed')
        with self.engine.q.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM demands').fetchone()[0], 2)

    def test_concurrent_original_effect_prevents_handoff_and_successor_enqueue(self):
        old, job = self.expired()
        start = self.engine.start
        def concurrent_effect(*args, **kwargs):
            successor = start(*args, **kwargs)
            with self.engine.q.connect() as c:
                c.execute("UPDATE steps SET status='completed' WHERE demand_id=? AND capability='apply_contribution'", (old,))
            return successor
        with patch.object(self.engine, 'start', side_effect=concurrent_effect):
            self.assertEqual(recover_expired(self.queue, self.engine), [])
        self.assertEqual(self.engine.q.inspect(old)['demand']['status'], 'queued')
        self.assertIsNone(self.engine.q.inspect(old)['demand']['superseded_by'])
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM executions').fetchone()[0], 1)
            self.assertIn('estado mudou', c.execute('SELECT reason FROM recovery_review WHERE old_job=?', (job['id'],)).fetchone()[0])

    def test_candidate_budget_progresses_past_quarantined_jobs(self):
        for index in range(7):
            old, job = self.expired('defer-' + str(index))
            self.engine.q.cancel(old)
            with self.queue.connect() as c:
                c.execute('UPDATE executions SET created=? WHERE id=?', (index, job['id']))
        valid, valid_job = self.expired('valid')
        with self.queue.connect() as c:
            c.execute('UPDATE executions SET created=7 WHERE id=?', (valid_job['id'],))
        for count in (2, 4, 6):
            with patch('recuperacao_fila._ineligible', wraps=recuperacao_fila._ineligible) as examined:
                self.assertEqual(recover_expired(self.queue, self.engine, max_candidates=2), [])
                self.assertEqual(examined.call_count, 2)
            with self.queue.connect() as c:
                self.assertEqual(c.execute('SELECT count(*) FROM recovery_review').fetchone()[0], count)
        with patch('recuperacao_fila._ineligible', wraps=recuperacao_fila._ineligible) as examined:
            recovered = recover_expired(self.queue, self.engine, max_candidates=2)
            self.assertEqual(len(recovered), 1); self.assertEqual(examined.call_count, 2)
        self.assertEqual(self.engine.q.inspect(valid)['demand']['status'], 'superseded')
        with patch('recuperacao_fila._ineligible', side_effect=AssertionError('não revarrer deferidos')):
            self.assertEqual(recover_expired(self.queue, self.engine, max_candidates=2), [])
        with self.queue.connect() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM events WHERE event='recovery_deferred'").fetchone()[0], 7)

    def test_success_limit_does_not_quarantine_unexamined_candidates(self):
        originals = [self.expired('success-' + str(i))[0] for i in range(3)]
        self.assertEqual(len(recover_expired(self.queue, self.engine, limit=1, max_candidates=3)), 1)
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM recovery_review').fetchone()[0], 0)
        self.assertEqual(sum(self.engine.q.inspect(i)['demand']['status'] == 'superseded' for i in originals), 1)
        self.assertEqual(len(recover_expired(self.queue, self.engine, limit=2, max_candidates=3)), 2)

    def test_deferred_job_requires_explicit_idempotent_release(self):
        old, job = self.expired()
        with self.engine.q.connect() as c:
            c.execute("UPDATE steps SET status='uncertain' WHERE demand_id=? AND capability='apply_contribution'", (old,))
        self.assertEqual(recover_expired(self.queue, self.engine), [])
        with self.engine.q.connect() as c:
            c.execute("UPDATE steps SET status='queued' WHERE demand_id=? AND capability='apply_contribution'", (old,))
        self.assertEqual(recover_expired(self.queue, self.engine), [])
        self.assertTrue(retry_review(self.queue, job['id']))
        self.assertFalse(retry_review(self.queue, job['id']))
        self.assertEqual(len(recover_expired(self.queue, self.engine)), 1)
        self.assertFalse(retry_review(self.queue, job['id']))
        with self.queue.connect() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM events WHERE event='recovery_review_released'").fetchone()[0], 1)

    def test_malformed_candidate_is_quarantined_then_next_candidate_progresses(self):
        _, bad = self.expired('malformed')
        good, _ = self.expired('well-formed')
        with self.queue.connect() as c:
            c.execute('UPDATE execution_inputs SET payload=? WHERE execution_id=?', ('{invalid', bad['id']))
        self.assertEqual(recover_expired(self.queue, self.engine, max_candidates=1), [])
        self.assertEqual(len(recover_expired(self.queue, self.engine, max_candidates=1)), 1)
        self.assertEqual(self.engine.q.inspect(good)['demand']['status'], 'superseded')
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT reason FROM recovery_review WHERE old_job=?', (bad['id'],)).fetchone()[0],
                             'entrada do trabalho inválida')

    def test_existing_review_schema_and_reasons_are_preserved(self):
        _, job = self.expired()
        with self.queue.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS recovery_review(old_job TEXT PRIMARY KEY,reason TEXT NOT NULL)')
            c.execute('INSERT INTO recovery_review VALUES(?,?)', (job['id'], 'revisão legada preservada'))
        self.assertEqual(recover_expired(self.queue, self.engine), [])
        with self.queue.connect() as c:
            self.assertEqual(c.execute('SELECT reason FROM recovery_review WHERE old_job=?', (job['id'],)).fetchone()[0],
                             'revisão legada preservada')
            self.assertEqual([r['name'] for r in c.execute('PRAGMA table_info(recovery_review)')], ['old_job', 'reason'])

    def test_limits_and_authorization_remain_fail_closed(self):
        old, _ = self.expired()
        for invalid in (True, 0, 101, None):
            with self.subTest(max_candidates=invalid):
                with self.assertRaises(Invalid):recover_expired(self.queue, self.engine, max_candidates=invalid)
        for invalid in (False, 0, 11):
            with self.subTest(limit=invalid):
                with self.assertRaises(Invalid):recover_expired(self.queue, self.engine, limit=invalid)
        with patch.object(self.engine.q, 'authorize', return_value=False):
            with self.assertRaises(Invalid):recover_expired(self.queue, self.engine)
            with self.assertRaises(Invalid):reconcile_lineage(self.queue, self.engine, self.rows(old))
        cfg = self.queue.config(); cfg['content_access'] = 'bloqueado'; atomic_json(self.queue.config_path, cfg)
        with self.assertRaises(Invalid):recover_expired(self.queue, self.engine)
        with self.assertRaises(Invalid):retry_review(self.queue, 'unknown')
        with self.assertRaises(Invalid):reconcile_lineage(self.queue, self.engine, self.rows(old))
        with self.engine.q.connect() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM demands').fetchone()[0], 1)

    def test_lineage_read_callback_allows_paused_queue_without_authorizing_execution(self):
        old, _, successor, successor_job = self.legacy_recovery()
        records = self.rows(old, successor)
        cfg = self.queue.config(); cfg['enabled'] = False; atomic_json(self.queue.config_path, cfg)
        engine_cfg = copy.deepcopy(self.cfg); engine_cfg['enabled'] = False
        atomic_json(self.store.root/'execucao.json', engine_cfg)
        with self.assertRaises(Invalid):
            reconcile_lineage(self.queue, self.engine, records)
        with self.assertRaises(Invalid):
            reconcile_lineage(self.queue, self.engine, records, authorize=None)
        self.assertFalse(self.engine.q.authorize())
        with self.engine.q.connect() as c:before_engine = list(c.iterdump())
        with self.queue.connect() as c:before_queue = list(c.iterdump())
        authorized = Mock(return_value=True)
        with (
            patch.object(self.queue, 'authorize', side_effect=AssertionError('não autorizar execução da fila')),
            patch.object(self.engine.q, 'authorize', side_effect=AssertionError('não autorizar execução do coordenador')),
            patch.object(self.store, 'read', side_effect=AssertionError('não ler fontes')),
            patch.object(self.engine.k, 'catalog', side_effect=AssertionError('não consultar catálogo')),
            patch.object(self.engine, 'start', side_effect=AssertionError('não criar demandas')),
            patch.object(self.engine, 'run', side_effect=AssertionError('não executar demandas')),
            patch.object(self.engine.q, 'capabilities', new={}),
        ):
            projected = reconcile_lineage(self.queue, self.engine, records, authorize=authorized)
        authorized.assert_called_once_with()
        self.assertEqual(projected[0]['status'], 'superseded')
        self.assertEqual(projected[0]['raw_status'], 'queued')
        self.assertTrue(projected[0]['lineage_verified'])
        self.assertEqual(projected[0]['superseded_by'], successor)
        self.assertEqual(projected[0]['recovery_job_id'], successor_job['id'])
        self.assertEqual(projected[1]['status'], 'queued')
        with self.engine.q.connect() as c:self.assertEqual(list(c.iterdump()), before_engine)
        with self.queue.connect() as c:self.assertEqual(list(c.iterdump()), before_queue)
        self.assertFalse(self.queue.config()['enabled'])
        self.assertFalse(self.engine.q.authorize())
        with self.assertRaises(Invalid):self.queue.claim('fixture-paused')

    def test_lineage_read_callback_denial_precedes_all_operational_and_database_access(self):
        old, _, successor, _ = self.legacy_recovery()
        records = self.rows(old, successor)
        with (
            patch.object(self.queue, 'authorize', side_effect=AssertionError('não consultar autorização operacional')) as queue_authorize,
            patch.object(self.engine.q, 'authorize', side_effect=AssertionError('não consultar autorização operacional')) as engine_authorize,
            patch.object(self.queue, 'connect', side_effect=AssertionError('não ler fila')) as queue_connect,
            patch.object(self.engine.q, 'connect', side_effect=AssertionError('não ler coordenador')) as engine_connect,
            patch.object(self.store, 'read', side_effect=AssertionError('não ler fontes')),
            patch.object(self.engine.k, 'catalog', side_effect=AssertionError('não consultar catálogo')),
        ):
            for permission in (False, None, 1, 'permitido'):
                with self.subTest(permission=permission):
                    authorized = Mock(return_value=permission)
                    with self.assertRaises(Invalid):
                        reconcile_lineage(self.queue, self.engine, records, authorize=authorized)
                    authorized.assert_called_once_with()
            with self.assertRaises(Invalid):
                reconcile_lineage(self.queue, self.engine, records, authorize=True)
            queue_authorize.assert_not_called(); engine_authorize.assert_not_called()
            queue_connect.assert_not_called(); engine_connect.assert_not_called()

    def test_legacy_projection_is_idempotent_read_only_and_preserves_successor_backlog(self):
        old, _, successor, successor_job = self.legacy_recovery()
        records = self.rows(old, successor); unchanged = copy.deepcopy(records)
        with self.engine.q.connect() as c:before_engine = list(c.iterdump())
        with self.queue.connect() as c:before_queue = list(c.iterdump())
        projected = reconcile_lineage(self.queue, self.engine, records)
        self.assertEqual(records, unchanged)
        self.assertEqual(reconcile_lineage(self.queue, self.engine, projected), projected)
        self.assertEqual(projected[0]['status'], 'superseded'); self.assertEqual(projected[0]['raw_status'], 'queued')
        self.assertEqual(projected[0]['superseded_by'], successor)
        self.assertEqual(projected[0]['recovery_job_id'], successor_job['id'])
        self.assertTrue(projected[0]['lineage_verified']); self.assertFalse(projected[0]['runnable'])
        self.assertEqual(projected[0]['lineage_source'], 'recovery_links')
        self.assertEqual(projected[1]['status'], 'queued'); self.assertIsNone(projected[1]['superseded_by'])
        with self.engine.q.connect() as c:self.assertEqual(list(c.iterdump()), before_engine)
        with self.queue.connect() as c:self.assertEqual(list(c.iterdump()), before_queue)
        self.assertEqual(self.engine.q.inspect(old)['demand']['status'], 'queued')

    def test_legacy_projection_accepts_completed_successor_without_content_access(self):
        old, _, successor, _ = self.legacy_recovery()
        with self.engine.q.connect() as c:
            c.execute("UPDATE demands SET status='completed' WHERE id=?", (successor,))
            c.execute("UPDATE steps SET status='completed' WHERE demand_id=?", (successor,))
        with patch.object(self.store, 'read', side_effect=AssertionError('não ler conteúdo')), patch.object(self.engine.k, 'catalog', side_effect=AssertionError('não consultar cofre')):
            projected = reconcile_lineage(self.queue, self.engine, self.rows(old, successor))
        self.assertEqual(projected[0]['status'], 'superseded')
        self.assertEqual(projected[1]['status'], 'completed')

    def test_legacy_projection_fails_closed_for_invalid_or_uncertain_lineage(self):
        for problem in ('missing-job', 'empty-job', 'wrong-job-input', 'wrong-source', 'uncertain-original'):
            with self.subTest(problem=problem):
                old, job, successor, successor_job = self.legacy_recovery(problem)
                if problem in ('missing-job', 'empty-job'):
                    with self.queue.connect() as c:
                        c.execute('UPDATE recovery_links SET new_job=? WHERE old_job=?',
                                  ('missing' if problem == 'missing-job' else '', job['id']))
                elif problem == 'wrong-job-input':
                    with self.queue.connect() as c:
                        c.execute('UPDATE execution_inputs SET payload=? WHERE execution_id=?',
                                  (json.dumps({'execution_id': old}), successor_job['id']))
                elif problem == 'wrong-source':
                    with self.engine.q.connect() as c:
                        payload = json.loads(c.execute('SELECT payload FROM demands WHERE id=?', (successor,)).fetchone()[0])
                        payload['source_ref']['revision'] += 1
                        c.execute('UPDATE demands SET payload=? WHERE id=?', (json.dumps(payload), successor))
                else:
                    with self.engine.q.connect() as c:
                        c.execute("UPDATE steps SET status='uncertain' WHERE demand_id=? AND capability='apply_contribution'", (old,))
                item = reconcile_lineage(self.queue, self.engine, self.rows(old))[0]
                self.assertEqual(item['status'], 'queued')
                self.assertFalse(item['lineage_verified']); self.assertTrue(item['lineage_issue'])
                self.assertIsNone(item['superseded_by'])

    def test_legacy_projection_does_not_overwrite_cancelled_original(self):
        old, _, _, _ = self.legacy_recovery(); self.engine.q.cancel(old)
        item = reconcile_lineage(self.queue, self.engine, self.rows(old))[0]
        self.assertEqual(item['status'], 'cancelled'); self.assertEqual(item['raw_status'], 'cancelled')
        self.assertFalse(item['lineage_verified']); self.assertTrue(item['lineage_issue'])

    def test_recovery_of_alone_is_not_proof_and_projection_creates_no_tables(self):
        old, job = self.expired()
        with self.engine.q.connect() as c:
            payload = json.loads(c.execute('SELECT payload FROM demands WHERE id=?', (old,)).fetchone()[0])
        source = self.store.read(payload['source_ref']['record_id'])
        self.engine.start('recuperar-' + job['id'].replace('-', ''), 'contribution',
            {'text': source['payload']['content'], 'source_ref': payload['source_ref'], 'recovery_of': old})
        with self.queue.connect() as c:before = list(c.iterdump())
        item = reconcile_lineage(self.queue, self.engine, self.rows(old))[0]
        self.assertEqual(item['status'], 'queued'); self.assertFalse(item['lineage_verified'])
        self.assertIsNone(item['superseded_by']); self.assertFalse(item['runnable'])
        with self.queue.connect() as c:self.assertEqual(list(c.iterdump()), before)


if __name__=='__main__':
    unittest.main(verbosity=2)
