"""Controles locais de atribuição, sem certificar semântica livre ou diagnóstico.

Reconhece nomes/aliases já cadastrados e a primeira pessoa explicitamente
vinculada ao proprietário configurado. Ambiguidades não são resolvidas por
similaridade, frequência ou pela ordem das entidades no catálogo.
"""
import json,re,unicodedata
from nucleo import Invalid,Conflict,config_file


class AttributionError(Invalid):
    def __init__(self,reason,*,ambiguous=False):
        self.reason=reason;self.ambiguous=ambiguous
        super().__init__('atribuição precisa de revisão: '+reason)


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text)).casefold()
                   if not unicodedata.combining(c))


def persons(records):
    return {i:r for i,r in records.items() if r.get('record_type')=='entity'
            and r.get('payload',{}).get('entity_kind')=='person'
            and r['payload'].get('identity_status')!='merged'}


def aliases(record):
    p=record['payload'];extra=p.get('aliases',[])
    if not isinstance(extra,list):raise Invalid('aliases de pessoa precisam de uma lista explícita')
    values=[p.get('display_name','')]+extra
    return {normalized(x).strip() for x in values if isinstance(x,str) and len(x.strip())>=2}


def owner_id(root,records):
    path=config_file(root,'execucao.json')
    if not path.exists():return None
    if path.is_symlink():raise Invalid('configuração de identidade redirecionada')
    ident=json.loads(path.read_text(encoding='utf-8')).get('owner_person_id')
    if ident is None:return None
    if not isinstance(ident,str) or ident not in persons(records):
        raise Invalid('proprietário configurado não corresponde a pessoa atual')
    return ident


def speaker_for_source(record,owner):
    # A primeira pessoa de um artigo, documento ou saída de ferramenta não é
    # uma credencial para atribuir a frase ao proprietário do cofre.
    return owner if record.get('payload',{}).get('source_kind') in ('conversation','conversation_turn','observation_record') else None


def mentions(text,records,owner=None,answer=False):
    text=normalized(text);hits=[]
    for ident,record in persons(records).items():
        for name in aliases(record):
            for match in re.finditer(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text):
                hits.append((match.start(),match.end(),ident))
    # Um nome completo prevalece sobre um alias curto contido nele. Homônimos
    # completos, em contrapartida, continuam ambíguos.
    found={i for a,b,i in hits if not any(c<=a and b<=d and (c<a or b<d) for c,d,_ in hits)}
    if owner:
        first=r'^\s*(?:eu\b|sou\b|estou\b|tenho\b|prefiro\b|nasci\b|moro\b|trabalho\b|estudo\b|quero\b|gosto\b|sinto\b|fiz\b|vou\b|consigo\b)'
        if re.search(first,text) or answer and re.search(r'\bvoce\b',text):found.add(owner)
    return found


def clauses(text):
    # Delimitação conservadora: não infere correferência entre duas frases.
    return [part.strip() for part in re.split(
        r'(?<=[.!?;])\s+|\n+|\s+(?:e|mas|enquanto|já)\s+(?=(?:eu\b|sou\b|você\b|[A-ZÀ-Ý]))',text) if part.strip()]


def primary_mentions(text,records,owner=None,answer=False):
    """Um nome citado como objeto não substitui o sujeito explícito da frase."""
    plain=normalized(text).lstrip(' \t\r\n"\'—-')
    if owner and (re.match(r'^(?:eu|sou|estou|tenho|prefiro|nasci|moro|trabalho|estudo|quero|gosto|sinto|fiz|vou|consigo)\b',plain)
                  or answer and re.match(r'^voce\b',plain)):
        return {owner}
    candidates=[]
    for ident,record in persons(records).items():
        for name in aliases(record):
            if re.match(r'^(?:o |a )?'+re.escape(name)+r'(?!\w)',plain):candidates.append((len(name),ident))
    if candidates:
        longest=max(n for n,_ in candidates)
        return {i for n,i in candidates if n==longest}
    return mentions(text,records,owner,answer)


def validate_quote(subject,quote,records,owner=None,value=None):
    if subject not in persons(records):return {'status':'not_applicable'}
    parts=clauses(quote)
    literal=normalized(value).strip() if isinstance(value,(str,int,float)) and not isinstance(value,bool) else ''
    selected=[part for part in parts if literal and literal in normalized(part)]
    examined=selected or parts
    found=set().union(*(primary_mentions(part,records,owner) for part in examined))
    if found and subject not in found:raise AttributionError('trecho identifica outra pessoa')
    if len(found)>1:raise AttributionError('trecho mistura pessoas sem vínculo inequívoco',ambiguous=True)
    if not found:
        pronoun=bool(re.search(r'\b(ele|ela|dele|dela|eles|elas)\b',normalized(quote)))
        return {'status':'unresolved' if pronoun or len(persons(records))>1 else 'limited',
                'reason':'sujeito não explicitado no trecho'}
    # Detecta troca de números literais, sem alegar equivalência de paráfrases.
    if literal and re.search(r'\d',literal) and not selected:
        numbers=re.findall(r'\d+(?::\d+)?',literal)
        if any(n not in re.findall(r'\d+(?::\d+)?',normalized(quote)) for n in numbers):
            raise AttributionError('valor numérico não corresponde ao trecho do sujeito')
    return {'status':'checked_for_known_mentions','scope':'identidade por menções explícitas; conteúdo permanece revisável'}


def validate_assertion(payload,records,owner=None):
    subject=payload.get('subject_ref',{}).get('record_id')
    if subject not in persons(records):return {'status':'not_applicable'}
    evidence=payload.get('attribution_evidence')
    value=payload.get('value',{}).get('content')
    bases=payload.get('source_refs',[]) if payload.get('nature')!='inference' else payload.get('basis_refs',[])
    if evidence is not None:
        if not isinstance(evidence,dict) or set(evidence)!={'source_ref','quote'}:
            raise Invalid('apoio de atribuição inválido')
        ref=evidence['source_ref'];quote=evidence['quote']
        if (not isinstance(ref,dict) or ref not in bases or type(ref.get('revision')) is not int
                or not isinstance(quote,str) or not quote):raise Invalid('apoio de atribuição exige origem própria')
        record=records.get(ref.get('record_id'))
        if not record or record.get('revision')!=ref['revision']:raise Conflict('origem da atribuição mudou')
        if record['record_type']!='source' or quote not in record['payload'].get('content',''):
            raise Invalid('trecho da atribuição não corresponde à fonte')
        result=validate_quote(subject,quote,records,speaker_for_source(record,owner),value)
        resolution=payload.get('attribution_resolution_ref')
        if result['status']=='unresolved' and resolution is not None:
            if resolution not in bases or type(resolution.get('revision')) is not int:
                raise Invalid('resolução de identidade exige fonte separada')
            answer=records.get(resolution.get('record_id'))
            if not answer or answer.get('revision')!=resolution['revision'] or answer['record_type']!='source':
                raise Conflict('fonte do esclarecimento mudou')
            resolved=mentions(answer['payload'].get('content',''),records,owner)
            if resolved!={subject}:raise AttributionError('esclarecimento não identifica unicamente o sujeito',ambiguous=True)
            return {'status':'resolved_by_separate_source'}
        return result
    # Compatibilidade dos pedidos antigos: só recusa contradição explícita nas
    # bases, sem preencher silenciosamente uma prova que o cliente não enviou.
    if isinstance(value,(str,int,float)) and not isinstance(value,bool) and str(value).strip():
        literal=normalized(value).strip();found=set()
        for ref in bases:
            record=records.get(ref.get('record_id'),{})
            if record.get('record_type')!='source':continue
            for part in clauses(record['payload'].get('content','')):
                if literal in normalized(part):found.update(primary_mentions(part,records,speaker_for_source(record,owner)))
        if found and subject not in found:raise AttributionError('valor literal vinculado a outra pessoa nas fontes')
    return {'status':'limited','reason':'pedido legado sem trecho de atribuição explícito'}


_STOP=set('a o as os um uma de da do das dos e ou que em no na nos nas ao aos com por para se sobre seu sua voce eu ele ela meu minha ficticio ficticia prefere preferencia estudar estudo esta estou sou tem tenho era foi ser e mora horario relatada relato acordo diz disse tambem mais como'.split())


def content_words(text,records):
    text=normalized(text)
    for record in persons(records).values():
        for name in sorted(aliases(record),key=len,reverse=True):text=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',' ',text)
    tokens=re.findall(r'\w+',text)
    return {('engenharia' if t in ('engenheiro','engenheira','engenharia') else 'confiar' if t in ('confio','confia','confiava','confiam','confiar') else t)
            for t in tokens if t not in _STOP and len(t)>1}


def check_answer(answer,citations,records,owner=None):
    if not isinstance(answer,str) or not isinstance(citations,list):raise Invalid('resposta de atribuição inválida')
    supports=[]
    for citation in citations:
        if not isinstance(citation,dict):raise Invalid('citação de atribuição inválida')
        record=records.get(citation.get('record_id'));quote=citation.get('quote')
        if (not record or type(citation.get('revision')) is not int or record['revision']!=citation['revision']
                or not isinstance(quote,str) or not quote):raise Conflict('citação da resposta mudou ou está ausente')
        payload=record.get('payload',{})
        from nucleo import canon
        if quote not in payload.get('content','') and quote not in canon(payload):raise Invalid('citação de atribuição não é literal')
        if record['record_type']=='assertion':
            subject=payload.get('subject_ref',{}).get('record_id')
            supports.append(({subject} if subject in persons(records) else set(),content_words(quote,records),False))
        else:
            speaker=speaker_for_source(record,owner)
            supports.extend((primary_mentions(part,records,speaker),content_words(part,records),
                bool(re.search(r'\b(ele|ela|dele|dela)\b',normalized(part)))
                or speaker is None and bool(re.match(r'^\s*(?:eu|sou|estou|tenho)\b',normalized(part)))) for part in clauses(quote))
    checked=0;findings=[]
    for part in clauses(answer):
        subjects=primary_mentions(part,records,owner,answer=True)
        if not subjects:continue
        if len(subjects)>1:
            findings.append('frase da resposta mistura sujeitos');continue
        subject=next(iter(subjects));words=content_words(part,records)
        own=max((len(words&terms) for owners,terms,_ in supports if owners=={subject}),default=0)
        other=max((len(words&terms) for owners,terms,_ in supports if owners and subject not in owners),default=0)
        if other>own and other>=1:findings.append('informação da resposta apoiada somente em trecho de outra pessoa')
        if not own and any(not owners and pronoun and words&terms for owners,terms,pronoun in supports):
            findings.append('pronome da evidência não identifica o sujeito da resposta')
        checked+=1
    return {'status':'rejected' if findings else 'checked_for_known_mentions' if checked else 'not_applicable',
            'findings':findings,'checked_clauses':checked,
            'limits':['Não comprova semântica geral; nomes desconhecidos, paráfrases e correferência continuam sujeitos à revisão.']}
