"""Executor local limitado: manutenção, demandas e tarefas semânticas registradas.

Não instala código de notas; modelos e rede obedecem ao provedor e aos limites
da demanda. A fila e os efeitos confirmados sobrevivem ao processo.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from nucleo import Store, REAL_SYSTEM, REAL_VAULT, NOW, sha, canon, exclusive, Invalid, Conflict, config_file

KINDS = {'audit_vault':'P08/P13', 'refresh_view':'P14', 'selftest':'P13','plan_demand':'P03','semantic_revalidation':'P08','research_external':'P11','evaluate_candidate':'P12/P13','recalculate_assessment':'P08'}
CODE_FILES = (
    'src/nucleo.py', 'src/conhecimento.py', 'src/autoteste.py', 'src/autonomia.py',
    'src/ponte_pessoal.py', 'src/cli.py', 'src/apoio_decisao.py', 'src/esquemas.py',
    'src/avaliacoes.py', 'src/documentos.py', 'src/provedores.py', 'src/pesquisa.py',
    'src/recuperacao.py', 'src/revalidacao.py', 'src/coordenador.py', 'src/execucao.py',
    'src/melhorias.py', 'src/revisoes.py', 'src/verificador_evidencias.py', 'src/evidencias.py',
    'src/recuperacao_fila.py', 'src/atribuicao.py', 'src/supervisor.py', 'src/dashboard.py',
    'tests/testes.py', 'tests/testes_conhecimento.py', 'tests/testes_autonomia.py',
    'tests/testes_decisao.py', 'tests/testes_esquemas.py', 'tests/testes_recuperacao.py',
    'tests/testes_coordenador.py', 'tests/testes_execucao.py', 'tests/testes_runtime.py',
    'tests/testes_provedores.py', 'tests/testes_mcp04.py', 'tests/apoio_testes04.py',
    'tests/testes_mcp_vetores.py', 'tests/testes_evidencias.py', 'tests/testes_persistencia05.py',
    'tests/testes_mcp05.py', 'tests/testes_recuperacao_fila.py', 'tests/testes_melhorias_seguranca.py',
    'tests/testes_operacao_melhorias.py', 'tests/testes_atribuicao.py', 'tests/testes_continuacoes07.py'
)
DEFAULTS = {'enabled':False,'content_access':'bloqueado','interval_seconds':60,
            'max_jobs_per_hour':12,'max_pending_jobs':100,'max_attempts':3,'job_timeout_seconds':120,
            'job_lifetime_seconds':600,'retry_base_seconds':10,
            'max_files':10000,'max_file_bytes':2000000,'max_total_bytes':64000000,
            'approved_code':None}

RUNTIME_VERSION = '0.5'


def code_hash():
    code_root = Path(__file__).resolve().parent.parent
    return sha(b''.join(name.encode()+b'\0'+(code_root/name).read_bytes() for name in CODE_FILES))

def atomic_json(path, value):
    path=Path(path)
    if path.is_symlink():raise Invalid('arquivo de estado redirecionado')
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp-'+str(uuid.uuid4()))
    with tmp.open('x',encoding='utf-8') as f:
        f.write(json.dumps(value,ensure_ascii=False,indent=2));f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

class Queue:
    def __init__(self, sources=None):
        self.sources=sources or Store()
        self.root,self.vault=self.sources.root,self.sources.vault
        self.state=self.root/'estado';self.db=self.state/'fila.sqlite3'
        self.config_path=config_file(self.root,'autonomia.json')
        self.state.mkdir(exist_ok=True)
        if self.state.resolve().parent!=self.root or self.db.is_symlink():raise Invalid('estado redirecionado')
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS executions(
              id TEXT PRIMARY KEY,request_key TEXT UNIQUE,fingerprint TEXT,kind TEXT,
              execution_status TEXT,created REAL,deadline REAL,not_before REAL,
              attempts INTEGER,max_attempts INTEGER,timeout REAL,owner TEXT,token TEXT,
              lease_until REAL,result TEXT,error TEXT);
            CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT,execution_id TEXT,event TEXT,at REAL,details TEXT);
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
            ''')
            c.execute('CREATE TABLE IF NOT EXISTS execution_inputs(execution_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
            c.execute('''CREATE TABLE IF NOT EXISTS continuations(
                parent_id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
                status TEXT NOT NULL, job_id TEXT, error TEXT)''')
            c.execute('CREATE TABLE IF NOT EXISTS continuation_contracts(parent_id TEXT PRIMARY KEY, contract TEXT NOT NULL, fingerprint TEXT NOT NULL)')

    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=15);c.row_factory=sqlite3.Row
        c.execute('PRAGMA synchronous=FULL')
        try:
            with c:yield c
        finally:c.close()

    def config(self):
        cfg=dict(DEFAULTS)
        if self.config_path.exists():
            if self.config_path.is_symlink():raise Invalid('configuração redirecionada')
            raw=json.loads(self.config_path.read_text(encoding='utf-8'))
            if set(raw)-set(DEFAULTS):raise Invalid('configuração desconhecida')
            cfg.update(raw)
        bounds={'interval_seconds':(5,3600),'max_jobs_per_hour':(1,120),'max_pending_jobs':(1,1000),'max_attempts':(1,5),
                'job_timeout_seconds':(1,300),'job_lifetime_seconds':(1,3600),
                'retry_base_seconds':(1,300),'max_files':(1,10000),
                'max_file_bytes':(1,2000000),'max_total_bytes':(1,64000000)}
        if type(cfg['enabled']) is not bool or cfg['content_access'] not in ('permitido','bloqueado'):
            raise Invalid('autorização inválida')
        for key,(low,high) in bounds.items():
            if type(cfg[key]) is not int or not low<=cfg[key]<=high:raise Invalid('limite inválido: '+key)
        return cfg

    def authorize(self, check_code=True):
        cfg=self.config()
        if (self.state/'implantacao.lock').exists():raise Invalid('executor pausado para manutenção')
        if not cfg['enabled'] or cfg['content_access']!='permitido':raise Invalid('executor desativado ou acesso revogado')
        if check_code and cfg['approved_code']!=code_hash():raise Invalid('código mudou; revisão e aprovação local necessárias')
        return cfg

    def event(self,c,ident,name,details=None,now=None):
        c.execute('INSERT INTO events(execution_id,event,at,details) VALUES(?,?,?,?)',
                  (ident,name,time.time() if now is None else now,canon(details or {})))

    def enqueue(self,key,kind,now=None,payload=None,*,_frozen_contract=None):
        cfg=self.authorize();now=time.time() if now is None else now
        if kind not in KINDS or not isinstance(key,str) or not 1<=len(key)<=120:raise Invalid('trabalho fora do contrato')
        contract={'kind':kind,'max_attempts':cfg['max_attempts'],'timeout':cfg['job_timeout_seconds'],'lifetime':cfg['job_lifetime_seconds']}
        if payload is not None:
            if not isinstance(payload,dict) or len(canon(payload))>40000:raise Invalid('entrada da fila fora do contrato')
            contract['payload']=payload
        if _frozen_contract is not None:
            self._validate_continuation_contract(_frozen_contract,kind)
            if payload is not None:raise Invalid('continuação não aceita entrada substituta')
            contract=dict(_frozen_contract)
        fingerprint=sha(canon(contract).encode())
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT * FROM executions WHERE request_key=?',(key,)).fetchone()
            if old:
                if old['fingerprint']!=fingerprint:raise Conflict('chave já utilizada com outro contrato')
                result=dict(old)
                entry=c.execute('SELECT payload FROM execution_inputs WHERE execution_id=?',(old['id'],)).fetchone()
                result['payload']=entry[0] if entry else '{}'
                return result
            pending=c.execute("SELECT COUNT(*) FROM executions WHERE execution_status IN ('queued','running','waiting','cancelling')").fetchone()[0]
            if pending>=cfg['max_pending_jobs']:raise Invalid('fila atingiu limite de trabalhos pendentes')
            ident=str(uuid.uuid4())
            c.execute('INSERT INTO executions(id,request_key,fingerprint,kind,execution_status,created,deadline,not_before,attempts,max_attempts,timeout,owner,token,lease_until,result,error) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (ident,key,fingerprint,kind,'queued',now,now+contract['lifetime'],now,0,
                       contract['max_attempts'],contract['timeout'],None,None,None,None,None))
            if payload is not None:c.execute('INSERT INTO execution_inputs VALUES(?,?)',(ident,canon(payload)))
            self.event(c,ident,'queued',{'process_ref':KINDS[kind],'root_execution_id':ident,
                       'authorization_ref':'configuracao_local','limits':{'timeout':contract['timeout'],
                       'attempts':contract['max_attempts'],'deadline':now+contract['lifetime']}},now)
            return dict(c.execute("SELECT e.*, COALESCE(i.payload,'{}') AS payload FROM executions e LEFT JOIN execution_inputs i ON i.execution_id=e.id WHERE e.id=?",(ident,)).fetchone())

    def recover(self,c,now):
        for row in c.execute("SELECT * FROM executions WHERE execution_status IN ('running','cancelling') AND lease_until<=?",(now,)).fetchall():
            if row['execution_status']=='cancelling':status='cancelled'
            elif row['attempts']>=row['max_attempts'] or now>=row['deadline']:status='failed'
            else:status='queued'
            c.execute('UPDATE executions SET execution_status=?,owner=NULL,token=NULL,lease_until=NULL,error=? WHERE id=?',
                      (status,'responsável anterior perdeu a reserva; resultado não confirmado',row['id']))
            self.event(c,row['id'],'lease_expired',{'next_status':status},now)
        for row in c.execute("SELECT id FROM executions WHERE execution_status='queued' AND deadline<=?",(now,)).fetchall():
            c.execute("UPDATE executions SET execution_status='failed',error='prazo total excedido' WHERE id=?",(row['id'],))
            self.event(c,row['id'],'deadline_exceeded',now=now)

    def claim(self,owner,now=None):
        cfg=self.authorize();now=time.time() if now is None else now
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');self.recover(c,now)
            starts=c.execute("SELECT COUNT(*) FROM events WHERE event='started' AND at>?",(now-3600,)).fetchone()[0]
            if starts>=cfg['max_jobs_per_hour']:return None
            row=c.execute("SELECT * FROM executions WHERE execution_status='queued' AND not_before<=? AND deadline>? ORDER BY created,id LIMIT 1",(now,now)).fetchone()
            if not row:return None
            token=str(uuid.uuid4());timeout=min(row['timeout'],row['deadline']-now)
            c.execute("UPDATE executions SET execution_status='running',attempts=attempts+1,owner=?,token=?,lease_until=? WHERE id=?",
                      (owner,token,now+timeout+15,row['id']))
            self.event(c,row['id'],'started',{'actor':owner,'attempt':row['attempts']+1,'timeout':timeout},now)
            return dict(c.execute('SELECT * FROM executions WHERE id=?',(row['id'],)).fetchone())

    def get(self,ident):
        with self.connect() as c:
            row=c.execute("SELECT e.*, COALESCE(i.payload,'{}') AS payload FROM executions e LEFT JOIN execution_inputs i ON i.execution_id=e.id WHERE e.id=?",(ident,)).fetchone()
        if not row:raise Invalid('execução inexistente')
        return dict(row)

    def finish(self,ident,token,result=None,error=None,now=None):
        cfg=self.authorize();now=time.time() if now is None else now
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM executions WHERE id=?',(ident,)).fetchone()
            if not row or row['token']!=token or row['execution_status'] not in ('running','cancelling') or row['lease_until']<=now:
                raise Conflict('responsabilidade vencida; não confirmar efeito')
            if row['execution_status']=='cancelling':
                status='cancelled';result=None;error=error or 'Cancelado; efeitos locais anteriores podem permanecer.'
            elif now>=row['deadline']:status='failed';error='prazo total excedido';result=None
            elif error:status='queued' if row['attempts']<row['max_attempts'] else 'failed'
            else:status='completed'
            if result is not None and len(canon(result))>64000:raise Invalid('resultado operacional excede limite')
            delay=min(300,cfg['retry_base_seconds']*2**max(0,row['attempts']-1))
            c.execute('UPDATE executions SET execution_status=?,not_before=?,owner=NULL,token=NULL,lease_until=NULL,result=?,error=? WHERE id=?',
                      (status,now+delay,canon(result) if result is not None else None,str(error)[:1000] if error else None,ident))
            self.event(c,ident,status,{'error':str(error)[:300] if error else None,'result_confirmed':status=='completed'},now)
            following={'audit_vault':('view-after-','refresh_view'),
                       'plan_demand':('audit-after-','audit_vault'),
                       'recalculate_assessment':('audit-after-','audit_vault'),
                       'semantic_revalidation':('audit-after-','audit_vault')}.get(row['kind'])
            if status=='completed' and following:
                c.execute('INSERT OR IGNORE INTO continuations VALUES(?,?,?,\'pending\',NULL,NULL)',
                          (ident,following[0]+ident,following[1]))
                contract={'kind':following[1],'max_attempts':cfg['max_attempts'],'timeout':cfg['job_timeout_seconds'],'lifetime':cfg['job_lifetime_seconds']}
                encoded=canon(contract)
                c.execute('INSERT OR IGNORE INTO continuation_contracts VALUES(?,?,?)',(ident,encoded,sha(encoded.encode())))
                self.event(c,ident,'continuation_reserved',{'kind':following[1]},now)
        return self.get(ident)

    @staticmethod
    def _validate_continuation_contract(contract,kind):
        if not isinstance(contract,dict) or set(contract)!={'kind','max_attempts','timeout','lifetime'} or contract['kind']!=kind:
            raise Invalid('contrato da continuação inválido')
        for key,high in (('max_attempts',5),('timeout',300),('lifetime',3600)):
            if type(contract[key]) is not int or not 1<=contract[key]<=high:raise Invalid('limite da continuação inválido')

    def _continuation_contract(self,entry):
        cfg=self.authorize()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            parent=c.execute('SELECT kind,execution_status FROM executions WHERE id=?',(entry['parent_id'],)).fetchone()
            following={'audit_vault':('view-after-','refresh_view'),'plan_demand':('audit-after-','audit_vault'),
                       'recalculate_assessment':('audit-after-','audit_vault'),'semantic_revalidation':('audit-after-','audit_vault')}
            expected=following.get(parent['kind']) if parent else None
            if not expected or parent['execution_status']!='completed' or (entry['request_key'],entry['kind'])!=(expected[0]+entry['parent_id'],expected[1]):
                raise Conflict('linhagem da continuação não corresponde ao trabalho concluído')
            saved=c.execute('SELECT contract,fingerprint FROM continuation_contracts WHERE parent_id=?',(entry['parent_id'],)).fetchone()
            if saved:
                if sha(saved['contract'].encode())!=saved['fingerprint']:raise Conflict('contrato da continuação divergiu')
                contract=json.loads(saved['contract'])
            else:
                child=c.execute('SELECT * FROM executions WHERE request_key=?',(entry['request_key'],)).fetchone()
                if child:
                    # Migração de uma intenção legada após confirmação perdida:
                    # reutiliza exatamente o filho, sem renovar os seus limites.
                    if child['kind']!=entry['kind'] or c.execute('SELECT 1 FROM execution_inputs WHERE execution_id=?',(child['id'],)).fetchone():
                        raise Conflict('filho legado não corresponde à continuação')
                    lifetime=child['deadline']-child['created']
                    if abs(lifetime-round(lifetime))>0.00001 or child['timeout']!=int(child['timeout']):
                        raise Conflict('limites legados não reconciliáveis')
                    contract={'kind':child['kind'],'max_attempts':child['max_attempts'],'timeout':int(child['timeout']),'lifetime':round(lifetime)}
                    if sha(canon(contract).encode())!=child['fingerprint']:raise Conflict('contrato legado não corresponde ao filho')
                else:
                    contract={'kind':entry['kind'],'max_attempts':cfg['max_attempts'],'timeout':cfg['job_timeout_seconds'],'lifetime':cfg['job_lifetime_seconds']}
                self._validate_continuation_contract(contract,entry['kind'])
                encoded=canon(contract)
                c.execute('INSERT INTO continuation_contracts VALUES(?,?,?)',(entry['parent_id'],encoded,sha(encoded.encode())))
            self._validate_continuation_contract(contract,entry['kind'])
            return contract

    def dispatch_continuations(self,limit=10):
        """A intenção nasce na transação da conclusão; a publicação pode ser repetida."""
        self.authorize()
        if type(limit)is not int or not 1<=limit<=100:raise Invalid('limite de continuações inválido')
        with self.connect() as c:
            pending=[dict(r) for r in c.execute("SELECT * FROM continuations WHERE status='pending' ORDER BY rowid LIMIT ?",(limit,))]
        delivered=[]
        for entry in pending:
            try:
                contract=self._continuation_contract(entry)
                job=self.enqueue(entry['request_key'],entry['kind'],_frozen_contract=contract)
            except (Invalid,Conflict,sqlite3.Error,OSError) as failure:
                # Lotação ou indisponibilidade não desfaz uma conclusão já confirmada.
                reason=str(failure)[:500]
                with self.connect() as c:
                    c.execute("UPDATE continuations SET error=? WHERE parent_id=? AND status='pending'",(reason,entry['parent_id']))
                    if entry['error']!=reason:self.event(c,entry['parent_id'],'continuation_deferred',{'reason':reason})
                continue
            with self.connect() as c:
                c.execute('BEGIN IMMEDIATE')
                changed=c.execute("UPDATE continuations SET status='delivered',job_id=?,error=NULL WHERE parent_id=? AND status='pending'",
                                  (job['id'],entry['parent_id'])).rowcount
                if changed:self.event(c,entry['parent_id'],'continuation_published',{'job_id':job['id']})
            delivered.append(job['id'])
        return delivered

    def cancel(self,ident):
        # Cancelar continua permitido após revogação de leitura.
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM executions WHERE id=?',(ident,)).fetchone()
            if not row:raise Invalid('execução inexistente')
            if row['execution_status'] in ('completed','failed','cancelled','cancelling'):return dict(row)
            status='cancelling' if row['execution_status']=='running' else 'cancelled'
            c.execute('UPDATE executions SET execution_status=? WHERE id=?',(status,ident));self.event(c,ident,status)
        return self.get(ident)

    def snapshot(self):
        cfg=self.authorize();records=[];total=0
        for folder in ('10_Entidades','20_Afirmacoes','30_Fontes','40_Avaliacoes','50_Sinteses','60_Questoes','70_Operacao'):
            directory=self.vault/folder
            if directory.is_symlink() or directory.resolve().parent!=self.vault:raise Invalid('pasta redirecionada')
            for path in sorted(directory.rglob('*.md')):
                if path.is_symlink() or not path.resolve().is_relative_to(self.vault):raise Invalid('arquivo redirecionado')
                size=path.stat().st_size;total+=size
                if size>cfg['max_file_bytes'] or total>cfg['max_total_bytes'] or len(records)>=cfg['max_files']:
                    raise Invalid('base excede orçamento de varredura')
                records.append((str(path.relative_to(self.vault)),sha(path.read_bytes())))
        # Uma alteração da autoridade de fontes também muda a geração observada.
        with self.sources.connect() as c:
            catalog=[tuple(r) for r in c.execute('SELECT id,filename,revision,digest FROM records ORDER BY id')]
            tombstones=[tuple(r) for r in c.execute('SELECT record_id FROM tombstones ORDER BY record_id')]
        return sha(canon({'files':records,'sources':catalog,'excluded':tombstones}).encode())

    def schedule_changes(self):
        self.authorize();generation=self.snapshot()
        with self.connect() as c:old=c.execute("SELECT value FROM metadata WHERE key='scheduled_generation'").fetchone()
        if not old or old[0]!=generation:
            job=self.enqueue('audit-'+generation,'audit_vault')
            with self.connect() as c:
                c.execute("INSERT OR REPLACE INTO metadata VALUES('scheduled_generation',?)",(generation,))
            return job
        return None

    def evidence_epoch(self):
        from conhecimento import Knowledge
        records,_,_=Knowledge(self.sources).catalog()
        primitive={ident:[r['revision'],sha(canon(r['payload']).encode())] for ident,r in records.items()
                   if (r['record_type']=='source' and r['payload']['source_kind'] in ('conversation','conversation_turn','observation_record'))
                   or r['record_type'] in ('instrument','assessment','assessment_response')}
        return sha(canon(primitive).encode())

    def schedule_dependents(self,audit):
        from execucao import config
        from conhecimento import Knowledge
        cfg=config(self.sources)
        if not cfg['enabled'] or not cfg['auto_process_sources']:return []
        records,_,_=Knowledge(self.sources).catalog();jobs=[];calculating=False
        for ident in audit.get('needs_revalidation',[]):
            record=records.get(ident)
            if not record or record['record_type']!='assessment_score':continue
            assessment_id=record['payload']['assessment_ref']['record_id']
            epoch=self.evidence_epoch();key='score-'+sha((assessment_id+epoch).encode())[:60]
            job=self.enqueue(key,'recalculate_assessment',payload={'assessment_id':assessment_id})
            jobs.append(job)
            calculating|=job['execution_status'] in ('queued','running','cancelling')
        epoch=self.evidence_epoch()
        semantic=any(records.get(i,{}).get('record_type') in ('entity','assertion','synthesis','question') for i in audit.get('needs_revalidation',[]))
        with self.connect() as c:prior=c.execute("SELECT value FROM metadata WHERE key='semantic_epoch_reserved'").fetchone()
        if semantic and not calculating and (not prior or prior[0]!=epoch):
            jobs.append(self.enqueue('sem-'+epoch[:60],'semantic_revalidation',payload={}))
            with self.connect() as c:c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('semantic_epoch_reserved',epoch))
        return jobs

    def schedule_runtime(self):
        from execucao import Engine,config
        cfg=config(self.sources)
        if not cfg['enabled'] or not cfg['auto_process_sources']:return []
        engine=Engine(self.sources,authorize=lambda:self.authorize() is not None)
        from recuperacao_fila import recover_expired
        recover_expired(self,engine)
        with engine.q.connect() as c:owned={(r[0],r[1]) for r in c.execute('SELECT id,revision FROM owned_sources')}
        current={};notes={}
        for item in self.sources.list():
            note=self.sources.read(item['id'])
            if note['payload']['source_kind'] not in ('conversation','conversation_turn','observation_record'):continue
            current[item['id']]=[item['revision'],sha(note['payload']['content'].encode())]
            notes[item['id']]=note
        with self.connect() as c:row=c.execute("SELECT value FROM metadata WHERE key='runtime_sources'").fetchone()
        if not row:
            # A implantação registra uma linha de base; não reinventa silenciosamente a entrevista histórica.
            with self.connect() as c:c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('runtime_sources',canon(current)))
            return []
        previous=json.loads(row[0]);jobs=[]
        for ident,version in current.items():
            if previous.get(ident)==version or (ident,version[0]) in owned:continue
            note=notes[ident];key='auto-'+sha(canon([ident,version]).encode())[:60]
            demand=engine.start(key,'contribution',{'text':note['payload']['content'],'title':note['title'],
                    'source_ref':{'record_id':ident,'revision':version[0]}})
            jobs.append(self.enqueue(key,'plan_demand',payload={'execution_id':demand}))
            if version[0]>1:
                with self.connect() as c:c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('semantic_epoch_reserved',self.evidence_epoch()))
        with self.connect() as c:c.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('runtime_sources',canon(current)))
        return jobs

    def schedule_laboratory(self):
        from execucao import Engine,config
        if not config(self.sources)['enabled']:return []
        engine=Engine(self.sources,authorize=lambda:self.authorize() is not None)
        with engine.q.connect() as c:
            failed=[dict(r) for r in c.execute("SELECT id,status,error FROM demands WHERE status IN ('failed','blocked','uncertain') ORDER BY created LIMIT 20")]
        if not failed:return []
        generation=sha(canon([code_hash(),failed]).encode())
        # Uma ocorrência e versão geram no máximo uma candidata, sem laço de chamadas.
        job=self.enqueue('gap-'+generation[:60],'evaluate_candidate',payload={'candidate':{
            'kind':'execution_gap','value':{'demands':[r['id'] for r in failed]},
            'reason':'Execuções interrompidas: investigar as falhas registradas antes de ampliar a capacidade.'}})
        return [job]

    def summary(self):
        with self.connect() as c:
            counts={r[0]:r[1] for r in c.execute('SELECT execution_status,COUNT(*) FROM executions GROUP BY execution_status')}
            latest=[dict(r) for r in c.execute('SELECT id,kind,execution_status,attempts,error FROM executions ORDER BY created DESC LIMIT 10')]
            continuations=c.execute("SELECT COUNT(*) FROM continuations WHERE status='pending'").fetchone()[0]
        return {'enabled':self.config()['enabled'],'counts':counts,'latest':latest,'pending_continuations':continuations}

    def publish_view(self):
        self.authorize();directory=self.vault/'80_Visoes'
        if directory.is_symlink() or directory.resolve().parent!=self.vault:raise Invalid('visão redirecionada')
        directory.mkdir(exist_ok=True);path=directory/'Manutenção automática.md'
        summary=self.summary()
        text='# Manutenção automática\n\nAtualizada em '+NOW()+'.\n\n'
        text+='Manutenção e demandas conforme os executores habilitados. Ajustes automáticos permanecem delimitados e registrados.\n\n'
        text+='| Estado | Quantidade |\n|---|---|\n'+''.join('| '+k+' | '+str(v)+' |\n' for k,v in sorted(summary['counts'].items()))
        text+='\nHistórico completo e resultados: `'+str(self.state/'fila.sqlite3')+'`.\n'
        data=text.encode('utf-8')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE');known=c.execute("SELECT value FROM metadata WHERE key='view_digest'").fetchone()
            with exclusive(path,create=not path.exists()) as f:
                old=f.read()
                if old and (not known or sha(old)!=known[0]):raise Conflict('visão editada externamente; não sobrescrita')
                f.seek(0);f.write(data);f.truncate();f.flush();os.fsync(f.fileno())
            c.execute("INSERT OR REPLACE INTO metadata VALUES('view_digest',?)",(sha(data),))
        return {'view_updated':True,'execution_counts':summary['counts']}

def perform(q,kind):
    q.authorize()
    if kind=='audit_vault':
        from conhecimento import Knowledge
        before=q.snapshot();result=Knowledge(q.sources).audit();after=q.snapshot()
        if before!=after:raise Conflict('base mudou durante auditoria; refazer sob o mesmo orçamento')
        dependent_jobs=q.schedule_dependents(result)
        return {'generation':after,'audit':result,'scheduled_dependents':len(dependent_jobs),'completion_quality':'limited',
                'limits':'Auditoria estrutural; não valida veracidade nem interpretações clínicas.'}
    if kind=='selftest':
        from autoteste import run_tests
        report=run_tests()
        if report['status']!='passed':raise Invalid('autotestes falharam; consultar estado/autoteste.json')
        return {'status':'passed','fingerprint':report['fingerprint'],'checked_at':report['checked_at']}
    if kind=='refresh_view':return q.publish_view()
    if kind=='recalculate_assessment':
        from avaliacoes import score
        job=q.get(os.environ['CEREBRO_JOB_ID']);payload=json.loads(job.get('payload') or '{}')
        return score(q.sources,'fila-'+job['id'].replace('-',''),payload['assessment_id'])
    if kind in ('plan_demand','semantic_revalidation','research_external','evaluate_candidate'):
        from execucao import Engine
        job=q.get(os.environ['CEREBRO_JOB_ID'])
        payload=json.loads(job.get('payload') or '{}');engine=Engine(q.sources,authorize=lambda:q.authorize() is not None)
        if kind=='plan_demand':ident=payload['execution_id']
        else:
            task={'semantic_revalidation':'revalidation','research_external':'research','evaluate_candidate':'improvement'}[kind]
            ident=engine.start('fila-'+job['id'].replace('-',''),task,payload)
        outcome=engine.run(ident)
        if outcome['status'] in ('failed','uncertain','blocked'):raise Invalid('demanda não concluiu: '+str(outcome['demand'].get('error')))
        if kind=='evaluate_candidate':
            from execucao import config
            if config(q.sources)['auto_adopt_config']:
                completed=[s for s in outcome['steps'] if s['capability']=='record_candidate' and s['result']]
                if completed:
                    result=json.loads(completed[-1]['result'])
                    if result.get('evaluation',{}).get('eligible'):
                        from melhorias import adopt
                        adopt(q.sources,'auto-'+job['id'],result['candidate_record']['id'])
        return {'status':outcome['status'],'execution_id':outcome['execution_id'],
                'question':outcome['demand'].get('question'),'error':outcome['demand'].get('error')}
    raise Invalid('função fora da lista permitida')

def stop_child(process):
    if process.poll() is not None:return
    # Somente a árvore do subprocesso criado por este trabalhador.
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
    else:process.kill()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill()

def run_one(q,owner='worker-local'):
    q.dispatch_continuations()
    job=q.claim(owner)
    if not job:return None
    timeout=min(job['timeout'],job['deadline']-time.time())
    command=[sys.executable,str(Path(__file__).resolve().with_name('autonomia.py')),'action','--root',str(q.root),
             '--vault',str(q.vault),'--job',job['id'],'--token',job['token']]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1',CEREBRO_JOB_ID=job['id'])
    child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags,env=env)
    start=time.monotonic();out=b'';error=None;heartbeat=0
    try:
        while True:
            cfg=q.config();current=q.get(job['id'])
            if (not cfg['enabled'] or cfg['content_access']!='permitido' or (q.state/'implantacao.lock').exists()
                    or current['execution_status'] in ('cancelling','cancelled')):
                stop_child(child);error='interrompido por cancelamento ou revogação';break
            if time.monotonic()>=heartbeat:
                atomic_json(q.state/'worker.json',{'pid':os.getpid(),'runtime_version':RUNTIME_VERSION,'status':'running','updated_at':NOW(),'active_job':job['id']})
                heartbeat=time.monotonic()+5
            remaining=timeout-(time.monotonic()-start)
            if remaining<=0:stop_child(child);error='tempo por tentativa excedido';break
            try:
                out,err=child.communicate(timeout=min(0.5,remaining))
                if child.returncode!=0:error='execução falhou: '+err.decode('utf-8',errors='replace')[-600:]
                break
            except subprocess.TimeoutExpired:continue
        if error is None:
            if len(out)>64000:raise Invalid('saída excede orçamento')
            result=json.loads(out.decode('utf-8'))
        else:result=None
        # Revogação impede publicar o conteúdo. A reserva expira para reconciliação.
        if not q.config()['enabled'] or q.config()['content_access']!='permitido':return {'status':'stopped_without_confirmation'}
        if (q.state/'implantacao.lock').exists():return {'status':'stopped_without_confirmation'}
        if q.get(job['id'])['execution_status']=='cancelled':return q.get(job['id'])
        record=q.finish(job['id'],job['token'],result,error)
        q.dispatch_continuations()
        return record
    except BaseException:
        stop_child(child)
        raise

def worker_health(path,now=None):
    """Separa o estado relatado do sinal de atividade e da existência do PID."""
    from datetime import datetime,timezone
    path=Path(path)
    if not path.exists():return {'status':'not_started','health':'not_started','pid_alive':None}
    record=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record,dict):raise Invalid('estado do trabalhador inválido')
    observed=time.time() if now is None else now
    try:age=observed-datetime.fromisoformat(record['updated_at']).timestamp()
    except (KeyError,TypeError,ValueError):age=None
    alive=None;pid=record.get('pid')
    if os.name=='nt' and type(pid)is int and pid>0:
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if handle:
            try:
                code=ctypes.c_uint32()
                if kernel.GetExitCodeProcess(handle,ctypes.byref(code)):alive=code.value==259
            finally:kernel.CloseHandle(handle)
        elif ctypes.get_last_error() in (87,1168):alive=False
    reported=record.get('status','unknown')
    health=('stopped' if reported=='stopped' else 'not_running' if alive is False else
            'stale' if age is None or age>30 or age < -5 else reported)
    return dict(record,reported_status=reported,health=health,pid_alive=alive,
                heartbeat_age_seconds=round(age,1) if age is not None else None,
                checked_at=datetime.fromtimestamp(observed,timezone.utc).isoformat(),
                limits='PID e atividade são diagnóstico local; não autenticam a identidade de um processo.')


def daemon(q):
    lock=q.state/'worker.lock'
    try:handle=exclusive(lock,create=not lock.exists())
    except Exception:raise Invalid('outro trabalhador já mantém a reserva local')
    with handle:
        atomic_json(q.state/'worker.json',{'pid':os.getpid(),'runtime_version':RUNTIME_VERSION,'status':'starting','updated_at':NOW()})
        loaded_signature=code_hash()
        with q.connect() as c:q.event(c,None,'worker_started',{'pid':os.getpid(),'code':loaded_signature})
        try:
            q.authorize()
            # Fixtures não iniciam recursivamente a própria suíte completa.
            if q.root==REAL_SYSTEM:
                q.enqueue('selftest-'+code_hash(),'selftest')
                from execucao import config
                if config(q.sources)['enabled']:q.enqueue('lab-'+code_hash(),'evaluate_candidate',payload={})
            next_scan=0;heartbeat=0;last_error=None
            while q.config()['enabled']:
                try:
                    if code_hash()!=loaded_signature:
                        raise Invalid('código mudou desde o início do trabalhador; validar e reiniciar antes de executar')
                    cfg=q.authorize()
                    if time.monotonic()>=next_scan:
                        next_scan=time.monotonic()+cfg['interval_seconds'];q.schedule_changes();q.schedule_runtime();q.schedule_laboratory()
                    result=run_one(q)
                    if time.monotonic()>=heartbeat or last_error:
                        atomic_json(q.state/'worker.json',{'pid':os.getpid(),'runtime_version':RUNTIME_VERSION,'status':'running','updated_at':NOW(),
                                    'last_job':result['id'] if result and 'id' in result else None})
                        heartbeat=time.monotonic()+5;last_error=None
                except Exception as error:
                    if str(error)!=last_error:
                        with q.connect() as c:q.event(c,None,'attention_required',{'reason':str(error)[:500]})
                    if str(error)!=last_error or time.monotonic()>=heartbeat:
                        atomic_json(q.state/'worker.json',{'pid':os.getpid(),'runtime_version':RUNTIME_VERSION,'status':'attention_required','updated_at':NOW(),'reason':str(error)[:500]})
                        heartbeat=time.monotonic()+30;last_error=str(error)
                time.sleep(1)
        finally:
            atomic_json(q.state/'worker.json',{'pid':os.getpid(),'runtime_version':RUNTIME_VERSION,'status':'stopped','updated_at':NOW()})
            with q.connect() as c:q.event(c,None,'worker_stopped',{'pid':os.getpid()})

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['serve','action','status','once','enable','disable','enqueue'])
    parser.add_argument('--root',default=str(REAL_SYSTEM));parser.add_argument('--vault',default=str(REAL_VAULT))
    parser.add_argument('--job');parser.add_argument('--token');parser.add_argument('--kind',choices=sorted(KINDS));parser.add_argument('--key')
    args=parser.parse_args();q=Queue(Store(args.root,args.vault))
    if args.command=='enable':
        from autoteste import gate
        gate(q.sources)
        cfg=q.config();cfg.update(enabled=True,content_access='permitido',approved_code=code_hash());atomic_json(q.config_path,cfg)
        print(json.dumps({'status':'enabled','limits':cfg}))
    elif args.command=='disable':
        cfg=q.config();cfg['enabled']=False;atomic_json(q.config_path,cfg);print('{"status":"disabled"}')
    elif args.command=='status':print(json.dumps(q.summary(),ensure_ascii=False))
    elif args.command=='enqueue':print(json.dumps(q.enqueue(args.key,args.kind),ensure_ascii=False))
    elif args.command=='once':q.schedule_changes();print(json.dumps(run_one(q),ensure_ascii=False))
    elif args.command=='serve':daemon(q)
    elif args.command=='action':
        job=q.get(args.job);q.authorize()
        if job['execution_status']!='running' or job['token']!=args.token or job['lease_until']<=time.time():raise Conflict('reserva inválida')
        print(json.dumps(perform(q,job['kind']),ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(str(error),file=sys.stderr);sys.exit(1)
