"""Regressões operacionais em cofres descartáveis; sem IA, rede ou estado pessoal."""
import json
import shutil
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from autonomia import Queue, DEFAULTS, atomic_json, code_hash
from nucleo import Store, REAL_SYSTEM, Invalid


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.store = Store(self.base/'sistema', self.base/'cofre')
        self.q = Queue(self.store)
        atomic_json(self.q.config_path, dict(DEFAULTS, enabled=True,
                    content_access='permitido', approved_code=code_hash()))

    def complete_audit(self):
        job = self.q.enqueue('original', 'audit_vault')
        claimed = self.q.claim('fixture')
        self.assertEqual(claimed['id'], job['id'])
        self.q.finish(job['id'], claimed['token'], {'status': 'ok'})
        return job

    def test_completion_reserves_continuation_in_same_commit(self):
        parent = self.complete_audit()
        self.assertEqual(self.q.summary()['pending_continuations'], 1)
        reopened = Queue(self.store)
        delivered = reopened.dispatch_continuations()
        self.assertEqual(len(delivered), 1)
        child = reopened.get(delivered[0])
        self.assertEqual(child['kind'], 'refresh_view')
        self.assertEqual(child['request_key'], 'view-after-'+parent['id'])
        self.assertEqual(reopened.dispatch_continuations(), [])
        self.assertEqual(reopened.summary()['pending_continuations'], 0)

    def test_full_queue_does_not_lose_or_unconfirm_continuation(self):
        cfg = self.q.config()
        cfg['max_pending_jobs'] = 1
        atomic_json(self.q.config_path, cfg)
        parent = self.complete_audit()
        filler = self.q.enqueue('filler', 'refresh_view')
        self.assertEqual(self.q.dispatch_continuations(), [])
        self.assertEqual(self.q.get(parent['id'])['execution_status'], 'completed')
        self.assertEqual(self.q.summary()['pending_continuations'], 1)
        self.q.cancel(filler['id'])
        self.assertEqual(len(self.q.dispatch_continuations()), 1)
        self.assertEqual(self.q.summary()['pending_continuations'], 0)

    def test_lost_enqueue_acknowledgement_does_not_duplicate_child(self):
        self.complete_audit()
        original = self.q.enqueue
        def lose_reply(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('confirmação fictícia perdida após enfileirar')
        with patch.object(self.q, 'enqueue', side_effect=lose_reply):
            self.assertEqual(self.q.dispatch_continuations(), [])
        reopened = Queue(self.store)
        self.assertEqual(len(reopened.dispatch_continuations()), 1)
        with reopened.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM executions WHERE kind='refresh_view'").fetchone()[0], 1)

    def test_two_dispatchers_publish_one_child(self):
        self.complete_audit()
        barrier = threading.Barrier(2)
        failures = []
        def dispatch():
            try:
                barrier.wait(timeout=5)
                Queue(self.store).dispatch_continuations()
            except Exception as error:
                failures.append(error)
        threads = [threading.Thread(target=dispatch) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        with self.q.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM executions WHERE kind='refresh_view'").fetchone()[0], 1)

    def test_repeated_cancel_stays_cancelling_until_owner_finishes(self):
        self.q.enqueue('cancel', 'audit_vault')
        job = self.q.claim('fixture')
        self.assertEqual(self.q.cancel(job['id'])['execution_status'], 'cancelling')
        self.assertEqual(self.q.cancel(job['id'])['execution_status'], 'cancelling')
        self.assertEqual(self.q.finish(job['id'], job['token'], {})['execution_status'], 'cancelled')
        self.assertEqual(self.q.summary()['pending_continuations'], 0)

    def test_failed_attempt_does_not_reserve_continuation(self):
        self.q.enqueue('failure', 'audit_vault')
        job = self.q.claim('fixture')
        self.q.finish(job['id'], job['token'], error='falha fictícia')
        self.assertEqual(self.q.summary()['pending_continuations'], 0)

    def test_maintenance_blocks_new_work_even_if_enabled(self):
        (self.q.state/'implantacao.lock').write_text('fixture', encoding='ascii')
        with self.assertRaises(Invalid):
            self.q.enqueue('blocked', 'audit_vault')
        with self.assertRaises(Invalid):
            self.q.dispatch_continuations()

    def test_dispatch_budget_requires_bounded_integer(self):
        for value in (True, 0, 101, '1'):
            with self.subTest(value=value), self.assertRaises(Invalid):
                self.q.dispatch_continuations(value)

    def test_worker_health_does_not_treat_old_heartbeat_as_running(self):
        from autonomia import worker_health
        path=self.q.state/'worker.json'
        atomic_json(path,{'status':'running','updated_at':'2000-01-01T00:00:00+00:00'})
        health=worker_health(path,now=946684900)
        self.assertEqual(health['reported_status'],'running')
        self.assertEqual(health['health'],'stale')
        self.assertEqual(health['heartbeat_age_seconds'],100.0)
        atomic_json(path,{'status':'running','updated_at':'não é uma data'})
        self.assertEqual(worker_health(path)['health'],'stale')

    def test_bridge_classifies_expired_history_without_enabling_queue(self):
        from coordenador import Coordinator
        from types import SimpleNamespace
        import ponte_pessoal as bridge
        coordinator=Coordinator(self.store.root/'estado'/'coordenacao')
        ident=coordinator.submit('expired',[{'id':'retrieve','capability':'retrieve','version':'v1','depends_on':[]}],
            {'kind':'question'},{'max_actions':1,'max_model_calls':0,'max_seconds':1})
        with coordinator.connect() as c:
            c.execute('UPDATE demands SET deadline=0 WHERE id=?',(ident,))
        cfg=self.q.config();cfg['enabled']=False;atomic_json(self.q.config_path,cfg)
        with patch.object(bridge,'store',self.store),patch.object(bridge,'authorized',return_value=True):
            row=bridge._project_demands(SimpleNamespace(q=coordinator),[{'id':ident,'status':'queued'}])[0]
        self.assertEqual(row['status'],'queued')
        self.assertEqual(row['operational_status'],'expired_needs_review')
        self.assertFalse(row['runnable'])
        self.assertFalse(self.q.config()['enabled'])

    def test_consistent_fixture_restore_preserves_history_and_tombstones(self):
        first = self.store.apply('source', 'create', title='Relato fictício', text='Versão fictícia inicial.')
        removed = self.store.apply('removed', 'create', title='Descartável fictício', text='Apagar somente na fixture.')
        self.store.apply('correct', 'correct', ident=first['id'], expected=1,
                         text='Versão fictícia corrigida.', reason='Retificação de teste')
        self.store.delete('delete', removed['id'], 1)
        restored_root, restored_vault = self.base/'restaurado', self.base/'cofre-restaurado'
        shutil.copytree(self.store.vault, restored_vault)
        shutil.copytree(self.store.hist, restored_root/'estado'/'revisoes')
        target = restored_root/'estado'/'controle.sqlite3'
        with closing(sqlite3.connect(self.store.db)) as source, closing(sqlite3.connect(target)) as destination:
            source.backup(destination)
        restored = Store(restored_root, restored_vault)
        record = restored.read(first['id'])
        self.assertEqual(record['revision'], 2)
        self.assertEqual(record['payload']['content'], 'Versão fictícia corrigida.')
        self.assertTrue((restored.hist/first['id']/'1.md').is_file())
        with self.assertRaises(Invalid):
            restored.read(removed['id'])
        with self.assertRaises(Invalid):
            restored.apply('removed', 'create', title='Descartável fictício', text='Apagar somente na fixture.')


if __name__ == '__main__':
    unittest.main(verbosity=2)
