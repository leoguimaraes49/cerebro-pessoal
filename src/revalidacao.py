"""Revisão semântica com proposta explícita e controle de bases antes de aplicar."""
import copy
from nucleo import Invalid,Conflict,NOW,sha,canon
from conhecimento import Knowledge,refs
from esquemas import derivation_refs


HUMAN_REVIEW_STATUSES=frozenset(('confirmed_by_user','disputed_by_user'))
CONTROL_FIELDS=('id','record_type','schema_version','revision','created_at','updated_at',
    'created_by','updated_by','reviewed_by','review_authorized','access_policy_ref',
    'lifecycle_status','payload_format','revalidation_note')
ASSERTION_AUTHOR_FIELDS=('asserted_by','nature','recorded_time')


def automatic_payload(kind,payload,old=None):
    """A proposta automática não é uma credencial de autoria ou revisão humana."""
    if not isinstance(payload,dict):raise Invalid('payload automático inválido')
    result=copy.deepcopy(payload);previous=old['payload'] if old else {}
    for name in CONTROL_FIELDS+(ASSERTION_AUTHOR_FIELDS if kind=='assertion' and old else ()):
        if name in result and (name not in previous or canon(result[name])!=canon(previous[name])):
            raise Invalid('saída automática não pode alterar autoria ou controle: '+name)
        if name in previous:result[name]=copy.deepcopy(previous[name])
    if old and ('author_refs' in previous or 'author_refs' in result):
        before=previous.get('author_refs');after=result.get('author_refs',before)
        if not isinstance(before,list) or not isinstance(after,list) or len(before)!=len(after):
            raise Invalid('saída automática não pode alterar autoria ou controle: author_refs')
        for original,updated in zip(before,after):
            if (not isinstance(original,dict) or not isinstance(updated,dict)
                    or type(original.get('revision')) is not int or type(updated.get('revision')) is not int
                    or updated['revision']<1 or updated['revision']<original['revision']
                    or canon({k:v for k,v in original.items() if k!='revision'})!=
                       canon({k:v for k,v in updated.items() if k!='revision'})):
                raise Invalid('saída automática não pode alterar autoria ou controle: author_refs')
        result['author_refs']=copy.deepcopy(after)
    events=previous.get('review_events',[])
    if 'review_events' in result and canon(result['review_events'])!=canon(events):
        raise Invalid('saída automática não pode criar, alterar ou remover eventos de revisão humana')
    if 'review_events' in previous:result['review_events']=copy.deepcopy(events)
    else:result.pop('review_events',None)
    status=result.get('review_status');previous_status=previous.get('review_status')
    if status is not None and status not in ('unreviewed','clarification_needed',*HUMAN_REVIEW_STATUSES):
        raise Invalid('estado de revisão automática inválido')
    if status in HUMAN_REVIEW_STATUSES and status!=previous_status:
        raise Invalid('saída automática não pode confirmar ou contestar em nome do usuário')
    if previous_status in HUMAN_REVIEW_STATUSES:
        # Mudanças de conteúdo ou de evidência exigem nova revisão; eventos antigos
        # continuam descrevendo somente a versão e o alcance examinados pelo usuário.
        ignored={'review_status','review_events','revalidation_note'}
        before={k:v for k,v in previous.items() if k not in ignored}
        after={k:v for k,v in result.items() if k not in ignored}
        result['review_status']=previous_status if canon(before)==canon(after) else 'clarification_needed'
    return result


def _review(sources,key,model,max_records,completed,unresolved):
    k=Knowledge(sources);initial,_,_=k.catalog();stale=k.stale(initial)
    pending=set(stale)
    if len(pending)>max_records:raise Invalid('revisão excede o lote; dividir sob o orçamento da demanda')
    for _ in range(max_records+1):
        records,_,_=k.catalog();current_stale=k.stale(records)
        pending &= current_stale
        if not pending:break
        ready=[ident for ident in sorted(pending) if all(r.get('record_id') not in current_stale
               for r in derivation_refs(records[ident]['payload']) if r.get('record_id') in records)]
        if not ready:
            unresolved.extend({'id':ident,'reason':'dependência sem revisão concluída'} for ident in sorted(pending));break
        for ident in ready:
            old=records[ident];kind=old['record_type']
            if kind not in ('entity','assertion','synthesis','question'):
                unresolved.append({'id':ident,'reason':'tipo exige procedimento específico, como recálculo de avaliação'})
                pending.remove(ident);continue
            bases=[];missing=False
            for ref in refs(old['payload']):
                target=records.get(ref.get('record_id'))
                if target is None:missing=True;break
                bases.append({'id':target['id'],'revision':target['revision'],'record_type':target['record_type'],
                              'title':target['title'],'payload':target['payload']})
            if missing:
                unresolved.append({'id':ident,'reason':'origem excluída ou indisponível'});pending.remove(ident);continue
            snapshot=sha(canon(bases).encode())
            prompt=('Reavalie um registro cuja base foi corrigida. Não atualize apenas os números de revisão. '
                'Compare o conteúdo antigo com as bases atuais. Se faltar suporte, responda {"status":"unresolved","reason":"..."}. '
                'Se houver suporte, retorne {"status":"proposed","payload":{...payload completo revisado...},'
                '"citations":[{"record_id":"...","revision":1,"quote":"trecho literal da base atual"}],"reason":"..."}. '
                'Preserve autoria, hipóteses, limitações e divergências. Não confirme diagnóstico, percentuais clínicos ou confirmação do usuário. '
                'Não crie nem reescreva review_events, asserted_by, nature, recorded_time ou metadados de controle; '
                'eventos de revisão podem ser omitidos da proposta e serão preservados pelo serviço. '
                'Em author_refs, somente revision pode acompanhar a revisão atual; preserve identidades, fragmentos, demais campos e ordem. '
                'Uma entidade pode manter identidade quando o texto atual continuar sustentando-a. '
                'Todas as referências do payload devem usar revisões atuais.\n'+canon({'old_record':old,'current_bases':bases}))
            try:proposal=model.call(prompt)
            except Exception as failure:
                if completed:
                    failure.partial_result={'status':'partial','completed':completed,'unresolved':unresolved+
                         [{'id':i,'reason':'revisão não concluída: '+str(failure)} for i in sorted(pending)]}
                raise
            if not isinstance(proposal,dict) or proposal.get('status')!='proposed':
                unresolved.append({'id':ident,'reason':proposal.get('reason','sem proposta revisável') if isinstance(proposal,dict) else 'saída inválida'})
                pending.remove(ident);continue
            citations=proposal.get('citations',[])
            if not isinstance(citations,list) or not citations:raise Invalid('revisão sem citações atuais')
            for citation in citations:
                if not isinstance(citation,dict) or type(citation.get('revision')) is not int:
                    raise Invalid('citação de revisão inválida')
                base=next((b for b in bases if b['id']==citation.get('record_id')),None)
                quote=citation.get('quote')
                if not base or citation.get('revision')!=base['revision'] or not isinstance(quote,str) or not quote or quote not in canon(base['payload']) and quote not in str(base['payload'].get('content','')):
                    raise Invalid('citação da revisão não corresponde à base atual')
            latest,_,_=k.catalog()
            current_bases=[{'id':latest[b['id']]['id'],'revision':latest[b['id']]['revision'],
                           'record_type':latest[b['id']]['record_type'],'title':latest[b['id']]['title'],'payload':latest[b['id']]['payload']} for b in bases if b['id'] in latest]
            if sha(canon(current_bases).encode())!=snapshot or latest.get(ident,{}).get('revision')!=old['revision']:
                raise Conflict('base mudou durante a revisão semântica')
            payload=automatic_payload(kind,proposal.get('payload'),old)
            if kind=='assertion' and 'attribution_evidence' in payload:
                primary=next((v for v in citations if v.get('record_id') in {r.get('record_id') for r in payload.get('source_refs',[])}),None)
                if not primary:raise Invalid('revisão de atribuição exige citação da fonte primária atual')
                payload['attribution_evidence']={'source_ref':{'record_id':primary['record_id'],'revision':primary['revision']},'quote':primary['quote']}
            if old['payload'].get('review_status') in HUMAN_REVIEW_STATUSES:
                # Até uma retificação da fonte de confirmação invalida sua vigência,
                # sem alterar o evento histórico nem simular uma nova revisão humana.
                payload['review_status']='clarification_needed'
            # Esta nota é produzida pelo serviço, não é um evento de revisão humana.
            payload['revalidation_note']={'reason':proposal.get('reason',''),
                'citations':copy.deepcopy(citations),'reviewed_at':NOW(),'previous_revision':old['revision'],
                'previous_review_status':old['payload'].get('review_status')}
            result=k.apply(sha(canon([key,ident,old['revision'],snapshot]).encode()),kind,old['title'],payload,ident,old['revision'])
            completed.append(result);pending.remove(ident)
    return {'status':'completed' if not unresolved else 'limited','completed':completed,'unresolved':unresolved,
            'limits':['Citações e estrutura verificadas; suporte semântico continua uma interpretação revisável.']}


def review(sources,key,model,max_records=12):
    completed=[];unresolved=[]
    try:return _review(sources,key,model,max_records,completed,unresolved)
    except Exception as failure:
        if completed and not getattr(failure,'partial_result',None):
            failure.partial_result={'status':'partial','completed':completed,'unresolved':unresolved,
                                    'error':str(failure),'remaining':'Consultar auditoria para derivados ainda suspensos.'}
        raise
