"""Cálculo restrito e reproduzível; nenhum escore é diagnóstico."""
import copy
from nucleo import NOW,Invalid,Conflict,sha,canon
from conhecimento import Knowledge
from esquemas import expected_scores


def _resume_score(k,key,assessment_id):
    matches=[]
    for operation,request in k._pending_requests('assessment_score'):
        p=request['payload'];ref=p.get('assessment_ref',{})
        if ref.get('record_id')==assessment_id and operation==sha(canon([key,assessment_id,ref.get('revision'),p.get('response_refs')]).encode()):
            matches.append(operation)
    if len(matches)>1:raise Conflict('há mais de uma pontuação pendente para este pedido; reconciliar')
    return k._resume(matches[0]) if matches else None


def score(sources,key,assessment_id):
    k=Knowledge(sources)
    resumed=_resume_score(k,key,assessment_id)
    if resumed is not None:return resumed
    records,_,_=k.catalog()
    if assessment_id not in records or records[assessment_id]['record_type']!='assessment':raise Invalid('aplicação inexistente')
    if assessment_id in k.stale(records):raise Conflict('aplicação precisa de revisão')
    scores,used,instrument=expected_scores(records[assessment_id],records)
    if any(r['record_id'] in k.stale(records) for r in used):raise Conflict('respostas precisam de revalidação')
    operation=sha(canon([key,assessment_id,records[assessment_id]['revision'],used]).encode())
    resumed=k._resume(operation)
    if resumed is not None:return resumed
    p={'assessment_ref':{'record_id':assessment_id,'revision':records[assessment_id]['revision']},
       'scoring_rule_ref':instrument['payload']['scoring_rule_ref'],'response_refs':used,'dimension_scores':scores,
       'computed_at':NOW(),'limitations':['Cálculo conforme a regra registrada; não é diagnóstico nem probabilidade clínica.'],
       'score_validity_status':'current'}
    existing=[r for r in records.values() if r['record_type']=='assessment_score' and
              r['payload'].get('assessment_ref',{}).get('record_id')==assessment_id]
    if len(existing)>1:raise Conflict('pontuações duplicadas exigem conciliação')
    old=existing[0] if existing else None
    return k._frozen_apply(operation,'assessment_score','Pontuação da avaliação',p,
                   ident=old['id'] if old else None,expected=old['revision'] if old else None)


def finish(sources,key,assessment_id):
    """Conclui a aplicação e atualiza referências técnicas, sem mudar valores de respostas."""
    k=Knowledge(sources)
    # Retomar os bytes/payloads congelados antes de consultar um catálogo bloqueado pelo próprio efeito.
    for operation,request in k._pending_requests('assessment'):
        if request['id']==assessment_id and operation==sha(canon([key,'finish',assessment_id,request['expected']]).encode()):
            k._resume(operation)
    for operation,request in k._pending_requests('assessment_response'):
        ref=request['payload'].get('assessment_ref',{})
        if ref.get('record_id')==assessment_id and operation==sha(canon([key,'link',request['id'],request['expected'],ref.get('revision')]).encode()):
            k._resume(operation)
    resumed=_resume_score(k,key,assessment_id)
    if resumed is not None:return resumed
    records,_,_=k.catalog();application=records.get(assessment_id)
    if not application or application['record_type']!='assessment':raise Invalid('aplicação inexistente')
    p=copy.deepcopy(application['payload']);oldrev=application['revision']
    if p['application_status']!='completed':
        p.update(application_status='completed',ended_at=NOW())
        operation=sha(canon([key,'finish',assessment_id,oldrev]).encode())
        result=k._frozen_apply(operation,'assessment',application['title'],p,assessment_id,oldrev)
        current=result['revision']
    else:current=oldrev
    records,_,_=k.catalog()
    for record in list(records.values()):
        rp=record.get('payload',{})
        if record['record_type']!='assessment_response' or rp.get('assessment_ref',{}).get('record_id')!=assessment_id:continue
        if rp['assessment_ref']['revision']==current:continue
        # A conclusão só altera estado e horário técnico desta mesma aplicação.
        if rp['assessment_ref']['revision']!=current-1:raise Conflict('resposta de aplicação antiga exige revisão explícita')
        from conhecimento import decode
        history=sources.root/'estado'/'conhecimento_revisoes'/assessment_id/(str(current-1)+'.md')
        if not history.is_file():raise Conflict('revisão anterior da aplicação indisponível')
        previous=decode(history.read_bytes())['payload']
        ignored={'application_status','ended_at'}
        if {k:v for k,v in previous.items() if k not in ignored}!={k:v for k,v in records[assessment_id]['payload'].items() if k not in ignored}:
            raise Conflict('condições da aplicação mudaram; respostas precisam de revisão explícita')
        updated=copy.deepcopy(rp);updated['assessment_ref']['revision']=current
        k.apply(sha(canon([key,'link',record['id'],record['revision'],current]).encode()),
                'assessment_response',record['title'],updated,record['id'],record['revision'])
    return score(sources,key,assessment_id)
