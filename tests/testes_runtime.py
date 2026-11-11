import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from nucleo import Store,REAL_SYSTEM,REAL_VAULT,Invalid,Conflict,config_file
from conhecimento import Knowledge
from autonomia import Queue,DEFAULTS,atomic_json,code_hash,run_one
from execucao import Engine,DEFAULT
from testes_execucao import FakeModel


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');root=Path(self.tmp.name)
        self.sources=Store(root/'sistema',root/'cofre');self.k=Knowledge(self.sources)
        manual=self.sources.vault/'00_Manual';manual.mkdir()
        manifest=json.loads(config_file(REAL_SYSTEM,'manual_manifest.json').read_text(encoding='utf-8'))
        for name in manifest:
            src_manual=REAL_SYSTEM/'00_Manual'/name
            (manual/name).write_bytes((src_manual if src_manual.exists() else REAL_VAULT/'00_Manual'/name).read_bytes())
        atomic_json(self.sources.root/'manual_manifest.json',manifest)
        self.cfg=copy.deepcopy(DEFAULT);self.cfg.update(enabled=True,auto_process_sources=True)
        atomic_json(self.sources.root/'execucao.json',self.cfg)
        self.q=Queue(self.sources)
        atomic_json(self.q.config_path,dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash(),max_jobs_per_hour=120))
    def tearDown(self):self.tmp.cleanup()
    def test_new_source_schedules_one_demand_and_does_not_duplicate(self):
        self.assertEqual(self.q.schedule_runtime(),[])
        source=self.sources.apply('new','create',title='Contribuição nova',text='Texto fictício novo.')
        jobs=self.q.schedule_runtime();self.assertEqual(len(jobs),1)
        self.assertEqual(jobs[0]['kind'],'plan_demand');self.assertEqual(self.q.schedule_runtime(),[])
        payload=json.loads(jobs[0]['payload']);engine=Engine(self.sources)
        demand=engine.q.inspect(payload['execution_id'])['demand'];self.assertEqual(demand['status'],'queued')
        self.assertEqual(len(self.sources.list()),1)
    def test_tool_output_and_publication_do_not_become_personal_experience(self):
        self.q.schedule_runtime()
        self.sources.apply('tool','create',title='Teste técnico',text='Resultado técnico fictício.',source_metadata={'source_kind':'tool_output'})
        self.sources.apply('paper','create',title='Publicação fictícia',text='Metadados apenas.',source_metadata={'source_kind':'publication','publication_title':'Fictício','reference_locator':'https://example.org'})
        self.assertEqual(self.q.schedule_runtime(),[])
    def test_owned_source_does_not_create_a_second_model_job(self):
        self.q.schedule_runtime();engine=Engine(self.sources)
        engine.start('owner','contribution',{'text':'Texto fictício fornecido ao coordenador','extractions':[]})
        self.assertEqual(self.q.schedule_runtime(),[])
    def test_revised_source_uses_same_history_and_schedules_review(self):
        source=self.sources.apply('one','create',title='Relato fictício',text='Prefere 16h.');self.q.schedule_runtime()
        self.sources.apply('correct','correct',ident=source['id'],expected=1,text='Prefere 09h.',reason='Correção fictícia')
        job=self.q.schedule_runtime()[0];engine=Engine(self.sources)
        demand=engine.q.inspect(json.loads(job['payload'])['execution_id'])
        self.assertEqual(demand['steps'][0]['capability'],'find_affected')
        self.assertIn('semantic_revalidation',[s['capability'] for s in demand['steps']])
    def test_worker_dispatches_real_demand_in_a_bounded_subprocess(self):
        engine=Engine(self.sources);ident=engine.start('provided','contribution',{'text':'Texto fictício completo.','extractions':[]})
        job=self.q.enqueue('dispatch','plan_demand',payload={'execution_id':ident})
        result=run_one(self.q);self.assertEqual(result['execution_status'],'completed')
        final=engine.q.inspect(ident);self.assertEqual(final['demand']['status'],'completed')
        self.assertEqual(len(self.sources.list()),1)
    def test_queue_idempotency_includes_demand_input(self):
        a=self.q.enqueue('one','plan_demand',payload={'execution_id':'abc'})
        self.assertEqual(a,self.q.enqueue('one','plan_demand',payload={'execution_id':'abc'}))
        with self.assertRaises(Conflict):self.q.enqueue('one','plan_demand',payload={'execution_id':'different'})
    def test_insufficient_answer_does_not_close_the_lacuna(self):
        def response(prompt):
            if '"clarification":null' in prompt:return {'decision':'ask','question':'Qual é o dado pessoal que falta?','citations':[]}
            return {'decision':'insufficient','answer':'A resposta ainda não esclareceu o essencial.','citations':[]}
        engine=Engine(self.sources,model_factory=lambda ident:FakeModel(response))
        ident=engine.start('question','question',{'query':'Pergunta fictícia sem evidência'})
        self.assertEqual(engine.run(ident)['status'],'waiting_user')
        self.assertEqual(engine.answer(ident,'Ainda não sei.')['status'],'completed')
        question=[r for r in self.k.catalog()[0].values() if r['record_type']=='question'][0]
        self.assertEqual(question['payload']['resolution_status'],'partially_resolved')
    def test_second_question_keeps_both_answers_and_different_origins(self):
        model=FakeModel(lambda prompt:{'decision':'ask','question':'Primeiro detalhe?' if '"clarification":null' in prompt else 'Outro detalhe?', 'citations':[]})
        engine=Engine(self.sources,model_factory=lambda ident:model)
        ident=engine.start('question','question',{'query':'Questão fictícia'})
        engine.run(ident);self.assertEqual(engine.answer(ident,'Sim')['status'],'waiting_user')
        engine.answer(ident,'Sim',execute=False)
        answer=json.loads(engine.q.inspect(ident)['demand']['answer'])
        self.assertNotEqual(answer['origin']['record_id'],answer['previous']['origin']['record_id'])
        self.assertEqual(answer['previous']['value'],'Sim')
    def test_corrected_response_schedules_and_recalculates_same_score(self):
        from testes_esquemas import SchemaTests
        from avaliacoes import score
        fixture=SchemaTests();fixture.setUp()
        try:
            cfg=copy.deepcopy(DEFAULT);cfg.update(enabled=True,auto_process_sources=True)
            atomic_json(fixture.sources.root/'execucao.json',cfg)
            inst,app=fixture.assessment();answer=fixture.response(inst,app,'i1',1);fixture.response(inst,app,'i2',3)
            old=score(fixture.sources,'score',app['id'])
            source=fixture.sources.apply('new-answer','create',title='Correção fictícia',text='Corrigi minha primeira resposta para 2.')
            record=fixture.k.read(answer['id'])['record'];p=copy.deepcopy(record['payload']);p['value']=2
            p['source_refs']=[{'record_id':source['id'],'revision':1}]
            fixture.k.apply('answer-update','assessment_response',record['title'],p,record['id'],1)
            q=Queue(fixture.sources);atomic_json(q.config_path,dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash(),max_jobs_per_hour=120))
            jobs=q.schedule_dependents(fixture.k.audit());self.assertEqual(len(jobs),1)
            self.assertEqual(jobs[0]['kind'],'recalculate_assessment')
            self.assertEqual(run_one(q)['execution_status'],'completed')
            updated=fixture.k.read(old['id'])['record'];self.assertEqual(updated['revision'],2)
            self.assertEqual(updated['payload']['dimension_scores'],{'d':2})
            self.assertEqual(q.schedule_dependents(fixture.k.audit()),[])
        finally:fixture.tearDown()


    def test_failed_flow_triggers_one_laboratory_candidate_without_model_call(self):
        engine=Engine(self.sources,model_factory=lambda ident:FakeModel(lambda prompt:(_ for _ in ()).throw(ConnectionError('fixture'))))
        ident=engine.start('gap-example','contribution',{'text':'Texto inteiramente fictício.'})
        self.assertEqual(engine.run(ident)['status'],'failed')
        jobs=self.q.schedule_laboratory();self.assertEqual(len(jobs),1)
        repeated=self.q.schedule_laboratory();self.assertEqual(jobs[0]['id'],repeated[0]['id'])
        self.assertEqual(run_one(self.q)['execution_status'],'completed')
        candidates=[r for r in self.k.catalog()[0].values() if r['record_type']=='improvement_candidate']
        self.assertEqual(len(candidates),1);self.assertEqual(candidates[0]['payload']['adoption_status'],'candidate')


    def test_legacy_maintenance_tool_does_not_accept_semantic_jobs_without_input(self):
        from unittest.mock import patch
        import ponte_pessoal as bridge
        with patch.object(bridge,'store',self.sources),patch.object(bridge,'authorized',return_value=True):
            result=bridge.enfileirar_manutencao('invalid-legacy','research_external')
        self.assertEqual(result['status'],'invalid');self.assertEqual(self.q.summary()['counts'],{})


if __name__=='__main__':unittest.main(verbosity=2)
