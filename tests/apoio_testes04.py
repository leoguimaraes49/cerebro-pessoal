"""Provedores fictícios usados somente pelos clientes de teste."""
import copy,json
from conhecimento import Knowledge,refs


def transport(url):
    return {'message':{'items':[{'DOI':'10.1234/fixture','title':['Estudo inteiramente fictício'],
           'abstract':'Fictional benchmark only, not a clinical study.','published':{'date-parts':[[2025]]}}]}}


class Model:
    def __init__(self,sources):self.sources=sources
    def call(self,prompt):
        start=prompt.rfind('\n{')
        data=json.loads(prompt[start+1:]);records=Knowledge(self.sources).catalog()[0]
        if 'Extraia apenas registros' in prompt:
            person=next(r for r in records.values() if r['record_type']=='entity' and r['payload'].get('entity_kind')=='person')
            hour='09h' if '09h' in data['text'] else '16h'
            return {'extractions':[{'tipo':'assertion','titulo':'Preferência relatada de estudo','evidence_quote':data['text'],
              'payload':{'subject_ref':{'record_id':person['id'],'revision':person['revision']},'predicate':'reports_preference',
                'value':{'type':'text','content':hour},'nature':'user_report','asserted_by':'usuária fictícia',
                'recorded_time':data['recorded_at'],'source_refs':[{'record_id':'$fonte','revision':1}],
                'context_description':'Cenário fictício','valid_time':{'precision':'unknown'},'review_status':'unreviewed'}}]}
        if 'Reavalie um registro' in prompt:
            old=data['old_record'];payload=copy.deepcopy(old['payload'])
            def update(value):
                if isinstance(value,dict):
                    if value.get('record_id') in records:value['revision']=records[value['record_id']]['revision']
                    return {k:update(v) for k,v in value.items()}
                if isinstance(value,list):return [update(v) for v in value]
                if isinstance(value,str):return value.replace('16h','09h')
                return value
            payload=update(payload)
            base=next(b for b in data['current_bases'] if b['record_type']=='source' and '09h' in b['payload'].get('content',''))
            return {'status':'proposed','payload':payload,'citations':[{'record_id':base['id'],'revision':base['revision'],'quote':'09h'}],
                    'reason':'A fonte fictícia corrigiu explicitamente o horário.'}
        if 'Determine se é possível' in prompt:
            source=next((r for r in data['records'] if r['record_type']=='source' and 'prefere estudar' in r['payload'].get('content','')),None)
            if not source:return {'decision':'ask','question':'Qual é a informação pessoal que falta?','citations':[]}
            hour='09h' if '09h' in source['payload']['content'] else '16h'
            return {'decision':'answer','answer':'A preferência relatada é '+hour+'.',
                    'citations':[{'record_id':source['id'],'revision':source['revision'],'quote':hour}]}
        if 'Avalie estes metadados' in prompt:
            return {'answer':'Documentos recuperados; não há texto integral para avaliar a eficácia.',
                    'studies':[{'doi':d['doi'],'design':'unknown','sample_size':None,'population':'unknown',
                                'supporting_quote':'','limitations':['Somente fixture de metadados']} for d in data['documents']],
                    'limitations':['Não é pesquisa clínica real.']}
        raise AssertionError('chamada não prevista pelo cenário fictício')
