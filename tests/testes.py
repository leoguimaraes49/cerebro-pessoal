import json, os, sqlite3, subprocess, sys, tempfile, threading, unittest, uuid
from pathlib import Path
from unittest.mock import MagicMock,patch
from nucleo import Store,REAL_SYSTEM,REAL_VAULT,exclusive,acquire_content,sha,Conflict,Invalid,Locked,Uncertain

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='fixture-',dir=REAL_SYSTEM/'testes_temporarios')
        b=Path(self.tmp.name); self.s=Store(b/'sistema',b/'cofre')
    def tearDown(self):self.tmp.cleanup()
    def create(self,key='c'):return self.s.apply(key,'create',title='Experiência fictícia',text='Relato fictício, português e ação.')
    def test_01_create_unicode_and_read(self):
        r=self.create(); n=self.s.read(r['id']); self.assertEqual(n['payload']['content'],'Relato fictício, português e ação.'); self.assertEqual(uuid.UUID(n['id']).version,4)
        self.assertIn('Experiência fictícia',next(self.s.folder.glob('*.md')).name)
    def test_02_idempotence_and_request_conflict(self):
        first=self.create(); self.assertEqual(first,self.create()); self.assertEqual(len(self.s.list()),1)
        with self.assertRaises(Conflict): self.s.apply('c','create',title='Experiência fictícia',text='Outro conteúdo')
    def test_03_correction_and_old_revision(self):
        r=self.create(); u=self.s.apply('u','correct',ident=r['id'],expected=1,text='Correção fictícia',reason='Retificação fictícia')
        self.assertEqual(u['revision'],2); self.assertTrue((self.s.hist/r['id']/'1.md').exists())
        with self.assertRaises(Conflict): self.s.apply('u2','correct',ident=r['id'],expected=1,text='Edição antiga',reason='Retificação fictícia')
    def test_04_external_edits_fail_closed(self):
        r=self.create(); p=next(self.s.folder.glob('*.md')); p.write_text('edição externa fictícia',encoding='utf-8')
        with self.assertRaises(Conflict):self.s.read(r['id'])
        with self.assertRaises(Conflict):self.s.apply('u','correct',ident=r['id'],expected=1,text='não deve sobrescrever',reason='Retificação fictícia')
        self.assertEqual(p.read_text(encoding='utf-8'),'edição externa fictícia')
    def test_05_exclusive_lock_blocks_cooperative_writer(self):
        r=self.create(); p=next(self.s.folder.glob('*.md')); other=p.parent/'temporario.txt'; other.write_text('outro',encoding='utf-8')
        with acquire_content(p):
            with patch('nucleo.time.sleep') as sleep:
                with self.assertRaises(Locked):exclusive(p)
                sleep.assert_not_called()
            if os.name == 'nt':
                with self.assertRaises(PermissionError):os.replace(other,p)
            with self.assertRaises(Locked):self.s.apply('u','correct',ident=r['id'],expected=1,text='tentativa',reason='Retificação fictícia')
        self.assertEqual(self.s.read(r['id'])['revision'],1)
    def test_06_restart_recovers_lost_confirmation(self):
        r=self.create(); p=next(self.s.folder.glob('*.md')); b=p.read_bytes()
        with self.s.connect() as c:
            c.execute("UPDATE operations SET status='proposed',pending=?,result=NULL WHERE key='c'",(b,)); c.execute('DELETE FROM records WHERE id=?',(r['id'],))
        restart=Store(self.s.root,self.s.vault)
        self.assertEqual(restart.apply('c','create',title='Experiência fictícia',text='Relato fictício, português e ação.'),r)
        self.assertEqual(len(restart.list()),1)
    def test_07_two_cooperative_writers(self):
        r=self.create(); barrier=threading.Barrier(2); result=[]
        def run(i):
            barrier.wait()
            try:self.s.apply('chave'+str(i),'correct',ident=r['id'],expected=1,text='revisão '+str(i),reason='Retificação fictícia'); result.append('ok')
            except (Conflict,Locked):result.append('conflict')
        t=[threading.Thread(target=run,args=(i,)) for i in range(2)]
        for x in t:x.start()
        for x in t:x.join()
        self.assertCountEqual(result,['ok','conflict']); self.assertEqual(self.s.read(r['id'])['revision'],2)
    def test_08_roots_and_safe_filenames(self):
        with self.assertRaises(Invalid):Store(REAL_SYSTEM,REAL_VAULT.parent)
        with self.assertRaises(Invalid):Store(REAL_SYSTEM,REAL_SYSTEM/'cofre-proibido')
        r=self.s.apply('c','create',title='../../Fictício',text='texto')
        p=next(self.s.folder.glob('*.md')); self.assertEqual(p.resolve().parent,self.s.folder.resolve())
    def test_09_same_title_disambiguated(self):
        a=self.create(); b=self.create('outro'); paths=list(self.s.folder.glob('*.md'))
        self.assertEqual(len(paths),2); self.assertNotEqual(a['id'],b['id']); self.assertTrue(any(b['id'][:8] in p.name for p in paths))
    def test_10_journal_clears_payload_after_confirmation(self):
        self.create()
        with self.s.connect() as c:r=c.execute("SELECT status,pending FROM operations WHERE key='c'").fetchone()
        self.assertEqual(r,('confirmed',None))
    def test_11_unrecognized_external_file_not_auto_imported(self):
        (self.s.folder/'Externa.md').write_text('texto não autorizado',encoding='utf-8')
        self.assertEqual(self.s.list(),[])


    def test_12_partial_write_never_confirmed(self):
        r=self.create(); p=next(self.s.folder.glob('*.md'))
        self.s.apply('u','correct',ident=r['id'],expected=1,text='Correção fictícia',reason='Retificação fictícia')
        final=p.read_bytes(); old=(self.s.hist/r['id']/'1.md').read_bytes()
        with self.s.connect() as c:
            c.execute("UPDATE operations SET status='proposed',pending=?,result=NULL WHERE key='u'",(final,))
            c.execute('UPDATE records SET revision=1,digest=? WHERE id=?',(sha(old),r['id']))
        p.write_bytes(b'conteudo parcial ficticio')
        with self.assertRaises(Conflict):self.s.apply('u','correct',ident=r['id'],expected=1,text='Correção fictícia',reason='Retificação fictícia')
        self.assertEqual(p.read_bytes(),b'conteudo parcial ficticio'); self.assertEqual(self.s.status('u')['status'],'proposed')
    def test_13_external_replace_is_blocked_or_detected(self):
        record=self.create(); p=next(self.s.folder.glob('*.md')); other=p.parent/'externa.txt'; other.write_text('fictício',encoding='utf-8')
        code="import os,sys; os.replace(sys.argv[1],sys.argv[2])"
        with acquire_content(p) as stream:
            result=subprocess.run([sys.executable,'-c',code,str(other),str(p)],capture_output=True,text=True)
            if os.name == 'nt':
                self.assertNotEqual(result.returncode,0); self.assertIn('PermissionError',result.stderr)
            else:
                from nucleo import verify_posix_file
                self.assertEqual(result.returncode,0,result.stderr)
                with self.assertRaises(Uncertain):verify_posix_file(p,stream.fileno())
        if os.name == 'nt':
            self.assertTrue(other.exists())
        else:
            with self.assertRaises(Conflict):self.s.read(record['id'])

    @unittest.skipUnless(os.name == 'posix', 'trava cooperativa POSIX')
    def test_posix_drift_during_commit_or_delete_stays_unconfirmed(self):
        import nucleo
        original_sync = os.fsync
        record = self.create()
        path = next(self.s.folder.glob('*.md'))
        original_bytes = path.read_bytes()

        def external_edit_after_sync(fd):
            original_sync(fd)
            if os.path.samestat(os.fstat(fd), path.stat()):
                path.write_bytes(b'alteracao externa')

        with patch('nucleo.os.fsync', side_effect=external_edit_after_sync):
            with self.assertRaises(Uncertain):
                self.s.apply('correcao','correct',ident=record['id'],expected=1,text='correcao ficticia',reason='fixture')
        self.assertEqual(self.s.status('correcao')['status'],'proposed')
        self.assertEqual(path.read_bytes(),b'alteracao externa')
        path.write_bytes(original_bytes)
        replacement = path.with_suffix('.tmp')
        replacement.write_bytes(original_bytes)
        remove = nucleo.remove_locked_file

        def replace_before_delete(name, stream, expected):
            os.replace(replacement, name)
            remove(name, stream, expected)

        with patch('nucleo.remove_locked_file', side_effect=replace_before_delete):
            with self.assertRaises(Uncertain):
                self.s.delete('excluir',record['id'],1)
        self.assertEqual(self.s.status('excluir')['status'],'proposed')
        self.assertEqual(path.read_bytes(),original_bytes)

    def test_14_controlled_delete_and_no_resurrection(self):
        r=self.create(); self.s.apply('u','correct',ident=r['id'],expected=1,text='Correção fictícia',reason='Retificação fictícia')
        d=self.s.delete('d',r['id'],2); self.assertEqual(d['status'],'confirmed')
        self.assertEqual(self.s.delete('d',r['id'],2),d); self.assertEqual(self.s.list(),[])
        self.assertFalse((self.s.hist/r['id']).exists()); self.assertEqual(list(self.s.folder.glob('*.md')),[])
        with self.assertRaises(Invalid):self.s.read(r['id'])
        with self.assertRaises(Invalid):self.create()
        with self.assertRaises(Invalid):self.s.apply('u','correct',ident=r['id'],expected=1,text='Correção fictícia',reason='Retificação fictícia')
    def test_15_delete_pending_stays_hidden_and_recovers(self):
        r=self.create(); p=next(self.s.folder.glob('*.md'))
        with acquire_content(p):
            with self.assertRaises(Locked):self.s.delete('d',r['id'],1)
            self.assertEqual(self.s.status('d')['status'],'proposed')
            with self.assertRaises(Invalid):self.s.read(r['id'])
        self.assertEqual(self.s.delete('d',r['id'],1)['status'],'confirmed')
        self.assertFalse(p.exists())

    def test_read_backoff_is_bounded_and_does_not_retry_writes(self):
        import nucleo
        record=self.create();original=nucleo.exclusive;attempts=[]
        path=next(self.s.folder.glob('*.md'));before=path.read_bytes()
        def transient(*args,**kwargs):
            attempts.append(args[0])
            if len(attempts)<3:raise Locked('lock transitório fictício')
            return original(*args,**kwargs)
        with patch('nucleo.exclusive',transient),patch('nucleo.time.sleep') as sleep:
            self.assertEqual(self.s.read(record['id'])['revision'],1)
            self.assertEqual([call.args[0] for call in sleep.call_args_list],list(nucleo.READ_BACKOFF[:2]))
        with patch('nucleo.exclusive',side_effect=Locked('lock persistente fictício')) as opening,patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(Locked):self.s.read(record['id'])
            self.assertEqual(opening.call_count,len(nucleo.READ_BACKOFF)+1)
            self.assertEqual(sleep.call_count,len(nucleo.READ_BACKOFF))
        with patch('nucleo.exclusive',side_effect=Locked('escrita ocupada')) as opening,patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(Locked):self.s.apply('blocked','correct',ident=record['id'],expected=1,text='Não gravar',reason='fixture')
            self.assertEqual(opening.call_count,len(nucleo.READ_BACKOFF)+1)
            self.assertEqual([call.args[0] for call in sleep.call_args_list],list(nucleo.READ_BACKOFF))
        self.assertEqual(self.s.status('blocked')['status'],'unknown')
        self.assertEqual(path.read_bytes(),before);self.assertFalse((self.s.hist/record['id']).exists())
        with self.s.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM operations').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT revision,digest FROM records WHERE id=?',(record['id'],)).fetchone(),(1,sha(before)))
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tombstones').fetchone()[0],0)

        opened=[];attempts=[]
        def before_write(*args,**kwargs):
            attempts.append(kwargs)
            if len(attempts) in (2,3):raise Locked('aquisição de escrita transitória fictícia')
            raw=original(*args,**kwargs);stream=MagicMock(wraps=raw)
            stream.__enter__.return_value=stream;stream.__exit__.side_effect=raw.__exit__
            opened.append(stream);return stream
        with patch('nucleo.exclusive',before_write),patch('nucleo.time.sleep') as sleep,patch('nucleo.os.fsync',wraps=os.fsync) as syncing:
            result=self.s.apply('once','correct',ident=record['id'],expected=1,text='Correção aplicada uma vez',reason='fixture')
            self.assertEqual([call.args[0] for call in sleep.call_args_list],list(nucleo.READ_BACKOFF[:2]))
            self.assertEqual(syncing.call_count,2)  # Uma revisão arquivada e um conteúdo atual.
        self.assertEqual(len(attempts),4);self.assertEqual(len(opened),2)
        self.assertTrue(all(flags=={'create':False,'delete':False} for flags in attempts))
        opened[0].write.assert_not_called()
        for method in ('write','truncate','flush','fileno','__exit__'):getattr(opened[1],method).assert_called_once()
        self.assertEqual(result['revision'],2);self.assertEqual(self.s.status('once')['status'],'confirmed')
        self.assertEqual((self.s.hist/record['id']/'1.md').read_bytes(),before)

    def test_content_acquisition_keeps_create_new_and_real_errors_immediate(self):
        import nucleo
        record=self.create();path=next(self.s.folder.glob('*.md'));before=path.read_bytes()
        for flags in ({'create':True},{'delete':True}):
            with self.subTest(flags=flags),patch('nucleo.exclusive',side_effect=Locked('persistente')) as opening,patch('nucleo.time.sleep') as sleep:
                with self.assertRaises(Locked):acquire_content(path,**flags)
                self.assertEqual(opening.call_count,len(nucleo.READ_BACKOFF)+1)
                self.assertEqual(sleep.call_count,len(nucleo.READ_BACKOFF))
                self.assertTrue(all(call.kwargs=={'create':flags.get('create',False),'delete':flags.get('delete',False)} for call in opening.call_args_list))
        with patch('nucleo.exclusive',wraps=nucleo.exclusive) as opening,patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(OSError):acquire_content(path,create=True)
            opening.assert_called_once_with(path,create=True,delete=False);sleep.assert_not_called()
        error=OSError(5,'erro real fictício')
        with patch('nucleo.exclusive',side_effect=error) as opening,patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(OSError) as caught:acquire_content(path)
            self.assertIs(caught.exception,error);opening.assert_called_once();sleep.assert_not_called()
        self.assertEqual(path.read_bytes(),before);self.assertEqual(self.s.read(record['id'])['revision'],1)

    def test_content_body_and_read_errors_after_open_are_never_retried(self):
        import nucleo
        record=self.create();path=next(self.s.folder.glob('*.md'));original=nucleo.exclusive
        for flags in ({},{'delete':True}):
            with self.subTest(flags=flags),patch('nucleo.exclusive',wraps=original) as opening,patch('nucleo.time.sleep') as sleep:
                bodies=[]
                with self.assertRaises(Locked):
                    with acquire_content(path,**flags):
                        bodies.append(1);raise Locked('falha no corpo após aquisição')
                self.assertEqual(bodies,[1]);opening.assert_called_once();sleep.assert_not_called()
        raw=acquire_content(path);stream=MagicMock(wraps=raw)
        stream.__enter__.return_value=stream;stream.__exit__.side_effect=raw.__exit__
        stream.read.side_effect=Locked('falha na leitura após aquisição')
        with patch('nucleo.exclusive',return_value=stream) as opening,patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(Locked):nucleo.read_exclusive(path)
            opening.assert_called_once();stream.read.assert_called_once();sleep.assert_not_called()
        self.assertTrue(raw.closed)

    def test_fsync_failure_after_write_keeps_proposal_without_repeating_effect(self):
        import nucleo
        record=self.create();path=next(self.s.folder.glob('*.md'));before=path.read_bytes()
        original=nucleo.exclusive;original_sync=os.fsync;opened=[];syncs=[]
        def tracked(*args,**kwargs):
            raw=original(*args,**kwargs);stream=MagicMock(wraps=raw)
            stream.__enter__.return_value=stream;stream.__exit__.side_effect=raw.__exit__
            opened.append(stream);return stream
        def fail_after_sync(handle):
            original_sync(handle);syncs.append(handle)
            if len(syncs)==2:raise Locked('confirmação do fsync perdida, não repetir corpo')
        with patch('nucleo.exclusive',tracked),patch('nucleo.os.fsync',fail_after_sync),patch('nucleo.time.sleep') as sleep:
            with self.assertRaises(Locked):
                self.s.apply('uncertain-sync','correct',ident=record['id'],expected=1,text='Conteúdo novo fictício',reason='fixture')
            sleep.assert_not_called()
        self.assertEqual(len(opened),2);self.assertEqual(len(syncs),2)
        for method in ('write','truncate','flush','fileno','__exit__'):getattr(opened[1],method).assert_called_once()
        with self.s.connect() as c:
            status,pending=c.execute('SELECT status,pending FROM operations WHERE key=?',('uncertain-sync',)).fetchone()
            self.assertEqual((status,pending),('proposed',path.read_bytes()))
            self.assertEqual(c.execute('SELECT revision,digest FROM records WHERE id=?',(record['id'],)).fetchone(),(1,sha(before)))
        self.assertEqual((self.s.hist/record['id']/'1.md').read_bytes(),before)
        with self.assertRaises(Conflict):self.s.read(record['id'])

    def test_knowledge_content_acquisition_retries_opening_not_write(self):
        import nucleo
        from conhecimento import Knowledge
        source=self.create();knowledge=Knowledge(self.s);original=nucleo.exclusive;attempts=[];opened=[]
        def transient(*args,**kwargs):
            if args[0].parent==self.s.vault/'10_Entidades':
                attempts.append(kwargs)
                if len(attempts)<3:raise Locked('abertura de conhecimento transitória')
                raw=original(*args,**kwargs);stream=MagicMock(wraps=raw)
                stream.__enter__.return_value=stream;stream.__exit__.side_effect=raw.__exit__
                opened.append(stream);return stream
            return original(*args,**kwargs)
        with patch('nucleo.exclusive',transient),patch('nucleo.time.sleep') as sleep:
            result=knowledge.apply('knowledge-content','entity','Pessoa fictícia',{'entity_kind':'person','display_name':'Pessoa fictícia',
                'origin_refs':[{'record_id':source['id'],'revision':1}],'identity_status':'provisional'})
            self.assertEqual([call.args[0] for call in sleep.call_args_list],list(nucleo.READ_BACKOFF[:2]))
        self.assertEqual(len(opened),1);self.assertEqual(len(attempts),3)
        self.assertTrue(all(flags=={'create':True,'delete':False} for flags in attempts))
        for method in ('write','truncate','flush','fileno','__exit__'):getattr(opened[0],method).assert_called_once()
        self.assertEqual(knowledge.read(result['id'])['record']['revision'],1)

    def test_read_backoff_still_checks_digest(self):
        import nucleo
        record=self.create();path=next(self.s.folder.glob('*.md'));original=nucleo.exclusive;attempts=[]
        def changed(*args,**kwargs):
            attempts.append(1)
            if len(attempts)==1:raise Locked('fixture')
            path.write_bytes(b'edicao externa ficticia')
            return original(*args,**kwargs)
        with patch('nucleo.exclusive',changed),patch('nucleo.time.sleep'):
            with self.assertRaises(Conflict):self.s.read(record['id'])
        self.assertEqual(path.read_bytes(),b'edicao externa ficticia')

    def test_parent_source_reference_shape_and_destination_are_checked_before_proposal(self):
        parent=self.create();ref={'record_id':parent['id'],'revision':1}
        invalid=[None,'texto',{},dict(ref,revision=True),dict(ref,revision=1.0),dict(ref,revision=0),dict(ref,record_id='')]
        for index,value in enumerate(invalid):
            key='invalid-parent-'+str(index)
            with self.subTest(value=value),self.assertRaises(Invalid):
                self.s.apply(key,'create',title='Filha fictícia',text='Texto fictício',source_metadata={'source_kind':'document','parent_source_ref':value})
            self.assertEqual(self.s.status(key)['status'],'unknown')
        for key,bad,error in [('missing',dict(ref,record_id='missing'),Invalid),('stale',dict(ref,revision=2),Conflict)]:
            with self.assertRaises(error):
                self.s.apply(key,'create',title='Filha fictícia',text='Texto fictício',source_metadata={'source_kind':'document','parent_source_ref':bad})
            self.assertEqual(self.s.status(key)['status'],'unknown')
        with self.assertRaises(Invalid):
            self.s.apply('self-parent','correct',ident=parent['id'],expected=1,text='Correção fictícia',reason='fixture',
                         source_metadata={'source_kind':'document','parent_source_ref':ref})
        self.s.delete('delete-parent',parent['id'],1)
        with self.assertRaises(Invalid):
            self.s.apply('deleted-parent','create',title='Filha fictícia',text='Texto fictício',source_metadata={'source_kind':'document','parent_source_ref':ref})
        self.assertEqual(self.s.status('deleted-parent')['status'],'unknown')

    def test_historical_parent_is_preserved_on_unrelated_child_correction(self):
        parent=self.create();ref={'record_id':parent['id'],'revision':1}
        metadata={'source_kind':'conversation_turn','parent_source_ref':ref}
        child=self.s.apply('child','create',title='Trecho fictício',text='Trecho original',source_metadata=metadata)
        self.s.apply('parent-correction','correct',ident=parent['id'],expected=1,text='Origem retificada',reason='fixture')
        self.s.apply('child-correction','correct',ident=child['id'],expected=1,text='Trecho retificado',reason='fixture')
        self.s.apply('child-metadata','correct',ident=child['id'],expected=2,text='Outro trecho retificado',reason='fixture',source_metadata=metadata)
        self.assertEqual(self.s.read(child['id'])['payload']['parent_source_ref'],ref)
        self.assertEqual(self.s.read(child['id'])['payload']['source_kind'],'conversation_turn')

    def test_parent_external_edit_is_not_accepted(self):
        parent=self.create();path=next(self.s.folder.glob('*.md'));path.write_bytes(path.read_bytes()+b'externo')
        with self.assertRaises(Conflict):
            self.s.apply('bad-parent','create',title='Trecho fictício',text='Trecho original',
                         source_metadata={'source_kind':'document','parent_source_ref':{'record_id':parent['id'],'revision':1}})
        self.assertEqual(self.s.status('bad-parent')['status'],'unknown')


if __name__=='__main__': unittest.main(verbosity=2)
