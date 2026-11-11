"""Coordenador: contratos registrados, fila durável e espera explícita.

Capacidades, modelos e rede são registrados pelo serviço hospedeiro.
Registrar capacidade é configuração do programa, não conteúdo de nota.
"""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


TERMINAL_STATUSES = frozenset(('completed','failed','cancelled','superseded'))


class ContractError(ValueError): pass


class NeedAnswer(Exception):
    def __init__(self, question):
        if not isinstance(question, str) or not question.strip():
            raise ContractError('espera precisa de uma pergunta específica')
        self.question=question


@dataclass(frozen=True)
class Capability:
    version: str
    handler: object
    validate: object
    writes: bool=False
    uses_model: bool=False
    reconcile: object=None


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def validate_plan(steps):
    if not isinstance(steps,list) or not steps or len(steps)>32:
        raise ContractError('plano vazio ou extenso demais')
    identifiers=[]
    for step in steps:
        if (not isinstance(step,dict) or set(step)-{'id','capability','version','depends_on'} or
                any(not isinstance(step.get(k),str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',step[k])
                    for k in ('id','capability','version'))):
            raise ContractError('etapa fora do contrato')
        if not isinstance(step.get('depends_on',[]),list):
            raise ContractError('dependências inválidas')
        identifiers.append(step['id'])
    if len(set(identifiers))!=len(identifiers):
        raise ContractError('identidade de etapa duplicada')
    if any(dep not in identifiers for s in steps for dep in s.get('depends_on',[])):
        raise ContractError('dependência inexistente')
    done=set()
    while len(done)<len(steps):
        ready={s['id'] for s in steps if set(s.get('depends_on',[]))<=done}-done
        if not ready: raise ContractError('ciclo sem ponto inicial')
        done|=ready


def plan_for(kind):
    """Escolhe contratos para intenções conhecidas; não executa código de uma fonte."""
    routes={
        'contribution':['retrieve','extract','apply_contribution','respond'],
        'question':['retrieve','assess_context','respond'],
        'correction':['correct_source','find_affected','semantic_revalidation','respond'],
        'revalidation':['find_affected','semantic_revalidation','respond'],
        'research':['research_external','evaluate_evidence','respond'],
        'improvement':['inspect_capabilities','research_external','propose_candidate','evaluate_candidate','record_candidate'],
        'outcome':['record_outcome','find_affected','semantic_revalidation','respond'],
    }
    if kind not in routes: raise ContractError('intenção sem contrato executável')
    result=[]
    for i,name in enumerate(routes[kind]):
        result.append({'id':name,'capability':name,'version':'v1',
                       'depends_on':[] if i==0 else [result[-1]['id']]})
    return result


class Coordinator:
    def __init__(self,root,capabilities=None,authorize=lambda:True,context_token=lambda:'fixture',clock=time.time,
                 origin_validator=None):
        self.root=Path(root).resolve()
        from nucleo import REAL_SYSTEM,Invalid
        valid=(self.root==REAL_SYSTEM/'estado'/'coordenacao' or
               self.root.is_relative_to(REAL_SYSTEM/'testes_temporarios'))
        if not valid:raise ContractError('estado da coordenação fora do serviço autorizado')
        self.root.mkdir(parents=True,exist_ok=True)
        self.db=self.root/'coordenacao.sqlite3'
        if self.db.is_symlink():raise ContractError('estado redirecionado')
        self.capabilities=dict(capabilities or {})
        self.authorize,self.context_token,self.clock=authorize,context_token,clock
        self.origin_validator=origin_validator
        with self.connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS demands(id TEXT PRIMARY KEY,request_key TEXT UNIQUE,fingerprint TEXT,
              payload TEXT,limits_json TEXT,status TEXT,created REAL,deadline REAL,actions INTEGER,model_calls INTEGER,
              context_token TEXT,question TEXT,answer TEXT,error TEXT);
            CREATE TABLE IF NOT EXISTS steps(demand_id TEXT,id TEXT,position INTEGER,capability TEXT,version TEXT,
              deps TEXT,status TEXT,result TEXT,token TEXT,lease REAL,operation_key TEXT,error TEXT,
              PRIMARY KEY(demand_id,id));
            CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,demand_id TEXT,
              step_id TEXT,event TEXT,details TEXT,at REAL);
            CREATE TABLE IF NOT EXISTS demand_supersessions(old_demand TEXT PRIMARY KEY,
              new_demand TEXT NOT NULL UNIQUE,old_job TEXT NOT NULL,created REAL NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.db,timeout=15); c.row_factory=sqlite3.Row
        c.execute('PRAGMA synchronous=FULL')
        try:
            with c:yield c
        finally:c.close()

    def event(self,c,ident,step,event,details=None):
        c.execute('INSERT INTO events(demand_id,step_id,event,details,at) VALUES(?,?,?,?,?)',
                  (ident,step,event,encoded(details or {}),self.clock()))

    def submit(self,key,steps,payload,limits):
        if not self.authorize(): raise ContractError('acesso revogado')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key):
            raise ContractError('chave inválida')
        validate_plan(steps)
        if not isinstance(payload,dict) or len(encoded(payload))>40000:
            raise ContractError('entrada fora do contrato')
        if not isinstance(limits,dict) or set(limits)!={'max_actions','max_model_calls','max_seconds'}:
            raise ContractError('limites devem ser explícitos')
        for name,low,high in [('max_actions',1,64),('max_model_calls',0,16),('max_seconds',1,3600)]:
            if type(limits[name]) is not int or not low<=limits[name]<=high:
                raise ContractError('limite inválido: '+name)
        fingerprint=hashlib.sha256(encoded([steps,payload,limits]).encode()).hexdigest()
        now=self.clock()
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            prior=c.execute('SELECT id,fingerprint FROM demands WHERE request_key=?',(key,)).fetchone()
            if prior:
                if prior['fingerprint']!=fingerprint: raise ContractError('chave reutilizada com outra demanda')
                return prior['id']
            ident=uuid.uuid4().hex
            c.execute('INSERT INTO demands VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (ident,key,fingerprint,encoded(payload),encoded(limits),'queued',now,now+limits['max_seconds'],
                       0,0,self.context_token(),None,None,None))
            for position,step in enumerate(steps):
                operation=hashlib.sha256((ident+':'+step['id']).encode()).hexdigest()
                c.execute('INSERT INTO steps VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                          (ident,step['id'],position,step['capability'],step['version'],
                           encoded(step.get('depends_on',[])),'queued',None,None,None,operation,None))
            self.event(c,ident,None,'submitted',{'steps':len(steps)})
        return ident

    def inspect(self,ident):
        if not self.authorize():raise ContractError('acesso revogado')
        with self.connect() as c:
            row=c.execute('SELECT * FROM demands WHERE id=?',(ident,)).fetchone()
            if not row: raise ContractError('demanda inexistente')
            steps=[dict(r) for r in c.execute('SELECT * FROM steps WHERE demand_id=? ORDER BY position',(ident,))]
            lineage=c.execute('SELECT new_demand FROM demand_supersessions WHERE old_demand=?',(ident,)).fetchone()
        demand=dict(row)
        demand['effects_uncertain']=any(s['status']=='uncertain' or
            (demand['status'] in TERMINAL_STATUSES and s['status']=='running') for s in steps)
        demand['superseded_by']=lineage['new_demand'] if lineage else None
        return {'demand':demand,'steps':steps}

    def _settle_cancellation(self,c,ident,previous_status):
        now=self.clock()
        running=c.execute("SELECT id,lease,token FROM steps WHERE demand_id=? AND status='running'",(ident,)).fetchall()
        active=False
        for step in running:
            if previous_status!='cancelled' and step['token'] and step['lease'] is not None and step['lease']>now:
                active=True
                continue
            c.execute("UPDATE steps SET status='uncertain',token=NULL,lease=NULL,error=COALESCE(error,?) WHERE demand_id=? AND id=?",
                      ('cancelamento após reserva vencida; efeito não confirmado',ident,step['id']))
            self.event(c,ident,step['id'],'cancelled_reservation_expired')
        status='cancelling' if active and previous_status!='cancelled' else 'cancelled'
        uncertain=c.execute("SELECT 1 FROM steps WHERE demand_id=? AND status='uncertain' LIMIT 1",(ident,)).fetchone()
        c.execute('UPDATE demands SET status=?,question=NULL,error=CASE WHEN ? THEN ? ELSE error END WHERE id=?',
                  (status,bool(uncertain),'cancelada; efeitos incertos exigem reconciliação',ident))
        if status!=previous_status:
            self.event(c,ident,None,status,{'previous_status':previous_status,'effects_uncertain':bool(uncertain)})
        return status

    def supersede(self,ident,successor,old_job):
        """Vincula a sucessora e impede novas etapas da original na mesma transação.

        O enfileiramento ocorre depois desta reserva durável; uma interrupção
        não devolve a original à fila nem renova os limites de nenhuma demanda.
        """
        if not self.authorize():raise ContractError('acesso revogado')
        if (any(not isinstance(value,str) or not value or len(value)>120 for value in (ident,successor,old_job))
                or ident==successor):raise ContractError('linhagem inválida')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            old=c.execute('SELECT status,payload,error FROM demands WHERE id=?',(ident,)).fetchone()
            new=c.execute('SELECT payload FROM demands WHERE id=?',(successor,)).fetchone()
            link=c.execute('SELECT * FROM demand_supersessions WHERE old_demand=?',(ident,)).fetchone()
            if not old or not new:raise ContractError('demanda da linhagem inexistente')
            try:
                before,after=json.loads(old['payload']),json.loads(new['payload'])
            except (ValueError,TypeError) as failure:
                raise ContractError('entrada da linhagem inválida') from failure
            if (not isinstance(before,dict) or not isinstance(after,dict) or before.get('kind')!='contribution'
                    or before.get('recovery_of') or after.get('kind')!='contribution' or after.get('recovery_of')!=ident
                    or not isinstance(before.get('source_ref'),dict) or before['source_ref']!=after.get('source_ref')):
                raise ContractError('sucessora não comprova a origem da recuperação')
            reference=before['source_ref']
            if (not isinstance(reference.get('record_id'),str) or not reference['record_id'] or
                    type(reference.get('revision')) is not int or reference['revision']<1):
                raise ContractError('referência da linhagem inválida')
            if link:
                if old['status']!='superseded' or link['new_demand']!=successor or link['old_job']!=old_job:
                    raise ContractError('original já vinculada a outra recuperação ou estado')
                return dict(link)
            if old['status'] not in ('queued','failed') or (old['status']=='failed' and old['error']!='prazo total excedido'):
                raise ContractError('original não pode ser substituída neste estado')
            steps=c.execute('SELECT capability,status FROM steps WHERE demand_id=?',(ident,)).fetchall()
            if not steps or any(s['status'] in ('running','uncertain') or
                    (s['capability']=='apply_contribution' and s['status'] in ('completed','failed')) for s in steps):
                raise ContractError('efeito aplicado ou incerto impede substituição')
            c.execute('INSERT INTO demand_supersessions VALUES(?,?,?,?)',(ident,successor,old_job,self.clock()))
            c.execute("UPDATE demands SET status='superseded',question=NULL WHERE id=?",(ident,))
            self.event(c,ident,None,'superseded',{'new_demand':successor,'old_job':old_job,'previous_status':old['status']})
            return dict(c.execute('SELECT * FROM demand_supersessions WHERE old_demand=?',(ident,)).fetchone())

    def run_one(self,ident):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            demand=c.execute('SELECT * FROM demands WHERE id=?',(ident,)).fetchone()
            if not demand: raise ContractError('demanda inexistente')
            if demand['status'] in ('cancelling','cancelled'):
                return self._settle_cancellation(c,ident,demand['status'])
            if demand['status'] not in ('queued','blocked','running'): return demand['status']
            if not self.authorize():
                c.execute("UPDATE demands SET status='blocked',error='acesso revogado' WHERE id=?",(ident,));return 'blocked'
            steps=list(c.execute('SELECT * FROM steps WHERE demand_id=? ORDER BY position',(ident,)))
            running=[s for s in steps if s['status']=='running']
            if running and (not running[0]['token'] or running[0]['lease'] is None or running[0]['lease']<=self.clock()):
                c.execute("UPDATE steps SET status='uncertain',token=NULL,lease=NULL,error='reserva vencida' WHERE demand_id=? AND id=?",(ident,running[0]['id']))
                c.execute("UPDATE demands SET status='uncertain',error='reconciliar antes de repetir' WHERE id=?",(ident,))
                self.event(c,ident,running[0]['id'],'reservation_expired')
                return 'uncertain'
            if self.clock()>=demand['deadline']:
                c.execute("UPDATE demands SET status='failed',error='prazo total excedido' WHERE id=?",(ident,));return 'failed'
            if self.context_token()!=demand['context_token']:
                c.execute("UPDATE demands SET status='blocked',error='contexto mudou; replanejamento necessário' WHERE id=?",(ident,));return 'blocked'
            if running:return 'running'
            done={s['id'] for s in steps if s['status']=='completed'}
            if len(done)==len(steps):
                c.execute("UPDATE demands SET status='completed',error=NULL WHERE id=?",(ident,));return 'completed'
            ready=[s for s in steps if s['status']=='queued' and set(json.loads(s['deps']))<=done]
            if not ready: raise ContractError('não há próxima etapa válida')
            step=ready[0];cap=self.capabilities.get(step['capability'])
            if not cap or cap.version!=step['version']:
                c.execute("UPDATE demands SET status='blocked',error=? WHERE id=?",('capacidade ausente/incompatível: '+step['capability'],ident))
                return 'blocked'
            limits=json.loads(demand['limits_json'])
            if demand['actions']>=limits['max_actions'] or (cap.uses_model and demand['model_calls']>=limits['max_model_calls']):
                c.execute("UPDATE demands SET status='failed',error='orçamento esgotado' WHERE id=?",(ident,));return 'failed'
            token=uuid.uuid4().hex
            c.execute("UPDATE steps SET status='running',token=?,lease=? WHERE demand_id=? AND id=?",(token,min(demand['deadline'],self.clock()+120),ident,step['id']))
            c.execute("UPDATE demands SET status='running',actions=actions+1,model_calls=model_calls+? WHERE id=?",(int(cap.uses_model),ident))
            previous={s['id']:json.loads(s['result']) for s in steps if s['status']=='completed'}
            context={'input':json.loads(demand['payload']),'previous':previous,'demand_id':ident,'step_id':step['id'],
                     'answer':json.loads(demand['answer']) if demand['answer'] else None,
                     'operation_key':step['operation_key']}
            self.event(c,ident,step['id'],'started')
        outcome='completed';error=None;result=None
        try:
            result=cap.handler(context)
            if len(encoded(result))>64000 or cap.validate(result) is not True:
                raise ContractError('saída não atende ao contrato consumidor')
        except NeedAnswer as waiting:
            outcome='waiting_user';error=waiting.question
        except Exception as failure:
            result=getattr(failure,'partial_result',result)
            try:
                observed=encoded(result)
                if len(observed)>64000:result={'oversized_partial_result':True,'digest':hashlib.sha256(observed.encode()).hexdigest()}
            except (TypeError,ValueError):result={'unserializable_partial_result':True,'type':type(result).__name__}
            outcome='uncertain' if cap.writes else 'failed';error=type(failure).__name__+': '+str(failure)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT status,token,lease FROM steps WHERE demand_id=? AND id=?',(ident,step['id'])).fetchone()
            current_demand=c.execute('SELECT status FROM demands WHERE id=?',(ident,)).fetchone()['status']
            if current['token']!=token or current['status']!='running':
                if result is not None:
                    self.event(c,ident,step['id'],'late_observation',{'result':result,'outcome':outcome})
                if current_demand in ('cancelling','cancelled'):
                    return self._settle_cancellation(c,ident,current_demand)
                return current_demand if current_demand in TERMINAL_STATUSES else 'uncertain'
            if current['lease'] is None or current['lease']<=self.clock():
                c.execute("UPDATE steps SET status='uncertain',result=?,token=NULL,lease=NULL,error='confirmação fora da reserva' WHERE demand_id=? AND id=?",(encoded(result) if result is not None else None,ident,step['id']))
                self.event(c,ident,step['id'],'uncertain',{'error':'confirmação fora da reserva'})
                if current_demand in ('cancelling','cancelled'):
                    return self._settle_cancellation(c,ident,current_demand)
                if current_demand in TERMINAL_STATUSES:return current_demand
                c.execute("UPDATE demands SET status='uncertain',error='confirmação fora da reserva' WHERE id=?",(ident,))
                return 'uncertain'
            if not self.authorize() or self.context_token()!=demand['context_token']:
                outcome='uncertain' if cap.writes else 'blocked';error='acesso/contexto mudou durante a etapa'
            c.execute('UPDATE steps SET status=?,result=?,token=NULL,lease=NULL,error=? WHERE demand_id=? AND id=?',
                      (outcome,encoded(result) if result is not None else None,error,ident,step['id']))
            if current_demand in ('cancelling','cancelled'):
                root_status=self._settle_cancellation(c,ident,current_demand)
            elif current_demand in TERMINAL_STATUSES:
                root_status=current_demand
            else:
                root_status='queued' if outcome=='completed' else outcome
                c.execute('UPDATE demands SET status=?,question=?,error=? WHERE id=?',
                          (root_status,error if outcome=='waiting_user' else None,error,ident))
            self.event(c,ident,step['id'],outcome,{'error':error})
        return root_status

    def answer(self,ident,value,origin):
        if (not self.authorize() or not origin or not isinstance(value,str) or not value.strip()
                or len(value)>20000 or not self.origin_validator or self.origin_validator(origin) is not True):
            raise ContractError('resposta precisa de conteúdo, origem e acesso')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT status,deadline,context_token,answer FROM demands WHERE id=?',(ident,)).fetchone()
            if not row or row['status']!='waiting_user': raise ContractError('demanda não está aguardando resposta')
            if self.clock()>=row['deadline'] or self.context_token()!=row['context_token']:
                raise ContractError('prazo ou contexto precisa de revisão antes da retomada')
            answer={'value':value,'origin':origin}
            if row['answer']:answer['previous']=json.loads(row['answer'])
            if len(encoded(answer))>60000:raise ContractError('histórico de esclarecimentos excede o limite da demanda')
            c.execute("UPDATE demands SET status='queued',answer=?,question=NULL,error=NULL WHERE id=?",(encoded(answer),ident))
            c.execute("UPDATE steps SET status='queued',error=NULL WHERE demand_id=? AND status='waiting_user'",(ident,))
            self.event(c,ident,None,'answer_received')

    def reconcile(self,ident,step_id):
        if not self.authorize():raise ContractError('acesso revogado')
        snapshot=self.inspect(ident)
        step=next((s for s in snapshot['steps'] if s['id']==step_id),None)
        if not step or step['status']!='uncertain':raise ContractError('etapa não está incerta')
        if snapshot['demand']['status'] not in ('uncertain','cancelled'):
            raise ContractError('demanda não admite reconciliação neste estado')
        if self.context_token()!=snapshot['demand']['context_token']:
            raise ContractError('acesso/contexto precisa ser revalidado')
        paused='cancelled' if snapshot['demand']['status']=='cancelled' else 'uncertain'
        cap=self.capabilities.get(step['capability'])
        if not cap or cap.version!=step['version'] or not cap.reconcile:return paused
        confirmed=cap.reconcile(step['operation_key'])
        if not isinstance(confirmed,dict) or confirmed.get('status')!='confirmed':return paused
        result=confirmed.get('result')
        if cap.validate(result) is not True or len(encoded(result))>64000:
            raise ContractError('confirmação inválida')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            current=c.execute('SELECT status FROM steps WHERE demand_id=? AND id=?',(ident,step_id)).fetchone()
            demand=c.execute('SELECT status,context_token FROM demands WHERE id=?',(ident,)).fetchone()
            if current['status']!='uncertain' or demand['status'] not in ('uncertain','cancelled'):
                raise ContractError('reconciliação perdeu a responsabilidade')
            if not self.authorize() or self.context_token()!=demand['context_token']:
                raise ContractError('acesso/contexto precisa ser revalidado')
            c.execute("UPDATE steps SET status='completed',result=?,token=NULL,lease=NULL,error=NULL WHERE demand_id=? AND id=?",(encoded(result),ident,step_id))
            status='cancelled' if demand['status']=='cancelled' else 'queued'
            remaining=c.execute("SELECT 1 FROM steps WHERE demand_id=? AND status='uncertain' LIMIT 1",(ident,)).fetchone()
            c.execute('UPDATE demands SET status=?,error=? WHERE id=?',
                      (status,'cancelada; efeitos incertos exigem reconciliação' if remaining else None,ident))
            self.event(c,ident,step_id,'reconciled_confirmed_effect',{'demand_status':status})
        return status

    def cancel(self,ident):
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT status FROM demands WHERE id=?',(ident,)).fetchone()
            if not row:raise ContractError('demanda inexistente')
            if row['status'] in TERMINAL_STATUSES and row['status']!='cancelled':return row['status']
            return self._settle_cancellation(c,ident,row['status'])

    def run_until_pause(self,ident):
        # O limite persistente da raiz impede renovação por reinício ou espera.
        for _ in range(65):
            status=self.run_one(ident)
            if status!='queued':return status
        raise ContractError('passos internos excedidos')
