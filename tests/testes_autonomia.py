import json
import tempfile
import threading
import time
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from nucleo import Store, REAL_SYSTEM, Invalid, Conflict,exclusive
from autonomia import Queue,DEFAULTS,code_hash,atomic_json,perform,run_one

class AutonomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios')
        base=Path(self.tmp.name);self.q=Queue(Store(base/'sistema',base/'cofre'))
        cfg=dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash(),retry_base_seconds=1)
        atomic_json(self.q.config_path,cfg)
    def tearDown(self):self.tmp.cleanup()
    def test_default_denied_and_unknown_handler(self):
        cfg=self.q.config();cfg['enabled']=False;atomic_json(self.q.config_path,cfg)
        with self.assertRaises(Invalid):self.q.enqueue('x','audit_vault')
        cfg['enabled']=True;atomic_json(self.q.config_path,cfg)
        with self.assertRaises(Invalid):self.q.enqueue('x','executar_prompt_arbitrario')
    def test_queue_survives_restart_and_key_does_not_duplicate(self):
        a=self.q.enqueue('same','audit_vault');q2=Queue(self.q.sources)
        self.assertEqual(q2.enqueue('same','audit_vault')['id'],a['id'])
        with self.assertRaises(Conflict):q2.enqueue('same','refresh_view')
    def test_two_claimants_single_owner(self):
        self.q.enqueue('a','audit_vault');barrier=threading.Barrier(2);results=[]
        def run(owner):barrier.wait();results.append(self.q.claim(owner))
        ts=[threading.Thread(target=run,args=(str(i),)) for i in range(2)]
        for t in ts:t.start()
        for t in ts:t.join()
        self.assertEqual(sum(x is not None for x in results),1)
    def test_expired_owner_cannot_complete_and_recovery_is_bounded(self):
        self.q.enqueue('a','audit_vault',now=1000);a=self.q.claim('dead',now=1001)
        b=self.q.claim('new',now=a['lease_until']+1)
        self.assertEqual(b['id'],a['id']);self.assertEqual(b['attempts'],2)
        with self.assertRaises(Conflict):self.q.finish(a['id'],a['token'],{},now=a['lease_until']+2)
        self.q.claim('third',now=b['lease_until']+1)
        c=self.q.get(a['id']);self.q.claim('fourth',now=c['lease_until']+1)
        self.assertEqual(self.q.get(a['id'])['execution_status'],'failed')
    def test_cancellation_terminal_does_not_resurrect(self):
        a=self.q.enqueue('a','audit_vault');self.q.cancel(a['id'])
        self.assertIsNone(self.q.claim('x'))
        self.assertEqual(self.q.enqueue('a','audit_vault')['execution_status'],'cancelled')
    def test_running_cancel_has_distinct_effect(self):
        self.q.enqueue('a','audit_vault');a=self.q.claim('x');self.q.cancel(a['id'])
        self.assertEqual(self.q.get(a['id'])['execution_status'],'cancelling')
        r=self.q.finish(a['id'],a['token'],{'ignored':True})
        self.assertEqual(r['execution_status'],'cancelled');self.assertIsNone(r['result'])
    def test_revocation_blocks_read_and_completion(self):
        a=self.q.enqueue('a','audit_vault');job=self.q.claim('x')
        cfg=self.q.config();cfg['content_access']='bloqueado';atomic_json(self.q.config_path,cfg)
        with self.assertRaises(Invalid):self.q.snapshot()
        with self.assertRaises(Invalid):self.q.finish(job['id'],job['token'],{})
        self.q.cancel(a['id'])
    def test_rate_and_deadline_limits(self):
        cfg=self.q.config();cfg['max_jobs_per_hour']=1;atomic_json(self.q.config_path,cfg)
        a=self.q.enqueue('a','audit_vault',now=1000);b=self.q.enqueue('b','audit_vault',now=1000.1)
        job=self.q.claim('x',now=1001);self.q.finish(job['id'],job['token'],{},now=1002)
        self.assertIsNone(self.q.claim('x',now=1003))
        self.q.claim('x',now=5000)
        self.assertEqual(self.q.get(b['id'])['execution_status'],'failed')
    def test_new_note_schedules_once_and_view_does_not_trigger_loop(self):
        a=self.q.schedule_changes();self.assertIsNone(self.q.schedule_changes())
        self.q.sources.apply('f','create',title='Fonte fictícia',text='Dados fictícios')
        b=self.q.schedule_changes();self.assertNotEqual(a['id'],b['id'])
        self.q.publish_view();self.assertIsNone(self.q.schedule_changes())
    def test_code_change_blocks_content_jobs(self):
        cfg=self.q.config();cfg['approved_code']='old';atomic_json(self.q.config_path,cfg)
        with self.assertRaises(Invalid):self.q.enqueue('a','audit_vault')
    def test_selftests_do_not_launch_parallel_suites(self):
        from autoteste import run_tests
        lock=self.q.state/'autoteste.lock'
        with exclusive(lock,create=True),patch('autoteste.REAL_SYSTEM',self.q.root):
            self.assertEqual(run_tests()['status'],'running')
    def test_scan_budget_and_derived_view_conflict(self):
        self.q.publish_view();path=self.q.vault/'80_Visoes'/'Manutenção automática.md'
        path.write_text('Edição fictícia',encoding='utf-8')
        with self.assertRaises(Conflict):self.q.publish_view()
        (self.q.vault/'30_Fontes'/'Grande.md').write_text('x'*50,encoding='utf-8')
        cfg=self.q.config();cfg['max_file_bytes']=10;atomic_json(self.q.config_path,cfg)
        with self.assertRaises(Invalid):self.q.snapshot()
    def test_pending_queue_limit_and_backoff(self):
        cfg=self.q.config();cfg['max_pending_jobs']=1;atomic_json(self.q.config_path,cfg)
        self.q.enqueue('a','audit_vault',now=1000)
        with self.assertRaises(Invalid):self.q.enqueue('b','audit_vault',now=1000)
        job=self.q.claim('a',now=1001);self.q.finish(job['id'],job['token'],error='falha fictícia',now=1002)
        self.assertIsNone(self.q.claim('b',now=1002.1))
        self.assertIsNotNone(self.q.claim('b',now=1003.1))
    def test_subprocess_audit_confirms_real_effects_in_fixture(self):
        self.q.sources.apply('f','create',title='Fonte fictícia',text='Relato fictício')
        self.q.enqueue('a','audit_vault');result=run_one(self.q)
        self.assertEqual(result['execution_status'],'completed')
        self.assertEqual(json.loads(result['result'])['audit']['records'],1)
        result=run_one(self.q)
        self.assertEqual(result['execution_status'],'completed')
        self.assertTrue((self.q.vault/'80_Visoes'/'Manutenção automática.md').exists())
    def test_daemon_observes_change_and_stops_cooperatively(self):
        cfg=self.q.config();cfg['interval_seconds']=5;atomic_json(self.q.config_path,cfg)
        process=subprocess.Popen([sys.executable,str(REAL_SYSTEM/'src'/'autonomia.py'),'serve','--root',str(self.q.root),'--vault',str(self.q.vault)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                if self.q.summary()['counts'].get('completed',0)>=2:break
                time.sleep(0.2)
            self.assertGreaterEqual(self.q.summary()['counts'].get('completed',0),2)
            cfg=self.q.config();cfg['enabled']=False;atomic_json(self.q.config_path,cfg)
            process.communicate(timeout=10)
            self.assertEqual(process.returncode,0)
            worker=json.loads((self.q.state/'worker.json').read_text(encoding='utf-8'))
            self.assertEqual(worker['status'],'stopped')
        finally:
            if process.poll() is None:process.kill();process.communicate()

if __name__=='__main__':unittest.main(verbosity=2)
