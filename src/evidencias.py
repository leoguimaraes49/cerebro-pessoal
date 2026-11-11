"""Adaptador local de comprovantes para registros canônicos versionados."""

import copy
import hashlib
import json
import re
from pathlib import Path

from autonomia import atomic_json
from conhecimento import Knowledge
from nucleo import Conflict, Invalid, NOW, canon, sha
from verificador_evidencias import prepare_manifest, verify

SCOPE = 'proprietario_local'
MAX_BYTES = 4_000_000
OBJECTIVE_KINDS = {'field', 'sum', 'chain'}
MISSING_ERRORS = {'missing_evidence', 'missing_citation_evidence'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def snapshot(sources, scope=SCOPE):
    knowledge = Knowledge(sources)
    records, _, issues = knowledge.catalog()
    if issues:
        raise Conflict('catálogo com problemas estruturais impede a verificação')
    stale = knowledge.stale(records)
    generation = sha(canon({'records': records, 'issues': issues, 'scope': scope}).encode())
    manifest = {
        'format': 'lab-assurance-1', 'scope': scope,
        'records': {
            ident: {'revision': record['revision'], 'record_type': record['record_type'],
                    'sha256': digest(record)}
            for ident, record in sorted(records.items())
        },
        'stale_ids': sorted(stale),
        'policy': {'transitive_predicates': ['requires', 'precedes'], 'max_claims': 64},
    }
    return records, manifest, digest(manifest), generation


def render(claims):
    return '\n'.join(claim['id'] + ' = ' + encoded(claim['value']).decode('utf-8')
                     for claim in claims)


def packet_for(records, manifest, anchor, draft, selected):
    claims = copy.deepcopy(draft['claims'])
    controlled = draft.get('answer_format', 'free_text') == 'controlled'
    packet = {
        'format': 'lab-assurance-2', 'scope': manifest['scope'],
        'manifest_anchor': anchor,
        'evidence': {ident: copy.deepcopy(records[ident]) for ident in selected if ident in records},
        'claims': claims, 'citations': copy.deepcopy(draft.get('citations', [])),
        'answer_type': 'controlled',
        'answer': draft['answer'] if controlled else render(claims),
        'response_format': 'controlled' if controlled else 'free_text',
        'response_text': draft['answer'],
    }
    packet['receipt_sha256'] = digest(packet)
    return packet


def required_ids(draft):
    identifiers = []
    references = list(draft.get('citations', []))
    for claim in draft['claims']:
        references.extend(claim.get('refs', []))
    for reference in references:
        if not isinstance(reference, dict) or not isinstance(reference.get('record_id'), str):
            raise Invalid('referência de alegação inválida')
        if reference['record_id'] not in identifiers:
            identifiers.append(reference['record_id'])
    return identifiers


def safe_folder(sources, name):
    state = sources.root / 'estado'
    folder = state / 'comprovantes' / name
    if not folder.resolve().is_relative_to(state.resolve()):
        raise Invalid('comprovante fora do estado autorizado')
    if (state / 'comprovantes').is_symlink() or folder.is_symlink():
        raise Invalid('pasta de comprovantes redirecionada')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def read_json(path):
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise Invalid('arquivo de comprovante fora do contrato')
    return json.loads(path.read_text(encoding='utf-8'))


def summary(receipt, verdict):
    controlled = receipt['packet']['response_format'] == 'controlled'
    if controlled and receipt['packet']['response_text'] != receipt['packet']['answer']:
        verdict = dict(verdict, status='rejected', all_claims_verified=False,
                       errors=['response_not_bound_to_proof'])
    if verdict['status'] == 'accepted':
        status = 'verified' if controlled else 'claims_verified'
    else:
        status = verdict['status']
    return {
        'status': status, 'receipt_id': receipt['id'],
        'route': receipt['route'], 'generation': receipt['generation'],
        'answer_verified': controlled and verdict['all_claims_verified'],
        'claims_verified': verdict['all_claims_verified'],
        'claims': verdict['claims'], 'errors': verdict['errors'],
        'context_before': receipt['context_before'],
        'context_after': len(receipt['packet']['evidence']),
        'limits': ['Valores e regras registradas conferidos nas fontes atuais.',
                   'Texto livre e hipóteses continuam sujeitos à revisão.'],
    }


def inspect_response(sources, operation_key, draft, context_ids=None,
                     max_context=8, expected_generation=None, scope=SCOPE):
    if not isinstance(operation_key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', operation_key):
        raise Invalid('chave de verificação inválida')
    if not isinstance(draft, dict) or not isinstance(draft.get('answer'), str):
        raise Invalid('resposta estruturada inválida')
    if type(max_context) is not int or not 1 <= max_context <= 50:
        raise Invalid('limite de evidências inválido')
    if draft.get('answer_format', 'free_text') not in ('free_text', 'controlled'):
        raise Invalid('formato da resposta desconhecido')
    identity=None
    if draft.get('citations'):
        from atribuicao import check_answer,owner_id
        records=Knowledge(sources).catalog()[0]
        identity=check_answer(draft['answer'],draft['citations'],records,owner_id(sources.root,records))
        if identity['status']=='rejected':
            return {'status':'rejected','answer_verified':False,'claims_verified':False,'route':'identity_attribution',
                    'receipt_id':None,'errors':['identity_attribution_conflict'],'identity_check':identity}
    claims = draft.get('claims')
    if claims is None or claims == []:
        if draft.get('answer_format') == 'controlled':
            raise Invalid('resposta controlada exige alegações')
        return {'status': 'not_requested', 'answer_verified': False, 'claims_verified': False,
                'route': 'legacy_free_text', 'receipt_id': None, 'identity_check':identity}
    if not isinstance(claims, list) or len(claims) > 64 or any(not isinstance(c, dict) for c in claims):
        raise Invalid('alegações fora do contrato')
    if any(not isinstance(c.get('refs', []), list) for c in claims):
        raise Invalid('referências de alegação fora do contrato')
    if len(encoded(draft)) > 40_000:
        raise Invalid('resposta excede o limite de verificação')
    needed = required_ids(draft)
    if context_ids is None:
        context_ids = needed[:max_context]
    if (not isinstance(context_ids, list) or len(context_ids) > max_context or
            any(not isinstance(ident, str) for ident in context_ids)):
        raise Invalid('contexto da verificação inválido')

    fingerprint = digest({'draft': draft, 'context_ids': context_ids,
                          'limit': max_context, 'scope': scope})
    ident = digest([scope, operation_key])
    path = safe_folder(sources, 'respostas') / (ident + '.json')
    if path.exists():
        old = read_json(path)
        if old['request_fingerprint'] != fingerprint:
            raise Conflict('chave de verificação reutilizada com outro pedido')
        return read_receipt(sources, ident, scope)

    records, manifest, anchor, generation = snapshot(sources, scope)
    if expected_generation is not None and generation != expected_generation:
        raise Conflict('contexto mudou antes da verificação da resposta')
    context = prepare_manifest(manifest, anchor, scope)
    packet = packet_for(records, manifest, anchor, draft, context_ids)
    verdict = verify(packet, anchor, scope, context)
    route = 'direct'

    if MISSING_ERRORS.intersection(verdict['errors']):
        if all(claim.get('kind') in OBJECTIVE_KINDS for claim in claims):
            if len(needed) > max_context:
                route = 'context_budget_exceeded'
            else:
                full = packet_for(records, manifest, anchor, draft, needed)
                full_verdict = verify(full, anchor, scope, context)
                if full_verdict['status'] == 'accepted':
                    packet, verdict, route = full, full_verdict, 'supplemented'
                else:
                    route = 'unsupported_or_invalid'
        else:
            route = 'unverifiable'

    latest = snapshot(sources, scope)
    if latest[2] != anchor:
        raise Conflict('base mudou durante a verificação da resposta')
    receipt = {
        'id': ident, 'created_at': NOW(), 'request_fingerprint': fingerprint,
        'scope': scope, 'generation': generation, 'manifest_anchor': anchor,
        'context_before': len(context_ids), 'route': route, 'packet': packet,
    }
    manifest_path = safe_folder(sources, 'manifestos') / (anchor + '.json')
    if manifest_path.exists():
        if digest(read_json(manifest_path)) != anchor:
            raise Conflict('manifesto persistido divergiu')
    else:
        atomic_json(manifest_path, manifest)
    if len(encoded(receipt)) > MAX_BYTES:
        raise Invalid('comprovante excede o limite de armazenamento')
    # Conferir repetição concorrente sob uma identidade estável.
    from nucleo import exclusive
    lock_path = path.with_suffix('.lock')
    with exclusive(lock_path, create=not lock_path.exists()):
        if path.exists():
            current = read_json(path)
            if current['request_fingerprint'] != fingerprint:
                raise Conflict('pedido de verificação concorrente divergiu')
        else:
            atomic_json(path, receipt)
    return read_receipt(sources, ident, scope)


def read_receipt(sources, ident, scope=SCOPE):
    if not isinstance(ident, str) or not re.fullmatch('[a-f0-9]{64}', ident):
        raise Invalid('identificador de comprovante inválido')
    path = safe_folder(sources, 'respostas') / (ident + '.json')
    if not path.exists():
        raise Invalid('comprovante inexistente')
    receipt = read_json(path)
    if receipt.get('id') != ident or receipt.get('scope') != scope:
        raise Conflict('identidade ou escopo do comprovante divergiu')
    records, manifest, anchor, generation = snapshot(sources, scope)
    if receipt['manifest_anchor'] != anchor or receipt['generation'] != generation:
        return {'status': 'stale', 'receipt_id': ident, 'route': 'revalidation_required',
                'answer_verified': False, 'claims_verified': False}
    if receipt['packet'].get('citations'):
        from atribuicao import check_answer,owner_id
        identity=check_answer(receipt['packet'].get('response_text',''),receipt['packet']['citations'],records,owner_id(sources.root,records))
        if identity['status']=='rejected':
            return {'status':'rejected','receipt_id':ident,'route':'identity_attribution',
                    'answer_verified':False,'claims_verified':False,'errors':['identity_attribution_conflict'],'identity_check':identity}
    context = prepare_manifest(manifest, anchor, scope)
    verdict = verify(receipt['packet'], anchor, scope, context)
    # A decisão é recalculada pelo checker, sem confiar num parecer salvo em disco.
    return summary(receipt, verdict)
