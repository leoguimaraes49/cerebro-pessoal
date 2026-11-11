"""Verificador independente: somente biblioteca padrão; não importa gerador ou produção.

O caller fornece o hash de um manifesto confiável por fora do artefato. Isso
não autentica o produtor nem prova que dados registrados sejam verdade no mundo.
"""
import argparse,hashlib,json,sys
from dataclasses import dataclass
from types import MappingProxyType

class Refusal(ValueError):pass

def valid_revision(value):return type(value)is int and value>0

def same_json(left,right):
    pending=[(left,right)]
    while pending:
        left,right=pending.pop()
        if type(left)is not type(right):return False
        if isinstance(left,dict):
            if left.keys()!=right.keys():return False
            pending.extend((left[key],right[key]) for key in left)
        elif isinstance(left,list):
            if len(left)!=len(right):return False
            pending.extend(zip(left,right))
        elif left!=right:return False
    return True

def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def sha(value):return hashlib.sha256(encode(value)).hexdigest()

def strict(text):
    def pairs(values):
        result={}
        for k,v in values:
            if k in result:raise Refusal('duplicate_json_key')
            result[k]=v
        return result
    def constant(value):raise Refusal('non_json_number')
    return json.loads(text,object_pairs_hook=pairs,parse_constant=constant)

def pointer(value,path):
    if not isinstance(path,str) or not path.startswith('/') or len(path)>500:raise Refusal('invalid_path')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        if isinstance(value,dict) and part in value:value=value[part]
        elif isinstance(value,list) and part.isdigit() and int(part)<len(value):value=value[int(part)]
        else:raise Refusal('missing_value')
    return value

def read_ref(reference,evidence,manifest):
    if not valid_revision(reference.get('revision')):raise Refusal('invalid_reference_revision')
    ident=reference.get('record_id');meta=manifest['records'].get(ident)
    if not meta:raise Refusal('unknown_reference')
    if reference.get('revision')!=meta['revision'] or ident in manifest.get('stale_ids',[]):raise Refusal('stale_reference')
    record=evidence.get(ident)
    if record is None:raise Refusal('missing_evidence')
    if record['record_type']!='source':raise Refusal('derived_is_not_primary')
    try:data=strict(record['payload']['content'])
    except (ValueError,KeyError,TypeError):raise Refusal('unstructured_source')
    return pointer(data,reference['path'])

def assess_claim(claim,evidence,manifest):
    refs=claim.get('refs',[])
    if not isinstance(refs,list) or len(refs)>64:raise Refusal('invalid_claim_references')
    kind=claim.get('kind')
    if kind in ('hypothesis','free_text'):return {'id':claim.get('id'),'status':'not_semantically_verified','needed':[]}
    if kind not in ('field','sum','chain'):return {'id':claim.get('id'),'status':'unsupported_claim_kind','needed':[]}
    try:
        values=[read_ref(ref,evidence,manifest) for ref in refs]
        if kind=='field':
            if len(values)!=1:raise Refusal('invalid_field_arity')
            expected=values[0]
            if expected is None:raise Refusal('unknown_value')
        elif kind=='sum':
            if not values or any(type(x)is not int for x in values):raise Refusal('not_integer_operands')
            expected=0
            for value in values:expected+=value
        else:
            if len(values)<2 or any(not isinstance(v,list) or len(v)!=3 or any(type(x)is not str for x in v) for v in values):raise Refusal('invalid_chain')
            predicate=values[0][1]
            if predicate not in manifest['policy']['transitive_predicates']:raise Refusal('unregistered_rule')
            if any(v[1]!=predicate for v in values) or any(a[2]!=b[0] for a,b in zip(values,values[1:])):raise Refusal('disconnected_chain')
            expected=[values[0][0],predicate,values[-1][2]]
        valid=same_json(expected,claim.get('value'))
        return {'id':claim.get('id'),'status':'verified_as_recorded' if valid else 'unsupported_value',
                'needed':sorted({ref['record_id'] for ref in refs})}
    except Refusal as error:
        return {'id':claim.get('id'),'status':str(error),'needed':sorted({r.get('record_id','') for r in refs})}

@dataclass(frozen=True)
class ManifestContext:
    anchor: str
    scope: str
    records: object
    stale_ids: frozenset
    policy: object
    def __getitem__(self,key):return getattr(self,key)
    def get(self,key,default=None):return getattr(self,key,default)


def prepare_manifest(manifest,anchor,scope):
    if sha(manifest)!=anchor or manifest.get('scope')!=scope:raise Refusal('untrusted_or_changed_manifest')
    if any(not isinstance(key,str) or not isinstance(meta,dict) or not valid_revision(meta.get('revision'))
           for key,meta in manifest['records'].items()):raise Refusal('invalid_manifest_revision')
    # Copiar valores primitivos e congelar os mapas: o caller não pode mudar a entrada validada por aliasing.
    records=MappingProxyType({key:MappingProxyType(dict(value)) for key,value in manifest['records'].items()})
    policy=MappingProxyType({'transitive_predicates':tuple(manifest['policy']['transitive_predicates']),
                             'max_claims':manifest['policy']['max_claims']})
    return ManifestContext(anchor,scope,records,frozenset(manifest.get('stale_ids',[])),policy)


def verify(packet,expected_anchor,expected_scope,context=None):
    errors=[];checked=[]
    try:
        if packet.get('format') not in ('lab-assurance-1','lab-assurance-2'):raise Refusal('unsupported_format')
        if packet.get('scope')!=expected_scope:raise Refusal('scope_mismatch')
        if packet['format']=='lab-assurance-2':
            if context is None:raise Refusal('trusted_manifest_required')
            if not isinstance(context,ManifestContext) or context.anchor!=expected_anchor or context.scope!=expected_scope or packet.get('manifest_anchor')!=expected_anchor:
                raise Refusal('context_anchor_mismatch')
            manifest=context
        else:
            manifest=packet['manifest']
            if sha(manifest)!=expected_anchor:raise Refusal('untrusted_or_changed_manifest')
            if manifest['scope']!=expected_scope:raise Refusal('manifest_scope_mismatch')
        body={k:v for k,v in packet.items() if k!='receipt_sha256'}
        if sha(body)!=packet.get('receipt_sha256'):raise Refusal('receipt_changed')
        evidence=packet['evidence']
        if not isinstance(evidence,dict) or len(evidence)>4096:raise Refusal('evidence_limit')
        for ident,record in evidence.items():
            if not valid_revision(record.get('revision')):raise Refusal('invalid_evidence_revision')
            entry=manifest['records'].get(ident)
            if not entry or record.get('id')!=ident or sha(record)!=entry['sha256'] or record.get('revision')!=entry['revision']:
                raise Refusal('evidence_changed')
        citations=packet.get('citations',[])
        if not isinstance(citations,list) or len(citations)>256:raise Refusal('citation_limit')
        for citation in citations:
            if not valid_revision(citation.get('revision')):raise Refusal('invalid_citation_revision')
            ident=citation.get('record_id');entry=manifest['records'].get(ident);record=evidence.get(ident)
            if not entry or citation.get('revision')!=entry['revision'] or ident in manifest.get('stale_ids',[]):raise Refusal('stale_citation')
            if not record:raise Refusal('missing_citation_evidence')
            quote=citation.get('quote')
            if not isinstance(quote,str) or not quote or quote not in record['payload'].get('content','') and quote not in encode(record['payload']).decode('utf-8'):
                raise Refusal('quote_not_found')
        claims=packet.get('claims',[])
        if not isinstance(claims,list) or len(claims)>manifest['policy']['max_claims']:raise Refusal('claim_limit')
        ids=[c.get('id') for c in claims]
        if len(set(ids))!=len(ids) or any(not isinstance(x,str) or not x for x in ids):raise Refusal('invalid_claim_ids')
        checked=[assess_claim(claim,evidence,manifest) for claim in claims]
        if packet['answer_type']=='controlled':
            rendered='\n'.join(c['id']+' = '+encode(c['value']).decode('utf-8') for c in claims)
            if packet['answer']!=rendered:errors.append('answer_not_bound_to_claims')
            if not claims:errors.append('empty_controlled_answer')
        elif packet['answer_type']!='free_text':errors.append('unknown_answer_type')
        statuses={c['status'] for c in checked}
        unresolved={'not_semantically_verified','unsupported_claim_kind','unstructured_source','unknown_value'}
        errors.extend(s for s in statuses if s not in unresolved and s!='verified_as_recorded')
        if errors:status='rejected'
        elif packet['answer_type']=='free_text' or statuses & unresolved:status='limited'
        else:status='accepted'
        return {'status':status,'errors':sorted(set(errors)),'claims':checked,
                'evidence_integrity_checked':True,'semantics':'only registered objective claims, as recorded; not truth about the world',
                'all_claims_verified':status=='accepted' and bool(claims)}
    except (Refusal,KeyError,TypeError,ValueError,AttributeError,IndexError,RecursionError) as error:
        return {'status':'rejected','errors':[str(error)],'claims':checked,'evidence_integrity_checked':False,'all_claims_verified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('packet');p.add_argument('--anchor',required=True);p.add_argument('--scope',required=True);p.add_argument('--manifest');a=p.parse_args()
    from pathlib import Path
    file=Path(a.packet)
    if file.stat().st_size>4_000_000:raise Refusal('packet_file_limit')
    packet=strict(file.read_text(encoding='utf-8-sig'));context=None
    if a.manifest:
        other=Path(a.manifest)
        if other.stat().st_size>4_000_000:raise Refusal('manifest_file_limit')
        context=prepare_manifest(strict(other.read_text(encoding='utf-8-sig')),a.anchor,a.scope)
    result=verify(packet,a.anchor,a.scope,context)
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='accepted' else 2 if result['status']=='limited' else 1
if __name__=='__main__':
    try:sys.exit(main())
    except (Refusal,OSError,ValueError,KeyError,TypeError,AttributeError,IndexError,RecursionError) as error:
        print(json.dumps({'status':'rejected','errors':[str(error)]}));sys.exit(1)
