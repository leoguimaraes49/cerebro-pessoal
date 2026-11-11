import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from nucleo import REAL_SYSTEM,Invalid,Conflict
from provedores import TextModel,parse_json


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');self.root=Path(self.tmp.name)
        self.executable=self.root/'client.exe';self.executable.write_bytes(b'ficticio')
        self.cfg={'enabled':True,'executable':str(self.executable),'model':'gpt-6.1-terra'}
    def tearDown(self):self.tmp.cleanup()
    def child(self,events,seen):
        class Child:
            returncode=0
            pid=0
            def __init__(child,args,**kwargs):
                seen.append((args,kwargs))
                for event in events:kwargs['stdout'].write((json.dumps(event)+'\n').encode())
                kwargs['stdout'].flush()
            def communicate(child,*args,**kwargs):return (None,None)
            def poll(child):return 0
        return Child
    def test_completed_call_is_cached_and_usage_is_recorded(self):
        seen=[];events=[{'type':'item.completed','item':{'type':'agent_message','text':'{"ok":true}'}},
                        {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}]
        with patch('provedores.subprocess.Popen',self.child(events,seen)):
            model=TextModel(self.root/'state',self.cfg,1)
            self.assertEqual(model.call('prompt fictício'),{'ok':True})
            self.assertEqual(model.call('prompt fictício'),{'ok':True});self.assertEqual(len(seen),1)
            self.assertEqual(model.summary()['usage']['input_tokens'],10)
            with self.assertRaises(Invalid):model.call('outra chamada')
    def test_failed_call_is_not_retried_automatically(self):
        seen=[]
        with patch('provedores.subprocess.Popen',self.child([],seen)):
            model=TextModel(self.root/'state',self.cfg,3)
            with self.assertRaises(Invalid):model.call('prompt')
            with self.assertRaises(Conflict):model.call('prompt')
        self.assertEqual(len(seen),1)
    def test_untrusted_tool_call_is_rejected(self):
        seen=[];events=[{'type':'item.completed','item':{'type':'command_execution'}},{'type':'turn.completed'}]
        with patch('provedores.subprocess.Popen',self.child(events,seen)):
            with self.assertRaises(Invalid):TextModel(self.root/'state',self.cfg,1).call('prompt')
    def test_no_paid_key_or_user_plugins_are_forwarded(self):
        seen=[];events=[{'type':'item.completed','item':{'type':'agent_message','text':'{}'}},{'type':'turn.completed'}]
        with patch.dict('os.environ',{'OPENAI_API_KEY':'ficticio'}),patch('provedores.subprocess.Popen',self.child(events,seen)):
            TextModel(self.root/'state',self.cfg,1).call('prompt')
        args,kwargs=seen[0];self.assertNotIn('OPENAI_API_KEY',kwargs['env']);self.assertIn('--ignore-user-config',args)
        self.assertIn('multi_agent',args);self.assertIn('web_search="disabled"',args)
    def test_disabled_provider_does_not_spawn_a_process(self):
        with patch('provedores.subprocess.Popen') as spawn:
            with self.assertRaises(Invalid):TextModel(self.root/'state',dict(self.cfg,enabled=False),1).call('prompt')
            spawn.assert_not_called()
    def test_duplicate_or_non_json_fields_are_rejected(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}'):
            with self.assertRaises(Invalid):parse_json(value)


if __name__=='__main__':unittest.main(verbosity=2)
