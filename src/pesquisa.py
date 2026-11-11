"""Pesquisa delimitada; resposta e plano duráveis precedem a importação."""
import copy,json,re,urllib.parse,urllib.request
from html import unescape
from nucleo import NOW,Invalid,Conflict,sha,canon
from conhecimento import Knowledge
from documentos import validate_metadata
from autonomia import atomic_json
from melhorias import _validate_key,_safe_path,_state_lock,_read_json

TERMS={'attention':'attention','executive_function':'executive function',
 'learning':'learning','memory':'memory','task_initiation':'task initiation','sleep':'sleep',
 'adult':'adult',
 'personality':'personality','social_communication':'social communication','study_methods':'study methods',
 'retrieval':'information retrieval','knowledge_graph':'knowledge graph','cache':'cache invalidation',
 'sqlite':'SQLite transactions','software_testing':'software testing','agent_communication':'multi agent communication'}


def query_terms(terms):
    if not isinstance(terms,list) or not 1<=len(terms)<=5 or any(not isinstance(t,str) or t not in TERMS for t in terms):
        raise Invalid('pesquisa exige termos técnicos autorizados, sem texto biográfico livre')
    return ' '.join(TERMS[t] for t in dict.fromkeys(terms))


def fetch_json(url,timeout=15):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='api.crossref.org' or parsed.path!='/works':
        raise Invalid('destino de pesquisa fora do provedor autorizado')
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):raise Invalid('redirecionamento não autorizado')
    request=urllib.request.Request(url,headers={'User-Agent':'CerebroPesquisa/0.4 (bounded local bibliographic client)'})
    opener=urllib.request.build_opener(NoRedirect)
    with opener.open(request,timeout=timeout) as response:
        data=response.read(1500001)
    if len(data)>1500000:raise Invalid('resposta bibliográfica excede limite')
    return json.loads(data.decode('utf-8'))


def crossref(terms,limit=3,transport=fetch_json):
    query=query_terms(terms)
    if type(limit)is not int or not 1<=limit<=5:raise Invalid('quantidade de estudos fora do limite')
    url='https://api.crossref.org/works?'+urllib.parse.urlencode({'query':query,'rows':limit,'filter':'type:journal-article'})
    raw=transport(url);items=raw.get('message',{}).get('items',[]);result=[]
    for item in items[:limit]:
        doi=item.get('DOI');titles=item.get('title') or []
        if not isinstance(doi,str) or not re.fullmatch(r'10\.\d{4,9}/[^\s]+',doi) or not titles:continue
        abstract=unescape(re.sub('<[^>]+>',' ',item.get('abstract') or '')).strip()
        published=(item.get('published') or {}).get('date-parts')
        authors=[' '.join(str(a.get(k,'')) for k in ('given','family')).strip() for a in item.get('author',[])]
        result.append({'title':str(titles[0]),'doi':doi,'url':'https://doi.org/'+urllib.parse.quote(doi,safe='/'),
                       'authors':authors,'published_date_parts':published,'abstract':abstract[:10000],
                       'availability':'abstract_and_metadata' if abstract else 'metadata_only',
                       'limitations':['Texto integral não foi consultado.','Metadados não comprovam eficácia, causalidade ou aplicabilidade individual.']})
    return {'query':query,'terms':copy.deepcopy(terms),'documents':result,'searched_at':NOW(),'provider':'Crossref',
            'limitations':['Busca delimitada; não é revisão sistemática.','Ausência de resumo impede avaliar resultados somente pelos metadados.']}


def _plan(fingerprint,request,data):
    try:
        if data['query']!=query_terms(request['terms']) or data['terms']!=request['terms'] or data['provider']!='Crossref' or not isinstance(data['searched_at'],str) or not data['searched_at']:
            raise Invalid('resposta não corresponde à pesquisa')
        if not isinstance(data['documents'],list) or len(data['documents'])>request['limit'] or not isinstance(data['limitations'],list):
            raise Invalid('resposta bibliográfica fora do limite')
        if len(canon(data).encode('utf-8'))>1500000:raise Invalid('resposta bibliográfica excede limite')
        plan=[];by_doi={}
        for doc in data['documents']:
            if not isinstance(doc['title'],str) or not doc['title'].strip() or not isinstance(doc['abstract'],str) or len(doc['abstract'])>10000 or not re.fullmatch(r'10\.\d{4,9}/[^\s]+',doc['doi']):
                raise Invalid('documento bibliográfico inválido')
            text='Título: '+doc['title']+'\nDOI: '+doc['doi']+'\n'
            text+=('Resumo disponível:\n'+doc['abstract']) if doc['abstract'] else 'Resumo não disponível; não inferir resultados.'
            if len(text)>20000:raise Invalid('fonte bibliográfica excede limite')
            metadata={'source_kind':'publication','origin_description':'Metadados recuperados do Crossref',
                      'availability_status':'partially_available','reference_locator':doc['url'],
                      'publication_title':doc['title'],'doi':doc['doi'],'authors':doc['authors'],
                      'accessed_at':data['searched_at'],'limitations':doc['limitations']}
            if doc['published_date_parts']:
                metadata['published_time']={'precision':'exact' if len(doc['published_date_parts'][0])==3 else 'approximate','date_parts':doc['published_date_parts']}
            entry={'key':sha(canon([fingerprint,doc['doi']]).encode()),'title':doc['title'][:110],
                   'text':text,'source_metadata':validate_metadata(metadata)}
            if doc['doi'] in by_doi and canon(by_doi[doc['doi']])!=canon(entry):raise Invalid('DOI duplicado com conteúdos divergentes')
            by_doi[doc['doi']]=entry;plan.append(entry)
        run={'key':sha((fingerprint+'run').encode()),'kind':'research_run','title':'Pesquisa de evidências',
             'payload':{'question':'Pesquisar '+data['query'],'query':data['query'],'limitations':data['limitations'],
                        'research_status':'limited' if plan else 'no_results','searched_at':data['searched_at']}}
        return {'sources':plan,'research':run}
    except (KeyError,TypeError,IndexError) as error:raise Invalid('resposta ou plano bibliográfico inválido') from error


def _prepared(request,fingerprint,data):
    state={'version':1,'phase':'prepared','request':copy.deepcopy(request),'fingerprint':fingerprint,
           'response':copy.deepcopy(data),'plan':_plan(fingerprint,request,data),'source_refs':[],'research_record':None}
    state['plan_hash']=sha(canon([state['request'],state['fingerprint'],state['response'],state['plan']]).encode())
    return state


def _verify_plan(state,request,fingerprint):
    if state.get('version')!=1 or canon(state.get('request'))!=canon(request) or state.get('fingerprint')!=fingerprint:
        raise Conflict('chave de pesquisa reutilizada ou journal divergente')
    if state.get('phase')=='fetching':raise Conflict('pesquisa incerta antes da resposta durável; não repetir rede, iniciar nova demanda')
    try:
        expected=_plan(fingerprint,request,state['response'])
        digest=sha(canon([request,fingerprint,state['response'],expected]).encode())
        if canon(expected)!=canon(state['plan']) or digest!=state['plan_hash']:raise Invalid('plano de pesquisa foi alterado')
        if state['phase'] not in ('prepared','importing','recorded','completed') or not isinstance(state['source_refs'],list) or len(state['source_refs'])>len(expected['sources']):
            raise Invalid('progresso da pesquisa inválido')
    except (KeyError,TypeError) as error:raise Invalid('journal de pesquisa incompleto') from error


def _run_payload(state):
    payload=copy.deepcopy(state['plan']['research']['payload']);payload['source_refs']=copy.deepcopy(state['source_refs'])
    return payload


def _source_current(sources,ref,entry):
    if not isinstance(ref,dict) or not isinstance(ref.get('record_id'),str) or type(ref.get('revision')) is not int:
        raise Invalid('referência bibliográfica inválida')
    record=sources.read(ref['record_id'])
    if record['revision']!=ref['revision']:raise Invalid('pesquisa anterior usa fonte corrigida; iniciar nova demanda de atualização')
    if record['title']!=entry['title'].strip() or record['payload'].get('content')!=entry['text'] or any(canon(record['payload'].get(name))!=canon(value) for name,value in entry['source_metadata'].items()):
        raise Invalid('fonte não corresponde ao plano bibliográfico')


def _current(sources,k,state):
    if len(state['source_refs'])!=len(state['plan']['sources']) or not isinstance(state['research_record'],dict):
        raise Invalid('pesquisa ainda não foi concluída')
    for ref,entry in zip(state['source_refs'],state['plan']['sources']):_source_current(sources,ref,entry)
    read=k.read(state['research_record']['id'])
    if read['validity']!='current_within_scope':raise Invalid('pesquisa anterior precisa de revalidação')
    record=read['record']
    if record['revision']!=state['research_record']['revision'] or canon(record['payload'])!=canon(_run_payload(state)):
        raise Invalid('registro de pesquisa foi revisado; iniciar nova demanda')


def _result(state):
    return dict(copy.deepcopy(state['response']),source_refs=copy.deepcopy(state['source_refs']),research_record=copy.deepcopy(state['research_record']))


def research(sources,key,terms,limit=3,transport=fetch_json):
    _validate_key(key);query_terms(terms)
    if type(limit)is not int or not 1<=limit<=5:raise Invalid('quantidade de estudos fora do limite')
    request={'key':key,'terms':copy.deepcopy(terms),'limit':limit};fingerprint=sha(canon([key,terms,limit]).encode())
    with _state_lock(sources,'pesquisas'):
        journal=_safe_path(sources,'estado','pesquisas',sha(key.encode())+'.request.json',create_parent=True)
        path=_safe_path(sources,'estado','pesquisas',fingerprint+'.json')
        if journal.exists():
            state=_read_json(journal);_verify_plan(state,request,fingerprint)
        elif path.exists():
            cached=_read_json(path);data={name:value for name,value in cached.items() if name not in ('source_refs','research_record')}
            state=_prepared(request,fingerprint,data)
            state.update(source_refs=cached['source_refs'],research_record=cached['research_record'],phase='completed')
            _current(sources,Knowledge(sources),state);atomic_json(journal,state)
            return cached
        else:
            # Uma reserva sem resposta não é repetida automaticamente: a rede pode ter sido acionada.
            atomic_json(journal,{'version':1,'phase':'fetching','request':request,'fingerprint':fingerprint})
            data=crossref(terms,limit,transport);state=_prepared(request,fingerprint,data);atomic_json(journal,state)
        k=Knowledge(sources)
        if path.exists():
            cached=_read_json(path)
            if canon(cached)!=canon(_result(state)):raise Invalid('cache não corresponde ao plano concluído')
            _current(sources,k,state)
            if state['phase']!='completed':state['phase']='completed';atomic_json(journal,state)
            return cached
        for index,entry in enumerate(state['plan']['sources']):
            if index<len(state['source_refs']):
                _source_current(sources,state['source_refs'][index],entry);continue
            source=sources.apply(entry['key'],'create',title=entry['title'],text=entry['text'],source_metadata=copy.deepcopy(entry['source_metadata']))
            ref={'record_id':source['id'],'revision':source['revision']};_source_current(sources,ref,entry)
            state['source_refs'].append(ref);state['phase']='importing';atomic_json(journal,state)
        if state['research_record'] is None:
            run=state['plan']['research']
            state['research_record']=k.apply(run['key'],run['kind'],run['title'],_run_payload(state))
            state['phase']='recorded';atomic_json(journal,state)
        _current(sources,k,state);result=_result(state);atomic_json(path,result)
        state['phase']='completed';atomic_json(journal,state)
        return result
