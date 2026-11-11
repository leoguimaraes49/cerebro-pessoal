"""Ajustes delimitados com avaliação determinística e intenções retomáveis."""
import copy,json,os,re,stat
from pathlib import Path
from contextlib import contextmanager
from nucleo import Invalid,Conflict,NOW,sha,canon
from conhecimento import Knowledge
from autonomia import atomic_json


KEY_PATTERN=r'[A-Za-z0-9_-]{1,80}'
PHASES=('adopt_intent','adopt_config','adopt_candidate','adopted',
        'rollback_intent','rollback_config','rollback_candidate','rolled_back')


def _validate_key(key):
    if not isinstance(key,str) or not re.fullmatch(KEY_PATTERN,key):raise Invalid('chave de operação inválida')


def _safe_path(sources,*parts,create_parent=False):
    root=Path(sources.root).absolute()
    if not root.is_dir():raise Invalid('raiz de estado inexistente')
    paths=[root];path=root
    for part in parts:
        if not isinstance(part,str) or part in ('','.','..') or '/' in part or '\\' in part or Path(part).anchor:
            raise Invalid('caminho de estado inválido')
        path=path/part;paths.append(path)
    def check():
        for item in paths:
            try:
                info=item.lstat()
            except FileNotFoundError:info=None
            if item.is_symlink() or getattr(item,'is_junction',lambda:False)() or (info and getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400)):
                raise Invalid('caminho de estado redirecionado')
            try:resolved=item.resolve()
            except (OSError,RuntimeError) as error:raise Invalid('caminho de estado não resolvido') from error
            if resolved!=item or not resolved.is_relative_to(root):raise Invalid('caminho fora da raiz de estado')
    check()
    if create_parent:
        path.parent.mkdir(parents=True,exist_ok=True);check()
    return path


@contextmanager
def _state_lock(sources,namespace='adocoes'):
    _validate_key(namespace)
    path=_safe_path(sources,'estado',namespace+'.lock',create_parent=True)
    flags=os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0)
    with os.fdopen(os.open(path,flags,0o600),'r+b') as stream:
        _safe_path(sources,'estado',namespace+'.lock')
        opened=os.fstat(stream.fileno());named=path.stat()
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(named.st_dev,named.st_ino):
            raise Invalid('arquivo de bloqueio mudou')
        if not opened.st_size:stream.write(b'\0');stream.flush()
        if os.name=='nt':
            import msvcrt
            def acquire():
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            def unlock():
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            def acquire():fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            def unlock():fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        try:acquire()
        except OSError as error:raise Conflict('outra operação de estado está em andamento') from error
        try:yield
        finally:unlock()


def _read_json(path):
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise Invalid('estado JSON inválido')
    return value


def _same(left,right):return canon(left)==canon(right)


def _validated_config(raw):
    # config() só recebe um arquivo; validar a proposta em memória evita gravá-la para testá-la.
    from execucao import DEFAULT
    if not isinstance(raw,dict) or set(raw)-set(DEFAULT):raise Invalid('opção de execução não reconhecida')
    try:json.dumps(raw,allow_nan=False)
    except (TypeError,ValueError) as error:raise Invalid('configuração não JSON') from error
    cfg=copy.deepcopy(DEFAULT);cfg.update(raw)
    for name,low,high in (('max_actions',1,64),('max_model_calls',0,16),('max_seconds',1,3600)):
        if type(cfg[name]) is not int or not low<=cfg[name]<=high:raise Invalid('limite de execução inválido: '+name)
    for name in ('enabled','auto_process_sources','auto_adopt_config'):
        if type(cfg[name]) is not bool:raise Invalid('permissão de execução inválida: '+name)
    for name in ('model','embeddings'):
        if not isinstance(cfg[name],dict) or type(cfg[name].get('enabled',False)) is not bool:
            raise Invalid('configuração de provedor inválida: '+name)
    if cfg['message_codec'] not in ('compact','pretty') or cfg['retrieval_policy'] not in ('hybrid','lexical'):
        raise Invalid('política de comunicação ou recuperação desconhecida')
    return cfg


def _read_config(sources,allow_missing=False):
    path=_safe_path(sources,'execucao.json')
    raw={} if allow_missing and not path.exists() else _read_json(path)
    _validated_config(raw)
    return raw


def _measure(candidate,current):
    if not isinstance(candidate,dict):raise Invalid('candidata inválida')
    candidate=copy.deepcopy(candidate)
    try:json.dumps(candidate,allow_nan=False)
    except (TypeError,ValueError) as error:raise Invalid('candidata não JSON') from error
    if candidate.get('kind')!='message_codec' or candidate.get('value') not in ('compact','pretty'):
        return {'status':'limited','candidate':candidate,'eligible':False,
                'reason':'Mudança exige um avaliador específico antes da adoção.'}
    fixture={'version':1,'records':[{'text':'  Texto completo, com exceção e dúvida.\nNão é zero.','unknown':None,
            'revision':2,'origin_refs':[{'record_id':'ficticio','revision':1}]}]}
    encodings={'pretty':json.dumps(fixture,ensure_ascii=False,indent=2),'compact':canon(fixture)}
    previous=_validated_config(current)['message_codec'];selected=candidate['value']
    intact=json.loads(encodings[selected])==fixture
    return {'status':'completed','candidate':candidate,'eligible':intact and len(encodings[selected])<len(encodings[previous]),
        'checks':{'roundtrip_equal':intact,'original_text_preserved':json.loads(encodings[selected])['records'][0]['text']==fixture['records'][0]['text']},
        'comparison':{'previous':previous,'selected':selected,'previous_chars':len(encodings[previous]),'selected_chars':len(encodings[selected])},
        'scope':'JSON completo; não é prova de equivalência universal entre respostas de modelos.',
        'previous_config_hash':sha(canon(current).encode())}


def _verify_evaluation(evaluation,current):
    if not isinstance(evaluation,dict):raise Invalid('avaliação inválida')
    expected=_measure(evaluation.get('candidate'),current)
    supplied=copy.deepcopy(evaluation);supplied.pop('evaluated_at',None)
    if expected['status']=='completed' and supplied.get('previous_config_hash')!=expected['previous_config_hash']:
        raise Conflict('configuração mudou após a comparação')
    if canon(supplied)!=canon(expected):raise Invalid('avaliação não corresponde ao cálculo determinístico')
    return expected


def evaluate(sources,key,candidate):
    _validate_key(key)
    with _state_lock(sources):
        path=_safe_path(sources,'estado','melhorias',key+'.json',create_parent=True)
        current=_read_config(sources,allow_missing=True);result=_measure(candidate,current)
        if path.exists():
            previous=_read_json(path);verified=_verify_evaluation(previous,current)
            if not _same(verified,result):raise Conflict('chave de avaliação reutilizada para outra candidata')
            return previous
        if result['status']=='completed':
            result['evaluated_at']=NOW();atomic_json(path,result)
        return result


def record(sources,key,evaluation):
    _validate_key(key)
    with _state_lock(sources):
        verified=_verify_evaluation(evaluation,_read_config(sources,allow_missing=True));k=Knowledge(sources)
        text='Resultado técnico de comparação de candidata: '+canon(evaluation)
        source=sources.apply(sha((key+'source').encode()),'create',title='Comparação de melhoria',text=text,
            source_metadata={'source_kind':'tool_output','origin_description':'Avaliador determinístico do serviço',
                             'limitations':['Resultado técnico; não é nova experiência do usuário.']})
        ref={'record_id':source['id'],'revision':source['revision']}
        payload={'purpose':'Avaliar ajuste sem perda do conteúdo','problem':evaluation.get('candidate',{}).get('reason','Oportunidade técnica'),
                 'basis_refs':[ref],'acceptance_criteria':['preservar o pacote completo','melhorar custo medido','manter contratos'],
                 'comparison':copy.deepcopy(evaluation),'comparison_refs':[ref],
                 'adoption_status':'tested' if verified['eligible'] else ('candidate' if verified['status']=='limited' else 'rejected'),
                 'rollback_plan':'Restaurar configuração anterior registrada.'}
        result=k.apply(sha((key+'candidate').encode()),'improvement_candidate','Candidata de melhoria',payload)
        return {'status':'confirmed','candidate_record':result,'evaluation':evaluation}


def _candidate(k,ident):
    read=k.read(ident)
    if read['validity']!='current_within_scope':raise Conflict('candidata precisa de revisão')
    record=read['record']
    if record['record_type']!='improvement_candidate' or type(record['revision']) is not int or record['revision']<1:
        raise Invalid('registro não é candidata de melhoria')
    return {name:copy.deepcopy(record[name]) for name in ('id','revision','record_type','title','payload')}


def _next_candidate(snapshot,status):
    result=copy.deepcopy(snapshot);result['revision']+=1;result['payload']['adoption_status']=status
    return result


def _require_candidate(k,expected):
    if canon(_candidate(k,expected['id']))!=canon(expected):raise Conflict('candidata mudou durante a operação')


def _apply_candidate(k,key,snapshot,status):
    expected=_next_candidate(snapshot,status)
    result=k.apply(sha((key+('adopt' if status=='adopted' else 'rollback')).encode()),'improvement_candidate',
        snapshot['title'],expected['payload'],snapshot['id'],snapshot['revision'])
    if result['id']!=expected['id'] or result['revision']!=expected['revision']:raise Conflict('resultado da candidata divergente')
    _require_candidate(k,expected)


def _intent(state):
    return {name:state[name] for name in ('version','candidate_id','before','after','previous_revision','candidate_before')}


def _check_journal(state):
    try:
        if state['version']!=2 or state['intent_hash']!=sha(canon(_intent(state)).encode()):raise Invalid('intenção de adoção divergente')
        snapshot=state['candidate_before'];payload=snapshot['payload']
        if snapshot['id']!=state['candidate_id'] or snapshot['record_type']!='improvement_candidate' or type(snapshot['revision']) is not int or snapshot['revision']<1 or type(state['previous_revision']) is not int or snapshot['revision']!=state['previous_revision'] or payload['adoption_status']!='tested':
            raise Invalid('base da candidata divergente')
        proof=_verify_evaluation(payload['comparison'],state['before'])
        if not proof['eligible']:raise Invalid('candidata não melhora o custo medido')
        following=copy.deepcopy(state['before']);following['message_codec']=proof['candidate']['value']
        _validated_config(state['before']);_validated_config(following)
        if canon(following)!=canon(state['after']):raise Invalid('intenção altera configuração fora do escopo')
        allowed={'proposed':PHASES[:3],'adopted':('adopted',),'rollback_proposed':PHASES[4:7],'rolled_back':('rolled_back',)}
        if state['phase'] not in allowed.get(state['status'],()):raise Invalid('fase de adoção inválida')
        if state['status'] in ('rollback_proposed','rolled_back'):
            intent=state['rollback_intent'];base=intent['candidate_before']
            original=canon(base)==canon(snapshot);adopted=canon(base)==canon(_next_candidate(snapshot,'adopted'))
            if not (original or adopted) or canon(intent['config_from'])!=canon(state['before'] if original else state['after']) or state['rollback_hash']!=sha(canon(intent).encode()):
                raise Invalid('intenção de reversão divergente')
    except (KeyError,TypeError) as error:raise Invalid('journal de adoção incompleto') from error


def _available(sources,key):
    path=_safe_path(sources,'estado','adocoes-intent.json')
    if not path.exists():return None
    owner=_read_json(path);_validate_key(owner.get('key'))
    if owner['key']==key:return owner
    other=_safe_path(sources,'estado','adocoes',owner['key']+'.json')
    if not other.is_file():raise Conflict('intenção de outra adoção exige conciliação')
    state=_read_json(other);_check_journal(state)
    if owner.get('intent_hash')!=state['intent_hash'] or state['status'] not in ('adopted','rolled_back'):
        raise Conflict('outra adoção ou reversão ainda não foi concluída')
    return owner


def _claim(sources,key,state):
    owner=_available(sources,key)
    desired={'key':key,'intent_hash':state['intent_hash']}
    if owner and owner['key']==key:
        if owner!=desired:raise Conflict('intenção ativa divergente')
    else:atomic_json(_safe_path(sources,'estado','adocoes-intent.json',create_parent=True),desired)


def _release(sources,key,state):
    path=_safe_path(sources,'estado','adocoes-intent.json')
    if path.exists():
        if _read_json(path)!={'key':key,'intent_hash':state['intent_hash']}:raise Conflict('intenção ativa mudou')
        path.unlink()


def _advance(path,state,phase):
    if PHASES.index(state['phase'])>=PHASES.index(phase):return
    state['phase']=phase
    if phase=='adopted':state.update(status='adopted',adopted_at=NOW())
    elif phase=='rolled_back':state.update(status='rolled_back',rolled_back_at=NOW())
    atomic_json(path,state)


def _write_config(sources,expected,following):
    _validated_config(following)
    if canon(_read_config(sources))!=canon(expected):raise Conflict('configuração concorrente não foi sobrescrita')
    atomic_json(_safe_path(sources,'execucao.json'),following)
    if canon(_read_config(sources))!=canon(following):raise Conflict('configuração mudou durante a escrita')


def _load_journal(sources,path,k):
    state=_read_json(path)
    if 'version' not in state:
        # O legado não guardava o payload da intenção. Só reconstruir quando o estado atual o comprova.
        if state.get('status') not in ('proposed','adopted','rolled_back'):raise Conflict('journal legado exige conciliação manual')
        try:
            snapshot=_candidate(k,state['candidate_id']);revision=state['previous_revision'];current=_read_config(sources)
            if snapshot['revision']==revision and snapshot['payload']['adoption_status']=='tested' and state['status']=='proposed':pass
            elif snapshot['revision']==revision+1 and snapshot['payload']['adoption_status']=='adopted' and state['status'] in ('proposed','adopted'):
                snapshot['revision']=revision;snapshot['payload']['adoption_status']='tested'
            elif snapshot['revision']==revision+2 and snapshot['payload']['adoption_status']=='rolled_back' and state['status']=='rolled_back':
                snapshot['revision']=revision;snapshot['payload']['adoption_status']='tested'
            else:raise Conflict('candidata legada não permite reconstruir a intenção')
            if not any(_same(current,value) for value in (state['before'],state['after'])) or state['status']=='adopted' and not _same(current,state['after']) or state['status']=='rolled_back' and not _same(current,state['before']):
                raise Conflict('configuração legada exige conciliação manual')
            state.update(version=2,candidate_before=snapshot,phase='adopt_intent' if state['status']=='proposed' else state['status'])
            if state['status']=='rolled_back':
                state['rollback_intent']={'candidate_before':_next_candidate(snapshot,'adopted'),'config_from':copy.deepcopy(state['after'])}
                state['rollback_hash']=sha(canon(state['rollback_intent']).encode())
            state['intent_hash']=sha(canon(_intent(state)).encode());_check_journal(state);atomic_json(path,state)
        except (KeyError,TypeError) as error:raise Invalid('journal legado incompleto') from error
    _check_journal(state)
    return state


def _resume_adoption(sources,key,path,state,k):
    if state['status'] not in ('proposed','adopted'):raise Conflict('adoção já entrou em reversão; usar nova demanda')
    current=_read_config(sources)
    if not _validated_config(current)['auto_adopt_config']:raise Invalid('adoção de configuração não habilitada')
    if not any(_same(current,value) for value in (state['before'],state['after'])):raise Conflict('configuração concorrente não foi sobrescrita')
    _claim(sources,key,state)
    if state['status']=='adopted':
        if not _same(current,state['after']):raise Conflict('configuração mudou após adoção')
        _require_candidate(k,_next_candidate(state['candidate_before'],'adopted'));_release(sources,key,state)
        return state
    if _same(current,state['before']):
        _require_candidate(k,state['candidate_before']);_write_config(sources,current,state['after'])
    _advance(path,state,'adopt_config')
    # Repetir o pedido congelado também reconcilia Knowledge.apply() interrompido antes da confirmação.
    _apply_candidate(k,key,state['candidate_before'],'adopted')
    _advance(path,state,'adopt_candidate');_advance(path,state,'adopted');_release(sources,key,state)
    return state


def adopt(sources,key,candidate_id):
    _validate_key(key)
    with _state_lock(sources):
        _available(sources,key)
        path=_safe_path(sources,'estado','adocoes',key+'.json',create_parent=True);k=Knowledge(sources)
        if path.exists():
            state=_load_journal(sources,path,k)
            if state['candidate_id']!=candidate_id:raise Conflict('chave de adoção reutilizada')
        else:
            previous=_read_config(sources)
            if not _validated_config(previous)['auto_adopt_config']:raise Invalid('adoção de configuração não habilitada')
            snapshot=_candidate(k,candidate_id);payload=snapshot['payload']
            if payload.get('adoption_status')!='tested':raise Invalid('candidata não testada')
            proof=_verify_evaluation(payload.get('comparison'),previous)
            if not proof['eligible'] or proof['candidate']['kind']!='message_codec':raise Invalid('candidata não elegível')
            following=copy.deepcopy(previous);following['message_codec']=proof['candidate']['value'];_validated_config(following)
            state={'version':2,'status':'proposed','phase':'adopt_intent','candidate_id':candidate_id,
                   'before':previous,'after':following,'previous_revision':snapshot['revision'],
                   'candidate_before':snapshot,'created_at':NOW()}
            state['intent_hash']=sha(canon(_intent(state)).encode());atomic_json(path,state)
        return _resume_adoption(sources,key,path,state,k)


def rollback(sources,key):
    _validate_key(key)
    with _state_lock(sources):
        _available(sources,key)
        path=_safe_path(sources,'estado','adocoes',key+'.json')
        if not path.is_file():raise Invalid('adoção não encontrada')
        k=Knowledge(sources);state=_load_journal(sources,path,k)
        if state['status']=='rolled_back':
            if not _same(_read_config(sources),state['before']):raise Conflict('configuração mudou após reversão')
            _require_candidate(k,_next_candidate(state['rollback_intent']['candidate_before'],'rolled_back'))
            _claim(sources,key,state);_release(sources,key,state);return state
        if state['status']!='rollback_proposed':
            current=_read_config(sources)
            if state['status']=='proposed' and _same(current,state['before']):
                base=state['candidate_before'];_require_candidate(k,base)
            else:
                if not _same(current,state['after']):raise Conflict('configuração mudou; reversão exige conciliação')
                state=_resume_adoption(sources,key,path,state,k);base=_next_candidate(state['candidate_before'],'adopted')
            state['rollback_intent']={'candidate_before':copy.deepcopy(base),'config_from':current}
            state['rollback_hash']=sha(canon(state['rollback_intent']).encode())
            state.update(status='rollback_proposed',phase='rollback_intent');atomic_json(path,state)
        _check_journal(state);_claim(sources,key,state)
        current=_read_config(sources);intent=state['rollback_intent']
        if not any(_same(current,value) for value in (intent['config_from'],state['before'])):raise Conflict('configuração mudou; reversão exige conciliação')
        if not _same(current,state['before']):
            _require_candidate(k,intent['candidate_before']);_write_config(sources,current,state['before'])
        _advance(path,state,'rollback_config');_apply_candidate(k,key,intent['candidate_before'],'rolled_back')
        _advance(path,state,'rollback_candidate');_advance(path,state,'rolled_back');_release(sources,key,state)
        return state
