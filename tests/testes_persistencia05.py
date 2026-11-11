"""Regressões de concorrência e confirmação em processos descartáveis."""
import json
import multiprocessing
import os
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

from conhecimento import Knowledge
from nucleo import Conflict, Invalid, REAL_SYSTEM, Store


def create_worker(root, vault, number, mode, ready, release, output, origin):
    store = Store(root, vault)
    key = 'worker-' + str(number)
    if mode == 'source':
        finish = store.finish

        def paused(operation):
            ready.put(number)
            if not release.wait(20):
                raise TimeoutError('gate fictício')
            return finish(operation)

        store.finish = paused
        result = store.apply(key, 'create', title='Mesmo título fictício', text='Fonte fictícia ' + str(number))
    else:
        knowledge = Knowledge(store)
        connect = knowledge.connect
        notified = False

        @contextmanager
        def paused_connection():
            nonlocal notified
            with connect() as database:
                yield database
            if not notified:
                with connect() as database:
                    pending = database.execute('SELECT status FROM operations WHERE key=?', (key,)).fetchone()
                if pending and pending[0] == 'proposed':
                    notified = True
                    ready.put(number)
                    if not release.wait(20):
                        raise TimeoutError('gate fictício')

        knowledge.connect = paused_connection
        result = knowledge.apply(key, 'entity', 'Mesmo título fictício', {
            'entity_kind': 'learning_topic', 'topic_description': 'Tema fictício ' + str(number),
            'origin_refs': [{'record_id': origin['id'], 'revision': 1}], 'identity_status': 'provisional',
        })
    output.put(result)


def business_worker(root, vault, key, kind, payload, ready, release, output, pause):
    knowledge=Knowledge(Store(root,vault));connect=knowledge.connect;notified=False
    @contextmanager
    def gated():
        nonlocal notified
        with connect() as database:yield database
        if pause and not notified:
            with connect() as database:pending=database.execute('SELECT status FROM operations WHERE key=?',(key,)).fetchone()
            if pending and pending[0]=='proposed':
                notified=True;ready.put(key)
                if not release.wait(15):raise TimeoutError('gate de negócio fictício')
    knowledge.connect=gated
    try:output.put(knowledge.apply(key,kind,'Registro fictício',payload))
    except (Conflict,Invalid) as error:output.put({'status':'conflict','reason':str(error)})


def crash_knowledge(root, vault, payload):
    store = Store(root, vault)
    knowledge = Knowledge(store)
    original = os.fsync

    def crash_after_flush(handle):
        original(handle)
        os._exit(73)

    os.fsync = crash_after_flush
    knowledge.apply('interrupted', 'entity', 'Entidade fictícia interrompida', payload)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='persist05-', dir=REAL_SYSTEM / 'testes_temporarios')
        root = Path(self.temporary.name)
        self.store = Store(root / 'system', root / 'vault')

    def tearDown(self):
        self.temporary.cleanup()

    def concurrency(self, mode):
        origin = None
        if mode == 'knowledge':
            origin = self.store.apply('origin', 'create', title='Origem fictícia', text='Origem das entidades fictícias.')
        context = multiprocessing.get_context('spawn')
        ready, output = context.Queue(), context.Queue()
        release = context.Event()
        processes = [context.Process(target=create_worker, args=(str(self.store.root), str(self.store.vault),
                     number, mode, ready, release, output, origin)) for number in range(4)]
        try:
            for process in processes:
                process.start()
            self.assertEqual({ready.get(timeout=20) for _ in processes}, set(range(4)))
            release.set()
            results = [output.get(timeout=25) for _ in processes]
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(len({result['id'] for result in results}), 4)
            if mode == 'source':
                self.assertEqual(len(self.store.list()), 4)
            else:
                records = Knowledge(self.store).catalog()[0]
                self.assertEqual(sum(r['record_type'] == 'entity' for r in records.values()), 4)
        finally:
            release.set()
            for process in processes:
                if process.is_alive():
                    process.terminate()
                process.join(5)
            ready.close()
            output.close()

    def test_source_names_are_reserved_before_commit(self):
        self.concurrency('source')

    def test_knowledge_names_are_reserved_before_commit(self):
        self.concurrency('knowledge')

    def business_concurrency(self,kind):
        from testes_esquemas import SchemaTests
        from esquemas import expected_scores
        from nucleo import NOW
        fixture=SchemaTests();fixture.setUp();self.addCleanup(fixture.tearDown)
        instrument,application=fixture.assessment()
        if kind=='assessment_response':
            payload={'assessment_ref':{'record_id':application['id'],'revision':1},
                     'item_ref':{'record_id':instrument['id'],'revision':1,'fragment':'i1'},'value':1,'source_refs':[fixture.ref]}
        else:
            fixture.response(instrument,application,'i1',1);fixture.response(instrument,application,'i2',3)
            records=fixture.k.catalog()[0];scores,used,_=expected_scores(records[application['id']],records)
            payload={'assessment_ref':{'record_id':application['id'],'revision':1},'scoring_rule_ref':fixture.ref,
                     'response_refs':used,'dimension_scores':scores,'computed_at':NOW(),'limitations':[],'score_validity_status':'current'}
        context=multiprocessing.get_context('spawn');ready=context.Queue();release=context.Event()
        first_output=context.Queue();second_output=context.Queue()
        first=context.Process(target=business_worker,args=(str(fixture.sources.root),str(fixture.sources.vault),'first-business',kind,payload,ready,release,first_output,True))
        second=context.Process(target=business_worker,args=(str(fixture.sources.root),str(fixture.sources.vault),'second-business',kind,payload,ready,release,second_output,False))
        started=[]
        try:
            first.start();started.append(first);self.assertEqual(ready.get(timeout=15),'first-business')
            second.start();started.append(second)
            self.assertEqual(second_output.get(timeout=15)['status'],'conflict')
            release.set();result=first_output.get(timeout=15);self.assertEqual(result['status'],'confirmed')
            for process in started:process.join(10);self.assertEqual(process.exitcode,0)
            records=fixture.k.catalog()[0]
            matching=[r for r in records.values() if r['record_type']==kind and r['payload'].get('assessment_ref',{}).get('record_id')==application['id']]
            self.assertEqual(len(matching),1);self.assertEqual(matching[0]['id'],result['id'])
            with fixture.k.connect() as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM operations WHERE key IN ('first-business','second-business')").fetchone()[0],1)
                self.assertEqual(c.execute('SELECT record_id FROM business_reservations WHERE record_type=? AND assessment_id=?',(kind,application['id'])).fetchone(),(result['id'],))
        finally:
            release.set()
            for process in started:
                if process.is_alive():process.terminate()
                process.join(5)
            for channel in (ready,first_output,second_output):channel.close();channel.join_thread()

    def test_response_business_key_is_reserved_between_transactions(self):self.business_concurrency('assessment_response')
    def test_score_business_key_is_reserved_between_transactions(self):self.business_concurrency('assessment_score')

    def test_unconfirmed_new_knowledge_is_blocked_and_replay_confirms(self):
        origin = self.store.apply('origin', 'create', title='Origem fictícia', text='Informação fictícia.')
        payload = {'entity_kind': 'learning_topic', 'topic_description': 'Tema fictício',
                   'origin_refs': [{'record_id': origin['id'], 'revision': 1}], 'identity_status': 'provisional'}
        process = multiprocessing.get_context('spawn').Process(target=crash_knowledge,
            args=(str(self.store.root), str(self.store.vault), payload))
        try:
            process.start()
            process.join(20)
            self.assertEqual(process.exitcode, 73)
            knowledge = Knowledge(self.store)
            with self.assertRaises(Conflict):
                knowledge.catalog()
            effect = knowledge.apply('interrupted', 'entity', 'Entidade fictícia interrompida', payload)
            self.assertEqual(knowledge.read(effect['id'])['validity'], 'current_within_scope')
            self.assertEqual(knowledge.apply('interrupted', 'entity', 'Entidade fictícia interrompida', payload), effect)
        finally:
            if process.is_alive():
                process.terminate()
            process.join(5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
