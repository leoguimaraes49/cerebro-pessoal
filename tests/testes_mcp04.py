"""Percurso novo por MCP real com modelo e pesquisa fictícios explicitamente identificados."""
import asyncio,copy,json,os,sys,tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from nucleo import REAL_SYSTEM,REAL_VAULT,config_file
from autonomia import DEFAULTS,atomic_json,code_hash
from execucao import DEFAULT


async def call(session,name,args):
    result=await session.call_tool(name,args)
    if result.isError:raise AssertionError('erro MCP: '+name)
    data=result.structuredContent if result.structuredContent is not None else json.loads(result.content[0].text)
    if data.get('status') in ('invalid','conflict','denied'):raise AssertionError(name+': '+str(data))
    return data


async def main():
    with tempfile.TemporaryDirectory(prefix='mcp04-',dir=REAL_SYSTEM/'testes_temporarios') as tmp:
        root=Path(tmp);system=root/'sistema';vault=root/'cofre';system.mkdir();vault.mkdir()
        manual=vault/'00_Manual';manual.mkdir();manifest=json.loads(config_file(REAL_SYSTEM,'manual_manifest.json').read_text(encoding='utf-8'))
        for name in manifest:
            src_manual=REAL_SYSTEM/'00_Manual'/name
            (manual/name).write_bytes((src_manual if src_manual.exists() else REAL_VAULT/'00_Manual'/name).read_bytes())
        atomic_json(system/'manual_manifest.json',manifest)
        cfg=copy.deepcopy(DEFAULT);cfg.update(enabled=True,auto_adopt_config=True,message_codec='pretty',max_model_calls=5)
        atomic_json(system/'execucao.json',cfg)
        atomic_json(system/'autonomia.json',dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash()))
        launcher=root/'server.py'
        launcher.write_text('import sys\nfrom unittest.mock import patch\nsys.path.insert(0,'+repr(str(REAL_SYSTEM/'src'))+')\nsys.path.insert(1,'+repr(str(REAL_SYSTEM/'tests'))+')\n'
            'import nucleo\noriginal=nucleo.Store.__init__\n'
            'def init(self,root='+repr(str(system))+',vault='+repr(str(vault))+'):\n original(self,root,vault)\n'
            'with patch.object(nucleo.Store,"__init__",init):\n import ponte_pessoal as p\n'
            'import execucao\nfrom apoio_testes04 import Model,transport\n'
            'real=execucao.Engine.__init__\n'
            'def engine(self,sources,*args,**kwargs):\n kwargs["model_factory"]=lambda root:Model(sources)\n kwargs["transport"]=transport\n real(self,sources,*args,**kwargs)\n'
            'execucao.Engine.__init__=engine\np.server.run(transport="stdio")\n',encoding='utf-8')
        env=dict(os.environ,CEREBRO_PESSOAL_ACESSO='permitido',PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
        params=StdioServerParameters(command=sys.executable,args=[str(launcher)],cwd=str(REAL_SYSTEM),env=env)
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w) as session:
                await session.initialize()
                state=await call(session,'estado',{});assert state['version']=='0.4' and state['vault']==str(vault)
                source=await call(session,'registrar_fonte',{'operation_key':'identity','titulo':'Identidade fictícia','conteudo':'Lara é uma pessoa fictícia.'})
                entity=await call(session,'registrar_conhecimento',{'operation_key':'person','tipo':'entity','titulo':'Lara fictícia',
                    'payload':{'entity_kind':'person','display_name':'Lara','origin_refs':[{'record_id':source['id'],'revision':1}],'identity_status':'identified'}})
                contribution=await call(session,'iniciar_demanda',{'operation_key':'contribution','tipo':'contribution',
                    'entrada':{'text':'Lara prefere estudar às 16h.','title':'Rotina fictícia'},'executar_agora':True})
                assert contribution['status']=='completed',json.dumps(contribution,ensure_ascii=False)
                sources=await call(session,'listar_fontes',{});routine=next(s for s in sources['records'] if s['title']=='Rotina fictícia')
                query=await call(session,'iniciar_demanda',{'operation_key':'question-before','tipo':'question','entrada':{'query':'Quando Lara prefere estudar?'},'executar_agora':True})
                assert query['status']=='completed' and '16h' in query['steps'][-1]['result']
                correction=await call(session,'iniciar_demanda',{'operation_key':'correction','tipo':'correction',
                    'entrada':{'record_id':routine['id'],'expected_revision':1,'text':'Lara prefere estudar às 09h.','reason':'Correção fictícia'},'executar_agora':True})
                assert correction['status']=='completed'
                identity=contribution['execution_id']
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w) as session:
                await session.initialize()
                resumed=await call(session,'consultar_demanda',{'execution_id':identity});assert resumed['demand']['status']=='completed'
                query=await call(session,'iniciar_demanda',{'operation_key':'question-after','tipo':'question','entrada':{'query':'Quando Lara prefere estudar?'},'executar_agora':True})
                assert '09h' in query['steps'][-1]['result'] and query['status']=='completed'
                external=await call(session,'iniciar_demanda',{'operation_key':'research','tipo':'research','entrada':{'research_terms':['learning']},'executar_agora':True})
                assert external['status']=='completed' and 'limited' in external['steps'][-1]['result'],json.dumps(external,ensure_ascii=False)
                experiment=await call(session,'iniciar_demanda',{'operation_key':'candidate','tipo':'improvement',
                    'entrada':{'candidate':{'kind':'message_codec','value':'compact','reason':'Comparação fictícia'}},'executar_agora':True})
                assert experiment['status']=='completed'
                candidate=json.loads(experiment['steps'][-1]['result'])['candidate_record']['id']
                assert (await call(session,'adotar_melhoria',{'operation_key':'adopt','candidate_id':candidate}))['status']=='adopted'
                assert (await call(session,'reverter_melhoria',{'operation_key':'adopt'}))['status']=='rolled_back'
                assert (await call(session,'verificar_fluxo',{}))['issues']==[]
                assert (await call(session,'listar_demandas',{}))['demands']
        print(json.dumps({'status':'passed','scope':'MCP real, dados fictícios, modelo e pesquisa simulados',
            'checked':['retomada','extração','origem','correção','revisão semântica','resposta atualizada','pesquisa delimitada','adoção/reversão'],
            'paid_api_calls':0,'real_model_calls':0},ensure_ascii=False))


if __name__=='__main__':asyncio.run(main())
