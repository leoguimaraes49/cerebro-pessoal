"""Confirmação perdida, alterações de limites e migração de intenções legadas."""
import json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from autonomia import Queue,DEFAULTS,atomic_json,code_hash
from nucleo import REAL_SYSTEM,Store


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name);self.s=Store(base/'sistema',base/'cofre');self.q=Queue(self.s)
        self.cfg=dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash(),job_timeout_seconds=120)
        atomic_json(self.q.config_path,self.cfg)
        parent=self.q.enqueue('audit','audit_vault');claimed=self.q.claim('fixture')
        self.q.finish(parent['id'],claimed['token'],{'status':'ok'});self.parent=parent

    def lose_ack(self):
        original=self.q.enqueue
        def lost(*a,**kw):original(*a,**kw);raise OSError('confirmação perdida fictícia')
        with patch.object(self.q,'enqueue',side_effect=lost):self.q.dispatch_continuations()

    def test_ack_loss_and_config_changes_reconcile_without_renewing_limits(self):
        self.lose_ack()
        with self.q.connect() as c:before=dict(c.execute("SELECT * FROM executions WHERE kind='refresh_view'").fetchone())
        self.cfg.update(max_attempts=5,job_timeout_seconds=250,job_lifetime_seconds=900)
        atomic_json(self.q.config_path,self.cfg)
        reopened=Queue(self.s);self.assertEqual(reopened.dispatch_continuations(),[before['id']])
        self.assertEqual(reopened.summary()['pending_continuations'],0)
        with self.q.connect() as c:
            after=dict(c.execute('SELECT * FROM executions WHERE id=?',(before['id'],)).fetchone())
            self.assertEqual(c.execute("SELECT COUNT(*) FROM executions WHERE kind='refresh_view'").fetchone()[0],1)
        self.assertEqual(before,after)

    def test_config_change_before_first_dispatch_preserves_reserved_contract(self):
        self.cfg.update(job_timeout_seconds=250,job_lifetime_seconds=900)
        atomic_json(self.q.config_path,self.cfg)
        ident=self.q.dispatch_continuations()[0];job=self.q.get(ident)
        self.assertEqual(job['timeout'],120);self.assertEqual(job['deadline']-job['created'],600)

    def test_legacy_lost_ack_child_is_recognized_after_config_change(self):
        self.lose_ack()
        with self.q.connect() as c:c.execute('DELETE FROM continuation_contracts')
        self.cfg['max_attempts']=5;atomic_json(self.q.config_path,self.cfg)
        self.assertEqual(len(Queue(self.s).dispatch_continuations()),1)
        self.assertEqual(self.q.summary()['pending_continuations'],0)

    def test_legacy_intention_without_child_freezes_once(self):
        with self.q.connect() as c:c.execute('DELETE FROM continuation_contracts')
        self.assertEqual(len(self.q.dispatch_continuations()),1)
        with self.q.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM continuation_contracts').fetchone()[0],1)

    def test_tampered_contract_does_not_enqueue_child(self):
        with self.q.connect() as c:c.execute("UPDATE continuation_contracts SET contract='{}'")
        self.assertEqual(self.q.dispatch_continuations(),[])
        self.assertEqual(self.q.summary()['pending_continuations'],1)
        with self.q.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM executions WHERE kind='refresh_view'").fetchone()[0],0)

    def test_unrelated_child_cannot_satisfy_legacy_continuation(self):
        with self.q.connect() as c:c.execute('DELETE FROM continuation_contracts')
        self.q.enqueue('view-after-'+self.parent['id'],'refresh_view',payload={'unrelated':True})
        self.assertEqual(self.q.dispatch_continuations(),[])
        self.assertEqual(self.q.summary()['pending_continuations'],1)

    def test_concurrent_dispatch_after_config_change_keeps_single_child(self):
        self.lose_ack();self.cfg['job_lifetime_seconds']=900;atomic_json(self.q.config_path,self.cfg)
        errors=[]
        def run():
            try:Queue(self.s).dispatch_continuations()
            except Exception as error:errors.append(error)
        threads=[threading.Thread(target=run) for _ in range(3)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(10)
        self.assertFalse(errors);self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(self.q.summary()['pending_continuations'],0)
        with self.q.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM executions WHERE kind='refresh_view'").fetchone()[0],1)


if __name__=='__main__':unittest.main(verbosity=2)
