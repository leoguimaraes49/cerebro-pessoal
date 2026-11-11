"""Casos de integração exclusivamente fictícios, separados do cofre pessoal."""
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from pathlib import Path
from nucleo import Store, REAL_SYSTEM, NOW, Conflict, Invalid
from conhecimento import Knowledge

class FlowTests(unittest.TestCase):
    def tearDown(self):
        self.tmp.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios')
        base=Path(self.tmp.name)
        self.sources=Store(base/'sistema',base/'cofre'); self.k=Knowledge(self.sources)
        self.source=self.sources.apply('fonte','create',title='Relato fictício',text='Pessoa fictícia estuda plantas pela manhã.')
        self.ref={'record_id':self.source['id'],'revision':1}
        self.entity=self.k.apply('pessoa','entity','Pessoa fictícia',{'entity_kind':'person','display_name':'Pessoa fictícia','identity_status':'identified','origin_refs':[self.ref]})
        self.subject={'record_id':self.entity['id'],'revision':1}

    def assertion(self):
        return {'subject_ref':self.subject,'predicate':'reports_preference','value':{'type':'text','content':'Estudar plantas pela manhã'},'nature':'user_report','asserted_by':'proprietario','recorded_time':NOW(),'source_refs':[self.ref],'context_description':'Relato fictício','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}

    def test_create_refs_and_graph_links(self):
        result=self.k.apply('afirma','assertion','Preferência fictícia',self.assertion())
        record=self.k.read(result['id']); self.assertEqual(record['validity'],'current_within_scope')
        note=next((self.k.vault/'20_Afirmacoes').glob('*.md')).read_text(encoding='utf-8')
        self.assertIn('[[30_Fontes/Relato fictício]]',note)
        self.assertIn('[[10_Entidades/Pessoa fictícia]]',note)

    def test_missing_reference_rejected(self):
        payload=self.assertion();payload['source_refs']=[{'record_id':'missing','revision':1}]
        with self.assertRaises(Invalid):self.k.apply('ruim','assertion','Inválida',payload)

    def test_old_revision_rejected(self):
        self.sources.apply('corrige','correct',ident=self.source['id'],expected=1,text='Estudo fictício à tarde',reason='Retificação fictícia')
        with self.assertRaises(Conflict):self.k.apply('ruim','assertion','Inválida',self.assertion())

    def test_propagated_staleness_and_novel_source(self):
        a=self.k.apply('afirma','assertion','Preferência fictícia',self.assertion())
        s=self.k.apply('sintese','synthesis','Síntese fictícia',{'synthesis_kind':'knowledge_summary','content':'Síntese fictícia','scope':'teste','basis_refs':[{'record_id':a['id'],'revision':1}],'limitations':['Uma fonte'],'coverage_status':'provisional','as_of':NOW()})
        self.sources.apply('corrige','correct',ident=self.source['id'],expected=1,text='Agora estuda à tarde',reason='Correção fictícia')
        self.assertEqual(self.k.read(s['id'])['validity'],'needs_revalidation')
        self.assertEqual(self.k.read(a['id'])['validity'],'needs_revalidation')
        self.sources.apply('nova','create',title='Novidade fictícia',text='Estuda cactos à tarde.')
        results=self.k.search('cactos')['results'];self.assertTrue(any(r['title']=='Novidade fictícia' for r in results))

    def test_idempotence_and_request_change(self):
        payload=self.assertion(); a=self.k.apply('afirma','assertion','Preferência fictícia',payload)
        self.assertEqual(a,self.k.apply('afirma','assertion','Preferência fictícia',payload))
        with self.assertRaises(Conflict):self.k.apply('afirma','assertion','Título diferente',payload)

    def test_external_edit_is_not_silently_overwritten(self):
        path=next((self.k.vault/'10_Entidades').glob('*.md'));path.write_bytes(path.read_bytes()+b'\nexterno')
        with self.assertRaises(Conflict):self.k.read(self.entity['id'])

    def test_open_question_then_answer_requires_origin(self):
        p={'question_text':'Qual horário?','purpose':'Esclarecer','trigger_refs':[self.ref],'information_needed':'horário','impact':'contexto','question_status':'open','resolution_status':'unresolved'}
        q=self.k.apply('pergunta','question','Pergunta fictícia',p)
        p['question_status']='answered'
        with self.assertRaises(Invalid):self.k.apply('semresposta','question','Pergunta fictícia',p,ident=q['id'],expected=1)
        p['answer_refs']=[self.ref];p['resolution_status']='resolved';p['resolution_refs']=[self.ref]
        self.assertEqual(self.k.apply('resposta','question','Pergunta fictícia',p,ident=q['id'],expected=1)['revision'],2)
        with self.assertRaises(Conflict):self.k.apply('antiga','question','Pergunta fictícia',p,ident=q['id'],expected=1)

    def test_candidate_cannot_self_adopt(self):
        p={'process_key':'investigar','purpose':'Investigar lacuna','triggers':['busca incompleta'],'input_contract':['fontes'],'output_contract':['caminho'],'preconditions':['autorização'],'allowed_effects':['proposta'],'calls':[],'failure_modes':['sem evidência'],'resource_limits':{'max_steps':3},'basis_refs':[self.ref],'acceptance_criteria':['Melhorar recuperação'],'stop_conditions':['Sem progresso'],'adoption_status':'adopted'}
        with self.assertRaises(Invalid):self.k.apply('candidata','process_definition','Caminho fictício',p)
        p['adoption_status']='candidate'
        self.assertEqual(self.k.apply('candidata','process_definition','Caminho fictício',p)['status'],'confirmed')

    def test_no_implicit_diagnosis_or_confirmation(self):
        p=self.assertion();p['nature']='instrument_result';p['predicate']='reports_diagnosis'
        with self.assertRaises(Invalid):self.k.apply('diag','assertion','Diagnóstico não permitido',p)
        p=self.assertion();p['review_status']='confirmed_by_user'
        with self.assertRaises(Invalid):self.k.apply('confirmacao','assertion','Não confirmado',p)

    def test_delete_invalidates_derivatives(self):
        a=self.k.apply('afirma','assertion','Preferência fictícia',self.assertion())
        self.sources.delete('excluir',self.source['id'],1)
        self.assertEqual(self.k.read(a['id'])['validity'],'needs_revalidation')
        self.assertIsNone(self.k.read(a['id'])['record'])
        self.assertFalse(any(r['id']==a['id'] for r in self.k.search('preferência')['results']))

    def test_bounds_and_non_overwrite_of_legacy(self):
        with self.assertRaises(Invalid):self.k.search('x',depth=10)
        self.assertEqual(self.k.search('nãoexiste')['results'],[])
        self.assertEqual(self.k.audit()['issues'],[])

    def test_contribution_original_extractions_and_retry(self):
        items=[{'tipo':'entity','titulo':'Plantas fictícias','payload':{'entity_kind':'learning_topic','topic_description':'Plantas','origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}}]
        r=self.k.contribution('turno','Fala fictícia','Texto original fictício',items)
        self.assertEqual(r['status'],'confirmed')
        self.assertEqual(self.sources.read(r['source']['id'])['payload']['content'],'Texto original fictício')
        self.assertEqual(r,self.k.contribution('turno','Fala fictícia','Texto original fictício',items))
        self.assertEqual(len(self.sources.list()),2)

    def test_partial_delivery_explicit_without_duplicate(self):
        items=[{'tipo':'entity','titulo':'Conceito fictício','payload':{'entity_kind':'concept','content':'Teste','idea_scope':'teste','origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}}, {'tipo':'assertion','titulo':'Inválida','payload':{}}]
        r=self.k.contribution('parcial','Fala fictícia','Texto original fictício',items)
        self.assertEqual(r['status'],'partial');self.assertEqual(len(r['completed']),1)
        again=self.k.contribution('parcial','Fala fictícia','Texto original fictício',items)
        self.assertEqual(again['completed'],r['completed']);self.assertEqual(len(self.sources.list()),2)

    def test_correction_recovers_after_file_written_before_commit(self):
        import conhecimento
        original=conhecimento.exclusive
        @contextmanager
        def fail_after_close(*args,**kwargs):
            with original(*args,**kwargs) as f: yield f
            raise OSError('falha fictícia após gravação')
        payload={'entity_kind':'person','display_name':'Pessoa fictícia','identity_status':'identified','origin_refs':[self.ref],'summary':'Atualizada'}
        with patch('conhecimento.exclusive',fail_after_close):
            with self.assertRaises(OSError):self.k.apply('atualiza','entity','Pessoa fictícia',payload,self.entity['id'],1)
        restarted=Knowledge(self.sources)
        result=restarted.apply('atualiza','entity','Pessoa fictícia',payload,self.entity['id'],1)
        self.assertEqual(result['revision'],2)
        self.assertEqual(restarted.read(result['id'])['record']['payload']['summary'],'Atualizada')

    def test_two_writers_no_silent_overwrite(self):
        barrier=threading.Barrier(2);results=[]
        def change(index):
            payload={'entity_kind':'person','display_name':'Pessoa fictícia','identity_status':'identified','origin_refs':[self.ref],'summary':str(index)}
            barrier.wait()
            try:self.k.apply('writer'+str(index),'entity','Pessoa fictícia',payload,self.entity['id'],1);results.append('ok')
            except Conflict:results.append('conflict')
        threads=[threading.Thread(target=change,args=(i,)) for i in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertCountEqual(results,['ok','conflict'])
        self.assertEqual(self.k.read(self.entity['id'])['record']['revision'],2)

    def test_search_keeps_ranked_seeds_before_graph_expansion(self):
        records={ident:{'id':ident,'title':title,'revision':1,'record_type':'entity','payload':{}}
                 for ident,title in [('z','alpha beta'),('b','alpha'),('a','alpha'),('0','sem correspondência')]}
        records['z']['payload']['origin_refs']=[{'record_id':'0','revision':1}]
        with patch.object(self.k,'catalog',return_value=(records,{},[])):
            lexical=self.k.search('alpha beta',limit=4,depth=0)
            expanded=self.k.search('alpha beta',limit=4,depth=1)
        self.assertEqual([record['id'] for record in lexical['results']],['z','a','b'])
        self.assertEqual([record['id'] for record in expanded['results']],['z','a','b','0'])

    def test_sqlite_failure_reports_source_and_confirmed_extractions(self):
        items=[{'tipo':'entity','titulo':'Conceito '+str(i),'payload':{'entity_kind':'concept','content':'Fixture',
                'idea_scope':'fixture','origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}} for i in range(2)]
        original=self.k.apply
        def interrupted(key,*args,**kwargs):
            if key=='sql-partial-1':raise sqlite3.OperationalError('database is locked - fixture')
            return original(key,*args,**kwargs)
        with patch.object(self.k,'apply',interrupted):result=self.k.contribution('sql-partial','Fala fictícia','Texto fictício',items)
        self.assertEqual(result['status'],'partial');self.assertEqual(result['pending_from'],1)
        self.assertEqual(len(result['completed']),1)
        self.assertEqual(self.sources.read(result['source']['id'])['payload']['content'],'Texto fictício')
        resumed=self.k.contribution('sql-partial','Fala fictícia','Texto fictício',items)
        self.assertEqual(resumed['status'],'confirmed');self.assertEqual(resumed['completed'][0],result['completed'][0])
        self.assertEqual(len(self.sources.list()),2)

    def test_historical_parent_source_does_not_suspend_retained_sources(self):
        child=self.sources.apply('child','create',title='Trecho fictício',text='Trecho original',
            source_metadata={'source_kind':'conversation_turn','parent_source_ref':self.ref})
        self.sources.apply('parent-correction','correct',ident=self.source['id'],expected=1,text='Origem corrigida',reason='fixture')
        self.assertEqual(self.k.read(child['id'])['validity'],'current_within_scope')
        self.assertEqual(self.k.read(child['id'])['record']['payload']['parent_source_ref'],self.ref)


if __name__=='__main__':unittest.main(verbosity=2)
