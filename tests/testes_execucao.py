import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from nucleo import Store,REAL_SYSTEM,Invalid,Conflict,canon,sha
from conhecimento import Knowledge,FOLDERS
from execucao import Engine,DEFAULT,EXTRACTION_TYPES
from revisoes import register
from autonomia import atomic_json
from melhorias import evaluate,record,adopt,rollback


class FakeModel:
    def __init__(self,fn):self.fn=fn;self.calls=0
    def call(self,prompt):self.calls+=1;return self.fn(prompt)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=REAL_SYSTEM/'testes_temporarios');root=Path(self.tmp.name)
        self.sources=Store(root/'sistema',root/'cofre');self.k=Knowledge(self.sources)
        manual=self.sources.vault/'00_Manual';manual.mkdir()
        texts={'manual-cerebro-07-experiencias-e-entrevista.md':'Manual de entrevista inteiramente fictício.',
               'manual-cerebro-08-catalogo-de-dados.md':'Catálogo fictício; validar contratos no serviço.'}
        manifest={}
        for name,text in texts.items():
            raw=text.encode('utf-8');(manual/name).write_bytes(raw);manifest[name]=sha(raw)
        (self.sources.root/'manual_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
        for target in ('execucao.TextModel','execucao.LocalEmbeddings','urllib.request.OpenerDirector.open'):
            guard=patch(target,side_effect=AssertionError('provedor real proibido nesta fixture'))
            guard.start();self.addCleanup(guard.stop)
        self.cfg=copy.deepcopy(DEFAULT);self.cfg.update(enabled=True,max_model_calls=3,auto_adopt_config=True)
        atomic_json(self.sources.root/'execucao.json',self.cfg)
    def tearDown(self):self.tmp.cleanup()
    def engine(self,model=None,**kwargs):
        return Engine(self.sources,model_factory=lambda root:model,**kwargs)
    def extraction_context(self,items=None,key='extraction-fixture',text='Preferência fictícia às 09h.'):
        source=self.sources.apply(key,'create',title='Contribuição fictícia',text=text)
        payload={'source_ref':{'record_id':source['id'],'revision':1},'chunks':[text],
                 'received_at':self.sources.read(source['id'])['payload']['received_at']}
        if items is not None:payload['extractions']=items
        return {'input':payload,'previous':{},'step_id':'extract_0','demand_id':'fixture',
                'operation_key':key+'-operation'}
    def fixture_assertion(self,author_refs=None):
        source=self.sources.apply('assertion-source','create',title='Relato fictício',text='Pessoa fictícia prefere estudar às 16h.')
        ref={'record_id':source['id'],'revision':1}
        person=self.k.apply('assertion-person','entity','Pessoa fictícia',{'entity_kind':'person',
            'display_name':'Pessoa fictícia','origin_refs':[ref],'identity_status':'identified'})
        payload={'subject_ref':{'record_id':person['id'],'revision':1},'predicate':'reports_preference',
            'value':{'type':'text','content':'16h'},'nature':'user_report','asserted_by':'autora fictícia',
            'recorded_time':self.sources.read(source['id'])['payload']['received_at'],'source_refs':[ref],
            'context_description':'Somente fixture','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}
        if author_refs is not None:payload['author_refs']=copy.deepcopy(author_refs)
        result=self.k.apply('fixture-assertion','assertion','Preferência fictícia',payload)
        return self.k.catalog()[0][result['id']]
    def confirmed_assertion(self):
        record=self.fixture_assertion()
        source=self.sources.apply('confirmation-source','create',title='Revisão humana fictícia',text='Confirmo apenas a preferência fictícia às 16h.')
        register(self.sources,'human-review',record['id'],1,'confirmed_by_user',
            {'record_id':source['id'],'revision':1},'preferência fictícia às 16h','Somente a preferência relatada')
        return self.k.catalog()[0][record['id']]
    def interrupted_batch(self):
        items=[{'tipo':'entity','titulo':'Tema fictício '+str(index),'payload':{
            'entity_kind':'learning_topic','topic_description':'Fixture '+str(index),
            'origin_refs':[{'record_id':'$fonte' if index==0 else '$'+str(index-1),'revision':1}],
            'identity_status':'provisional'}} for index in range(3)]
        context=self.extraction_context(items,key='interrupted-batch');context['step_id']='apply_0'
        engine=self.engine();sync=os.fsync;calls=0
        def fail_after_fsync(descriptor):
            nonlocal calls
            sync(descriptor);calls+=1
            if calls==2:raise OSError('queda fictícia após fsync e antes da confirmação SQLite')
        with patch('os.fsync',side_effect=fail_after_fsync):
            with self.assertRaises(OSError) as failure:engine.apply_contribution(context)
        self.assertEqual(len(getattr(failure.exception,'partial_result')['completed']),1)
        keys=[sha(canon([context['operation_key'],index]).encode()) for index in range(3)]
        with self.k.connect() as connection:
            rows=connection.execute('SELECT key,status,path,data,result FROM operations').fetchall()
        operations={row[0]:{'status':row[1],'path':row[2],'data':row[3],'result':json.loads(row[4])} for row in rows}
        self.assertEqual(operations[keys[0]]['status'],'confirmed')
        self.assertEqual(operations[keys[1]]['status'],'proposed');self.assertNotIn(keys[2],operations)
        return context,keys,operations
    def test_contribution_captures_original_and_applies_existing_tools(self):
        e=self.engine();payload={'text':'  Texto fictício completo.\n','extractions':[],'title':'Original'}
        ident=e.start('contribution','contribution',payload);result=e.run(ident)
        self.assertEqual(result['status'],'completed');self.assertEqual(len(self.sources.list()),1)
        self.assertEqual(self.sources.read(self.sources.list()[0]['id'])['payload']['content'],payload['text'])
        self.assertEqual(e.start('contribution','contribution',payload),ident)
    def test_model_failure_does_not_lose_original_contribution(self):
        def fail(prompt):raise ConnectionError('provedor fictício indisponível')
        e=self.engine(FakeModel(fail));ident=e.start('new','contribution',{'text':'Fala fictícia original'})
        result=e.run(ident);self.assertEqual(result['status'],'failed');self.assertEqual(len(self.sources.list()),1)
    def test_clarification_waits_registers_question_and_resumes(self):
        original=self.sources.apply('source','create',title='Relato fictício',text='Dani Souza mora em Curitiba. Dani Lima mora em Recife.')
        def answer(prompt):
            if '"clarification":null' in prompt:return {'decision':'ask','question':'Você se refere a Dani Souza ou Dani Lima?','citations':[]}
            return {'decision':'answer','answer':'Dani Lima mora em Recife.','citations':[{'record_id':original['id'],'revision':1,'quote':'Dani Lima mora em Recife.'}]}
        e=self.engine(FakeModel(answer));ident=e.start('question','question',{'query':'Em qual cidade Dani mora?'})
        self.assertEqual(e.run(ident)['status'],'waiting_user')
        result=e.answer(ident,'Dani Lima');self.assertEqual(result['status'],'completed')
        question=[r for r in self.k.catalog()[0].values() if r['record_type']=='question'][0]
        self.assertEqual(question['payload']['resolution_status'],'resolved')
        self.assertEqual(e.answer(ident,'Dani Lima')['status'],'completed')
    def test_unknown_research_terms_do_not_leave_the_program(self):
        calls=[]
        e=self.engine(transport=lambda url:calls.append(url))
        ident=e.start('research','research',{'research_terms':['nome pessoal não autorizado']})
        self.assertEqual(e.run(ident)['status'],'uncertain');self.assertEqual(calls,[])
    def test_lossy_or_unregistered_configuration_cannot_be_adopted(self):
        result=evaluate(self.sources,'no',{'kind':'remove_source_text','value':True})
        self.assertFalse(result['eligible'])
    def test_configuration_adoption_and_rollback_preserve_old_value(self):
        self.cfg['message_codec']='pretty';atomic_json(self.sources.root/'execucao.json',self.cfg)
        ev=evaluate(self.sources,'eval',{'kind':'message_codec','value':'compact','reason':'Reduzir transporte JSON'})
        self.assertTrue(ev['eligible']);candidate=record(self.sources,'record',ev)['candidate_record']
        change=adopt(self.sources,'adopt',candidate['id']);self.assertEqual(change['status'],'adopted')
        self.assertEqual(json.loads((self.sources.root/'execucao.json').read_text(encoding='utf-8'))['message_codec'],'compact')
        restored=rollback(self.sources,'adopt');self.assertEqual(restored['status'],'rolled_back')
        self.assertEqual(json.loads((self.sources.root/'execucao.json').read_text(encoding='utf-8'))['message_codec'],'pretty')
    def test_concurrent_configuration_change_blocks_adoption(self):
        self.cfg['message_codec']='pretty';atomic_json(self.sources.root/'execucao.json',self.cfg)
        ev=evaluate(self.sources,'eval',{'kind':'message_codec','value':'compact'});candidate=record(self.sources,'record',ev)['candidate_record']
        self.cfg['max_actions']=24;atomic_json(self.sources.root/'execucao.json',self.cfg)
        with self.assertRaises(Conflict):adopt(self.sources,'adopt',candidate['id'])
    def test_partial_extraction_failure_keeps_confirmed_records_visible(self):
        items=[{'tipo':'entity','titulo':title,'payload':{'entity_kind':'learning_topic','topic_description':'Teste',
            'origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}}
            for title in ('Primeiro tema fictício','Segundo tema fictício')]
        e=self.engine();ident=e.start('partial','contribution',{'text':'Texto fictício completo.','extractions':items})
        apply=e.k.apply
        def fail_second(*args,**kwargs):
            if args[2]=='Segundo tema fictício':raise OSError('falha fictícia após a primeira gravação')
            return apply(*args,**kwargs)
        with patch.object(e.k,'apply',side_effect=fail_second):result=e.run(ident)
        self.assertEqual(result['status'],'uncertain')
        failed=next(s for s in result['steps'] if s['capability']=='apply_contribution')
        partial=json.loads(failed['result']);self.assertEqual(len(partial['completed']),1);self.assertEqual(partial['pending_from'],1)
        extracted=next(s for s in result['steps'] if s['capability']=='extract')
        context={'input':json.loads(result['demand']['payload']),'previous':{'extract_0':json.loads(extracted['result'])},
                 'step_id':'apply_0','operation_key':failed['operation_key']}
        with patch.object(e.k,'apply',wraps=apply) as writes:resumed=e.apply_contribution(context)
        self.assertEqual(len(resumed['completed']),2);self.assertEqual(writes.call_count,1)
        self.assertEqual(resumed['completed'][0],partial['completed'][0])
        self.assertEqual(len([r for r in self.k.catalog()[0].values() if r['record_type']=='entity']),2)


    def test_new_engine_resumes_batch_after_fsync_before_sqlite_confirmation(self):
        context,keys,operations=self.interrupted_batch();pending=operations[keys[1]]
        path=self.sources.vault/pending['path'];written=path.read_bytes()
        self.assertEqual(written,pending['data'])
        with self.k.connect() as connection:
            self.assertIsNone(connection.execute('SELECT 1 FROM managed WHERE id=?',(pending['result']['id'],)).fetchone())
        with self.assertRaises(Conflict):self.k.catalog()
        engine=self.engine()
        with patch.object(engine.k,'_resume',wraps=engine.k._resume) as replayed, \
             patch.object(engine.k,'apply',wraps=engine.k.apply) as applied,patch('os.fsync',wraps=os.fsync) as synced:
            result=engine.apply_contribution(copy.deepcopy(context))
        replayed.assert_called_once_with(keys[1],review_authorized=False)
        self.assertEqual([call.args[0] for call in applied.call_args_list],keys[1:])
        self.assertEqual(synced.call_count,1);self.assertEqual(path.read_bytes(),written)
        self.assertEqual(result['completed'][:2],[operations[keys[0]]['result'],pending['result']])
        self.assertEqual(len(result['completed']),3)
        records=self.k.catalog()[0]
        self.assertEqual(len([r for r in records.values() if r['record_type']=='entity']),3)
        self.assertTrue(all(records[row['id']]['revision']==1 for row in result['completed']))
        repeated=self.engine()
        with patch.object(repeated.k,'_resume',side_effect=AssertionError('confirmados não exigem reconciliação')), \
             patch.object(repeated.k,'apply',side_effect=AssertionError('confirmados não devem ser reaplicados')):
            self.assertEqual(repeated.apply_contribution(copy.deepcopy(context)),result)
    def test_pending_replay_compares_the_entire_frozen_batch_request(self):
        context,keys,operations=self.interrupted_batch();variants=[]
        for field,value in (('titulo','Título diferente'),('tipo','question'),('revisao_esperada',1)):
            changed=copy.deepcopy(context);changed['input']['extractions'][1][field]=value;variants.append((field,changed))
        changed=copy.deepcopy(context);changed['input']['extractions'][1]['payload']['topic_description']='Outro conteúdo'
        variants.append(('payload',changed))
        changed=copy.deepcopy(context);changed['input']['extractions'][1].update(
            record_id=operations[keys[0]]['result']['id'],revisao_esperada=1);variants.append(('identity',changed))
        changed=copy.deepcopy(context);changed['input']['extractions'][2]['tipo']='process_definition'
        variants.append(('contract',changed))
        changed=copy.deepcopy(context);changed['operation_key']='another-batch-operation';variants.append(('batch',changed))
        source=self.sources.apply('another-source','create',title='Outra fonte fictícia',text='Outra contribuição fictícia.')
        changed=copy.deepcopy(context);changed['input']['source_ref']={'record_id':source['id'],'revision':1}
        variants.append(('source',changed))
        for label,changed in variants:
            with self.subTest(change=label):
                engine=self.engine()
                with patch.object(engine.k,'_resume',side_effect=AssertionError('pedido divergente não pode ser reconciliado')), \
                     patch.object(engine.k,'apply',side_effect=AssertionError('pedido divergente não pode gravar')):
                    with self.assertRaises((Invalid,Conflict)):engine.apply_contribution(changed)
                with self.k.connect() as connection:
                    self.assertEqual(connection.execute('SELECT status FROM operations WHERE key=?',(keys[1],)).fetchone()[0],'proposed')
                    self.assertIsNone(connection.execute('SELECT 1 FROM operations WHERE key=?',(keys[2],)).fetchone())
    def test_pending_replay_requires_source_and_execution_and_review_authorization(self):
        context,keys,_=self.interrupted_batch()
        with self.k.connect() as connection:
            connection.execute('UPDATE prepared_requests SET review_authorized=1 WHERE key=?',(keys[1],))
        engine=self.engine()
        with patch.object(engine.k,'_resume',side_effect=AssertionError('não usar capacidade de revisão humana')):
            with self.assertRaises(Invalid):engine.apply_contribution(copy.deepcopy(context))
        with self.k.connect() as connection:
            connection.execute('UPDATE prepared_requests SET review_authorized=0 WHERE key=?',(keys[1],))
        denied=self.engine(authorize=lambda:False)
        with patch.object(denied.k,'_resume',side_effect=AssertionError('acesso revogado não pode reconciliar')):
            with self.assertRaises(Invalid):denied.apply_contribution(copy.deepcopy(context))
        source=context['input']['source_ref']
        self.sources.apply('correct-input','correct',ident=source['record_id'],expected=1,
            text='Contribuição fictícia corrigida.',reason='Correção fictícia durante a interrupção')
        with patch.object(engine.k,'_resume',side_effect=AssertionError('fonte corrigida não pode reconciliar')):
            with self.assertRaises(Conflict):engine.apply_contribution(copy.deepcopy(context))
        with self.k.connect() as connection:
            self.assertEqual(connection.execute('SELECT status FROM operations WHERE key=?',(keys[1],)).fetchone()[0],'proposed')
    def test_reconciliation_does_not_apply_new_items_before_normal_preflight(self):
        context,keys,_=self.interrupted_batch();del context['input']['extractions'][2]['payload']['topic_description']
        engine=self.engine()
        with patch.object(engine.k,'_resume',wraps=engine.k._resume) as resumed,patch.object(engine.k,'apply',wraps=engine.k.apply) as applied:
            with self.assertRaises(Invalid):engine.apply_contribution(context)
        resumed.assert_called_once_with(keys[1],review_authorized=False)
        self.assertEqual([call.args[0] for call in applied.call_args_list],[keys[1]])
        with self.k.connect() as connection:
            self.assertEqual(connection.execute('SELECT status FROM operations WHERE key=?',(keys[1],)).fetchone()[0],'confirmed')
            self.assertIsNone(connection.execute('SELECT 1 FROM operations WHERE key=?',(keys[2],)).fetchone())
    def test_frozen_request_without_proposal_still_requires_full_preflight(self):
        item={'tipo':'entity','titulo':'Extração inválida congelada','payload':{}}
        context=self.extraction_context([item],key='frozen-only');context['step_id']='apply_0'
        key=sha(canon([context['operation_key'],0]).encode())
        with patch.object(self.k,'_apply_prepared',side_effect=OSError('queda fictícia antes da validação')):
            with self.assertRaises(OSError):self.k._frozen_apply(key,item['tipo'],item['titulo'],item['payload'])
        engine=self.engine()
        with patch.object(engine.k,'_resume',side_effect=AssertionError('congelamento não autoriza nova gravação')), \
             patch.object(engine.k,'apply',side_effect=AssertionError('item novo inválido não pode gravar')):
            with self.assertRaises(Invalid):engine.apply_contribution(context)
        with self.k.connect() as connection:
            self.assertIsNone(connection.execute('SELECT 1 FROM operations WHERE key=?',(key,)).fetchone())
    def test_new_engine_resumes_assertion_update_after_fsync_without_new_human_review(self):
        old=self.confirmed_assertion();payload=copy.deepcopy(old['payload'])
        payload['value']['content']='09h';payload['source_refs']=[{'record_id':'$fonte','revision':1}]
        item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],'revisao_esperada':old['revision'],'payload':payload}
        context=self.extraction_context([item],key='interrupted-update');engine=self.engine()
        context['previous']={'extract_0':engine.extract(context)};context['step_id']='apply_0'
        sync=os.fsync
        def fail_after_fsync(descriptor):
            sync(descriptor);raise OSError('queda fictícia após fsync de atualização')
        with patch('os.fsync',side_effect=fail_after_fsync):
            with self.assertRaises(OSError):engine.apply_contribution(context)
        key=sha(canon([context['operation_key'],0]).encode())
        with self.assertRaises(Conflict):self.k.catalog()
        restarted=self.engine()
        with patch.object(restarted.k,'_resume',wraps=restarted.k._resume) as resumed,patch('os.fsync',side_effect=AssertionError('bytes já gravados')):
            result=restarted.apply_contribution(copy.deepcopy(context))
        resumed.assert_called_once_with(key,review_authorized=False)
        current=self.k.catalog()[0][old['id']]
        self.assertEqual(result['completed'][0]['revision'],old['revision']+1)
        self.assertEqual(current['payload']['review_status'],'clarification_needed')
        self.assertEqual(current['payload']['review_events'],old['payload']['review_events'])
        self.assertEqual(current['payload']['value']['content'],'09h')
    def test_invalid_explicit_batch_is_rejected_before_any_derived_write(self):
        items=[{'tipo':'entity','titulo':'Tema fictício','payload':{'entity_kind':'learning_topic','topic_description':'Teste',
            'origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}},
            {'tipo':'assertion','titulo':'Inválida','payload':{}}]
        e=self.engine();ident=e.start('invalid-batch','contribution',{'text':'Original fictício preservado.','extractions':items})
        with patch.object(e.k,'apply',side_effect=AssertionError('lote inválido não pode gravar')):
            result=e.run(ident)
        self.assertEqual(result['status'],'failed');self.assertEqual(len(self.sources.list()),1)
        self.assertFalse(any(r['record_type']!='source' for r in self.k.catalog()[0].values()))
    def test_explicit_extraction_cannot_use_other_registered_families(self):
        e=self.engine();self.assertEqual(EXTRACTION_TYPES,{'entity','assertion','synthesis','question'})
        for index,kind in enumerate(sorted(set(FOLDERS)-EXTRACTION_TYPES|{'source','unknown'})):
            with self.subTest(kind=kind):
                item={'tipo':kind,'titulo':'Família proibida','payload':{}}
                context=self.extraction_context([item],key='forbidden-'+str(index))
                with patch.object(e.k,'_validate',side_effect=AssertionError('família proibida chegou ao núcleo')):
                    with self.assertRaisesRegex(Invalid,'família'):e.extract(context)
    def test_model_extraction_cannot_expand_allowed_types(self):
        item={'tipo':'process_definition','titulo':'Processo não permitido','evidence_quote':'Preferência fictícia',
              'payload':{}}
        model=FakeModel(lambda prompt:{'extractions':[item]});e=self.engine(model)
        context=self.extraction_context()
        with patch.object(e,'model',return_value=model):
            with self.assertRaisesRegex(Invalid,'família'):e.extract(context)
        self.assertEqual(model.calls,2)
    def test_model_contract_lists_the_enforced_record_types(self):
        def propose(prompt):
            contract=json.loads(prompt.split('CONTRATO_EXECUTAVEL: ',1)[1].split('\n',1)[0])
            self.assertEqual(set(contract['allowed_record_types']),EXTRACTION_TYPES)
            return {'extractions':[]}
        model=FakeModel(propose);e=self.engine(model);context=self.extraction_context()
        with patch.object(e,'model',return_value=model):result=e.extract(context)
        assert isinstance(result,dict)
        self.assertEqual(result['extractions'],[])
    def test_apply_rechecks_entire_batch_without_trusting_previous_step(self):
        items=[{'tipo':'entity','titulo':'Tema fictício','payload':{'entity_kind':'learning_topic','topic_description':'Teste',
            'origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}},
            {'tipo':'process_definition','titulo':'Não permitido','payload':{}}]
        e=self.engine();context=self.extraction_context(items);context['step_id']='apply_0'
        with patch.object(e.k,'apply',side_effect=AssertionError('lote inválido não pode gravar')):
            with self.assertRaises(Invalid):e.apply_contribution(context)
        self.assertFalse(any(r['record_type']!='source' for r in self.k.catalog()[0].values()))
    def test_automatic_and_explicit_updates_cannot_fabricate_human_reviews(self):
        old=self.fixture_assertion();e=self.engine()
        for explicit in (False,True):
            for status in ('confirmed_by_user','disputed_by_user'):
                with self.subTest(explicit=explicit,status=status):
                    payload=copy.deepcopy(old['payload']);payload['review_status']=status
                    payload['review_events']=[{'actor':'user','reviewed_revision':1,
                        'source_ref':{'record_id':'$fonte','revision':1},'quote':'Preferência fictícia',
                        'scope':'Alcance inventado pelo modelo','recorded_at':'2026-11-02T00:00:00Z'}]
                    item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],'revisao_esperada':1,
                          'payload':payload,'evidence_quote':'Preferência fictícia'}
                    context=self.extraction_context([item] if explicit else None,
                        key=('explicit-' if explicit else 'model-')+status)
                    model=FakeModel(lambda prompt:{'extractions':[item]})
                    with patch.object(e,'model',return_value=model):
                        with self.assertRaises(Invalid):e.extract(context)
                    self.assertEqual(model.calls,0 if explicit else 2)
                    self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_automatic_update_preserves_history_without_confirming_new_content(self):
        old=self.confirmed_assertion();payload=copy.deepcopy(old['payload'])
        payload['value']['content']='09h';payload['source_refs']=[{'record_id':'$fonte','revision':1}]
        del payload['review_events']
        item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],'revisao_esperada':old['revision'],'payload':payload}
        e=self.engine();context=self.extraction_context([item]);extracted=e.extract(context)
        context.update(step_id='apply_0',previous={'extract_0':extracted})
        with patch.object(e.k,'apply',wraps=e.k.apply) as writes:result=e.apply_contribution(context)
        self.assertEqual(result['status'],'confirmed');self.assertEqual(writes.call_count,1)
        assert writes.call_args is not None
        self.assertNotIn('review_authorized',writes.call_args.kwargs)
        current=self.k.catalog()[0][old['id']]
        self.assertEqual(current['revision'],old['revision']+1)
        self.assertEqual(current['payload']['review_status'],'clarification_needed')
        self.assertEqual(current['payload']['review_events'],old['payload']['review_events'])
        self.assertEqual(current['payload']['review_events'][-1]['reviewed_revision'],1)
        for field in ('asserted_by','nature','recorded_time'):
            self.assertEqual(current['payload'][field],old['payload'][field])
        with patch.object(e.k,'apply',wraps=e.k.apply) as repeated:
            self.assertEqual(e.apply_contribution(context),result)
        self.assertEqual(repeated.call_count,0)
        self.assertEqual(self.k.catalog()[0][old['id']],current)
        context['previous']['extract_0']['extractions'][0]['payload']['value']['content']='08h'
        with self.assertRaises(Conflict):e.apply_contribution(context)
    def test_explicit_update_cannot_rewrite_or_delete_human_history(self):
        old=self.confirmed_assertion();e=self.engine()
        changes=[[],[dict(old['payload']['review_events'][0],scope='Alcance ampliado pelo modelo')],
                 [dict(old['payload']['review_events'][0],reviewed_revision=old['revision'])]]
        for index,events in enumerate(changes):
            with self.subTest(events=events):
                payload=copy.deepcopy(old['payload']);payload['review_events']=events
                item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],
                      'revisao_esperada':old['revision'],'payload':payload}
                context=self.extraction_context([item],key='history-'+str(index))
                with self.assertRaisesRegex(Invalid,'eventos'):e.extract(context)
                self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_extraction_cannot_change_assertion_authorship_or_control(self):
        old=self.fixture_assertion();e=self.engine()
        for index,(field,value) in enumerate((('asserted_by','outro autor'),('nature','inference'),
                ('recorded_time','2000-01-01'),('author_refs',[]),('created_by','user'),('review_authorized',True))):
            with self.subTest(field=field):
                payload=copy.deepcopy(old['payload']);payload[field]=value
                item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],'revisao_esperada':1,'payload':payload}
                context=self.extraction_context([item],key='control-'+str(index))
                with self.assertRaisesRegex(Invalid,'autoria ou controle'):e.extract(context)
                self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_author_reference_technical_update_requires_current_revision(self):
        author=self.sources.apply('author-source','create',title='Autora fictícia',text='Identidade fictícia da autora.')
        ref={'record_id':author['id'],'revision':1,'fragment':'/author','role':'relator'}
        old=self.fixture_assertion(author_refs=[ref])
        self.sources.apply('correct-author','correct',ident=author['id'],expected=1,
            text='Identidade fictícia da autora; anotação técnica corrigida.',reason='Correção técnica fictícia')
        engine=self.engine();item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],
            'revisao_esperada':old['revision'],'payload':copy.deepcopy(old['payload'])}
        for index,revision in enumerate((1,3,None)):
            with self.subTest(revision=revision):
                stale=copy.deepcopy(item)
                if revision is None:del stale['payload']['author_refs']
                else:stale['payload']['author_refs'][0]['revision']=revision
                with self.assertRaises(Conflict):engine.extract(self.extraction_context([stale],key='stale-author-'+str(index)))
        item['payload']['author_refs'][0]['revision']=2
        context=self.extraction_context([item],key='technical-author',text='Preferência fictícia às 16h.')
        context['previous']={'extract_0':engine.extract(context)};context['step_id']='apply_0'
        self.assertEqual(engine.apply_contribution(context)['status'],'confirmed')
        current=self.k.read(old['id'])['record'];self.assertIsNotNone(current)
        self.assertEqual(current['payload']['author_refs'],[dict(ref,revision=2)])
        self.assertEqual(current['payload']['asserted_by'],old['payload']['asserted_by'])
    def test_author_reference_cannot_be_replaced_by_another_existing_author(self):
        first=self.sources.apply('author-one','create',title='Primeira autora fictícia',text='Autora fictícia original.')
        other=self.sources.apply('author-two','create',title='Outra autora fictícia',text='Outra identidade fictícia.')
        ref={'record_id':first['id'],'revision':1,'fragment':'/author','role':'relator'}
        old=self.fixture_assertion(author_refs=[ref]);payload=copy.deepcopy(old['payload'])
        payload['author_refs'][0]['record_id']=other['id']
        item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],'revisao_esperada':1,'payload':payload}
        with self.assertRaisesRegex(Invalid,'autoria ou controle'):
            self.engine().extract(self.extraction_context([item]))
        self.assertEqual(self.k.catalog()[0][old['id']],old)
    def test_explicit_extraction_requires_current_update_revision(self):
        old=self.fixture_assertion();e=self.engine()
        for index,expected in enumerate((None,0,2,True)):
            with self.subTest(expected=expected):
                item={'tipo':'assertion','titulo':old['title'],'record_id':old['id'],
                      'revisao_esperada':expected,'payload':old['payload']}
                with self.assertRaises(Conflict):e.extract(self.extraction_context([item],key='revision-'+str(index)))
    def test_explicit_placeholders_require_revision_one(self):
        e=self.engine()
        for index,revision in enumerate((None,2,True)):
            with self.subTest(revision=revision):
                ref:dict[str,object]={'record_id':'$fonte'}
                if revision is not None:ref['revision']=revision
                item={'tipo':'entity','titulo':'Tema fictício','payload':{'entity_kind':'learning_topic',
                    'topic_description':'Teste','origin_refs':[ref],'identity_status':'provisional'}}
                with self.assertRaisesRegex(Invalid,'placeholder'):
                    e.extract(self.extraction_context([item],key='placeholder-'+str(index)))
    def test_valid_explicit_batch_resolves_references_to_previous_extractions(self):
        items=[{'tipo':'entity','titulo':'Pessoa fictícia','payload':{'entity_kind':'person','display_name':'Pessoa fictícia',
                    'origin_refs':[{'record_id':'$fonte','revision':1}],'identity_status':'provisional'}},
               {'tipo':'assertion','titulo':'Preferência fictícia','payload':{'subject_ref':{'record_id':'$0','revision':1},
                    'predicate':'reports_preference','value':{'type':'text','content':'09h'},'nature':'user_report',
                    'asserted_by':'autora fictícia','recorded_time':'2026-11-02T00:00:00Z',
                    'source_refs':[{'record_id':'$fonte','revision':1}],'context_description':'Fixture',
                    'valid_time':{'precision':'unknown'},'review_status':'unreviewed'}}]
        e=self.engine();ident=e.start('valid-batch','contribution',{'text':'Preferência fictícia às 09h.','extractions':items})
        self.assertEqual(e.run(ident)['status'],'completed')
        records=self.k.catalog()[0];assertion=next(r for r in records.values() if r['record_type']=='assertion')
        self.assertEqual(records[assertion['payload']['subject_ref']['record_id']]['record_type'],'entity')
    def test_repeated_answer_respects_execute_false_and_does_not_repeat_completed_work(self):
        source=self.sources.apply('clarification-source','create',title='Relato fictício',text='Dani fictícia mora em Recife.')
        def respond(prompt):
            if '"clarification":null' in prompt:return {'decision':'ask','question':'Qual Dani fictícia?','citations':[]}
            return {'decision':'answer','answer':'Dani fictícia mora em Recife.',
                    'citations':[{'record_id':source['id'],'revision':1,'quote':'Recife'}]}
        model=FakeModel(respond);e=self.engine(model);ident=e.start('repeat-answer','question',{'query':'Onde mora Dani fictícia?'})
        self.assertEqual(e.run(ident)['status'],'waiting_user')
        self.assertEqual(e.answer(ident,'A Dani fictícia',execute=False)['status'],'queued')
        before=e.q.inspect(ident);records=copy.deepcopy(self.k.catalog()[0]);calls=model.calls
        with patch.object(e,'run',side_effect=AssertionError('execute=False não pode executar')):
            self.assertEqual(e.answer(ident,'A Dani fictícia',execute=False)['status'],'queued')
        self.assertEqual(e.q.inspect(ident),before);self.assertEqual(self.k.catalog()[0],records);self.assertEqual(model.calls,calls)
        self.assertEqual(e.run(ident)['status'],'completed');completed=e.q.inspect(ident);calls=model.calls
        with patch.object(e,'run',side_effect=AssertionError('demanda concluída não pode ser reexecutada')):
            for execute in (False,True):self.assertEqual(e.answer(ident,'A Dani fictícia',execute=execute)['status'],'completed')
        self.assertEqual(e.q.inspect(ident),completed);self.assertEqual(model.calls,calls)
        with self.assertRaises(Conflict):e.answer(ident,'Outra pessoa fictícia',execute=False)
    def test_insufficient_context_routes_generic_research_without_biographical_query(self):
        from apoio_testes04 import transport,Model
        evidence=Model(self.sources)
        calls=[]
        def answer(prompt):
            if 'Determine se é possível' in prompt:
                return {'decision':'insufficient','answer':'Falta evidência externa.','citations':[],'research_terms':['learning','adult']}
            return evidence.call(prompt)
        engine=self.engine(FakeModel(answer),transport=lambda url:(calls.append(url) or transport(url)))
        ident=engine.start('external-fallback','question',{'query':'Pergunta fictícia sem evidência local'})
        result=engine.run(ident)
        self.assertEqual(result['status'],'completed');self.assertEqual(len(calls),1)
        response=json.loads(result['steps'][-1]['result']);self.assertEqual(response['quality'],'limited')
        self.assertEqual(len(response['source_refs']),1)


if __name__=='__main__':unittest.main(verbosity=2)
