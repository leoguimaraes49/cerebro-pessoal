"""Regressão: primeira busca vetorial em processo MCP frio, com dados fictícios."""
import asyncio,json,os,sys,tempfile,time
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from nucleo import REAL_SYSTEM,REAL_VAULT,Store,config_file
from autonomia import atomic_json
from execucao import DEFAULT

async def check():
    with tempfile.TemporaryDirectory(prefix='cold-mcp-',dir=REAL_SYSTEM/'testes_temporarios') as folder:
        root=Path(folder);sources=Store(root/'sistema',root/'cofre')
        manual=sources.vault/'00_Manual';manual.mkdir()
        manifest=json.loads(config_file(REAL_SYSTEM,'manual_manifest.json').read_text(encoding='utf-8'))
        for name in manifest:
            src_manual=REAL_SYSTEM/'00_Manual'/name
            (manual/name).write_bytes((src_manual if src_manual.exists() else REAL_VAULT/'00_Manual'/name).read_bytes())
        atomic_json(sources.root/'manual_manifest.json',manifest)
        model=Path(os.environ.get('EMC_EMBEDDINGS_DIR',str(REAL_SYSTEM/'modelos'/'e5-multilingual-small')))
        assert (model/'model.onnx').exists(),'Recursos vetoriais validados precisam estar instalados'
        cfg=dict(DEFAULT,enabled=True,embeddings={'enabled':True,'folder':str(model)})
        atomic_json(sources.root/'execucao.json',cfg)
        original=sources.apply('original','create',title='Dado inteiramente fictício',text='A palavra de controle da fixture é maracujá.')
        launcher=root/'launch.py'
        launcher.write_text('import sys\nsys.path.insert(0,'+repr(str(REAL_SYSTEM/'src'))+')\nimport ponte_pessoal as p\nfrom nucleo import Store\np.store=Store('+repr(str(sources.root))+','+repr(str(sources.vault))+')\np.run_server()\n',encoding='utf-8')
        env=dict(os.environ,CEREBRO_PESSOAL_ACESSO='permitido',PYTHONUTF8='1')
        params=StdioServerParameters(command=sys.executable,args=[str(launcher)],cwd=str(REAL_SYSTEM),env=env)
        start=time.monotonic()
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                async def query():
                    response=await session.call_tool('buscar_contexto',{'consulta':'palavra de controle maracujá'})
                    assert not response.isError
                    return json.loads('\n'.join(c.text for c in response.content if getattr(c,'type',None)=='text'))
                first=await asyncio.wait_for(query(),30)
                assert original['id'] in {r['id'] for r in first['results']},first
                second=await asyncio.wait_for(query(),15);assert second['cache_reused']
        return {'status':'passed','scope':'MCP frio + ONNX real, fixture fictícia','cache_reused':True,
                'elapsed_seconds':round(time.monotonic()-start,3),'model_calls':0}

if __name__=='__main__':print(json.dumps(asyncio.run(check()),ensure_ascii=False))
