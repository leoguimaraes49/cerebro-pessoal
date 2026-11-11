"""Registra opções e análise explícita; não escolhe nem executa pelo usuário."""
import sqlite3
from nucleo import Invalid,Conflict,Uncertain,Locked
from conhecimento import Knowledge

def prepare(knowledge, key, title, situation, options, sources, gaps):
    effects=[]
    try:return _prepare(knowledge,key,title,situation,options,sources,gaps,effects)
    except (Invalid,Conflict,Uncertain,Locked,OSError,sqlite3.Error) as error:
        if effects:return {'status':'partial','confirmed_effects':effects,'reason':str(error),'choice':'not_made','external_actions':False}
        raise

def _prepare(knowledge, key, title, situation, options, sources, gaps,effects):
    if not isinstance(title,str) or not 1<=len(title)<=90:raise Invalid('título fora do limite')
    if not isinstance(key,str) or len(key)>55 or not isinstance(situation,str) or not situation.strip():
        raise Invalid('identidade ou situação da decisão inválida')
    if not isinstance(options,list) or not 2<=len(options)<=8:
        raise Invalid('informe entre duas e oito opções')
    if not isinstance(sources,list) or not sources:
        raise Invalid('decisão sem fontes de contexto')
    if not isinstance(gaps,list) or len(gaps)>12 or any(not isinstance(x,str) or not x.strip() or len(x)>500 for x in gaps):
        raise Invalid('lacunas fora dos limites')
    records,_,_=knowledge.catalog()
    for ref in sources:
        if not isinstance(ref,dict) or ref.get('record_id') not in records:
            raise Invalid('fonte inexistente')
        n=records[ref['record_id']]
        if n['record_type']!='source' or ref.get('revision')!=n['revision']:
            raise Invalid('contexto precisa de fontes atuais')
    normalized=[]
    for item in options:
        if not isinstance(item,dict) or set(item)!={'descricao','origem','pros','contras','incertezas'}:
            raise Invalid('opção precisa de descrição, origem, prós, contras e incertezas')
        if item['origem'] not in ('relatada_pelo_usuario','sugerida_pela_ia'):
            raise Invalid('origem da opção desconhecida')
        if not isinstance(item['descricao'],str) or not 1<=len(item['descricao'])<=500:
            raise Invalid('descrição fora dos limites')
        for field in ('pros','contras','incertezas'):
            if not isinstance(item[field],list) or len(item[field])>10 or any(not isinstance(x,str) or len(x)>500 for x in item[field]):
                raise Invalid('análise fora dos limites')
        normalized.append(dict(item))
    reported=[x['descricao'] for x in normalized if x['origem']=='relatada_pelo_usuario']
    if not reported:
        raise Invalid('falta pelo menos uma opção relatada; não inventar opções percebidas pelo usuário')
    decision=knowledge.apply(key+'-decisao','entity',title,{
        'entity_kind':'decision','identity_status':'provisional','origin_refs':sources,
        'situation':situation,'perceived_options':reported,'decision_status':'considering'})
    effects.append(decision)
    decision_ref={'record_id':decision['id'],'revision':decision['revision']}
    lines=['Análise provisória fornecida pela IA, ainda não confirmada pelo usuário.',situation]
    for option in normalized:
        lines.extend(['Opção: '+option['descricao'],'Origem: '+option['origem'],
                      'Prós propostos: '+('; '.join(option['pros']) or 'não informados'),
                      'Contras propostos: '+('; '.join(option['contras']) or 'não informados'),
                      'Incertezas: '+('; '.join(option['incertezas']) or 'não informadas')])
    if gaps:lines.append('Lacunas: '+'; '.join(gaps))
    # O momento vem da fonte para que repetir o pedido seja idempotente.
    as_of=records[sources[0]['record_id']]['updated_at']
    analysis=knowledge.apply(key+'-analise','synthesis','Análise — '+title,{
        'synthesis_kind':'knowledge_summary','content':'\n'.join(lines),'scope':'Apoio à decisão; escolha e execução permanecem pendentes.',
        'basis_refs':sources+[decision_ref],'limitations':['Prós e contras são formulações da IA, não evidência independente.',
        'Não estima probabilidade de sucesso, diagnóstico ou retorno financeiro.','Não executa ações externas.'],
        'coverage_status':'limited' if gaps else 'provisional','as_of':as_of})
    effects.append(analysis)
    questions=[]
    for index,gap in enumerate(gaps):
        question=knowledge.apply(key+'-lacuna-'+str(index),'question','Lacuna '+str(index+1)+' — '+title,{
            'question_text':gap,'purpose':'Esclarecer base da decisão','trigger_refs':[decision_ref],
            'information_needed':gap,'impact':'Pode alterar a análise ou viabilidade das opções.',
            'question_status':'open','resolution_status':'unresolved'})
        questions.append(question)
        effects.append(question)
    return {'status':'confirmed','decision':decision,'analysis':analysis,'questions':questions,
            'choice':'not_made','external_actions':False,'limits':'Resultado da ferramenta confirma os registros, não a verdade ou suficiência da análise.'}
