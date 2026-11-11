"""Fontes externas mantêm natureza e localizador, sem virar relato pessoal."""
import copy
from nucleo import Invalid

KINDS={'conversation','conversation_turn','document','publication','web_page','tool_output','observation_record'}
ALLOWED={'source_kind','origin_description','availability_status','retention_conditions','reference_locator',
         'publication_title','published_time','doi','authors','accessed_at','limitations','parent_source_ref'}


def validate_metadata(metadata):
    if not isinstance(metadata,dict) or set(metadata)-ALLOWED:raise Invalid('metadados de fonte não reconhecidos')
    if metadata.get('source_kind') not in KINDS:raise Invalid('natureza de fonte inválida')
    if metadata.get('availability_status','retained') not in ('retained','reference_only','partially_available','unavailable'):
        raise Invalid('disponibilidade inválida')
    if metadata['source_kind'] in ('publication','web_page') and not metadata.get('reference_locator'):
        raise Invalid('fonte externa exige localizador')
    if metadata['source_kind']=='publication' and not metadata.get('publication_title'):raise Invalid('publicação exige título')
    if 'parent_source_ref' in metadata:
        ref=metadata['parent_source_ref']
        if (not isinstance(ref,dict) or not isinstance(ref.get('record_id'),str) or not ref['record_id'].strip()
                or type(ref.get('revision')) is not int or ref['revision']<1):
            raise Invalid('referência da fonte de origem inválida')
    return copy.deepcopy(metadata)
