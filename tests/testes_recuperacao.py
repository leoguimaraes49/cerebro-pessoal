import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from nucleo import Store,REAL_SYSTEM,Invalid,Conflict,canon,sha
from conhecimento import Knowledge
from recuperacao import Retrieval
from revalidacao import review,automatic_payload
from revisoes import register


class FakeEmbeddings:
    def chunks(self,text,kind='passage'):
        text=text.lower()
        return [[float('sono' in text or 'dorm' in text),float('projeto' in text or 'atlas' in text),1.0]]


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');root=Path(self.tmp.name)
        self.sources=Store(root/'sistema',root/'cofre');self.k=Knowledge(self.sources)
        self.source=self.sources.apply('source','create',title='Preferência fictícia',text='Pessoa fictícia prefere estudar às 16h.')
        self.ref={'record_id':self.source['id'],'revision':1}
        self.retrieval=Retrieval(self.sources,FakeEmbeddings())
        for target in ('recuperacao.LocalEmbeddings','urllib.request.OpenerDirector.open'):
            guard=patch(target,side_effect=AssertionError('provedor real proibido nesta fixture'))
            guard.start();self.addCleanup(guard.stop)
    def tearDown(self):self.tmp.cleanup()
    def stale_assertion(self,human_status=None,correct_source=True,author_refs=None):
        source=self.sources.apply('identity-source','create',title='Identidade fictícia',text='Pessoa inteiramente fictícia.')
        person=self.k.apply('person','entity','Pessoa fictícia',{'entity_kind':'person','display_name':'Pessoa fictícia',
            'origin_refs':[{'record_id':source['id'],'revision':1}],'identity_status':'identified'})
        payload={'subject_ref':{'record_id':person['id'],'revision':1},'predicate':'reports_preference',
            'value':{'type':'text','content':'16h'},'nature':'user_report','asserted_by':'autora fictícia',
            'recorded_time':self.sources.read(self.source['id'])['payload']['received_at'],'source_refs':[self.ref],
            'context_description':'Somente fixture','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}
        if author_refs is not None:payload['author_refs']=copy.deepcopy(author_refs)
        assertion=self.k.apply('assertion','assertion','Preferência fictícia',payload)
        if human_status:
            confirmation=self.sources.apply('confirmation','create',title='Revisão humana fictícia',
                text='Revisei apenas a preferência fictícia às 16h.')
            register(self.sources,'human-review',assertion['id'],1,human_status,
                {'record_id':confirmation['id'],'revision':1},'preferência fictícia às 16h','Somente a preferência relatada')
        old=self.k.catalog()[0][assertion['id']]
        updated=copy.deepcopy(old['payload'])
        if correct_source:
            self.sources.apply('correct','correct',ident=self.source['id'],expected=1,
                text='Pessoa fictícia prefere estudar às 09h.',reason='Correção inteiramente fictícia')
            updated['value']['content']='09h';updated['source_refs'][0]['revision']=2
        return old,updated
    def review_model(self,payload):
        model=Mock();model.call.return_value={'status':'proposed','payload':payload,'reason':'Fonte fictícia corrigida',
            'citations':[{'record_id':self.source['id'],'revision':2,'quote':'09h'}]}
        return model
    def ranked_sources(self,index):
        query='nebulosa'+str(index)+' quasar'+str(index)
        strong_id='lexical-'+str(index)+('-z' if index==0 else '-a')
        weak_id='lexical-'+str(index)+('-a' if index==0 else '-z')
        strong_title='Documento forte '+str(index);weak_title='Documento fraco '+str(index)
        with patch('nucleo.uuid.uuid4',return_value=strong_id):
            strong=self.sources.apply('strong-'+str(index),'create',title=strong_title,text=query)
        with patch('nucleo.uuid.uuid4',return_value=weak_id):
            weak=self.sources.apply('weak-'+str(index),'create',title=weak_title,text='nebulosa'+str(index))
        return query,strong,weak,strong_title,weak_title
    def test_semantic_channel_is_used_even_when_lexical_results_exist(self):
        other=self.sources.apply('other','create',title='Relato de sono fictício',text='Pessoa fictícia teve dificuldade para dormir.')
        self.sources.apply('distractor','create',title='Outra ocorrência da palavra',text='A palavra sono aparece num título fictício.')
        result=self.retrieval.search('Como anda o sono?',limit=10)
        self.assertEqual(result['mode'],'hybrid_lexical_vector_graph')
        self.assertIn(other['id'],[r['id'] for r in result['results']])
    def test_cache_reuse_requires_same_generation(self):
        first=self.retrieval.search('estudar');second=self.retrieval.search('estudar')
        self.assertFalse(first['cache_reused']);self.assertTrue(second['cache_reused'])
        self.sources.apply('novel','create',title='Nota nova sem arestas',text='Nova informação de estudo fictício.')
        third=self.retrieval.search('estudar');self.assertFalse(third['cache_reused'])
        self.assertNotEqual(first['generation'],third['generation'])
    def test_correction_invalidates_cached_result(self):
        self.retrieval.search('estudar')
        self.sources.apply('correct','correct',ident=self.source['id'],expected=1,text='Pessoa fictícia prefere estudar às 09h.',reason='Correção fictícia')
        result=self.retrieval.search('estudar');self.assertFalse(result['cache_reused'])
        row=next(r for r in result['results'] if r['id']==self.source['id'])
        self.assertEqual(row['revision'],2);self.assertIn('09h',row['record']['payload']['content'])
    def test_deleted_source_is_removed_from_vector_results(self):
        self.retrieval.search('estudar');self.sources.delete('delete',self.source['id'],1)
        self.assertEqual(self.retrieval.search('estudar')['results'],[])
    def test_scope_is_part_of_cache_contract(self):
        self.retrieval.search('estudar')
        other=Retrieval(self.sources,FakeEmbeddings(),scope='outra-politica')
        self.assertFalse(other.search('estudar')['cache_reused'])
    def test_suspended_derived_content_is_not_searched(self):
        synth=self.k.apply('synth','synthesis','Síntese fictícia',{'synthesis_kind':'knowledge_summary','content':'Preferência às 16h',
            'scope':'fictício','basis_refs':[self.ref],'limitations':['uma fonte'],'coverage_status':'provisional','as_of':'2026-10-30'})
        self.sources.apply('correct','correct',ident=self.source['id'],expected=1,text='Preferência corrigida para 09h.',reason='Teste')
        result=self.retrieval.search('preferência')
        self.assertNotIn(synth['id'],[r['id'] for r in result['results']])
    def test_semantic_review_updates_content_and_preserves_original_history(self):
        payload={'synthesis_kind':'knowledge_summary','content':'Preferência às 16h','scope':'fictício','basis_refs':[self.ref],
                 'limitations':['uma fonte'],'coverage_status':'provisional','as_of':'2026-10-30'}
        synth=self.k.apply('synth','synthesis','Síntese fictícia',payload)
        self.sources.apply('correct','correct',ident=self.source['id'],expected=1,text='Pessoa fictícia prefere estudar às 09h.',reason='Teste')
        updated=copy.deepcopy(payload);updated['content']='Preferência às 09h';updated['basis_refs'][0]['revision']=2
        class Model:
            def call(model,prompt):return {'status':'proposed','payload':updated,'reason':'Fonte corrigida',
                'citations':[{'record_id':self.source['id'],'revision':2,'quote':'09h'}]}
        result=review(self.sources,'review',Model());self.assertEqual(result['status'],'completed')
        current=self.k.read(synth['id'])['record'];self.assertIn('09h',current['payload']['content']);self.assertEqual(current['revision'],2)
        self.assertTrue((self.sources.root/'estado'/'conhecimento_revisoes'/synth['id']/'1.md').is_file())
    def test_review_cannot_cite_unavailable_or_old_content(self):
        payload={'synthesis_kind':'knowledge_summary','content':'16h','scope':'fictício','basis_refs':[self.ref],
                 'limitations':[],'coverage_status':'provisional','as_of':'2026-10-30'}
        self.k.apply('synth','synthesis','Síntese fictícia',payload)
        self.sources.apply('correct','correct',ident=self.source['id'],expected=1,text='Agora 09h.',reason='Teste')
        class Model:
            def call(model,prompt):return {'status':'proposed','payload':payload,'citations':[{'record_id':self.source['id'],'revision':1,'quote':'16h'}]}
        with self.assertRaises(Invalid):review(self.sources,'review',Model())


    def test_semantic_hit_keeps_origin_when_other_hits_fill_the_limit(self):
        target=self.k.apply('target','synthesis','Alvo semântico',{'synthesis_kind':'knowledge_summary','content':'ALVO SEMANTICO',
            'scope':'fixture','basis_refs':[self.ref],'limitations':['fictício'],'coverage_status':'provisional','as_of':'2026-10-30'})
        self.sources.apply('distractor','create',title='Sem relação',text='semLigacao')
        class Embeddings:
            def chunks(self,text,kind='passage'):
                if kind=='query' or 'ALVO SEMANTICO' in text:return [[1.0,0.0]]
                return [[0.8,0.2]] if 'semLigacao' in text else [[0.0,1.0]]
        result=Retrieval(self.sources,Embeddings()).search('zzqsemantic',limit=2,depth=1)
        self.assertEqual({r['id'] for r in result['results']},{target['id'],self.source['id']})


    def test_lexical_relevance_is_preserved_when_record_ids_are_permuted(self):
        for index in range(2):
            with self.subTest(permutation=index):
                query,strong,weak,_,_=self.ranked_sources(index)
                result=Retrieval(self.sources).search(query,limit=2,depth=0)
                self.assertEqual([r['id'] for r in result['results']],[strong['id'],weak['id']])
    def test_rrf_tie_uses_lexical_rank_before_record_id(self):
        class OpposingEmbeddings:
            def chunks(model,text,kind='passage'):
                vector=[0.0]*4
                for case in range(2):
                    if kind=='query' and 'nebulosa'+str(case) in text or 'Documento fraco '+str(case) in text:
                        vector[case*2]=1.0;break
                    if 'Documento forte '+str(case) in text:
                        vector[case*2]=0.8;vector[case*2+1]=0.2;break
                return [vector]
        for index in range(2):
            with self.subTest(permutation=index):
                query,strong,weak,_,_=self.ranked_sources(index)
                result=Retrieval(self.sources,OpposingEmbeddings()).search(query,limit=2,depth=0)
                self.assertEqual([r['id'] for r in result['results']],[strong['id'],weak['id']])
    def test_rrf_requests_lexical_ranking_without_graph_expansion(self):
        derived=self.k.apply('graph-neighbor','synthesis','Contexto conectado',{'synthesis_kind':'knowledge_summary',
            'content':'Contexto sem a palavra consultada','scope':'fixture','basis_refs':[self.ref],
            'limitations':['fictício'],'coverage_status':'provisional','as_of':'2026-11-02'})
        retrieval=Retrieval(self.sources)
        with patch.object(retrieval.k,'search',wraps=retrieval.k.search) as lexical:
            result=retrieval.search('estudar',limit=4,depth=1)
        lexical.assert_called_once_with('estudar',limit=4,depth=0)
        self.assertEqual([r['id'] for r in result['results']],[self.source['id'],derived['id']])
    def test_old_rrf_cache_is_not_reused_after_ranking_contract_change(self):
        generation=self.retrieval.snapshot()[0]
        key=sha(canon(['estudar',12,1,self.retrieval.scope,True,'rrf-v2-context-reserved']).encode())
        with self.retrieval.connect() as connection:
            connection.execute('INSERT INTO cache VALUES(?,?,?)',(key,generation,canon({'results':[]})))
        result=self.retrieval.search('estudar')
        self.assertFalse(result['cache_reused']);self.assertTrue(result['results'])
        self.assertTrue(self.retrieval.search('estudar')['cache_reused'])
    def test_review_cannot_fabricate_human_confirmation_or_dispute(self):
        old,updated=self.stale_assertion()
        for status in ('confirmed_by_user','disputed_by_user'):
            with self.subTest(status=status):
                proposed=copy.deepcopy(updated);proposed['review_status']=status
                proposed['review_events']=[{'actor':'user','reviewed_revision':old['revision'],
                    'source_ref':{'record_id':self.source['id'],'revision':2},'quote':'09h',
                    'scope':'Alcance inventado pelo modelo','recorded_at':'2026-11-02T00:00:00Z'}]
                with self.assertRaises(Invalid):review(self.sources,'forged-'+status,self.review_model(proposed))
                self.assertEqual(self.k.catalog()[0][old['id']],old)
                self.assertIn(old['id'],self.k.stale(self.k.catalog()[0]))
    def test_review_cannot_promote_human_status_even_without_events(self):
        old,updated=self.stale_assertion();updated['review_status']='confirmed_by_user'
        with self.assertRaisesRegex(Invalid,'nome do usuário'):
            review(self.sources,'forged-status',self.review_model(updated))
        self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_review_preserves_human_history_without_extending_confirmation_to_changed_text(self):
        old,updated=self.stale_assertion('confirmed_by_user');del updated['review_events']
        with patch('revalidacao.Knowledge',return_value=self.k),patch.object(self.k,'apply',wraps=self.k.apply) as writes:
            result=review(self.sources,'review-human-history',self.review_model(updated))
        self.assertEqual(result['status'],'completed');self.assertEqual(writes.call_count,1)
        self.assertNotIn('review_authorized',writes.call_args.kwargs)
        current=self.k.read(old['id'])['record'];self.assertIsNotNone(current)
        self.assertEqual(current['revision'],old['revision']+1)
        self.assertEqual(current['payload']['value']['content'],'09h')
        self.assertEqual(current['payload']['review_status'],'clarification_needed')
        self.assertEqual(current['payload']['review_events'],old['payload']['review_events'])
        self.assertEqual(current['payload']['review_events'][-1]['reviewed_revision'],1)
        for field in ('asserted_by','nature','recorded_time'):
            self.assertEqual(current['payload'][field],old['payload'][field])
        note=current['payload']['revalidation_note']
        self.assertEqual(note['previous_revision'],old['revision'])
        self.assertEqual(note['previous_review_status'],'confirmed_by_user')
        history=self.sources.root/'estado'/'conhecimento_revisoes'/old['id']/(str(old['revision'])+'.md')
        self.assertTrue(history.is_file());self.assertIn('16h',history.read_text(encoding='utf-8'))
    def test_corrected_confirmation_source_does_not_renew_human_review(self):
        old,updated=self.stale_assertion('confirmed_by_user',correct_source=False)
        confirmation=old['payload']['review_events'][-1]['source_ref']
        self.sources.apply('correct-confirmation','correct',ident=confirmation['record_id'],expected=1,
            text='A menção fictícia às 16h tem alcance menor.',reason='Correção fictícia do alcance da confirmação')
        model=Mock();model.call.return_value={'status':'proposed','payload':updated,'reason':'Relato original mantido',
            'citations':[{'record_id':confirmation['record_id'],'revision':2,'quote':'16h'}]}
        self.assertEqual(review(self.sources,'review-confirmation-source',model)['status'],'completed')
        current=self.k.read(old['id'])['record'];self.assertIsNotNone(current)
        self.assertEqual(current['payload']['review_status'],'clarification_needed')
        self.assertEqual(current['payload']['value'],old['payload']['value'])
        self.assertEqual(current['payload']['review_events'],old['payload']['review_events'])
    def test_review_cannot_rewrite_remove_or_append_human_events(self):
        old,updated=self.stale_assertion('disputed_by_user')
        invented={'actor':'user','reviewed_revision':old['revision'],
            'source_ref':{'record_id':self.source['id'],'revision':2},'quote':'09h',
            'scope':'Novo alcance inventado','recorded_at':'2026-11-02T00:00:00Z'}
        variants=[[],[invented],old['payload']['review_events']+[invented],
                  [dict(old['payload']['review_events'][0],scope='Alcance alterado')]]
        for index,events in enumerate(variants):
            with self.subTest(events=events):
                payload=copy.deepcopy(updated);payload['review_events']=events
                with self.assertRaisesRegex(Invalid,'eventos'):
                    review(self.sources,'tampered-history-'+str(index),self.review_model(payload))
                self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_review_cannot_change_authorship_or_control_fields(self):
        old,updated=self.stale_assertion()
        for index,(field,value) in enumerate((('asserted_by','outro autor'),('nature','inference'),
                ('recorded_time','2000-01-01'),('created_by','user'),('review_authorized',True))):
            with self.subTest(field=field):
                payload=copy.deepcopy(updated);payload[field]=value
                with self.assertRaisesRegex(Invalid,'autoria ou controle'):
                    review(self.sources,'tampered-control-'+str(index),self.review_model(payload))
                self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_review_accepts_current_author_revision_without_changing_author_identity(self):
        author=self.sources.apply('author-source','create',title='Autora fictícia',text='Autora fictícia; versão inicial.')
        ref={'record_id':author['id'],'revision':1,'fragment':'/author','role':'relator'}
        old,updated=self.stale_assertion(correct_source=False,author_refs=[ref])
        self.sources.apply('correct-author','correct',ident=author['id'],expected=1,
            text='Autora fictícia; anotação técnica corrigida.',reason='Correção técnica fictícia')
        updated['author_refs'][0]['revision']=2
        model=Mock();model.call.return_value={'status':'proposed','payload':updated,'reason':'Referência técnica atualizada',
            'citations':[{'record_id':author['id'],'revision':2,'quote':'Autora fictícia'}]}
        self.assertEqual(review(self.sources,'review-author-revision',model)['status'],'completed')
        current=self.k.read(old['id'])['record'];self.assertIsNotNone(current)
        self.assertEqual(current['payload']['author_refs'],[dict(ref,revision=2)])
        self.assertEqual(current['payload']['asserted_by'],old['payload']['asserted_by'])
        self.assertEqual(current['payload']['value'],old['payload']['value'])
    def test_review_cannot_replace_author_with_another_existing_identity(self):
        author=self.sources.apply('author-source','create',title='Autora fictícia',text='Autora fictícia; versão inicial.')
        other=self.sources.apply('other-author','create',title='Outra autora fictícia',text='Outra identidade fictícia.')
        ref={'record_id':author['id'],'revision':1,'fragment':'/author','role':'relator'}
        old,updated=self.stale_assertion(correct_source=False,author_refs=[ref])
        self.sources.apply('correct-author','correct',ident=author['id'],expected=1,
            text='Autora fictícia; anotação técnica corrigida.',reason='Correção técnica fictícia')
        updated['author_refs'][0]['record_id']=other['id']
        model=Mock();model.call.return_value={'status':'proposed','payload':updated,'reason':'Troca não autorizada',
            'citations':[{'record_id':author['id'],'revision':2,'quote':'Autora fictícia'}]}
        with self.assertRaisesRegex(Invalid,'autoria ou controle'):review(self.sources,'review-other-author',model)
        self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_review_does_not_apply_if_current_basis_changes_during_model_call(self):
        old,updated=self.stale_assertion();model=self.review_model(updated);proposal=model.call.return_value
        def concurrent_correction(prompt):
            self.sources.apply('concurrent-correction','correct',ident=self.source['id'],expected=2,
                text='Pessoa fictícia prefere estudar às 08h.',reason='Mudança concorrente fictícia')
            return proposal
        model.call.side_effect=concurrent_correction
        with self.assertRaises(Conflict):review(self.sources,'concurrent-review',model)
        self.assertEqual(self.k.catalog()[0][old['id']],old)


class AutomaticPayloadTests(unittest.TestCase):
    def old_record(self):
        return {'id':'assertion-fixture','revision':2,'payload':{'value':{'type':'text','content':'16h'},
            'asserted_by':'autora fictícia','nature':'user_report','recorded_time':'2026-11-02T00:00:00Z',
            'review_status':'confirmed_by_user','review_events':[{'actor':'user','reviewed_revision':1,
                'source_ref':{'record_id':'source-fixture','revision':1},'quote':'16h','scope':'preferência',
                'recorded_at':'2026-11-02T00:00:00Z'}]}}
    def test_unchanged_payload_keeps_legitimate_review_and_does_not_mutate_inputs(self):
        old=self.old_record();before=copy.deepcopy(old);proposal=copy.deepcopy(old['payload'])
        del proposal['review_events'];del proposal['asserted_by']
        result=automatic_payload('assertion',proposal,old)
        self.assertEqual(result,old['payload']);self.assertEqual(old,before)
        self.assertNotIn('review_events',proposal);self.assertNotIn('asserted_by',proposal)
    def test_changed_payload_keeps_events_bound_to_the_reviewed_revision(self):
        old=self.old_record();proposal=copy.deepcopy(old['payload']);proposal['value']['content']='09h'
        result=automatic_payload('assertion',proposal,old)
        self.assertEqual(result['review_status'],'clarification_needed')
        self.assertEqual(result['review_events'],old['payload']['review_events'])
        self.assertEqual(result['review_events'][-1]['reviewed_revision'],1)
        self.assertEqual(proposal['review_status'],'confirmed_by_user')
    def test_boolean_cannot_impersonate_integer_in_historical_review(self):
        old=self.old_record();proposal=copy.deepcopy(old['payload'])
        proposal['review_events'][-1]['reviewed_revision']=True
        with self.assertRaisesRegex(Invalid,'eventos'):automatic_payload('assertion',proposal,old)
    def test_author_reference_allows_only_technical_revision_updates(self):
        old=self.old_record();old['payload']['author_refs']=[
            {'record_id':'author-a','revision':1,'fragment':'/authors/0','role':'relator'},
            {'record_id':'author-b','revision':2,'fragment':'/authors/1','role':'coautor'}]
        before=copy.deepcopy(old);proposal=copy.deepcopy(old['payload'])
        proposal['author_refs'][0]['revision']=2;proposal['author_refs'][1]['revision']=3
        result=automatic_payload('assertion',proposal,old)
        self.assertEqual(result['author_refs'],proposal['author_refs']);self.assertEqual(old,before)
        self.assertEqual(result['review_status'],'clarification_needed')
        for previous,current in zip(old['payload']['author_refs'],result['author_refs']):
            self.assertEqual({k:v for k,v in previous.items() if k!='revision'},
                             {k:v for k,v in current.items() if k!='revision'})
    def test_author_reference_cannot_change_identity_fragment_fields_or_order(self):
        old=self.old_record();authors=[{'record_id':'author-a','revision':1,'fragment':'/authors/0','role':'relator'},
            {'record_id':'author-b','revision':1,'fragment':'/authors/1','role':'coautor'}]
        old['payload']['author_refs']=copy.deepcopy(authors)
        variants=[[dict(authors[0],record_id='another-author'),authors[1]],
            [dict(authors[0],fragment='/other'),authors[1]],[dict(authors[0],role='outro papel'),authors[1]],
            [dict(authors[0],extra='campo inventado'),authors[1]],list(reversed(authors)),authors[:1],
            authors+[dict(authors[0],record_id='third-author')],[dict(authors[0],revision=True),authors[1]],
            [dict(authors[0],revision=0),authors[1]]]
        for kind in ('assertion','entity','synthesis','question'):
            for refs in variants:
                with self.subTest(kind=kind,refs=refs):
                    proposal=copy.deepcopy(old['payload']);proposal['author_refs']=copy.deepcopy(refs)
                    with self.assertRaisesRegex(Invalid,'autoria ou controle'):
                        automatic_payload(kind,proposal,old)
    def test_other_families_cannot_hide_human_reviews_or_control_authorship(self):
        for kind in ('entity','synthesis','question'):
            for payload in ({'review_status':'confirmed_by_user'},{'review_events':[{'actor':'user'}]},
                            {'created_by':'user'},{'review_authorized':True}):
                with self.subTest(kind=kind,payload=payload):
                    with self.assertRaises(Invalid):automatic_payload(kind,payload)


if __name__=='__main__':unittest.main(verbosity=2)
