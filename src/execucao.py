"""Coordena operações reais sob contratos, versões e orçamento da demanda."""
import copy,json,time,re
from pathlib import Path
from nucleo import Store,Invalid,Conflict,NOW,sha,canon,config_file,REAL_SYSTEM
from conhecimento import Knowledge,refs,_request_json
from coordenador import Coordinator,Capability,NeedAnswer,plan_for,ContractError
from recuperacao import Retrieval,LocalEmbeddings
from provedores import TextModel
from pesquisa import research,TERMS
from revalidacao import review,automatic_payload

DEFAULT={'enabled':False,'model':{'enabled':False},'embeddings':{'enabled':False},
         'max_actions':32,'max_model_calls':3,'max_seconds':600,'auto_process_sources':False,
         'auto_adopt_config':False,'message_codec':'compact','retrieval_policy':'hybrid','owner_person_id':None}
_EMBEDDERS={}
EXTRACTION_TYPES=frozenset(('entity','assertion','synthesis','question'))
EXTRACTION_FIELDS=frozenset(('tipo','titulo','payload','evidence_quote','evidence_source','record_id','revisao_esperada'))


def resolve_extraction(value,mapping):
    if isinstance(value,dict):
        ident=value.get('record_id')
        if isinstance(ident,str) and ident in mapping:
            if type(value.get('revision')) is not int or value['revision']!=1:
                raise Invalid('placeholder exige revisão explícita igual a 1')
            return dict(value,**mapping[ident])
        return {k:resolve_extraction(v,mapping) for k,v in value.items()}
    if isinstance(value,list):return [resolve_extraction(v,mapping) for v in value]
    return value


def config(sources):
    path=config_file(sources.root,'execucao.json');result=copy.deepcopy(DEFAULT)
    if path.exists():
        if path.is_symlink():raise Invalid('configuração redirecionada')
        raw=json.loads(path.read_text(encoding='utf-8'))
        if set(raw)-set(DEFAULT):raise Invalid('opção de execução não reconhecida')
        result.update(raw)
    for name,low,high in (('max_actions',1,64),('max_model_calls',0,16),('max_seconds',1,3600)):
        if type(result[name])is not int or not low<=result[name]<=high:raise Invalid('limite de execução inválido: '+name)
    if result['message_codec'] not in ('compact','pretty') or result['retrieval_policy'] not in ('hybrid','lexical'):
        raise Invalid('política de comunicação ou recuperação desconhecida')
    if result['owner_person_id'] is not None and (not isinstance(result['owner_person_id'],str) or not result['owner_person_id'].strip()):
        raise Invalid('identidade do proprietário inválida')
    return result


def validate_citations(sources,citations):
    k=Knowledge(sources);records,_,_=k.catalog();invalid=k.stale(records)
    if not isinstance(citations,list):raise Invalid('citações inválidas')
    for citation in citations:
        if not isinstance(citation,dict) or type(citation.get('revision')) is not int or citation['revision']<1:
            raise Invalid('citação exige referência e revisão inteira positiva')
        target=records.get(citation.get('record_id'))
        quote=citation.get('quote')
        if not target or target['id'] in invalid or citation.get('revision')!=target['revision']:
            raise Conflict('citação ausente, suspensa ou de outra revisão')
        if not isinstance(quote,str) or not quote or quote not in canon(target['payload']) and quote not in str(target['payload'].get('content','')):
            raise Invalid('citação não corresponde ao texto da origem')
    return True


class Engine:
    def __init__(self,sources,authorize=lambda:True,model_factory=None,embedder=None,transport=None):
        self.sources=sources;self.k=Knowledge(sources);self.authorize=authorize;self.cfg=config(sources)
        self.model_factory=model_factory;self.transport=transport;self._models={}
        if embedder is None and self.cfg['embeddings'].get('enabled'):
            folder=self.cfg['embeddings']['folder']
            if folder not in _EMBEDDERS:_EMBEDDERS[folder]=LocalEmbeddings(folder)
            embedder=_EMBEDDERS[folder]
        self.retrieval=Retrieval(sources,embedder if self.cfg['retrieval_policy']=='hybrid' else None)
        manifest=json.loads(config_file(sources.root,'manual_manifest.json').read_text(encoding='utf-8'))
        self.manual={}
        for name,digest in manifest.items():
            manual_dir=sources.vault/'00_Manual'
            path=manual_dir/name
            if sources.root==REAL_SYSTEM and not path.exists() and not path.is_symlink() and (REAL_SYSTEM/'00_Manual'/name).exists():
                manual_dir=REAL_SYSTEM/'00_Manual'
                path=manual_dir/name
            if path.is_symlink() or path.resolve().parent!=manual_dir.resolve():raise Invalid('manual fora do escopo')
            raw=path.read_bytes()
            if sha(raw)!=digest:raise Conflict('manual divergente do manifesto')
            self.manual[name]=raw.decode('utf-8-sig')
        version=sha(canon([manifest,self.cfg]).encode())
        self.q=Coordinator(sources.root/'estado'/'coordenacao',authorize=lambda:self.authorize() and config(sources)['enabled'],
                           context_token=lambda:sha(canon([json.loads(config_file(sources.root,'manual_manifest.json').read_text(encoding='utf-8')),config(sources)]).encode()),
                           origin_validator=self.valid_origin)
        with self.q.connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS owned_sources(id TEXT,revision INTEGER,execution_id TEXT,PRIMARY KEY(id,revision))')
            c.execute('CREATE TABLE IF NOT EXISTS question_links(execution_id TEXT,record_id TEXT,PRIMARY KEY(execution_id,record_id))')
        self.q.capabilities={
          'retrieve':self.cap(self.retrieve), 'extract':self.cap(self.extract,model=True),
          'apply_contribution':self.cap(self.apply_contribution,writes=True),
          'assess_context':self.cap(self.assess,model=True),'respond':self.cap(self.respond,model=False),
          'correct_source':self.cap(self.correct,writes=True),'find_affected':self.cap(self.affected),
          'semantic_revalidation':self.cap(self.revalidate,writes=True,model=True),
          'research_external':self.cap(self.research,writes=True),'evaluate_evidence':self.cap(self.evidence,model=True),
          'record_outcome':self.cap(self.apply_contribution,writes=True),
          'inspect_capabilities':self.cap(self.inspect_capabilities),
          'propose_candidate':self.cap(self.propose,model=True),'evaluate_candidate':self.cap(self.evaluate,writes=True),
          'record_candidate':self.cap(self.record_candidate,writes=True)}
    def cap(self,fn,writes=False,model=False):
        return Capability('v1',fn,lambda r:isinstance(r,dict) and r.get('status') in ('ok','confirmed','completed','limited'),writes,model)
    def valid_origin(self,ref):
        if not isinstance(ref,dict) or type(ref.get('revision')) is not int or ref['revision']<1:return False
        try:return self.sources.read(ref['record_id'])['revision']==ref['revision']
        except (Invalid,Conflict,KeyError):return False
    def _source(self,c):
        ref=c['input'].get('source_ref')
        if ref and not self.valid_origin(ref):raise Conflict('fonte de entrada foi corrigida ou excluída')
    def model(self,c):
        root=c['demand_id']
        if root not in self._models:
            demand=self.q.inspect(root)['demand']
            self._models[root]=(self.model_factory(root) if self.model_factory else
                TextModel(self.sources.root/'estado'/'modelos'/root,self.cfg['model'],
                          json.loads(demand['limits_json'])['max_model_calls'],deadline=demand['deadline']))
        return self._models[root]
    def packet(self,value):
        return json.dumps(value,ensure_ascii=False,indent=2) if self.cfg['message_codec']=='pretty' else canon(value)
    def start(self,key,kind,payload):
        if not self.authorize() or not self.cfg['enabled']:raise Invalid('execução desabilitada')
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key):raise Invalid('chave de demanda inválida')
        if not isinstance(payload,dict):raise Invalid('entrada inválida')
        p=copy.deepcopy(payload)
        if kind in ('contribution','outcome') and 'source_ref' not in p:
            text=p.get('text')
            if not isinstance(text,str) or not text.strip():raise Invalid('contribuição exige texto original')
            source=self.sources.apply(sha((key+'-original').encode()),'create',title=p.get('title','Contribuição recebida'),text=text)
            p['source_ref']={'record_id':source['id'],'revision':source['revision']}
            p['received_at']=self.sources.read(source['id'])['payload']['received_at']
        if kind in ('contribution','outcome'):
            original=self.sources.read(p['source_ref']['record_id'])
            if original['revision']!=p['source_ref']['revision'] or original['payload']['content']!=p.get('text'):
                raise Conflict('trecho recebido não corresponde à origem identificada')
            p['received_at']=original['payload']['received_at']
        if kind in ('contribution','outcome'):
            # O texto original é armazenado uma vez; cada trecho usa a mesma origem.
            text=p['text'];p.setdefault('query',text[:500])
            chunks=[text] if 'extractions' in p else [text[i:i+9000] for i in range(0,len(text),9000)]
            p['chunks']=chunks
            del p['text']
            steps=[{'id':'retrieve','capability':'retrieve','version':'v1','depends_on':[]}]
            if p['source_ref']['revision']>1:
                steps=[{'id':'find_affected','capability':'find_affected','version':'v1','depends_on':[]},
                       {'id':'semantic_revalidation','capability':'semantic_revalidation','version':'v1','depends_on':['find_affected']},
                       {'id':'retrieve','capability':'retrieve','version':'v1','depends_on':['semantic_revalidation']}]
            for index in range(len(chunks)):
                ex='extract_'+str(index);ap='apply_'+str(index)
                steps.append({'id':ex,'capability':'extract','version':'v1','depends_on':[steps[-1]['id']]})
                steps.append({'id':ap,'capability':'apply_contribution','version':'v1','depends_on':[ex]})
            if kind=='outcome':
                steps.append({'id':'find_affected_outcome','capability':'find_affected','version':'v1','depends_on':[steps[-1]['id']]})
                steps.append({'id':'semantic_revalidation_outcome','capability':'semantic_revalidation','version':'v1','depends_on':[steps[-1]['id']]})
            steps.append({'id':'respond','capability':'respond','version':'v1','depends_on':[steps[-1]['id']]})
        elif kind=='improvement' and ('research_terms' not in p or p.get('candidate',{}).get('kind')=='message_codec'):
            names=['inspect_capabilities','propose_candidate','evaluate_candidate','record_candidate']
            steps=[{'id':n,'capability':n,'version':'v1','depends_on':[] if i==0 else [names[i-1]]} for i,n in enumerate(names)]
        elif kind=='question':
            names=['retrieve','assess_context','research_external','evaluate_evidence','respond']
            steps=[{'id':n,'capability':n,'version':'v1','depends_on':[] if i==0 else [names[i-1]]} for i,n in enumerate(names)]
        else:steps=plan_for(kind)
        p['kind']=kind
        ident=self.q.submit(key,steps,p,{'max_actions':self.cfg['max_actions'],'max_model_calls':self.cfg['max_model_calls'],'max_seconds':self.cfg['max_seconds']})
        if p.get('source_ref'):
            with self.q.connect() as c:c.execute('INSERT OR REPLACE INTO owned_sources VALUES(?,?,?)',
                (p['source_ref']['record_id'],p['source_ref']['revision'],ident))
        return ident
    def run(self,ident):
        status=self.q.run_until_pause(ident);snapshot=self.q.inspect(ident)
        if status=='waiting_user':self.record_question(ident,snapshot)
        if status=='completed':self.close_questions(ident,snapshot)
        return {'status':status,'execution_id':ident,'demand':snapshot['demand'],'steps':snapshot['steps']}
    def record_question(self,ident,snapshot):
        p=json.loads(snapshot['demand']['payload']);retrieved=next((json.loads(s['result']) for s in snapshot['steps'] if s['id']=='retrieve' and s['result']),{})
        bases=[{'record_id':r['id'],'revision':r['revision']} for r in retrieved.get('results',[])[:3]]
        if p.get('source_ref') and p['source_ref'] not in bases:bases.append(p['source_ref'])
        question=snapshot['demand']['question']
        result=self.k.apply(sha(canon([ident,question,bases]).encode()),'question','Esclarecimento necessário',
            {'question_text':question,'purpose':'Preencher a lacuna que impediu responder à demanda','trigger_refs':bases,
             'information_needed':question,'impact':'Retomada da demanda','question_status':'awaiting_answer','resolution_status':'unresolved'})
        with self.q.connect() as c:c.execute('INSERT OR IGNORE INTO question_links VALUES(?,?)',(ident,result['id']))
    def close_questions(self,ident,snapshot):
        responses=[json.loads(s['result']) for s in snapshot['steps'] if s['capability']=='respond' and s['result']]
        if not responses or responses[-1].get('quality')=='limited':return
        with self.q.connect() as c:links=[r[0] for r in c.execute('SELECT record_id FROM question_links WHERE execution_id=?',(ident,))]
        records,_,_=self.k.catalog()
        for record_id in links:
            record=records[record_id];p=copy.deepcopy(record['payload'])
            if p['question_status']!='answered' or p['resolution_status']=='resolved':continue
            p['resolution_status']='resolved';p['resolution_refs']=p['answer_refs']+[
                {'record_id':r['record_id'],'revision':r['revision']} for r in responses[-1].get('citations',[])]
            self.k.apply(sha(canon([ident,'resolve',record_id,record['revision']]).encode()),'question',record['title'],p,record_id,record['revision'])
    def answer(self,ident,text,execute=True):
        snapshot=self.q.inspect(ident);current=snapshot['demand']
        if current['answer'] and current['status']!='waiting_user':
            previous=json.loads(current['answer'])
            if previous['value']!=text:raise Conflict('resposta já fornecida; usar nova demanda para outra informação')
            if execute and current['status'] in ('queued','blocked'):return self.run(ident)
            return {'status':current['status'],'execution_id':ident,'demand':current,'steps':snapshot['steps']}
        with self.q.connect() as c:links=[r[0] for r in c.execute('SELECT record_id FROM question_links WHERE execution_id=?',(ident,))]
        records,_,_=self.k.catalog();question_id=next((i for i in reversed(links) if records[i]['payload']['question_text']==current['question']),None)
        source=self.sources.apply(sha(canon([ident,question_id,'answer',text]).encode()),'create',title='Resposta a esclarecimento',text=text)
        ref={'record_id':source['id'],'revision':source['revision']}
        with self.q.connect() as c:c.execute('INSERT OR REPLACE INTO owned_sources VALUES(?,?,?)',(source['id'],source['revision'],ident))
        self.q.answer(ident,text,ref)
        # Retomar implica recuperar contexto novo; não repetir gravações confirmadas.
        with self.q.connect() as c:
            c.execute("UPDATE steps SET status='queued',result=NULL WHERE demand_id=? AND capability='retrieve'",(ident,))
        if question_id:
            q=records[question_id];p=copy.deepcopy(q['payload']);p.update(question_status='answered',answer_refs=[ref],resolution_status='partially_resolved')
            self.k.apply(sha(canon([ident,question_id,'answered',text]).encode()),'question',q['title'],p,q['id'],q['revision'])
        return self.run(ident) if execute else {'status':'queued','execution_id':ident}
    def retrieve(self,c):
        self._source(c);query=c['input'].get('query') or c['input'].get('text','')[:500] or 'contexto'
        result=self.retrieval.search(query,limit=8,depth=1)
        # Corpo canônico é lido quando necessário, mantendo o estado operacional limitado.
        result['results']=[{k:v for k,v in r.items() if k!='record'} for r in result['results']]
        return dict(result,status='ok')
    def context_records(self,c):
        self._source(c);retrieved=c['previous'].get('retrieve',{})
        current=self.retrieval.snapshot()
        if retrieved.get('generation') and retrieved['generation']!=current[0]:raise Conflict('contexto mudou; recuperar antes de responder')
        records=current[1]
        return [records[r['id']] for r in retrieved.get('results',[]) if r['id'] in records]
    def _answer_origin(self,c):
        answer=c.get('answer')
        if answer is None:return None
        if not isinstance(answer,dict) or not self.valid_origin(answer.get('origin')):raise Conflict('origem do esclarecimento mudou')
        record=self.sources.read(answer['origin']['record_id'])
        if record['payload']['content']!=answer.get('value'):raise Conflict('texto do esclarecimento divergiu da origem')
        return answer['origin']
    def _mapping(self,c):
        mapping={'$fonte':c['input']['source_ref']}
        answer=self._answer_origin(c)
        if answer:mapping['$resposta']=answer
        return mapping
    def _resume_extractions(self,c,items):
        self._source(c)
        if not self.authorize() or not config(self.sources)['enabled']:raise Invalid('retomada de extrações desabilitada')
        mapping=self._mapping(c);confirmed={};pending=[];unstarted=False
        for position,item in enumerate(items):
            key=sha(canon([c['operation_key'],position]).encode())
            with self.k.connect() as connection:
                operation=connection.execute('SELECT fingerprint,status,result FROM operations WHERE key=?',(key,)).fetchone()
                frozen=connection.execute('SELECT fingerprint,request,review_authorized FROM prepared_requests WHERE key=?',(key,)).fetchone()
            if frozen and frozen[2]!=0:raise Invalid('extração automática não pode retomar operação humana autorizada')
            if not operation:
                # Um pedido apenas congelado ainda não passou necessariamente pela
                # validação do núcleo: não iniciar seu efeito durante a reconciliação.
                unstarted=True;continue
            if unstarted:raise Conflict('diário de extrações não corresponde ao prefixo do lote')
            request={'kind':item['tipo'],'title':item['titulo'],'payload':resolve_extraction(item['payload'],mapping),
                     'id':item.get('record_id'),'expected':item.get('revisao_esperada')}
            serialized=_request_json(request);fingerprint=sha(serialized.encode())
            if operation[0]!=fingerprint or frozen and frozen[0]!=fingerprint:
                raise Conflict('extração existente não corresponde ao mesmo pedido congelado')
            if frozen and frozen[1] is not None and _request_json(json.loads(frozen[1]))!=serialized:
                raise Conflict('conteúdo do pedido congelado divergiu da extração')
            if operation[1]=='proposed':
                if not frozen or frozen[1] is None:raise Conflict('proposta sem pedido congelado verificável; reconciliar manualmente')
                pending.append((position,key))
            elif operation[1]!='confirmed':raise Conflict('estado da extração exige reconciliação manual')
            result=json.loads(operation[2]);revision=1 if request['id'] is None else request['expected']+1
            if (not isinstance(result,dict) or result.get('status')!='confirmed' or not isinstance(result.get('id'),str)
                    or type(result.get('revision')) is not int or result['revision']!=revision
                    or request['id'] is not None and result['id']!=request['id']):
                raise Conflict('identidade ou revisão do resultado não corresponde ao pedido')
            confirmed[position]=result;mapping['$'+str(position)]={'record_id':result['id'],'revision':result['revision']}
        # Não consultar catalog() antes: os bytes de uma proposta podem já ter sido
        # gravados. Somente propostas deste lote, comparadas acima, podem ser retomadas.
        for position,key in pending:
            self._source(c)
            if not self.authorize() or not config(self.sources)['enabled']:raise Invalid('retomada de extrações desabilitada')
            result=self.k._resume(key,review_authorized=False)
            if canon(result)!=canon(confirmed[position]):raise Conflict('replay retornou outra identidade ou revisão')
            confirmed[position]=result
        return confirmed
    def validate_extractions(self,c,items,require_quotes=False,resume=False):
        if not isinstance(items,list) or len(items)>20:raise Invalid('extrações fora do contrato')
        index=int(c['step_id'].split('_')[-1]) if c['step_id'].startswith(('extract_','apply_')) else 0
        text=c['input'].get('chunks',[c['input'].get('text','')])[index];prepared=[]
        for raw in items:
            if not isinstance(raw,dict) or not {'tipo','titulo','payload'}<=raw.keys() or set(raw)-EXTRACTION_FIELDS:
                raise Invalid('campos da extração fora do contrato')
            item=copy.deepcopy(raw);kind=item['tipo'];title=item['titulo'];ident=item.get('record_id')
            if not isinstance(kind,str) or kind not in EXTRACTION_TYPES:
                raise Invalid('família de extração não permitida')
            if not isinstance(title,str) or not title.strip() or len(title)>120 or any(x in title for x in '[]|#'):
                raise Invalid('título da extração inválido')
            if not isinstance(item['payload'],dict):raise Invalid('payload da extração inválido')
            if ident is not None and (not isinstance(ident,str) or not ident):raise Invalid('identidade da extração inválida')
            if ident is not None and (type(item.get('revisao_esperada')) is not int or item['revisao_esperada']<1):
                raise Conflict('extração exige a revisão atual explícita')
            if ident is None and item.get('revisao_esperada') is not None:raise Invalid('revisão esperada exige identidade existente')
            if require_quotes or 'evidence_quote' in item:
                quote=item.get('evidence_quote');which=item.get('evidence_source','original')
                if which not in ('original','clarification'):raise Invalid('natureza da evidência da extração inválida')
                evidence_text=text
                if which=='clarification':
                    if not self._answer_origin(c):raise Invalid('extração exige esclarecimento com origem própria')
                    evidence_text=c['answer']['value']
                if not isinstance(quote,str) or not quote or quote not in evidence_text:
                    raise Invalid('extração sem trecho literal da origem selecionada')
            if kind=='assertion' and item.get('evidence_quote'):
                reference='$resposta' if item.get('evidence_source')=='clarification' else '$fonte'
                item['payload']['attribution_evidence']={'source_ref':{'record_id':reference,'revision':1},'quote':item['evidence_quote']}
            prepared.append(item)
        confirmed=self._resume_extractions(c,prepared) if resume else {}
        current=self.k.catalog()[0];preview=copy.deepcopy(current);mapping=self._mapping(c)
        from atribuicao import validate_assertion,owner_id,AttributionError
        for position,item in enumerate(prepared):
            kind=item['tipo'];ident=item.get('record_id')
            if ident is not None and ident not in current:raise Invalid('atualização exige identidade conhecida')
            if position in confirmed:
                result=confirmed[position];mapping['$'+str(position)]={'record_id':result['id'],'revision':result['revision']}
                continue
            old=preview.get(ident) if ident else None
            if old:
                if old['record_type']!=kind:raise Invalid('família não pode mudar na extração')
                if item['revisao_esperada']!=old['revision']:raise Conflict('extração exige a revisão atual explícita')
            item['payload']=automatic_payload(kind,item['payload'],old)
            if kind=='assertion' and item.get('evidence_quote'):
                reference='$resposta' if item.get('evidence_source')=='clarification' else '$fonte'
                item['payload']['attribution_evidence']={'source_ref':{'record_id':reference,'revision':1},'quote':item['evidence_quote']}
            payload=resolve_extraction(item['payload'],mapping)
            if payload.get('attribution_resolution_ref') and payload['attribution_resolution_ref']!=self._answer_origin(c):
                raise Invalid('resolução da extração exige a resposta desta demanda')
            self.k._validate(kind,payload,preview,ident)
            if kind=='assertion' and item.get('evidence_quote'):
                attribution=validate_assertion(payload,preview,owner_id(self.sources.root,preview))
                if attribution['status']=='unresolved':raise AttributionError('sujeito não explicitado no trecho',ambiguous=True)
            preview_id=ident or 'extraction-preview-'+str(position)
            revision=old['revision']+1 if old else 1
            preview[preview_id]={'id':preview_id,'record_type':kind,'revision':revision,'title':item['titulo'],'payload':payload}
            mapping['$'+str(position)]={'record_id':preview_id,'revision':revision}
        return prepared,confirmed
    def extract(self,c):
        self._source(c)
        if 'extractions' in c['input']:
            items,_=self.validate_extractions(c,c['input']['extractions'])
            return {'status':'ok','extractions':items}
        index=int(c['step_id'].split('_')[-1]) if '_' in c['step_id'] else 0
        text=c['input'].get('chunks',[c['input'].get('text','')])[index]
        known=self.k.catalog()[0]
        identities=[{'id':r['id'],'revision':r['revision'],'payload':r['payload']} for r in known.values() if r['record_type']=='entity'][:20]
        from conhecimento import PREDICATES
        contract={'allowed_record_types':sorted(EXTRACTION_TYPES),'allowed_predicates':sorted(PREDICATES),
            'reference':{'record_id':'ID conhecido ou $fonte/$0','revision':1},
            'assertion_example':{'subject_ref':{'record_id':'ID da entidade conhecida','revision':1},
                'predicate':'reports_preference','value':{'type':'text','content':'preferência relatada'},
                'nature':'user_report','asserted_by':'autor do relato','recorded_time':c['input'].get('received_at'),
                'source_refs':[{'record_id':'$fonte','revision':1}],
                'context_description':'Contexto desconhecido, quando não informado','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}}
        prompt=(self.manual['manual-cerebro-07-experiencias-e-entrevista.md']+'\n'+self.manual['manual-cerebro-08-catalogo-de-dados.md']+
            '\nExtraia apenas registros sustentados pelo trecho. Retorne {"extractions":[{"tipo":"entity|assertion|synthesis|question",'
            '"titulo":"...","payload":{...},"evidence_quote":"trecho literal"}]}. Reutilize identidades conhecidas quando inequívocas. '
            'Use $fonte, revisão 1, para a origem; $0 etc. para extrações anteriores do mesmo lote. '
            'Uma citação sobre outra pessoa não sustenta o sujeito da afirmação. Separe pessoas e frases. '
            'Se só um esclarecimento do usuário resolver a identidade, retorne decision=ask, question e evidence_quote literal. '
            'A resposta do usuário aparece em clarification, com origem distinta $resposta. Use evidence_source=clarification '
            'somente para citar literalmente essa resposta; mantenha-a em source_refs. Para resolver um pronome no relato '
            'original, mantenha a citação original e inclua attribution_resolution_ref=$resposta também em source_refs. '
            'Não marque confirmação ou contestação do usuário, não crie nem altere review_events ou autoria de controle. '
            'Ao atualizar, preserve asserted_by, nature e recorded_time e informe record_id e revisao_esperada atuais. '
            'Em author_refs, altere somente revision para a revisão atual, mantendo identidade, fragmento, demais campos e ordem. '
            'Não invente datas narradas. Para recorded_time/as_of de registros novos use o instante fornecido. '
            'O contrato executável abaixo é obrigatório: não invente predicados; use value.content, não value.value; '
            'toda referência precisa de record_id E revision. asserted_by é texto. context_description e valid_time '
            'precisam existir, mesmo desconhecidos. field_states não substitui esses campos nesta versão. '
            'Use as revisões atuais mostradas nas entidades conhecidas.\nCONTRATO_EXECUTAVEL: '+canon(contract)+'\n'
            'Se não houver extração segura, use lista vazia.\n'+self.packet({'text':text,'known_entities':identities,
                'recorded_at':c['input'].get('received_at'),'source_ref':c['input'].get('source_ref'),
                'clarification':c.get('answer'),'owner_person_id':self.cfg.get('owner_person_id')}))
        self._answer_origin(c)
        from atribuicao import AttributionError
        repair=None
        for attempt in range(2):
            result=self.model(c).call(prompt if repair is None else prompt+'\nCORRECAO_DE_FORMATO: '+canon(repair))
            self._source(c);current=self.k.catalog()[0]
            if any(i['id'] not in current or current[i['id']]['revision']!=i['revision'] for i in identities):
                raise Conflict('identidade mudou durante a extração; revisar o contexto')
            try:
                if not isinstance(result,dict):raise Invalid('saída de extração inválida')
                if result.get('decision')=='ask':
                    quote=result.get('evidence_quote');question=result.get('question')
                    if not isinstance(question,str) or not question.strip() or len(question)>500 or not isinstance(quote,str) or not quote or quote not in text:
                        raise Invalid('esclarecimento de identidade sem trecho literal e pergunta delimitada')
                    raise NeedAnswer(question)
                if repair and repair.get('error_kind')=='identity_attribution' and result.get('extractions')==[]:
                    raise AttributionError('proposta rejeitada sem extração corrigida')
                items,_=self.validate_extractions(c,result.get('extractions'),require_quotes=True)
                return {'status':'ok','extractions':items,'format_attempts':attempt+1}
            except (Invalid,Conflict,KeyError,TypeError,ValueError) as error:
                if attempt:
                    if isinstance(error,AttributionError) and error.ambiguous:
                        raise NeedAnswer('A quem você se refere neste trecho: '+text[:250]+'?')
                    raise
                repair={'invalid_proposal':result,'validation_error':str(error),
                        'error_kind':'identity_attribution' if isinstance(error,AttributionError) else 'format',
                        'instruction':'Corrija formato e atribuição ao sujeito conservando somente conteúdo sustentado; se a identidade continuar ambígua, peça esclarecimento.'}
    def apply_contribution(self,c):
        self._source(c);index=c['step_id'].split('_')[-1] if c['step_id'].startswith('apply_') else None
        extracted=c['previous'].get('extract_'+str(index),{}) if index is not None else {}
        items,confirmed=self.validate_extractions(c,extracted.get('extractions',c['input'].get('extractions',[])),resume=True)
        mapping=self._mapping(c);results=[]
        for n,item in enumerate(items):
            try:
                if n in confirmed:record=confirmed[n]
                else:
                    payload=resolve_extraction(item['payload'],mapping)
                    record=self.k.apply(sha(canon([c['operation_key'],n]).encode()),item['tipo'],item['titulo'],payload,
                        ident=item.get('record_id'),expected=item.get('revisao_esperada'))
                mapping['$'+str(n)]={'record_id':record['id'],'revision':record['revision']};results.append(record)
            except Exception as failure:
                failure.partial_result={'status':'partial','source':c['input']['source_ref'],'completed':results,
                                        'pending_from':n,'reason':str(failure)}
                raise
        return {'status':'confirmed','source':c['input']['source_ref'],'completed':results}
    def assess(self,c):
        records=self.context_records(c)
        prompt=('Determine se é possível responder com estes registros. Retorne '
            '{"decision":"answer|ask|insufficient","answer":"...","citations":[{"record_id":"...","revision":1,"quote":"trecho literal"}],'
            '"question":"pergunta essencial, se depender do usuário"}. Admita conflitos e ausência de dados. '
            'Uma hipótese não é diagnóstico. Para fontes cujo payload.content é JSON estruturado, '
            'pode acrescentar claims opcionais [{"id":"c1","kind":"field|sum|chain",'
            '"refs":[{"record_id":"id da fonte","revision":1,"path":"/campo no JSON da fonte"}],"value":"valor alegado"}]. '
            'field confere um valor explícito, sum soma operandos inteiros e chain encadeia arestas de requires/precedes. '
            'Preserve a resposta natural em answer. Não invente campos estruturados para relatos de texto livre. '
            'Se faltar evidência externa, inclua research_terms com até três chaves genéricas da lista permitida; nunca envie biografia. Lista: '+','.join(sorted(TERMS))+'.\n'+self.packet({'question':c['input'].get('query'), 'records':records,'clarification':c.get('answer'),'owner_person_id':self.cfg.get('owner_person_id')}))
        from atribuicao import check_answer,owner_id
        repair=None;identity=None
        for attempt in range(2):
            try:result=self.model(c).call(prompt if repair is None else prompt+'\nCORRECAO_DE_ATRIBUICAO: '+canon(repair))
            except Invalid as failure:
                if repair is not None and str(failure)=='orçamento do modelo esgotado':break
                raise
            self.context_records(c)
            if not isinstance(result,dict):raise Invalid('resposta de suficiência inválida')
            if result.get('decision')=='ask':raise NeedAnswer(result.get('question','Qual informação está faltando?'))
            if result.get('decision') not in ('answer','insufficient'):raise Invalid('decisão de suficiência inválida')
            if result['decision']=='answer' and not result.get('citations'):raise Invalid('resposta factual sem origem')
            validate_citations(self.sources,result.get('citations',[]))
            all_records=self.k.catalog()[0]
            identity=check_answer(result.get('answer',''),result.get('citations',[]),all_records,owner_id(self.sources.root,all_records))
            if identity['status']!='rejected':return dict(result,status='ok',identity_check=identity,identity_attempts=attempt+1)
            repair={'rejected_answer':result,'identity_check':identity,
                    'instruction':'Separe as pessoas e corrija a atribuição com as evidências existentes. Não invente fatos nem peça ao usuário que corrija um erro técnico seu. Se as fontes não bastarem, declare insuficiência.'}
        return {'status':'ok','decision':'insufficient','answer':'A resposta proposta confundiu a atribuição de informações entre pessoas e precisa ser revista.',
                'citations':[],'identity_check':identity,'identity_attempts':2}
    def respond(self,c):
        if c['input']['kind'] in ('contribution','outcome'):
            return {'status':'completed','answer':'Contribuição registrada com origem e extrações validadas.',
                    'source_ref':c['input'].get('source_ref')}
        if 'assess_context' in c['previous'] and c['previous']['assess_context']['decision']=='insufficient' and c['previous'].get('evaluate_evidence',{}).get('source_refs'):
            return dict(c['previous']['evaluate_evidence'],status='completed',quality='limited')
        if 'assess_context' in c['previous']:
            self.context_records(c);result=c['previous']['assess_context'];validate_citations(self.sources,result.get('citations',[]))
            response={'status':'completed','answer':result.get('answer','Não há base suficiente.'),'citations':result.get('citations',[]),
                    'quality':'limited' if result['decision']=='insufficient' else 'provisional'}
            from atribuicao import check_answer,owner_id
            records=self.k.catalog()[0]
            identity=check_answer(response['answer'],response['citations'],records,owner_id(self.sources.root,records))
            response['identity_check']=identity
            if identity['status']=='rejected':
                response.update(answer='A atribuição das informações a pessoas precisa de revisão antes de responder.',quality='limited')
                return response
            if 'claims' in result:
                from evidencias import inspect_response
                retrieved=c['previous']['retrieve']
                draft={name:result[name] for name in ('answer','citations','claims','answer_format') if name in result}
                checked=inspect_response(self.sources,c['operation_key'],draft,
                    context_ids=[r['id'] for r in retrieved.get('results',[])],max_context=8,
                    expected_generation=retrieved.get('generation'),scope=self.retrieval.scope)
                response['assurance']=checked
                if checked['status'] in ('rejected','stale'):
                    response['answer']='A verificação das alegações encontrou uma lacuna ou divergência nas evidências. A conclusão precisa de revisão.'
                    response['quality']='limited'
                elif checked['status']=='limited':
                    response['quality']='limited'
                elif checked.get('answer_verified'):
                    response['quality']='verified_as_recorded'
                self.context_records(c)
            return response
        if 'evaluate_evidence' in c['previous']:return dict(c['previous']['evaluate_evidence'],status='completed',quality=c['previous']['evaluate_evidence']['status'])
        return {'status':'completed','answer':'Etapas executadas; consulte os resultados e limitações.',
                'quality':'limited' if any(v.get('status')=='limited' for v in c['previous'].values()) else 'provisional',
                'results':c['previous']}
    def correct(self,c):
        p=c['input'];result=self.sources.apply(c['operation_key'],'correct',ident=p['record_id'],expected=p['expected_revision'],
            text=p['text'],reason=p['reason'])
        return dict(result,status='confirmed')
    def affected(self,c):return dict(self.k.audit(),status='ok')
    def revalidate(self,c):return review(self.sources,c['operation_key'],self.model(c))
    def research(self,c):
        args={'transport':self.transport} if self.transport else {}
        terms=c['input'].get('research_terms')
        if c['input']['kind']=='question':
            decision=c['previous']['assess_context']
            if decision['decision']!='insufficient':
                return {'status':'ok','skipped':True,'documents':[],'source_refs':[],'limitations':[]}
            terms=terms or decision.get('research_terms')
            if not terms:return {'status':'limited','skipped':True,'documents':[],'source_refs':[],'limitations':['Nenhum tema externo autorizado foi identificado.']}
        result=research(self.sources,c['operation_key'],terms,limit=3,**args)
        return dict(result,status='limited')
    def evidence(self,c):
        data=c['previous']['research_external']
        if data.get('skipped'):return dict(data,answer='Etapa externa dispensada ou sem tema autorizado.')
        if not data['documents']:return {'status':'limited','answer':'A busca delimitada não encontrou documentos utilizáveis.','citations':[],'limitations':data['limitations']}
        result=self.model(c).call('Avalie estes metadados e resumos, sem fingir acesso ao texto integral. '
            'Retorne {"answer":"síntese com limites","studies":[{"doi":"...","design":"unknown se não declarado",'
            '"sample_size":null,"population":"unknown se ausente","supporting_quote":"trecho literal do resumo ou vazio","limitations":[]}],"limitations":[]}. '
            'Não complete tamanho de amostra, método ou resultados por adivinhação. Não trate estudos como fatos pessoais.\n'+canon(data))
        allowed={d['doi'] for d in data['documents']}
        studies=result.get('studies',[])
        if not isinstance(studies,list) or {s.get('doi') for s in studies}!=allowed or len(studies)!=len(allowed):raise Invalid('cobertura dos estudos não corresponde aos documentos recuperados')
        for study in studies:
            doc=next(d for d in data['documents'] if d['doi']==study['doi'])
            quote=study.get('supporting_quote','')
            if quote and quote not in doc['abstract']:raise Invalid('trecho científico não foi encontrado no resumo')
            claims=study.get('sample_size') is not None or study.get('design','unknown')!='unknown' or study.get('population','unknown')!='unknown'
            if claims and not quote:raise Invalid('resultado científico sem trecho de apoio')
            if study.get('sample_size') is not None:
                number=study['sample_size']
                if type(number)is not int or number<1 or str(number) not in quote.replace(',','').replace('.',''):raise Invalid('tamanho da amostra não está sustentado pelo trecho')
        result['limitations']=data['limitations']+result.get('limitations',[])
        return dict(result,status='limited',source_refs=data['source_refs'])
    def inspect_capabilities(self,c):return {'status':'ok','capabilities':sorted(self.q.capabilities)}
    def propose(self,c):
        # Ajustes da produção ficam restritos a configurações com avaliador registrado.
        proposal=c['input'].get('candidate')
        if proposal is None:proposal={'kind':'message_codec','value':'compact','reason':'Comparar transporte JSON sem descartar campos.'}
        if not isinstance(proposal,dict):raise Invalid('candidata técnica inválida')
        return {'status':'ok','candidate':proposal}
    def evaluate(self,c):
        from melhorias import evaluate
        return evaluate(self.sources,c['operation_key'],c['previous']['propose_candidate']['candidate'])
    def record_candidate(self,c):
        from melhorias import record
        return record(self.sources,c['operation_key'],c['previous']['evaluate_candidate'])
