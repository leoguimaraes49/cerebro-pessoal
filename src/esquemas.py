"""Contratos adicionais do catálogo, sem inferir respostas ou diagnósticos."""
import math
from nucleo import Invalid,Conflict

FOLDERS={'instrument':'40_Avaliacoes/Instrumentos','assessment':'40_Avaliacoes/Aplicacoes',
         'assessment_response':'40_Avaliacoes/Respostas','assessment_score':'40_Avaliacoes/Pontuacoes',
         'search_recipe':'70_Operacao/Receitas','research_run':'70_Operacao/Pesquisas',
         'improvement_candidate':'70_Operacao/Melhorias'}
LIST_REFS=('origin_refs','source_refs','basis_refs','trigger_refs','answer_refs','opposing_refs',
    'alternative_refs','dependency_refs','resolution_refs','personal_basis_refs','external_basis_refs',
    'pattern_basis_refs','original_source_refs','validation_evidence_refs','response_refs','norms_refs',
    'verification_refs','comparison_refs','context_refs','participant_refs','topic_refs','method_refs','completion_refs','author_refs')
SINGLE_REFS=('subject_ref','object_ref','recommendation_ref','instrument_ref','assessment_ref',
             'item_ref','scoring_rule_ref','items_source_ref','instructions_source_ref',
             'translation_source_ref','attribution_resolution_ref','search_run_ref','question_ref','merged_into_ref','parent_source_ref','place_ref','decision_ref','action_ref','experience_ref','project_ref')


def references(payload):
    found=[]
    for name in LIST_REFS:
        if name in payload:
            if not isinstance(payload[name],list):raise Invalid('lista de referências inválida: '+name)
            found.extend(payload[name])
    for name in SINGLE_REFS:
        if name in payload:
            if not isinstance(payload[name],dict):raise Invalid('referência inválida: '+name)
            found.append(payload[name])
    if payload.get('review_status') in ('confirmed_by_user','disputed_by_user'):
        events=payload.get('review_events',[])
        if not isinstance(events,list) or any(not isinstance(event,dict) for event in events):
            raise Invalid('histórico de revisão inválido')
        if events and events[-1].get('source_ref'):found.append(events[-1]['source_ref'])
    return found


def derivation_refs(payload):
    # Sujeito/alvo semântico não são, isoladamente, novas evidências da afirmação.
    return [ref for name in LIST_REFS for ref in payload.get(name,[])]+[
        payload[name] for name in SINGLE_REFS if name in payload and name not in ('subject_ref','object_ref')]


def require(payload,keys):
    if any(k not in payload or payload[k] is None for k in keys):raise Invalid('campos obrigatórios ausentes')


def state(value,allowed):
    if value not in allowed:raise Invalid('estado não previsto no contrato')


def target(ref,records,kind=None):
    if not isinstance(ref,dict) or ref.get('record_id') not in records:raise Invalid('referência inexistente')
    record=records[ref['record_id']]
    if ref.get('revision')!=record['revision']:raise Conflict('referência desatualizada')
    if kind and record['record_type']!=kind:raise Invalid('família do destino incompatível')
    return record


def finite_number(value):
    if type(value) not in (int,float):return False
    try:return math.isfinite(value)
    except (OverflowError,ValueError):return False


def scoring_items(spec):
    if (not isinstance(spec,dict) or spec.get('method')!='weighted_sum'
            or not isinstance(spec.get('items'),list) or not spec['items']):
        raise Invalid('regra de pontuação não executável nesta versão')
    names=set()
    for item in spec['items']:
        if not isinstance(item,dict):raise Invalid('definição de item inválida')
        require(item,['id','min','max','dimension'])
        if (not isinstance(item['id'],str) or not item['id'] or item['id'] in names
                or not isinstance(item['dimension'],str) or not item['dimension']
                or not finite_number(item['min']) or not finite_number(item['max']) or item['min']>item['max']
                or not finite_number(item.get('weight',1))):
            raise Invalid('definição de item, faixa ou peso inválidos')
        names.add(item['id'])
    return spec['items']


def expected_scores(application,records):
    assessment=application['payload'];instrument=target(assessment['instrument_ref'],records,'instrument')
    ip=instrument['payload']
    if assessment['application_status']!='completed' or assessment['scoring_eligibility']!='calculable':
        raise Invalid('aplicação não está concluída e calculável')
    if ip.get('verification_status')!='verified_for_intended_scope':raise Invalid('instrumento não verificado para o escopo')
    items=scoring_items(ip.get('scoring_spec'))
    responses={}
    for record in records.values():
        p=record.get('payload',{})
        if record['record_type']=='assessment_response' and p.get('assessment_ref',{}).get('record_id')==application['id']:
            name=p.get('item_ref',{}).get('fragment')
            if name in responses:raise Invalid('há mais de uma resposta para o mesmo item; reconciliar')
            responses[name]=record
    scores={};used=[];seen=set()
    for item in items:
        if item['id'] in seen:raise Invalid('item repetido na regra')
        seen.add(item['id']);record=responses.get(item['id'])
        if not record:raise Invalid('resposta obrigatória ausente; resultado não é zero')
        p=record['payload'];target(p['assessment_ref'],records,'assessment');target(p['item_ref'],records,'instrument')
        if p['assessment_ref']['revision']!=application['revision']:raise Conflict('resposta depende de outra revisão da aplicação')
        if p['item_ref']['record_id']!=instrument['id']:raise Invalid('item pertence a outro instrumento')
        value=p.get('value')
        if not finite_number(value) or not item['min']<=value<=item['max']:
            raise Invalid('resposta ausente ou fora da faixa do item')
        try:
            if item.get('reverse'):value=item['max']+item['min']-value
            product=value*item.get('weight',1)
            total=scores.get(item['dimension'],0)+product
        except OverflowError as error:
            raise Invalid('overflow no cálculo da pontuação') from error
        if not all(finite_number(number) for number in (value,product,total)):
            raise Invalid('pontuação ou intermediário não finito')
        scores[item['dimension']]=total
        used.append({'record_id':record['id'],'revision':record['revision']})
    if set(responses)-seen:raise Invalid('há resposta de item não previsto')
    return scores,used,instrument


def validate(kind,p,records,current_id=None):
    if kind=='instrument':
        require(p,['instrument_name','instrument_version','purpose','constructs','language','original_source_refs',
          'target_population','age_scope','items_source_ref','instructions_source_ref','scoring_rule_ref',
          'missing_response_rule','use_conditions','administration_modes','verification_status'])
        state(p['verification_status'],('pending_verification','verified_for_intended_scope','not_suitable'))
        if not p['original_source_refs'] or not p['administration_modes']:raise Invalid('instrumento sem origem ou modalidade')
        if p['verification_status']=='verified_for_intended_scope':
            if not p.get('verification_refs') or not p.get('verification_scope'):
                raise Invalid('verificação exige evidências e escopo explícitos')
        if 'scoring_spec' in p:scoring_items(p['scoring_spec'])
    elif kind=='assessment':
        require(p,['instrument_ref','subject_ref','purpose','application_status','conditions','scoring_eligibility','eligibility_reason'])
        instrument=target(p['instrument_ref'],records,'instrument');subject=target(p['subject_ref'],records,'entity')
        if subject['payload'].get('entity_kind')!='person':raise Invalid('aplicação exige pessoa como sujeito')
        state(p['application_status'],('not_started','in_progress','interrupted','completed'))
        state(p['scoring_eligibility'],('pending_verification','calculable','not_calculable'))
        if p['scoring_eligibility']=='calculable':
            ip=instrument['payload']
            if ip.get('verification_status')!='verified_for_intended_scope':raise Invalid('instrumento ainda pendente')
            if p['conditions'].get('mode') not in ip['administration_modes']:raise Invalid('modalidade não verificada')
            if p['conditions'].get('language')!=ip['language']:raise Invalid('idioma não verificado')
    elif kind=='assessment_response':
        require(p,['assessment_ref','item_ref','source_refs'])
        if ('value' in p)==('missing_reason' in p):raise Invalid('usar resposta ou ausência explícita')
        application=target(p['assessment_ref'],records,'assessment');instrument=target(p['item_ref'],records,'instrument')
        if application['payload']['instrument_ref']['record_id']!=instrument['id']:raise Invalid('instrumento incompatível')
        if not p['source_refs'] or not isinstance(p['item_ref'].get('fragment'),str) or not p['item_ref']['fragment']:
            raise Invalid('resposta sem origem ou item')
        if 'missing_reason' in p:state(p['missing_reason'],('unknown','not_asked','not_applicable','declined'))
        for ident,record in records.items():
            other=record.get('payload',{})
            if ident!=current_id and record['record_type']=='assessment_response' and other.get('assessment_ref',{}).get('record_id')==application['id'] and other.get('item_ref',{}).get('fragment')==p['item_ref']['fragment']:
                raise Invalid('item já possui resposta; retificar o registro existente')
    elif kind=='assessment_score':
        require(p,['assessment_ref','scoring_rule_ref','response_refs','dimension_scores','computed_at','limitations','score_validity_status'])
        state(p['score_validity_status'],('current','needs_revalidation','invalid'))
        if (not isinstance(p['dimension_scores'],dict) or any(not isinstance(name,str) or not name or not finite_number(value)
                for name,value in p['dimension_scores'].items())):
            raise Invalid('pontuações exigem dimensões numéricas finitas, sem booleanos')
        application=target(p['assessment_ref'],records,'assessment')
        if any(ident!=current_id and r['record_type']=='assessment_score' and r['payload'].get('assessment_ref',{}).get('record_id')==application['id'] for ident,r in records.items()):
            raise Invalid('aplicação já possui pontuação; recalcular a mesma identidade')
        if p['score_validity_status']=='current':
            scores,used,instrument=expected_scores(application,records)
            if p['dimension_scores']!=scores or p['response_refs']!=used or p['scoring_rule_ref']!=instrument['payload']['scoring_rule_ref']:
                raise Invalid('pontuação ou bases não correspondem ao cálculo reproduzível')
        if any(k in p for k in ('diagnosis','diagnostic_probability','percentile')):raise Invalid('escore não produz diagnóstico ou percentil sem norma')
    elif kind=='search_recipe':
        require(p,['purpose','steps','basis_refs','acceptance_criteria','stop_conditions','adoption_status'])
        state(p['adoption_status'],('candidate','adopted','rejected','superseded'))
        if not p['basis_refs'] or not p['steps']:raise Invalid('receita sem origem ou percurso')
    elif kind=='research_run':
        require(p,['question','query','source_refs','limitations','research_status','searched_at'])
        state(p['research_status'],('completed','limited','no_results','unavailable'))
        if p['research_status']=='completed' and not p['source_refs']:raise Invalid('pesquisa concluída sem fontes')
    elif kind=='improvement_candidate':
        require(p,['purpose','problem','basis_refs','acceptance_criteria','comparison','adoption_status','rollback_plan'])
        state(p['adoption_status'],('candidate','tested','adopted','rejected','rolled_back'))
        if p['adoption_status'] in ('tested','adopted') and not p.get('comparison_refs'):
            raise Invalid('adoção exige resultados de comparação')
    else:raise Invalid('família sem contrato adicional')


def validate_review(p,records,current_id,*,review_authorized=False):
    status=p.get('review_status','unreviewed')
    state(status,('unreviewed','confirmed_by_user','disputed_by_user','clarification_needed'))
    previous=records.get(current_id,{}).get('payload',{})
    events=p.get('review_events',[]);history=previous.get('review_events',[])
    if not isinstance(events,list) or any(not isinstance(event,dict) for event in events):
        raise Invalid('histórico de revisão inválido')
    # Comparação canônica distingue inclusive alterações bool/int em eventos históricos.
    from nucleo import canon
    if not review_authorized:
        if canon(events)!=canon(history):raise Invalid('eventos humanos só podem ser registrados pela revisão autorizada')
        if status in ('confirmed_by_user','disputed_by_user'):
            if status!=previous.get('review_status') or canon(p)!=canon(previous):
                raise Invalid('confirmação ou divergência humana exige revisão autorizada')
        return
    if not current_id or current_id not in records or len(events)!=len(history)+1 or canon(events[:-1])!=canon(history):
        raise Invalid('revisão autorizada deve acrescentar um evento e preservar o histórico')
    controls={'review_status','review_events'}
    if canon({k:v for k,v in p.items() if k not in controls})!=canon({k:v for k,v in previous.items() if k not in controls}):
        raise Invalid('revisão humana não pode alterar o conteúdo examinado')
    event=events[-1];source=target(event.get('source_ref'),records,'source')
    if (type(event.get('reviewed_revision')) is not int or event['reviewed_revision']!=records[current_id]['revision']
            or not isinstance(event.get('scope'),str) or not event['scope'].strip()):
        raise Invalid('revisão exige alcance e versão efetivamente examinada')
    quote=event.get('quote')
    if event.get('actor')!='user' or source['payload']['source_kind'] not in ('conversation','conversation_turn') or not isinstance(quote,str) or not quote or quote not in source['payload']['content']:
        raise Invalid('confirmação ou divergência exige relato atribuível com trecho literal')


def validate_relation(p,records):
    predicate=p['predicate'];subject=target(p['subject_ref'],records)
    if predicate in ('supports','contradicts','limits_scope_of'):
        if subject['record_type'] not in ('assertion','source','assessment_score'):raise Invalid('sujeito incompatível com avaliação de evidência')
        obj=target(p.get('object_ref'),records)
        if obj['record_type'] not in ('assertion','synthesis'):raise Invalid('alvo incompatível com avaliação de evidência')
        if p['nature']!='inference' or not p.get('scope_note'):raise Invalid('avaliação de evidência exige inferência e alcance')
        return
    if subject['record_type']!='entity':raise Invalid('relação de domínio exige entidade como sujeito')
    s=subject['payload']['entity_kind']
    allowed={
      'participates_in':({'person','group','organization'},{'experience','project','study_session','trial'}),
      'member_of':({'person','group'},{'group','organization'}),
      'has_relationship_with':({'person','group'},{'person','group'}),
      'occurs_at':({'experience','action','study_session'},{'place'}),
      'occurs_during':({'experience','action','study_session'},{'life_period'}),
      'concerns_topic':({'experience','idea','project','decision','study_session'},{'learning_topic','concept','idea'}),
      'pursues_goal':({'person','project','decision','action'},{'goal'}),
      'uses_method':({'study_session','action','trial'},{'study_method','concept'}),
      'implements_decision':({'action'},{'decision'}),
      'relates_outcome_to':({'outcome'},{'action','trial','experience'}),
      'prerequisite_for':({'learning_topic'},{'learning_topic'}),
      'hypothesized_pattern':({'person','habit','experience'},None),
    }
    subjects,objects=allowed.get(predicate,({'person'},None))
    if s not in subjects:raise Invalid('subtipo do sujeito incompatível com predicado')
    if objects is not None:
        obj=target(p.get('object_ref'),records,'entity')
        if obj['payload'].get('entity_kind') not in objects:raise Invalid('subtipo do alvo incompatível com predicado')
    if predicate=='hypothesized_pattern' and (p['nature']!='inference' or not (p.get('scope_note') or p.get('limitations'))):
        raise Invalid('padrão hipotético exige natureza inferida e limites explícitos')
    if 'object_ref' in p:
        obj=target(p['object_ref'],records)
        if predicate=='reports_feeling':raise Invalid('sentimento exige valor descritivo')
        if predicate=='reports_diagnosis' and obj['record_type']!='source':raise Invalid('diagnóstico relatado exige fonte autorizada, nunca escore')
        if predicate in ('reports_value','hypothesized_pattern') and (obj['record_type']!='entity' or obj['payload'].get('entity_kind') not in ('concept','idea')):
            raise Invalid('alvo exige conceito ou ideia contextualizada')
        if predicate=='reports_difficulty' and (obj['record_type']!='entity' or obj['payload'].get('entity_kind') not in ('learning_topic','concept','idea','action','task','study_session','project')):
            raise Invalid('dificuldade exige conteúdo ou atividade pertinente')
