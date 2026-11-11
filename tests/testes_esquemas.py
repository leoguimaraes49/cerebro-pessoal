import copy,sqlite3,tempfile,unittest,uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from nucleo import Store,REAL_SYSTEM,NOW,Invalid,Conflict,Locked,render
from conhecimento import Knowledge,decode
from avaliacoes import score,finish
from pesquisa import research,query_terms,crossref


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');root=Path(self.tmp.name)
        self.sources=Store(root/'sistema',root/'cofre');self.k=Knowledge(self.sources)
        self.source=self.sources.apply('original','create',title='Fonte fictícia',text='Respostas fictícias: primeiro 1, segundo 3.')
        self.ref={'record_id':self.source['id'],'revision':1}
        self.person=self.k.apply('person','entity','Pessoa fictícia',{'entity_kind':'person','display_name':'Pessoa fictícia',
            'origin_refs':[self.ref],'identity_status':'identified'})
        self.personref={'record_id':self.person['id'],'revision':1}
    def tearDown(self):self.tmp.cleanup()
    def instrument(self,verified=True,items=None):
        p={'instrument_name':'Instrumento didático fictício','instrument_version':'1','purpose':'Testar o cálculo, sem avaliação clínica',
           'constructs':['dimensão fictícia'],'language':'pt-BR','original_source_refs':[self.ref],'target_population':'cenários fictícios',
           'age_scope':'adult','items_source_ref':self.ref,'instructions_source_ref':self.ref,'scoring_rule_ref':self.ref,
           'missing_response_rule':'not_calculable','use_conditions':'Somente fixture','administration_modes':['text'],
           'verification_status':'verified_for_intended_scope' if verified else 'pending_verification',
           'verification_refs':[self.ref],'verification_scope':'Cálculo de teste em fixture',
           'scoring_spec':{'method':'weighted_sum','items':[{'id':'i1','min':0,'max':3,'dimension':'d'},
                         {'id':'i2','min':0,'max':3,'dimension':'d','reverse':True}]}}
        if items is not None:p['scoring_spec']['items']=items
        return self.k.apply('instrument','instrument','Instrumento de teste',p)
    def assessment(self,verified=True,status='completed',items=None):
        inst=self.instrument(verified,items)
        p={'instrument_ref':{'record_id':inst['id'],'revision':1},'subject_ref':self.personref,'purpose':'Teste fictício',
           'application_status':status,'conditions':{'mode':'text','language':'pt-BR'},
           'scoring_eligibility':'calculable' if verified else 'pending_verification','eligibility_reason':'Regra do teste'}
        return inst,self.k.apply('assessment','assessment','Aplicação de teste',p)
    def response(self,inst,app,item,value):
        return self.k.apply('response-'+item,'assessment_response','Resposta '+item,{'assessment_ref':{'record_id':app['id'],'revision':app['revision']},
            'item_ref':{'record_id':inst['id'],'revision':1,'fragment':item},'value':value,'source_refs':[self.ref]})
    def statement(self):
        return self.k.apply('statement','assertion','Relato fictício',{'subject_ref':self.personref,'predicate':'reports_feeling',
            'value':{'type':'text','content':'fictício'},'nature':'user_report','asserted_by':'usuário fictício','source_refs':[self.ref],
            'recorded_time':NOW(),'context_description':'fixture','valid_time':{'precision':'unknown'},'review_status':'unreviewed'})
    def interrupt_write(self,after=False,at=1):
        import conhecimento
        original=conhecimento.exclusive;calls=[]
        @contextmanager
        def interrupted(*args,**kwargs):
            calls.append(1);selected=len(calls)==at
            if selected and not after:raise Locked('falha fictícia antes dos bytes')
            with original(*args,**kwargs) as stream:yield stream
            if selected and after:raise OSError('falha fictícia após bytes e antes do commit')
        return patch('conhecimento.exclusive',interrupted)

    def test_score_is_computed_and_repeat_does_not_duplicate(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        result=score(self.sources,'score',app['id'])
        self.assertEqual(self.k.read(result['id'])['record']['payload']['dimension_scores'],{'d':1})
        self.assertEqual(score(self.sources,'score',app['id']),result)
    def test_missing_answer_does_not_become_zero(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1)
        with self.assertRaises(Invalid):score(self.sources,'score',app['id'])
    def test_unverified_instrument_is_not_scored(self):
        inst,app=self.assessment(False);self.response(inst,app,'i1',1);self.response(inst,app,'i2',2)
        with self.assertRaises(Invalid):score(self.sources,'score',app['id'])
    def test_completion_updates_technical_refs_without_changing_answers(self):
        inst,app=self.assessment(status='in_progress');a=self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        result=finish(self.sources,'finish',app['id'])
        self.assertEqual(self.k.read(result['id'])['record']['payload']['dimension_scores'],{'d':1})
        answer=self.k.read(a['id'])['record'];self.assertEqual(answer['payload']['value'],1)
        self.assertEqual(answer['payload']['assessment_ref']['revision'],2)
    def test_forged_score_is_rejected(self):
        inst,app=self.assessment();a=self.response(inst,app,'i1',1);b=self.response(inst,app,'i2',3)
        p={'assessment_ref':{'record_id':app['id'],'revision':1},'scoring_rule_ref':self.ref,
           'response_refs':[{'record_id':a['id'],'revision':1},{'record_id':b['id'],'revision':1}],
           'dimension_scores':{'d':999},'computed_at':NOW(),'limitations':[],'score_validity_status':'current'}
        with self.assertRaises(Invalid):self.k.apply('forged','assessment_score','Não aceitar',p)
    def test_response_correction_suspends_score(self):
        inst,app=self.assessment();a=self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        result=score(self.sources,'score',app['id']);old=self.k.read(a['id'])['record'];p=copy.deepcopy(old['payload']);p['value']=2
        self.k.apply('answer-correct','assessment_response',old['title'],p,a['id'],1)
        self.assertEqual(self.k.read(result['id'])['validity'],'needs_revalidation')
        new=score(self.sources,'score',app['id']);self.assertEqual(self.k.read(new['id'])['record']['payload']['dimension_scores'],{'d':2})
    def test_evidence_relation_can_target_synthesis_without_derivation_cycle(self):
        synth=self.k.apply('synthesis','synthesis','Hipótese de teste',{'synthesis_kind':'knowledge_summary','content':'Hipótese fictícia',
            'scope':'fixture','basis_refs':[self.ref],'limitations':['não clínica'],'coverage_status':'provisional','as_of':NOW()})
        p={'subject_ref':self.ref,'object_ref':{'record_id':synth['id'],'revision':1},'predicate':'supports','nature':'inference',
           'asserted_by':'modelo de teste','recorded_time':NOW(),'context_description':'fixture','valid_time':{'precision':'unknown'},
           'review_status':'unreviewed','basis_refs':[self.ref],'scope_note':'Suporte apenas no cenário fictício'}
        result=self.k.apply('relation','assertion','Apoio provisório',p)
        self.assertEqual(self.k.read(result['id'])['validity'],'current_within_scope')
    def test_wrong_semantic_target_type_is_rejected(self):
        p={'subject_ref':self.personref,'object_ref':self.personref,'predicate':'pursues_goal','nature':'user_report','source_refs':[self.ref],
           'asserted_by':'usuário fictício','recorded_time':NOW(),'context_description':'fixture','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}
        with self.assertRaises(Invalid):self.k.apply('wrong','assertion','Tipo incorreto',p)
    def test_external_source_keeps_publication_kind(self):
        data={'message':{'items':[{'DOI':'10.1234/ficticio','title':['Estudo fictício'],'abstract':'Resumo de teste','published':{'date-parts':[[2025]]}}]}}
        out=research(self.sources,'search',['learning'],transport=lambda url:data)
        record=self.sources.read(out['source_refs'][0]['record_id'])
        self.assertEqual(record['payload']['source_kind'],'publication')
        self.assertIn('Texto integral não foi consultado.',record['payload']['limitations'])
        self.assertEqual(research(self.sources,'search',['learning'],transport=lambda url:(_ for _ in ()).throw(AssertionError())),out)
    def test_research_does_not_send_free_biographical_text(self):
        with self.assertRaises(Invalid):query_terms(['meu nome é uma pessoa real'])
    def test_missing_abstract_does_not_invent_results(self):
        result=crossref(['memory'],transport=lambda url:{'message':{'items':[{'DOI':'10.1234/ficticio','title':['Sem resumo']}]}})
        self.assertEqual(result['documents'][0]['availability'],'metadata_only')
    def test_source_metadata_is_included_in_idempotency_contract(self):
        m={'source_kind':'web_page','reference_locator':'https://example.org','origin_description':'Fonte fictícia'}
        a=self.sources.apply('meta','create',title='Documento',text='Texto',source_metadata=m)
        self.assertEqual(a,self.sources.apply('meta','create',title='Documento',text='Texto',source_metadata=m))
        with self.assertRaises(Conflict):self.sources.apply('meta','create',title='Documento',text='Texto',source_metadata=dict(m,source_kind='document'))


    def test_duplicate_item_requires_revision_instead_of_new_identity(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1)
        with self.assertRaises(Invalid):
            self.k.apply('duplicate','assessment_response','Duplicada',{'assessment_ref':{'record_id':app['id'],'revision':1},
                'item_ref':{'record_id':inst['id'],'revision':1,'fragment':'i1'},'value':2,'source_refs':[self.ref]})
    def test_user_review_requires_literal_origin_and_preserves_scope(self):
        from revisoes import register
        record=self.k.apply('statement','assertion','Relato fictício',{'subject_ref':self.personref,'predicate':'reports_feeling',
            'value':{'type':'text','content':'fictício'},'nature':'user_report','asserted_by':'usuário fictício','source_refs':[self.ref],
            'recorded_time':NOW(),'context_description':'fixture','valid_time':{'precision':'unknown'},'review_status':'unreviewed'})
        with self.assertRaises(Invalid):
            register(self.sources,'bad-review',record['id'],1,'confirmed_by_user',self.ref,'frase ausente','apenas o relato')
        out=register(self.sources,'review',record['id'],1,'confirmed_by_user',self.ref,'Respostas fictícias','apenas o relato')
        self.assertEqual(out,register(self.sources,'review',record['id'],1,'confirmed_by_user',self.ref,'Respostas fictícias','apenas o relato'))
        current=self.k.read(out['id'])['record']
        self.assertEqual(current['payload']['review_status'],'confirmed_by_user')
        self.assertEqual(current['payload']['review_events'][-1]['scope'],'apenas o relato')
        with self.assertRaises(Conflict):register(self.sources,'stale-review',record['id'],1,'disputed_by_user',self.ref,'Respostas fictícias','somente isto')


    def test_reported_diagnosis_may_reference_source_but_not_person_or_score(self):
        base={'subject_ref':self.personref,'predicate':'reports_diagnosis','object_ref':self.ref,'nature':'user_report',
              'source_refs':[self.ref],'asserted_by':'usuário fictício','recorded_time':NOW(),'context_description':'fixture',
              'valid_time':{'precision':'unknown'},'review_status':'unreviewed'}
        self.k.apply('diagnosis-reference','assertion','Relato fictício, não diagnóstico confirmado',base)
        base['object_ref']=self.personref
        with self.assertRaises(Invalid):self.k.apply('bad-diagnosis','assertion','Alvo errado',base)
    def test_absence_map_does_not_replace_or_contradict_a_value(self):
        p={'entity_kind':'person','display_name':'Nome fictício','origin_refs':[self.ref],'identity_status':'identified',
           'field_states':{'display_name':'unknown'}}
        with self.assertRaises(Invalid):self.k.apply('contradiction','entity','Ausência contraditória',p)
        p['field_states']={'unprovided_detail':'not_asked'}
        self.k.apply('absence','entity','Lacuna explícita',p)


    def test_score_values_are_numeric_and_finite_even_when_marked_invalid(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        result=score(self.sources,'score',app['id']);record=self.k.read(result['id'])['record']
        for index,value in enumerate((True,False,'1',None,float('nan'),float('inf'),-float('inf'),10**400)):
            for status in ('current','needs_revalidation','invalid'):
                p=copy.deepcopy(record['payload']);p.update(dimension_scores={'d':value},score_validity_status=status)
                with self.subTest(value=value,status=status),self.assertRaises(Invalid):
                    self.k.apply('bad-score-'+str(index)+'-'+status,'assessment_score',record['title'],p,record['id'],1)
        self.assertEqual(self.k.read(result['id'])['record']['payload']['dimension_scores'],{'d':1})
        self.assertEqual(self.k.read(result['id'])['record']['revision'],1)

    def test_instrument_bounds_and_weights_are_finite_without_booleans(self):
        for field in ('min','max','weight'):
            for value in (True,float('nan'),float('inf'),-float('inf'),10**400):
                item={'id':'i1','min':0,'max':3,'dimension':'d'};item[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(Invalid):self.instrument(items=[item])
        self.instrument(items=[{'id':'i1','min':0,'max':3,'dimension':'d','weight':0.5}])

    def test_score_rejects_product_overflow(self):
        inst,app=self.assessment(items=[{'id':'i1','min':0,'max':3,'dimension':'d','weight':1e308}])
        self.response(inst,app,'i1',3)
        with self.assertRaises(Invalid):score(self.sources,'overflow',app['id'])
        self.assertFalse(any(record['record_type']=='assessment_score' for record in self.k.catalog()[0].values()))

    def test_score_rejects_accumulation_overflow(self):
        items=[{'id':'i'+str(i),'min':0,'max':1,'dimension':'d','weight':1e308} for i in (1,2)]
        inst,app=self.assessment(items=items);self.response(inst,app,'i1',1);self.response(inst,app,'i2',1)
        with self.assertRaises(Invalid):score(self.sources,'overflow',app['id'])

    def test_score_rejects_reverse_overflow_and_boolean_answers(self):
        inst,app=self.assessment(items=[{'id':'i1','min':1e308,'max':1.7e308,'dimension':'d','reverse':True}])
        response=self.response(inst,app,'i1',1.2e308)
        with self.assertRaises(Invalid):score(self.sources,'reverse-overflow',app['id'])
        old=self.k.read(response['id'])['record'];p=copy.deepcopy(old['payload']);p['value']=True
        self.k.apply('boolean-answer','assessment_response',old['title'],p,old['id'],1)
        with self.assertRaises(Invalid):score(self.sources,'boolean-score',app['id'])

    def _score_replay_case(self,after=False,legacy=False):
        inst,app=self.assessment();self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        first='2001-01-01T00:00:00+00:00';second='2002-01-01T00:00:00+00:00'
        with patch('avaliacoes.NOW',return_value=first),self.interrupt_write(after):
            with self.assertRaises(OSError if after else Locked):score(self.sources,'retry-score',app['id'])
        with self.k.connect() as c:
            operation,data,path=c.execute("SELECT key,data,path FROM operations WHERE status='proposed'").fetchone()
            if legacy:c.execute('DELETE FROM prepared_requests WHERE key=?',(operation,))
        if after:
            with self.assertRaises(Conflict):self.k.catalog()
        with patch('avaliacoes.NOW',return_value=second):result=score(self.sources,'retry-score',app['id'])
        self.assertEqual(self.k.read(result['id'])['record']['payload']['computed_at'],first)
        self.assertEqual((self.k.vault/path).read_bytes(),data)
        with self.k.connect() as c:self.assertIsNone(c.execute('SELECT request FROM prepared_requests WHERE key=?',(operation,)).fetchone()[0])
        self.assertEqual(result,score(self.sources,'retry-score',app['id']))

    def test_score_replays_frozen_request_before_write(self):self._score_replay_case()
    def test_score_replays_frozen_request_after_write(self):self._score_replay_case(after=True)
    def test_legacy_score_proposal_is_replayed_without_new_timestamp(self):self._score_replay_case(after=True,legacy=True)

    def test_score_recovers_request_frozen_before_proposal(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        first='2001-01-01T00:00:00+00:00'
        with patch('avaliacoes.NOW',return_value=first),patch.object(Knowledge,'apply',side_effect=sqlite3.OperationalError('fixture')):
            with self.assertRaises(sqlite3.OperationalError):score(self.sources,'prepared-score',app['id'])
        with patch('avaliacoes.NOW',return_value='2002-01-01T00:00:00+00:00'):result=score(self.sources,'prepared-score',app['id'])
        self.assertEqual(self.k.read(result['id'])['record']['payload']['computed_at'],first)

    def _finish_replay_case(self,after=False,at=1):
        inst,app=self.assessment(status='in_progress');answer=self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        first='2001-01-01T00:00:00+00:00'
        with patch('avaliacoes.NOW',return_value=first),self.interrupt_write(after,at):
            with self.assertRaises(OSError if after else Locked):finish(self.sources,'retry-finish',app['id'])
        with patch('avaliacoes.NOW',return_value='2002-01-01T00:00:00+00:00'):result=finish(self.sources,'retry-finish',app['id'])
        self.assertEqual(self.k.read(app['id'])['record']['payload']['ended_at'],first)
        self.assertEqual(self.k.read(result['id'])['record']['payload']['dimension_scores'],{'d':1})
        response=self.k.read(answer['id'])['record'];self.assertEqual(response['payload']['value'],1)
        self.assertEqual(response['payload']['assessment_ref']['revision'],2)
        self.assertEqual(finish(self.sources,'retry-finish',app['id']),result)

    def test_finish_replays_frozen_request_before_write(self):self._finish_replay_case()
    def test_finish_replays_frozen_request_after_write(self):self._finish_replay_case(after=True)
    def test_finish_replays_interrupted_response_link(self):self._finish_replay_case(after=True,at=2)

    def _review_replay_case(self,after=False,legacy=False):
        from revisoes import register
        statement=self.statement();first='2001-01-01T00:00:00+00:00'
        arguments=(self.sources,'retry-review',statement['id'],1,'confirmed_by_user',self.ref,'Respostas fictícias','apenas o relato')
        with patch('revisoes.NOW',return_value=first),self.interrupt_write(after):
            with self.assertRaises(OSError if after else Locked):register(*arguments)
        operation,request=self.k._pending_requests('assertion')[0]
        if legacy:
            with self.k.connect() as c:c.execute('DELETE FROM prepared_requests WHERE key=?',(operation,))
        with self.assertRaises(Invalid):
            self.k.apply(operation,request['kind'],request['title'],request['payload'],request['id'],request['expected'])
        with patch('revisoes.NOW',return_value='2002-01-01T00:00:00+00:00'):result=register(*arguments)
        record=self.k.read(result['id'])['record'];self.assertEqual(record['revision'],2)
        self.assertEqual(record['payload']['review_events'][-1]['reviewed_revision'],1)
        self.assertEqual(record['payload']['review_events'][-1]['recorded_at'],first)
        self.assertEqual(register(*arguments),result)

    def test_review_replays_frozen_request_before_write(self):self._review_replay_case()
    def test_review_replays_after_bytes_using_examined_revision(self):self._review_replay_case(after=True)
    def test_legacy_review_proposal_preserves_examined_revision(self):self._review_replay_case(after=True,legacy=True)

    def test_generic_writes_cannot_create_review_events_or_promote_human_status(self):
        statement=self.statement();record=self.k.read(statement['id'])['record']
        event={'actor':'user','reviewed_revision':1,'source_ref':self.ref,'quote':'Respostas fictícias','scope':'fixture','recorded_at':NOW()}
        for index,status in enumerate(('unreviewed','confirmed_by_user','disputed_by_user')):
            p=copy.deepcopy(record['payload']);p.update(review_status=status,review_events=[event])
            with self.assertRaises(Invalid):self.k.apply('forged-review-'+str(index),'assertion',record['title'],p,record['id'],1)
            with self.assertRaises(Invalid):self.k.apply('forged-new-'+str(index),'assertion',record['title'],p)
        with self.assertRaises(TypeError):self.k.apply('positional-auth','assertion',record['title'],record['payload'],record['id'],1,True)
        person=self.k.read(self.person['id'])['record'];p=copy.deepcopy(person['payload']);p['review_events']=[event]
        with self.assertRaises(Invalid):self.k.apply('entity-review','entity',person['title'],p,person['id'],1)

    def test_generic_write_preserves_history_but_cannot_rewrite_or_extend_confirmation(self):
        from revisoes import register
        statement=self.statement();register(self.sources,'review',statement['id'],1,'confirmed_by_user',self.ref,'Respostas fictícias','fixture')
        record=self.k.read(statement['id'])['record'];history=copy.deepcopy(record['payload']['review_events'])
        for index,mode in enumerate(('remove','edit','switch','content')):
            p=copy.deepcopy(record['payload'])
            if mode=='remove':p.pop('review_events');p['review_status']='unreviewed'
            if mode=='edit':p['review_events'][0]['scope']='outro alcance';p['review_status']='unreviewed'
            if mode=='switch':p['review_status']='disputed_by_user'
            if mode=='content':p['value']['content']='Outro conteúdo'
            with self.subTest(mode=mode),self.assertRaises(Invalid):self.k.apply('rewrite-review-'+str(index),'assertion',record['title'],p,record['id'],2)
        self.k.apply('preserve-review','assertion',record['title'],copy.deepcopy(record['payload']),record['id'],2)
        p=copy.deepcopy(record['payload']);p['review_status']='unreviewed';p['value']['content']='Conteúdo retificado, sem nova confirmação'
        self.k.apply('demote-review','assertion',record['title'],p,record['id'],3)
        current=self.k.read(record['id'])['record']
        self.assertEqual(current['payload']['review_events'],history)
        self.assertEqual(current['payload']['review_status'],'unreviewed')
        register(self.sources,'new-review',record['id'],4,'disputed_by_user',self.ref,'Respostas fictícias','outro alcance')
        self.assertEqual(self.k.read(record['id'])['record']['payload']['review_events'][:-1],history)

    def test_parent_reference_must_target_source_not_entity(self):
        with self.assertRaises(Invalid):
            self.sources.apply('entity-parent','create',title='Fonte fictícia',text='Texto fictício',
                source_metadata={'source_kind':'document','parent_source_ref':self.personref})

    def test_proposed_response_reserves_business_key_before_file_exists(self):
        inst,app=self.assessment()
        with self.interrupt_write():
            with self.assertRaises(Locked):self.response(inst,app,'i1',1)
        with self.k.connect() as c:
            operation,data=c.execute("SELECT key,data FROM operations WHERE status='proposed'").fetchone()
            c.execute('DELETE FROM prepared_requests WHERE key=?',(operation,))
            c.execute('DELETE FROM business_reservations')
        p=decode(data)['payload']
        with self.assertRaises(Conflict):self.k.apply('duplicate-proposal','assessment_response','Outra resposta',p)
        result=self.response(inst,app,'i1',1)
        with self.k.connect() as c:
            self.assertEqual(c.execute('SELECT record_id FROM business_reservations WHERE record_type=? AND assessment_id=? AND item_id=?',('assessment_response',app['id'],'i1')).fetchone(),(result['id'],))
        self.assertEqual(len([r for r in self.k.catalog()[0].values() if r['record_type']=='assessment_response']),1)

    def test_proposed_score_reserves_application_before_file_exists(self):
        inst,app=self.assessment();self.response(inst,app,'i1',1);self.response(inst,app,'i2',3)
        with self.interrupt_write():
            with self.assertRaises(Locked):score(self.sources,'original-score',app['id'])
        with self.k.connect() as c:c.execute('DELETE FROM business_reservations')
        with self.assertRaises(Conflict):score(self.sources,'other-score',app['id'])
        result=score(self.sources,'original-score',app['id'])
        self.assertEqual(self.k.read(result['id'])['record']['payload']['dimension_scores'],{'d':1})

    def test_additive_migration_reserves_legacy_records_without_rewriting_them(self):
        inst,app=self.assessment();response=self.response(inst,app,'i1',1)
        records,paths,_=self.k.catalog();path=paths[response['id']];before=path.read_bytes()
        with self.k.connect() as c:
            c.execute('DELETE FROM managed WHERE id=?',(response['id'],))
            c.execute('DROP TABLE business_reservations');c.execute('DROP TABLE prepared_requests')
        migrated=Knowledge(self.sources)
        migrated.apply('migration-trigger','entity','Conceito novo',{'entity_kind':'concept','content':'Fixture',
            'idea_scope':'fixture','origin_refs':[self.ref],'identity_status':'provisional'})
        with migrated.connect() as c:
            self.assertEqual(c.execute('SELECT record_id FROM business_reservations WHERE record_type=? AND assessment_id=? AND item_id=?',('assessment_response',app['id'],'i1')).fetchone(),(response['id'],))
            self.assertEqual([row[1] for row in c.execute('PRAGMA table_info(operations)')],['key','fingerprint','status','path','data','result'])
        p=records[response['id']]['payload']
        with self.assertRaises(Invalid):migrated.apply('legacy-duplicate','assessment_response','Duplicada',p)
        self.assertEqual(path.read_bytes(),before)

    def test_legacy_collisions_block_key_without_selecting_or_rewriting_owner(self):
        inst,app=self.assessment();response=self.response(inst,app,'i1',1)
        records,paths,_=self.k.catalog();duplicate=copy.deepcopy(records[response['id']]);duplicate['id']=str(uuid.uuid4())
        duplicate['title']='Duplicada legada';path=paths[response['id']].with_name('Duplicada legada.md');path.write_bytes(render(duplicate))
        before={p:p.read_bytes() for p in (paths[response['id']],path)}
        self.k.apply('legacy-collision-trigger','entity','Conceito novo',{'entity_kind':'concept','content':'Fixture',
            'idea_scope':'fixture','origin_refs':[self.ref],'identity_status':'provisional'})
        with self.k.connect() as c:
            self.assertEqual(c.execute('SELECT record_id FROM business_reservations WHERE record_type=? AND assessment_id=? AND item_id=?',('assessment_response',app['id'],'i1')).fetchone(),(None,))
        with self.assertRaises(Invalid):score(self.sources,'legacy-score',app['id'])
        for original,data in before.items():self.assertEqual(original.read_bytes(),data)


if __name__=='__main__':unittest.main(verbosity=2)
