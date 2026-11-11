"""Regressões isoladas: AST dos módulos, armazenamento em memória e arquivos só em temporários.

Executar diretamente com Python -I -B. Não importa Store, Engine, provedores ou estado real.
"""
import ast,copy,hashlib,json,os,sys,tempfile,types,unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch


class Invalid(Exception):pass
class Conflict(Exception):pass


def canon(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def sha(value):return hashlib.sha256(value).hexdigest()


DEFAULT={'enabled':False,'model':{'enabled':False},'embeddings':{'enabled':False},
         'max_actions':32,'max_model_calls':3,'max_seconds':600,'auto_process_sources':False,
         'auto_adopt_config':False,'message_codec':'compact','retrieval_policy':'hybrid'}
PROJECT=Path(__file__).resolve().parent.parent/'src'


def isolated_module(name,dependencies):
    path=PROJECT/(name+'.py');tree=ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
    blocked={'nucleo','conhecimento','autonomia','documentos','melhorias'}
    tree.body=[node for node in tree.body if not (isinstance(node,ast.ImportFrom) and node.module in blocked)]
    module=types.ModuleType('isolated_'+name);module.__file__=str(path);module.__dict__.update(dependencies)
    exec(compile(tree,str(path),'exec'),module.__dict__)
    return module


class MemorySources:
    def __init__(self,env):
        self.env=env;self.root=env.root;self.records={};self.operations={};self.calls=[]
    def read(self,ident):return copy.deepcopy(self.records[ident])
    def apply(self,key,kind,title='',text='',source_metadata=None):
        self.env.hit('source','before')
        if self.env.before_source:self.env.before_source()
        request={'kind':kind,'title':title,'text':text,'id':'','expected':0,'reason':''}
        if source_metadata is not None:request['source_metadata']=copy.deepcopy(source_metadata)
        fingerprint=sha(canon(request).encode());self.calls.append((key,copy.deepcopy(request)))
        if key in self.operations:
            prior,result=self.operations[key]
            if fingerprint!=prior:raise Conflict('pedido de fonte mudou')
        else:
            ident='source-'+str(len(self.records)+1);payload={'source_kind':'conversation','content':text}
            payload.update(copy.deepcopy(source_metadata or {}))
            self.records[ident]={'id':ident,'record_type':'source','revision':1,'title':title.strip(),'payload':payload}
            result={'status':'confirmed','id':ident,'revision':1};self.operations[key]=(fingerprint,result)
        self.env.hit('source','after')
        return copy.deepcopy(result)


class MemoryKnowledge:
    def __init__(self,env):self.env=env;self.records={};self.operations={};self.invalid=set()
    def read(self,ident):
        if any(op['state']=='proposed' for op in self.operations.values()):raise Conflict('efeito pendente no conhecimento')
        if ident in self.invalid:return {'validity':'needs_revalidation','record':None}
        return {'validity':'current_within_scope','record':copy.deepcopy(self.records[ident])}
    def apply(self,key,kind,title,payload,ident=None,expected=None):
        status=payload.get('adoption_status')
        label='adopt-candidate' if status=='adopted' else 'rollback-candidate' if status=='rolled_back' else 'research-record' if kind=='research_run' else 'record-candidate'
        self.env.hit(label,'before')
        request={'kind':kind,'title':title,'payload':copy.deepcopy(payload),'id':ident,'expected':expected}
        fingerprint=sha(canon(request).encode())
        if key in self.operations:
            op=self.operations[key]
            if op['fingerprint']!=fingerprint:raise Conflict('pedido de conhecimento mudou')
            if op['state']=='proposed':
                if canon(self.records[op['record']['id']])!=canon(op['record']):raise Conflict('efeito pendente divergente')
                op['state']='confirmed'
        else:
            if ident:
                old=self.records[ident]
                if old['record_type']!=kind or type(expected) is not int or old['revision']!=expected:raise Conflict('revisão concorrente')
                revision=expected+1
            else:ident='knowledge-'+str(len(self.records)+1);revision=1
            record={'id':ident,'record_type':kind,'revision':revision,'title':title,'payload':copy.deepcopy(payload)}
            result={'status':'confirmed','id':ident,'revision':revision}
            op={'fingerprint':fingerprint,'state':'proposed','record':copy.deepcopy(record),'result':result,'label':label}
            self.operations[key]=op;self.records[ident]=record
            self.env.hit(label,'pending');op['state']='confirmed'
        self.env.hit(label,'after')
        return copy.deepcopy(op['result'])


class Fixture:
    before_source: Callable[[],None] | None

    def __enter__(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='cerebro-seguranca-isolada-');self.base=Path(self.tmp.name).resolve()
        self.root=self.base/'sistema';self.root.mkdir();self.clock='2030-01-01T00:00:00+00:00'
        self.failure=None;self.before_source=None;self.network_calls=[]
        self.sources=MemorySources(self);self.k=MemoryKnowledge(self)
        self.initial=copy.deepcopy(DEFAULT);self.initial.update(enabled=True,auto_adopt_config=True,message_codec='pretty')
        self.set_config(self.initial)
        fake_exec=types.ModuleType('execucao');fake_exec.__dict__['DEFAULT']=copy.deepcopy(DEFAULT)
        self.import_guard=patch.dict(sys.modules,{'execucao':fake_exec});self.import_guard.start()
        self.network_guard=patch('urllib.request.build_opener',side_effect=AssertionError('rede real proibida'));self.network_guard.start()
        dependencies={'Invalid':Invalid,'Conflict':Conflict,'canon':canon,'sha':sha,'NOW':lambda:self.clock,
                      'Knowledge':lambda sources:self.k,'atomic_json':self.atomic_json}
        self.m=isolated_module('melhorias',dependencies)
        documents=isolated_module('documentos',dependencies)
        research_dependencies=dict(dependencies,validate_metadata=documents.validate_metadata)
        research_dependencies.update({name:getattr(self.m,name) for name in ('_validate_key','_safe_path','_state_lock','_read_json')})
        self.p=isolated_module('pesquisa',research_dependencies)
        release=self.m._release
        def checked_release(*args):
            self.hit('release','before');release(*args);self.hit('release','after')
        self.m.__dict__['_release']=checked_release
        return self
    def __exit__(self,*args):
        self.network_guard.stop();self.import_guard.stop();self.tmp.cleanup()
    def set_config(self,value):(self.root/'execucao.json').write_text(canon(value),encoding='utf-8')
    def config(self):return json.loads((self.root/'execucao.json').read_text(encoding='utf-8'))
    def journal(self,key='adopt'):return self.root/'estado'/'adocoes'/(key+'.json')
    def request_path(self,key='search'):return self.root/'estado'/'pesquisas'/(sha(key.encode())+'.request.json')
    def arm(self,label,when,occurrence=1):self.failure=[label,when,occurrence]
    def hit(self,label,when):
        if self.failure and self.failure[:2]==[label,when]:
            self.failure[2]-=1
            if not self.failure[2]:self.failure=None;raise OSError('interrupção fictícia: '+label+'/'+when)
    def atomic_json(self,path,value):
        path=Path(path)
        if not path.resolve().is_relative_to(self.base):raise AssertionError('escrita fora do temporário isolado')
        if path.name=='execucao.json':label='config'
        elif path.name=='adocoes-intent.json':label='owner'
        elif path.name.endswith('.request.json'):label='research-'+value['phase']
        elif 'phase' in value:label=value['phase']
        elif path.parent.name=='pesquisas':label='research-cache'
        else:label='evaluation'
        self.hit(label,'before');path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(path.name+'.fixture-tmp')
        with tmp.open('w',encoding='utf-8') as stream:
            stream.write(json.dumps(value,ensure_ascii=False));stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path);self.hit(label,'after')
    def candidate(self,key='candidate',value='compact'):
        evaluation=self.m.evaluate(self.sources,'eval-'+key,{'kind':'message_codec','value':value,'reason':'Fixture determinística'})
        return self.m.record(self.sources,'record-'+key,evaluation)['candidate_record']['id']
    def transport(self,url):
        self.network_calls.append(url)
        return {'message':{'items':[
            {'DOI':'10.1234/fixture-one','title':['Artigo inteiramente fictício'],'abstract':'Resumo fictício, sem conclusão clínica.',
             'published':{'date-parts':[[2025]]},'author':[{'given':'Autor','family':'Fictício'}]},
            {'DOI':'10.1234/fixture-two','title':['Outro artigo fictício']}]}}
    def research(self,**kwargs):return self.p.research(self.sources,'search',['learning'],transport=self.transport,**kwargs)


class ImprovementSecurityTests(unittest.TestCase):
    def test_bad_keys_are_rejected_by_all_entry_points(self):
        with Fixture() as env:
            ident=env.candidate();outside=env.base/'sentinel.json';outside.write_text('unchanged',encoding='utf-8')
            keys=('../sentinel','..\\sentinel','../../../sentinel','C:\\sentinel','a/b','a\\b','',None,True,'a'*81,str(outside.with_suffix('')))
            for key in keys:
                for operation,args in ((env.m.evaluate,(env.sources,key,{'kind':'message_codec','value':'compact'})),
                                       (env.m.adopt,(env.sources,key,ident)),(env.m.rollback,(env.sources,key))):
                    with self.subTest(key=key,operation=operation.__name__):self.assertRaises(Invalid,operation,*args)
            self.assertEqual(outside.read_text(encoding='utf-8'),'unchanged');self.assertEqual(env.config(),env.initial)

    def test_reparse_parent_is_rejected_even_if_it_resolves_inside_root(self):
        with Fixture() as env:
            ident=env.candidate();bad=env.root/'estado';original=Path.lstat
            def reparse(path,*args,**kwargs):
                info=original(path,*args,**kwargs)
                return types.SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if path==bad else info
            with patch.object(Path,'lstat',reparse):
                self.assertRaises(Invalid,env.m.evaluate,env.sources,'again',{'kind':'message_codec','value':'compact'})
                self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)
                self.assertRaises(Invalid,env.m.rollback,env.sources,'adopt')
            self.assertEqual(env.config(),env.initial)

    def test_directory_symlink_is_rejected(self):
        with Fixture() as env:
            ident=env.candidate();outside=env.base/'outside';outside.mkdir();link=env.root/'estado'/'adocoes'
            try:link.symlink_to(outside,target_is_directory=True)
            except (OSError,NotImplementedError):self.skipTest('criação de symlink indisponível; reparse simulado é testado separadamente')
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)
            self.assertRaises(Invalid,env.m.rollback,env.sources,'adopt');self.assertEqual(list(outside.iterdir()),[])

    def test_configuration_and_evaluation_symlinks_are_rejected(self):
        with Fixture() as env:
            ident=env.candidate();outside=env.base/'outside.json';outside.write_text(canon(env.initial),encoding='utf-8')
            config=env.root/'execucao.json';config.unlink()
            try:config.symlink_to(outside)
            except (OSError,NotImplementedError):self.skipTest('symlink indisponível')
            self.assertRaises(Invalid,env.m.evaluate,env.sources,'again',{'kind':'message_codec','value':'compact'})
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)
            config.unlink();env.set_config(env.initial)
            evaluation=env.root/'estado'/'melhorias'/'linked.json';evaluation.symlink_to(outside)
            self.assertRaises(Invalid,env.m.evaluate,env.sources,'linked',{'kind':'message_codec','value':'compact'})
            self.assertEqual(json.loads(outside.read_text(encoding='utf-8')),env.initial)

    def test_journal_symlink_is_rejected_for_adoption_and_rollback(self):
        with Fixture() as env:
            ident=env.candidate();outside=env.base/'outside.json';outside.write_text('{}',encoding='utf-8')
            link=env.journal();link.parent.mkdir(exist_ok=True)
            try:link.symlink_to(outside)
            except (OSError,NotImplementedError):self.skipTest('symlink indisponível')
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)
            self.assertRaises(Invalid,env.m.rollback,env.sources,'adopt');self.assertEqual(outside.read_text(encoding='utf-8'),'{}')

    def test_evaluation_key_keeps_original_inputs_and_timestamp(self):
        with Fixture() as env:
            candidate={'kind':'message_codec','value':'compact'}
            first=env.m.evaluate(env.sources,'stable',candidate);env.clock='2030-01-08T00:00:00+00:00'
            self.assertEqual(env.m.evaluate(env.sources,'stable',candidate),first)
            self.assertRaises(Conflict,env.m.evaluate,env.sources,'stable',dict(candidate,reason='Outra entrada'))
            changed=env.config();changed['max_actions']=24;env.set_config(changed)
            self.assertRaises(Conflict,env.m.evaluate,env.sources,'stable',candidate)
            self.assertRaises(Invalid,env.m.evaluate,env.sources,'nonfinite',dict(candidate,reason=float('nan')))

    def test_fabricated_evaluation_is_rejected_before_recording_sources(self):
        with Fixture() as env:
            evaluation=env.m.evaluate(env.sources,'eval',{'kind':'message_codec','value':'compact'})
            evaluation['candidate']['value']='invalid-codec';count=len(env.sources.operations)
            self.assertRaises((Invalid,Conflict),env.m.record,env.sources,'forged',evaluation)
            self.assertEqual(len(env.sources.operations),count)

    def test_generic_candidate_write_cannot_self_assert_eligibility(self):
        mutations=(lambda p:p['comparison']['candidate'].update(value='invalid-codec'),
                   lambda p:p['comparison']['checks'].update(roundtrip_equal=False),
                   lambda p:p['comparison']['comparison'].update(selected_chars=1))
        for mutate in mutations:
            with self.subTest(mutation=mutate),Fixture() as env:
                ident=env.candidate();mutate(env.k.records[ident]['payload'])
                self.assertRaises((Invalid,Conflict),env.m.adopt,env.sources,'adopt',ident)
                self.assertEqual(env.config(),env.initial)
        with Fixture() as env:
            current=env.config();current['message_codec']='compact';env.set_config(current)
            ident=env.candidate();payload=env.k.records[ident]['payload'];payload['adoption_status']='tested';payload['comparison']['eligible']=True
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident);self.assertEqual(env.config(),current)

    def test_changed_configuration_and_invalid_permission_types_are_rejected(self):
        with Fixture() as env:
            ident=env.candidate();current=env.config();current['max_actions']=24;env.set_config(current)
            self.assertRaises(Conflict,env.m.adopt,env.sources,'adopt',ident);self.assertEqual(env.config(),current)
            current['auto_adopt_config']='true';env.set_config(current)
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)

    def test_journal_cannot_expand_permissions_even_with_recomputed_hash(self):
        with Fixture() as env:
            ident=env.candidate();env.arm('adopt_intent','after');self.assertRaises(OSError,env.m.adopt,env.sources,'adopt',ident)
            state=json.loads(env.journal().read_text(encoding='utf-8'));state['after']['model']['enabled']=True
            state['intent_hash']=sha(canon(env.m._intent(state)).encode());env.journal().write_text(canon(state),encoding='utf-8')
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident);self.assertEqual(env.config(),env.initial)

    def test_adoption_resumes_at_every_effect_boundary(self):
        labels=('adopt_intent','owner','config','adopt_config','adopt-candidate','adopt_candidate','adopted','release')
        points=[(label,when) for label in labels for when in ('before','after')]+[('adopt-candidate','pending')]
        for label,when in points:
            with self.subTest(label=label,when=when),Fixture() as env:
                ident=env.candidate();env.arm(label,when)
                self.assertRaises(OSError,env.m.adopt,env.sources,'adopt',ident);env.clock='2030-01-02T00:00:00+00:00'
                result=env.m.adopt(env.sources,'adopt',ident)
                self.assertEqual(result['status'],'adopted');self.assertEqual(env.k.read(ident)['record']['revision'],2)
                expected=copy.deepcopy(env.initial);expected['message_codec']='compact';self.assertEqual(env.config(),expected)
                self.assertEqual(env.m.adopt(env.sources,'adopt',ident),result)
                self.assertEqual(len([op for op in env.k.operations.values() if op['label']=='adopt-candidate']),1)
                self.assertFalse((env.root/'estado'/'adocoes-intent.json').exists())

    def test_rollback_resumes_at_every_effect_boundary(self):
        labels=('rollback_intent','owner','config','rollback_config','rollback-candidate','rollback_candidate','rolled_back','release')
        points=[(label,when) for label in labels for when in ('before','after')]+[('rollback-candidate','pending')]
        for label,when in points:
            with self.subTest(label=label,when=when),Fixture() as env:
                ident=env.candidate();env.m.adopt(env.sources,'adopt',ident);env.arm(label,when)
                self.assertRaises(OSError,env.m.rollback,env.sources,'adopt');env.clock='2030-01-02T00:00:00+00:00'
                result=env.m.rollback(env.sources,'adopt')
                self.assertEqual(result['status'],'rolled_back');self.assertEqual(env.config(),env.initial)
                self.assertEqual(env.k.read(ident)['record']['revision'],3)
                self.assertEqual(env.m.rollback(env.sources,'adopt'),result)
                self.assertRaises(Conflict,env.m.adopt,env.sources,'adopt',ident)

    def test_partial_adoption_can_be_cancelled_or_recovered_then_rolled_back(self):
        for label,when,revision in (('adopt_intent','after',2),('config','after',3),('adopt-candidate','pending',3)):
            with self.subTest(label=label),Fixture() as env:
                ident=env.candidate();env.arm(label,when);self.assertRaises(OSError,env.m.adopt,env.sources,'adopt',ident)
                self.assertEqual(env.m.rollback(env.sources,'adopt')['status'],'rolled_back')
                self.assertEqual(env.config(),env.initial);self.assertEqual(env.k.read(ident)['record']['revision'],revision)

    def test_other_keys_cannot_bypass_an_unfinished_intent(self):
        with Fixture() as env:
            first=env.candidate('first');second=env.candidate('second');env.arm('config','after')
            self.assertRaises(OSError,env.m.adopt,env.sources,'first',first);current=env.config()
            self.assertRaises(Conflict,env.m.adopt,env.sources,'second',second);self.assertEqual(env.config(),current)
            self.assertEqual(env.m.adopt(env.sources,'first',first)['status'],'adopted')

    def test_concurrent_configuration_or_candidate_edit_is_not_overwritten(self):
        with Fixture() as env:
            ident=env.candidate();env.arm('config','after');self.assertRaises(OSError,env.m.adopt,env.sources,'adopt',ident)
            current=env.config();current['auto_adopt_config']=False;env.set_config(current)
            self.assertRaises(Invalid,env.m.adopt,env.sources,'adopt',ident)
            self.assertRaises(Conflict,env.m.rollback,env.sources,'adopt');self.assertEqual(env.config(),current)
        with Fixture() as env:
            ident=env.candidate();env.arm('adopt_intent','after');self.assertRaises(OSError,env.m.adopt,env.sources,'adopt',ident)
            env.k.records[ident]['revision']+=1;env.k.records[ident]['payload']['problem']='Alteração concorrente fictícia'
            self.assertRaises(Conflict,env.m.adopt,env.sources,'adopt',ident);self.assertEqual(env.config(),env.initial)

    def test_cached_knowledge_operation_cannot_hide_a_later_candidate_edit(self):
        for status,label,operation in (('adopted','adopt-candidate','adopt'),('rolled_back','rollback-candidate','rollback')):
            with self.subTest(status=status),Fixture() as env:
                ident=env.candidate()
                if operation=='rollback':env.m.adopt(env.sources,'adopt',ident)
                env.arm(label,'after')
                function=(lambda:env.m.adopt(env.sources,'adopt',ident)) if operation=='adopt' else (lambda:env.m.rollback(env.sources,'adopt'))
                self.assertRaises(OSError,function)
                env.k.records[ident]['revision']+=1;env.k.records[ident]['payload']['problem']='Edição posterior fictícia'
                snapshot=copy.deepcopy(env.k.records[ident]);current=env.config()
                self.assertRaises(Conflict,function)
                self.assertEqual(env.k.records[ident],snapshot);self.assertEqual(env.config(),current)
                self.assertNotEqual(json.loads(env.journal().read_text(encoding='utf-8'))['status'],status)

    def test_process_lock_is_nonblocking_and_released_after_use(self):
        with Fixture() as env:
            ident=env.candidate()
            with env.m._state_lock(env.sources):self.assertRaises(Conflict,env.m.adopt,env.sources,'adopt',ident)
            self.assertEqual(env.m.adopt(env.sources,'adopt',ident)['status'],'adopted')

    def test_unambiguous_legacy_adoption_is_migrated_before_rollback(self):
        with Fixture() as env:
            ident=env.candidate();state=env.m.adopt(env.sources,'adopt',ident)
            legacy={name:state[name] for name in ('status','candidate_id','before','after','previous_revision','created_at','adopted_at')}
            env.journal().write_text(canon(legacy),encoding='utf-8')
            result=env.m.rollback(env.sources,'adopt');self.assertEqual(result['version'],2);self.assertEqual(result['status'],'rolled_back')
            self.assertEqual(env.config(),env.initial)

    def test_completed_legacy_rollback_remains_idempotent_without_new_candidate_writes(self):
        with Fixture() as env:
            ident=env.candidate();env.m.adopt(env.sources,'adopt',ident);state=env.m.rollback(env.sources,'adopt')
            legacy={name:state[name] for name in ('status','candidate_id','before','after','previous_revision','created_at','adopted_at','rolled_back_at')}
            env.journal().write_text(canon(legacy),encoding='utf-8');operations=len(env.k.operations)
            migrated=env.m.rollback(env.sources,'adopt')
            self.assertEqual(migrated['status'],'rolled_back');self.assertEqual(migrated['version'],2)
            self.assertEqual(env.k.read(ident)['record']['revision'],3);self.assertEqual(len(env.k.operations),operations)
            self.assertEqual(env.m.rollback(env.sources,'adopt'),migrated);self.assertEqual(env.config(),env.initial)

    def test_ambiguous_legacy_rollback_is_not_guessed(self):
        with Fixture() as env:
            ident=env.candidate();state=env.m.adopt(env.sources,'adopt',ident)
            legacy={name:state[name] for name in ('status','candidate_id','before','after','previous_revision','created_at','adopted_at')}
            env.journal().write_text(canon(legacy),encoding='utf-8');env.set_config(env.initial)
            self.assertRaises(Conflict,env.m.rollback,env.sources,'adopt');self.assertEqual(env.config(),env.initial)


class ResearchRecoveryTests(unittest.TestCase):
    def test_response_timestamp_and_plan_exist_before_any_source(self):
        with Fixture() as env:
            def check():
                state=json.loads(env.request_path().read_text(encoding='utf-8'))
                self.assertIn(state['phase'],('prepared','importing'));self.assertEqual(state['response']['searched_at'],env.clock)
                self.assertEqual(len(state['plan']['sources']),2)
            env.before_source=check;result=env.research()
            self.assertEqual(len(result['source_refs']),2);self.assertEqual(len(env.network_calls),1)
            second=env.sources.read(result['source_refs'][1]['record_id']);self.assertEqual(second['payload']['source_kind'],'publication')
            self.assertIn('não inferir resultados',second['payload']['content'])

    def test_research_resumes_without_network_or_new_metadata_at_each_boundary(self):
        labels=('research-prepared','source','research-importing','research-record','research-recorded','research-cache','research-completed')
        points=[(label,when) for label in labels for when in ('before','after') if (label,when)!=('research-prepared','before')]
        points.append(('research-record','pending'))
        for label,when in points:
            with self.subTest(label=label,when=when),Fixture() as env:
                original_time=env.clock;env.arm(label,when);self.assertRaises(OSError,env.research)
                env.clock='2030-01-03T00:00:00+00:00';result=env.research()
                self.assertEqual(len(env.network_calls),1);self.assertEqual(result['searched_at'],original_time)
                self.assertEqual(len(env.sources.operations),2);self.assertEqual(len(env.k.operations),1)
                for ref in result['source_refs']:self.assertEqual(env.sources.read(ref['record_id'])['payload']['accessed_at'],original_time)
                self.assertEqual(env.research(),result);self.assertEqual(len(env.network_calls),1)

    def test_second_source_acknowledgement_loss_keeps_the_first_source_and_original_clock(self):
        with Fixture() as env:
            env.arm('source','after',occurrence=2);self.assertRaises(OSError,env.research)
            saved=json.loads(env.request_path().read_text(encoding='utf-8'));self.assertEqual(len(saved['source_refs']),1)
            env.clock='2030-01-04T00:00:00+00:00';result=env.research()
            self.assertEqual(len(env.network_calls),1);self.assertEqual(len(env.sources.records),2)
            self.assertEqual(result['source_refs'][0],saved['source_refs'][0]);self.assertEqual(result['searched_at'],saved['response']['searched_at'])

    def test_uncertain_response_is_not_fetched_again(self):
        with Fixture() as env:
            env.arm('research-prepared','before');self.assertRaises(OSError,env.research)
            self.assertEqual(len(env.sources.operations),0);env.clock='2030-01-05T00:00:00+00:00'
            self.assertRaises(Conflict,env.research);self.assertEqual(len(env.network_calls),1)
        with Fixture() as env:
            env.arm('research-fetching','after');self.assertRaises(OSError,env.research)
            self.assertRaises(Conflict,env.research);self.assertEqual(len(env.network_calls),0)

    def test_failure_before_network_reservation_can_be_retried_without_duplicate_network(self):
        with Fixture() as env:
            env.arm('research-fetching','before');self.assertRaises(OSError,env.research)
            self.assertEqual(len(env.network_calls),0);env.research();self.assertEqual(len(env.network_calls),1)

    def test_same_key_is_bound_to_original_terms_and_limit(self):
        with Fixture() as env:
            env.research()
            self.assertRaises(Conflict,env.p.research,env.sources,'search',['memory'],transport=env.transport)
            self.assertRaises(Conflict,env.research,limit=2);self.assertEqual(len(env.network_calls),1)

    def test_changed_plan_is_rejected_before_source_creation(self):
        with Fixture() as env:
            env.arm('research-prepared','after');self.assertRaises(OSError,env.research)
            state=json.loads(env.request_path().read_text(encoding='utf-8'));state['plan']['sources'][0]['text']='Plano adulterado'
            state['plan_hash']=sha(canon([state['request'],state['fingerprint'],state['response'],state['plan']]).encode())
            env.request_path().write_text(canon(state),encoding='utf-8')
            self.assertRaises(Invalid,env.research);self.assertEqual(len(env.sources.operations),0);self.assertEqual(len(env.network_calls),1)

    def test_source_corrected_during_partial_research_is_not_silently_reused(self):
        with Fixture() as env:
            env.arm('research-importing','after');self.assertRaises(OSError,env.research)
            state=json.loads(env.request_path().read_text(encoding='utf-8'));ident=state['source_refs'][0]['record_id']
            env.sources.records[ident]['revision']+=1
            self.assertRaises(Invalid,env.research);self.assertEqual(len(env.network_calls),1);self.assertEqual(len(env.sources.records),1)

    def test_completed_legacy_cache_is_migrated_without_network(self):
        with Fixture() as env:
            result=env.research();env.request_path().unlink();env.clock='2030-01-06T00:00:00+00:00'
            self.assertEqual(env.research(),result);self.assertEqual(len(env.network_calls),1)
            self.assertEqual(json.loads(env.request_path().read_text(encoding='utf-8'))['phase'],'completed')

    def test_revised_research_record_does_not_return_an_old_cached_record(self):
        with Fixture() as env:
            result=env.research();ident=result['research_record']['id'];env.k.records[ident]['revision']+=1
            self.assertRaises(Invalid,env.research);self.assertEqual(len(env.network_calls),1)

    def test_research_lock_and_input_limits_prevent_network(self):
        with Fixture() as env:
            with env.m._state_lock(env.sources,'pesquisas'):self.assertRaises(Conflict,env.research)
            self.assertRaises(Invalid,env.p.research,env.sources,'bad',['texto biográfico livre'],transport=env.transport)
            self.assertRaises(Invalid,env.research,limit=True);self.assertRaises(Invalid,env.research,limit=6)
            self.assertEqual(env.network_calls,[])


if __name__=='__main__':unittest.main(verbosity=2)
