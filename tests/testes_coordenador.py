import json,sys,tempfile,threading,unittest
from pathlib import Path
from nucleo import REAL_SYSTEM as SYSTEM
from coordenador import Coordinator,Capability,ContractError,NeedAnswer,plan_for,validate_plan

LIMITS={'max_actions':12,'max_model_calls':2,'max_seconds':600}


def step(name='one',depends=None):
    return {'id':name,'capability':name,'version':'v1','depends_on':depends or []}


def cap(fn,**kwargs):
    return Capability('v1',fn,lambda r:isinstance(r,dict) and r.get('ok') is True,**kwargs)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=SYSTEM/'testes_temporarios')
        self.root=Path(self.tmp.name)
        self.active=True;self.generation='g1';self.now=1000.0
        self.q=Coordinator(self.root/'coordenador',authorize=lambda:self.active,
            context_token=lambda:self.generation,clock=lambda:self.now,
            origin_validator=lambda ref:ref=={'record_id':'ficticio','revision':1})
    def tearDown(self):self.tmp.cleanup()
    def submit(self,steps=None,limits=None):return self.q.submit('pedido',steps or [step()],{},limits or LIMITS)

    def test_intent_selects_existing_contracts_and_no_extra_area(self):
        route=plan_for('correction')
        self.assertEqual([s['capability'] for s in route],['correct_source','find_affected','semantic_revalidation','respond'])
        validate_plan(route)
        with self.assertRaises(ContractError):plan_for('executar_codigo_da_nota')

    def test_unknown_capability_blocks_instead_of_completing(self):
        ident=self.submit();self.assertEqual(self.q.run_until_pause(ident),'blocked')
        self.assertEqual(self.q.inspect(ident)['demand']['actions'],0)

    def test_success_requires_validated_output(self):
        self.q.capabilities['one']=cap(lambda c:{'ok':False})
        ident=self.submit();self.assertEqual(self.q.run_until_pause(ident),'failed')

    def test_dependency_outputs_are_delivered_in_order(self):
        self.q.capabilities['one']=cap(lambda c:{'ok':True,'value':3})
        self.q.capabilities['two']=cap(lambda c:{'ok':c['previous']['one']['value']==3})
        ident=self.submit([step(),step('two',['one'])])
        self.assertEqual(self.q.run_until_pause(ident),'completed')

    def test_cycles_and_missing_dependencies_are_rejected(self):
        for plan in ([step('one',['one'])],[step('one',['missing'])],
                     [step('one',['two']),step('two',['one'])]):
            with self.assertRaises(ContractError):validate_plan(plan)

    def test_same_request_is_idempotent_and_changed_request_is_rejected(self):
        ident=self.submit();self.assertEqual(ident,self.submit())
        with self.assertRaises(ContractError):self.q.submit('pedido',[step()],{'different':True},LIMITS)

    def test_wait_does_not_repeat_question_until_answer_with_origin(self):
        calls=[]
        def handler(c):
            calls.append(1)
            if not c['answer']:raise NeedAnswer('Qual horário foi relatado?')
            return {'ok':c['answer']['value']=='09h'}
        self.q.capabilities['one']=cap(handler)
        ident=self.submit();self.assertEqual(self.q.run_until_pause(ident),'waiting_user')
        self.assertEqual(self.q.run_until_pause(ident),'waiting_user');self.assertEqual(len(calls),1)
        with self.assertRaises(ContractError):self.q.answer(ident,'09h',{'record_id':'inventado'})
        self.q.answer(ident,'09h',{'record_id':'ficticio','revision':1})
        self.assertEqual(self.q.run_until_pause(ident),'completed')

    def test_waiting_does_not_renew_deadline(self):
        def handler(c):raise NeedAnswer('Detalhe necessário?')
        self.q.capabilities['one']=cap(handler)
        ident=self.submit();deadline=self.q.inspect(ident)['demand']['deadline']
        self.q.run_until_pause(ident);self.now=deadline+1
        with self.assertRaises(ContractError):self.q.answer(ident,'resposta',{'record_id':'ficticio','revision':1})
        self.assertEqual(self.q.inspect(ident)['demand']['deadline'],deadline)

    def test_persistent_state_resumes_only_pending_steps(self):
        calls=[]
        self.q.capabilities={'one':cap(lambda c:(calls.append('one') or {'ok':True})),
                             'two':cap(lambda c:(calls.append('two') or {'ok':True}))}
        ident=self.submit([step(),step('two',['one'])]);self.assertEqual(self.q.run_one(ident),'queued')
        reopened=Coordinator(self.root/'coordenador',self.q.capabilities,context_token=lambda:'g1',clock=lambda:self.now)
        self.assertEqual(reopened.run_until_pause(ident),'completed');self.assertEqual(calls,['one','two'])

    def test_revoked_access_blocks_reading_and_new_execution(self):
        ident=self.submit();self.active=False
        with self.assertRaises(ContractError):self.q.inspect(ident)
        self.assertEqual(self.q.run_one(ident),'blocked')
        self.assertEqual(self.q.cancel(ident),'cancelled')

    def test_changed_context_requires_review_before_resume(self):
        ident=self.submit();self.generation='g2';self.assertEqual(self.q.run_one(ident),'blocked')

    def test_model_budget_is_shared_and_charged_before_call(self):
        calls=[]
        self.q.capabilities={name:cap(lambda c:(calls.append(1) or {'ok':True}),uses_model=True) for name in ('one','two')}
        ident=self.submit([step(),step('two',['one'])],dict(LIMITS,max_model_calls=1))
        self.assertEqual(self.q.run_until_pause(ident),'failed');self.assertEqual(len(calls),1)
        self.assertEqual(self.q.inspect(ident)['demand']['model_calls'],1)

    def test_step_budget_is_not_reset_on_restart(self):
        calls=[]
        self.q.capabilities={name:cap(lambda c:(calls.append(1) or {'ok':True})) for name in ('one','two')}
        ident=self.submit([step(),step('two',['one'])],dict(LIMITS,max_actions=1))
        deadline=self.q.inspect(ident)['demand']['deadline']
        self.assertEqual(self.q.run_one(ident),'queued')
        reopened=Coordinator(self.root/'coordenador',self.q.capabilities,context_token=lambda:'g1',clock=lambda:self.now)
        self.assertEqual(reopened.run_until_pause(ident),'failed')
        self.assertEqual(calls,[1])
        self.assertEqual(reopened.inspect(ident)['demand']['actions'],1)
        self.assertEqual(reopened.inspect(ident)['demand']['deadline'],deadline)

    def test_two_workers_do_not_claim_the_same_step(self):
        started=threading.Event();finish=threading.Event();results=[];calls=[]
        def handler(c):
            calls.append(1);started.set();finish.wait(3);return {'ok':True}
        self.q.capabilities['one']=cap(handler)
        ident=self.submit();thread=threading.Thread(target=lambda:results.append(self.q.run_one(ident)))
        thread.start()
        try:
            self.assertTrue(started.wait(3));self.assertEqual(self.q.run_one(ident),'running')
        finally:finish.set();thread.join(4)
        self.assertFalse(thread.is_alive());self.assertEqual(len(calls),1)

    def test_cancellation_preserves_confirmed_effects(self):
        started=threading.Event();finish=threading.Event()
        def handler(c):started.set();finish.wait(3);return {'ok':True,'effect':'confirmed'}
        self.q.capabilities['one']=cap(handler,writes=True)
        ident=self.submit();thread=threading.Thread(target=lambda:self.q.run_one(ident));thread.start()
        try:
            self.assertTrue(started.wait(3));self.assertEqual(self.q.cancel(ident),'cancelling')
        finally:finish.set();thread.join(4)
        record=self.q.inspect(ident)
        self.assertEqual(record['demand']['status'],'cancelled');self.assertEqual(record['steps'][0]['status'],'completed')

    def test_partial_effect_is_not_hidden_or_accepted(self):
        self.q.capabilities['one']=cap(lambda c:{'ok':False,'completed_effects':['source_saved']},writes=True)
        ident=self.submit();self.assertEqual(self.q.run_one(ident),'uncertain')
        self.assertIn('source_saved',self.q.inspect(ident)['steps'][0]['result'])

    def test_reconcile_real_source_after_lost_acknowledgement_without_duplicate(self):
        sys.path.insert(0,str(SYSTEM/'src'));from nucleo import Store
        sources=Store(self.root/'sistema',self.root/'cofre')
        def writer(context):
            sources.apply(context['operation_key'],'create',title='Fonte fictícia',text='Texto fictício preservado.')
            raise ConnectionError('resposta perdida após confirmação')
        capability=Capability('v1',writer,lambda r:isinstance(r,dict) and r.get('status')=='confirmed',
                              writes=True,reconcile=sources.status)
        self.q.capabilities['one']=capability
        ident=self.submit();self.assertEqual(self.q.run_one(ident),'uncertain')
        self.assertEqual(self.q.reconcile(ident,'one'),'queued')
        self.assertEqual(self.q.run_until_pause(ident),'completed');self.assertEqual(len(sources.list()),1)

    def test_candidate_cannot_create_state_in_personal_vault(self):
        with self.assertRaises(ContractError):Coordinator(SYSTEM/'cofre-pessoal')

    def test_late_owner_cannot_overwrite_reconciled_completion(self):
        started=threading.Event();finish=threading.Event();result={'ok':True,'effect':'confirmed'}
        def handler(c):started.set();finish.wait(3);return result
        self.q.capabilities['one']=cap(handler,writes=True,reconcile=lambda key:{'status':'confirmed','result':result})
        ident=self.submit();thread=threading.Thread(target=lambda:self.q.run_one(ident));thread.start()
        try:
            self.assertTrue(started.wait(3));self.now+=121
            self.assertEqual(self.q.run_one(ident),'uncertain')
            self.assertEqual(self.q.reconcile(ident,'one'),'queued')
            self.assertEqual(self.q.run_until_pause(ident),'completed')
        finally:finish.set();thread.join(4)
        self.assertEqual(self.q.inspect(ident)['demand']['status'],'completed')

    def test_context_change_during_write_keeps_effect_visible_as_uncertain(self):
        def writer(c):self.generation='g2';return {'ok':True,'effect':'source_confirmed'}
        self.q.capabilities['one']=cap(writer,writes=True)
        ident=self.submit();self.assertEqual(self.q.run_one(ident),'uncertain')
        self.assertIn('source_confirmed',self.q.inspect(ident)['steps'][0]['result'])

    def test_repeated_cancellation_never_reopens_or_runs_dependents(self):
        started=threading.Event();finish=threading.Event();calls=[];results=[]
        def writer(context):
            calls.append('one');started.set();finish.wait(5)
            return {'ok':True,'effect':'confirmed'}
        self.q.capabilities={'one':cap(writer,writes=True),
                             'two':cap(lambda c:(calls.append('two') or {'ok':True}))}
        ident=self.submit([step(),step('two',['one'])])
        before=self.q.inspect(ident)['demand']
        thread=threading.Thread(target=lambda:results.append(self.q.run_one(ident)));thread.start()
        try:
            self.assertTrue(started.wait(3))
            self.assertEqual(self.q.cancel(ident),'cancelling')
            self.assertEqual(self.q.cancel(ident),'cancelling')
            self.assertEqual(self.q.run_one(ident),'cancelling')
        finally:finish.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(results,['cancelled'])
        self.assertEqual(self.q.cancel(ident),'cancelled')
        self.assertEqual(self.q.run_until_pause(ident),'cancelled');self.assertEqual(calls,['one'])
        snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['steps'][0]['status'],'completed')
        self.assertIn('confirmed',snapshot['steps'][0]['result'])
        self.assertEqual(snapshot['steps'][1]['status'],'queued')
        self.assertEqual(snapshot['demand']['deadline'],before['deadline'])
        self.assertEqual(snapshot['demand']['actions'],1)

    def test_expired_cancellation_resumes_after_restart_without_losing_late_evidence(self):
        started=threading.Event();finish=threading.Event();results=[]
        def writer(context):
            started.set();finish.wait(5)
            return {'ok':True,'effect':'confirmed-after-expiry'}
        self.q.capabilities['one']=cap(writer,writes=True,uses_model=True)
        ident=self.submit();thread=threading.Thread(target=lambda:results.append(self.q.run_one(ident)));thread.start()
        try:
            self.assertTrue(started.wait(3));self.assertEqual(self.q.cancel(ident),'cancelling')
            before=self.q.inspect(ident)
            self.now=before['steps'][0]['lease']+1
            reopened=Coordinator(self.root/'coordenador',self.q.capabilities,
                authorize=lambda:self.active,context_token=lambda:self.generation,clock=lambda:self.now)
            self.assertEqual(reopened.run_one(ident),'cancelled')
            self.now=before['demand']['deadline']+1
            self.assertEqual(reopened.run_one(ident),'cancelled')
            self.assertEqual(reopened.cancel(ident),'cancelled')
            snapshot=reopened.inspect(ident)
            self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
            self.assertIsNone(snapshot['steps'][0]['token'])
            self.assertTrue(snapshot['demand']['effects_uncertain'])
            self.assertEqual(snapshot['demand']['actions'],1)
            self.assertEqual(snapshot['demand']['model_calls'],1)
            self.assertEqual(snapshot['demand']['deadline'],before['demand']['deadline'])
        finally:finish.set();thread.join(5)
        self.assertFalse(thread.is_alive());self.assertEqual(results,['cancelled'])
        snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['demand']['status'],'cancelled')
        self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
        with self.q.connect() as c:
            evidence=c.execute("SELECT details FROM events WHERE demand_id=? AND event='late_observation'",(ident,)).fetchone()
        self.assertEqual(json.loads(evidence['details'])['result']['effect'],'confirmed-after-expiry')

    def test_cancel_expired_reservation_preserves_partial_result_even_after_revocation(self):
        ident=self.submit();partial=json.dumps({'completed_effects':['ficticio']})
        with self.q.connect() as c:
            c.execute("UPDATE demands SET status='running',actions=1,model_calls=1 WHERE id=?",(ident,))
            c.execute("UPDATE steps SET status='running',token='lost-owner',lease=?,result=? WHERE demand_id=?",
                      (self.now,partial,ident))
        self.active=False
        self.assertEqual(self.q.cancel(ident),'cancelled')
        self.assertEqual(self.q.cancel(ident),'cancelled')
        self.assertEqual(self.q.run_one(ident),'cancelled')
        with self.assertRaises(ContractError):self.q.inspect(ident)
        self.active=True;snapshot=self.q.inspect(ident)
        self.assertTrue(snapshot['demand']['effects_uncertain'])
        self.assertEqual(snapshot['steps'][0]['result'],partial)
        self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
        self.assertIsNone(snapshot['steps'][0]['token'])
        self.assertEqual(snapshot['demand']['actions'],1)
        self.assertEqual(snapshot['demand']['model_calls'],1)

    def test_legacy_premature_cancellation_fences_live_token_without_reopening(self):
        ident=self.submit()
        with self.q.connect() as c:
            c.execute("UPDATE demands SET status='cancelled',actions=1 WHERE id=?",(ident,))
            c.execute("UPDATE steps SET status='running',token='legacy-owner',lease=? WHERE demand_id=?",
                      (self.now+100,ident))
        self.assertTrue(self.q.inspect(ident)['demand']['effects_uncertain'])
        self.assertEqual(self.q.run_one(ident),'cancelled')
        snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
        self.assertIsNone(snapshot['steps'][0]['token'])
        self.assertEqual(snapshot['demand']['actions'],1)
        self.assertEqual(self.q.cancel(ident),'cancelled')

    def test_expired_running_step_keeps_uncertainty_before_deadline_failure(self):
        ident=self.submit();deadline=self.q.inspect(ident)['demand']['deadline']
        partial=json.dumps({'completed_effects':['ficticio']})
        with self.q.connect() as c:
            c.execute("UPDATE demands SET status='running',actions=1 WHERE id=?",(ident,))
            c.execute("UPDATE steps SET status='running',token='lost',lease=?,result=? WHERE demand_id=?",
                      (deadline,partial,ident))
        self.now=deadline+1
        self.assertEqual(self.q.run_one(ident),'uncertain')
        snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
        self.assertEqual(snapshot['steps'][0]['result'],partial)
        self.assertIsNone(snapshot['steps'][0]['token'])
        self.assertEqual(self.q.cancel(ident),'cancelled')
        self.q.capabilities['one']=cap(lambda c:{'ok':True},writes=True,
            reconcile=lambda key:{'status':'confirmed','result':{'ok':True}})
        self.assertEqual(self.q.reconcile(ident,'one'),'cancelled')
        self.assertEqual(self.q.inspect(ident)['demand']['deadline'],deadline)
        self.assertEqual(self.q.inspect(ident)['demand']['actions'],1)

    def test_cancelled_partial_write_reconciles_real_fixture_without_resuming(self):
        from nucleo import Store
        sources=Store(self.root/'sistema',self.root/'cofre');calls=[]
        def writer(context):
            source=sources.apply(context['operation_key'],'create',title='Fonte fictícia',text='Efeito fictício preservado.')
            self.q.cancel(context['demand_id'])
            failure=ConnectionError('confirmação fictícia perdida')
            failure.partial_result={'completed_effects':[source['id']]}
            raise failure
        self.q.capabilities={'one':Capability('v1',writer,lambda r:isinstance(r,dict) and r.get('status')=='confirmed',
                                              writes=True,reconcile=sources.status),
                             'two':cap(lambda c:(calls.append('two') or {'ok':True}))}
        ident=self.submit([step(),step('two',['one'])]);before=self.q.inspect(ident)['demand']
        self.assertEqual(self.q.run_one(ident),'cancelled')
        self.assertTrue(self.q.inspect(ident)['demand']['effects_uncertain'])
        self.assertIn('completed_effects',self.q.inspect(ident)['steps'][0]['result'])
        self.assertEqual(self.q.reconcile(ident,'one'),'cancelled')
        self.assertEqual(self.q.run_until_pause(ident),'cancelled');self.assertEqual(calls,[])
        snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['steps'][0]['status'],'completed')
        self.assertFalse(snapshot['demand']['effects_uncertain'])
        self.assertEqual(snapshot['steps'][1]['status'],'queued')
        self.assertEqual(snapshot['demand']['deadline'],before['deadline'])
        self.assertEqual(snapshot['demand']['actions'],1);self.assertEqual(len(sources.list()),1)

    def test_cancelled_reconciliation_keeps_validation_context_and_access_checks(self):
        self.q.capabilities['one']=cap(lambda c:{'ok':False},writes=True,
            reconcile=lambda key:{'status':'confirmed','result':{'ok':False}})
        ident=self.submit();self.assertEqual(self.q.run_one(ident),'uncertain')
        self.assertEqual(self.q.cancel(ident),'cancelled')
        with self.assertRaises(ContractError):self.q.reconcile(ident,'one')
        self.q.capabilities['one']=cap(lambda c:{'ok':True},writes=True,
            reconcile=lambda key:{'status':'confirmed','result':{'ok':True}})
        self.generation='g2'
        with self.assertRaises(ContractError):self.q.reconcile(ident,'one')
        self.generation='g1';self.active=False
        with self.assertRaises(ContractError):self.q.reconcile(ident,'one')
        self.active=True;snapshot=self.q.inspect(ident)
        self.assertEqual(snapshot['demand']['status'],'cancelled')
        self.assertEqual(snapshot['steps'][0]['status'],'uncertain')
        self.assertEqual(self.q.reconcile(ident,'one'),'cancelled')
        self.assertEqual(self.q.inspect(ident)['demand']['actions'],1)

    def test_unconfirmed_reconciliation_keeps_cancelled_effect_uncertain(self):
        self.q.capabilities['one']=cap(lambda c:{'ok':False},writes=True,
            reconcile=lambda key:{'status':'unknown'})
        ident=self.submit();self.assertEqual(self.q.run_one(ident),'uncertain')
        self.q.cancel(ident)
        before=self.q.inspect(ident)
        self.assertEqual(self.q.reconcile(ident,'one'),'cancelled')
        self.assertEqual(self.q.inspect(ident),before)
        self.assertTrue(before['demand']['effects_uncertain'])

    def test_cancellation_during_reconciliation_does_not_reopen_demand(self):
        ident=self.submit()
        def confirmed(key):
            self.q.cancel(ident)
            return {'status':'confirmed','result':{'ok':True}}
        self.q.capabilities['one']=cap(lambda c:{'ok':False},writes=True,reconcile=confirmed)
        self.assertEqual(self.q.run_one(ident),'uncertain')
        self.assertEqual(self.q.reconcile(ident,'one'),'cancelled')
        self.assertEqual(self.q.run_one(ident),'cancelled')
        self.assertEqual(self.q.inspect(ident)['steps'][0]['status'],'completed')

    def test_late_handler_never_reopens_any_terminal_demand(self):
        for status in ('completed','failed','cancelled','superseded'):
            with self.subTest(status=status):
                def handler(context):
                    with self.q.connect() as c:
                        c.execute('UPDATE demands SET status=? WHERE id=?',(status,context['demand_id']))
                    return {'ok':True,'effect':'confirmed'}
                self.q.capabilities['one']=cap(handler,writes=True)
                ident=self.q.submit('terminal-'+status,[step()],{},LIMITS)
                self.assertEqual(self.q.run_one(ident),status)
                self.assertEqual(self.q.inspect(ident)['demand']['status'],status)
                self.assertEqual(self.q.cancel(ident),status)

    def recovery_pair(self,key):
        payload={'kind':'contribution','source_ref':{'record_id':'ficticio','revision':1}}
        old=self.q.submit(key,plan_for('contribution'),payload,LIMITS)
        successor=self.q.submit(key+'-new',plan_for('contribution'),dict(payload,recovery_of=old),LIMITS)
        return old,successor

    def test_supersession_is_durable_idempotent_terminal_and_preserves_budgets(self):
        old,successor=self.recovery_pair('lineage')
        with self.q.connect() as c:
            c.execute('UPDATE demands SET actions=2,model_calls=1 WHERE id=?',(old,))
        before=self.q.inspect(old)
        first=self.q.supersede(old,successor,'old-job')
        self.assertEqual(first,self.q.supersede(old,successor,'old-job'))
        reopened=Coordinator(self.root/'coordenador',context_token=lambda:'g1',clock=lambda:self.now)
        snapshot=reopened.inspect(old)
        self.assertEqual(snapshot['demand']['superseded_by'],successor)
        self.assertEqual(snapshot['steps'],before['steps'])
        for field in ('actions','model_calls','deadline','limits_json','payload','fingerprint'):
            self.assertEqual(snapshot['demand'][field],before['demand'][field])
        self.assertEqual(reopened.run_until_pause(old),'superseded')
        self.assertEqual(reopened.cancel(old),'superseded')
        with self.assertRaises(ContractError):reopened.answer(old,'resposta',{'record_id':'ficticio','revision':1})
        with reopened.connect() as c:
            self.assertEqual(c.execute("SELECT count(*) FROM events WHERE demand_id=? AND event='superseded'",(old,)).fetchone()[0],1)
        with self.assertRaises(ContractError):self.q.supersede(old,successor,'another-job')

    def test_supersession_refuses_running_uncertain_or_applied_steps(self):
        for index,(capability,status) in enumerate((('retrieve','running'),('extract','uncertain'),
                                                   ('apply_contribution','completed'),('apply_contribution','failed'))):
            with self.subTest(capability=capability,status=status):
                old,successor=self.recovery_pair('unsafe-'+str(index))
                with self.q.connect() as c:
                    c.execute('UPDATE steps SET status=? WHERE demand_id=? AND capability=?',(status,old,capability))
                with self.assertRaises(ContractError):self.q.supersede(old,successor,'old-job')
                self.assertEqual(self.q.inspect(old)['demand']['status'],'queued')
                self.assertIsNone(self.q.inspect(old)['demand']['superseded_by'])

    def test_supersession_refuses_terminal_original_or_unproven_successor(self):
        old,successor=self.recovery_pair('cancelled-original');self.q.cancel(old)
        with self.assertRaises(ContractError):self.q.supersede(old,successor,'old-job')
        old,successor=self.recovery_pair('foreign-origin')
        with self.q.connect() as c:
            payload=json.loads(c.execute('SELECT payload FROM demands WHERE id=?',(successor,)).fetchone()[0])
            payload['source_ref']['revision']=2
            c.execute('UPDATE demands SET payload=? WHERE id=?',(json.dumps(payload),successor))
        with self.assertRaises(ContractError):self.q.supersede(old,successor,'old-job')
        self.assertEqual(self.q.inspect(old)['demand']['status'],'queued')

    def test_concurrent_supersessions_choose_only_one_successor(self):
        old,first=self.recovery_pair('contested')
        payload=json.loads(self.q.inspect(first)['demand']['payload'])
        second=self.q.submit('contested-second',plan_for('contribution'),payload,LIMITS)
        barrier=threading.Barrier(2);results=[];errors=[]
        reopened=Coordinator(self.root/'coordenador',context_token=lambda:'g1',clock=lambda:self.now)
        def claim(coordinator,successor,job):
            try:
                barrier.wait(timeout=3)
                results.append(coordinator.supersede(old,successor,job))
            except Exception as failure:errors.append(failure)
        threads=[threading.Thread(target=claim,args=(self.q,first,'job-one')),
                 threading.Thread(target=claim,args=(reopened,second,'job-two'))]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(results),1);self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],ContractError)
        self.assertEqual(self.q.inspect(old)['demand']['superseded_by'],results[0]['new_demand'])
        self.assertEqual(self.q.run_one(old),'superseded')

    def test_additive_schema_keeps_legacy_rows_and_limits_unchanged(self):
        ident=self.submit()
        with self.q.connect() as c:
            c.execute('UPDATE demands SET actions=2,model_calls=1 WHERE id=?',(ident,))
            before=dict(c.execute('SELECT * FROM demands WHERE id=?',(ident,)).fetchone())
            steps=[dict(row) for row in c.execute('SELECT * FROM steps WHERE demand_id=?',(ident,))]
            c.execute('DROP TABLE demand_supersessions')
        reopened=Coordinator(self.root/'coordenador',clock=lambda:self.now)
        with reopened.connect() as c:
            self.assertEqual(dict(c.execute('SELECT * FROM demands WHERE id=?',(ident,)).fetchone()),before)
            self.assertEqual([dict(row) for row in c.execute('SELECT * FROM steps WHERE demand_id=?',(ident,))],steps)
            self.assertEqual(c.execute('SELECT count(*) FROM demand_supersessions').fetchone()[0],0)


if __name__=='__main__':unittest.main(verbosity=2)
