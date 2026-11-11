"""Registra alcance exato do que o usuário confirmou ou contestou, sem validar diagnóstico."""
import copy
from nucleo import Invalid,Conflict,NOW,sha,canon
from conhecimento import Knowledge


def register(sources,key,record_id,expected,status,source_ref,quote,scope):
    k=Knowledge(sources)
    operation=sha(canon([key,record_id,expected,status,source_ref,quote,scope]).encode())
    resumed=k._resume(operation,review_authorized=True)
    if resumed is not None:return resumed
    read=k.read(record_id)
    if not read['record'] or read['record']['record_type']!='assertion':raise Invalid('afirmação atual não encontrada')
    record=read['record']
    if record['revision']!=expected:raise Conflict('a afirmação mudou desde a revisão')
    p=copy.deepcopy(record['payload']);p['review_status']=status
    p.setdefault('review_events',[]).append({'actor':'user','reviewed_revision':expected,'source_ref':source_ref,
                                          'quote':quote,'scope':scope,'status':status,'recorded_at':NOW()})
    return k._frozen_apply(operation,'assertion',record['title'],p,record_id,expected,review_authorized=True)
