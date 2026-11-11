import asyncio,json,os,sys,tempfile
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from nucleo import REAL_SYSTEM,Store

async def call(s,name,args):
    r=await s.call_tool(name,args)
    if r.isError:raise AssertionError('erro da ferramenta '+name)
    return r.structuredContent if r.structuredContent is not None else json.loads(r.content[0].text)
async def main():
    env=dict(os.environ); env.pop('CEREBRO_PESSOAL_ACESSO',None)
    real=StdioServerParameters(command=sys.executable,args=[str(REAL_SYSTEM/'src'/'ponte_pessoal.py')],cwd=str(REAL_SYSTEM),env=env)
    async with stdio_client(real) as (r,w):
        async with ClientSession(r,w) as s:
            info=await s.initialize(); assert 'manual' in (info.instructions or '').lower(); names={x.name for x in (await s.list_tools()).tools}
            assert names=={'estado','ler_manual','listar_fontes','ler_fonte','registrar_fonte','retificar_fonte','consultar_operacao','excluir_fonte','registrar_conhecimento','ler_conhecimento','buscar_contexto','verificar_fluxo','executar_autotestes','processar_contribuicao','estado_executor','enfileirar_manutencao','consultar_execucao','cancelar_execucao','preparar_decisao','registrar_revisao','adotar_melhoria','cancelar_demanda','concluir_avaliacao','consultar_demanda','estado_execucao','iniciar_demanda','listar_demandas','pontuar_avaliacao','registrar_documento','responder_pendencia','reverter_melhoria'}
            assert (await call(s,'estado',{}))['content_access']=='disabled'
            assert (await call(s,'ler_manual',{'nome':'indice-manual-cerebro.md'}))['status']=='ok'
            assert (await call(s,'ler_manual',{'nome':'../Comece aqui.md'}))['status']=='denied'
            assert (await call(s,'registrar_fonte',{'operation_key':'negada','titulo':'Fictício','conteudo':'não registrar'}))['status']=='denied'
            assert (await call(s,'ler_fonte',{'record_id':'inexistente'}))['status']=='denied'
            assert (await call(s,'excluir_fonte',{'operation_key':'negada','record_id':'inexistente','revisao_esperada':1}))['status']=='denied'
            assert (await call(s,'estado_executor',{}))['status']=='denied'
            assert (await call(s,'enfileirar_manutencao',{'operation_key':'negada','tipo':'audit_vault'}))['status']=='denied'
            print('Protocolo',info.protocolVersion,'ferramentas',len(names),'bloqueio padrão confirmado')
    with tempfile.TemporaryDirectory(prefix='mcp-fixture-',dir=REAL_SYSTEM/'testes_temporarios') as d:
        root=Path(d); fixture=root/'fixture_sistema'; vault=root/'fixture_cofre'
        launcher=root/'run_test.py'; launcher.write_text('import sys\nsys.path.insert(0, '+repr(str(REAL_SYSTEM/'src'))+')\nimport ponte_pessoal as p\nfrom nucleo import Store\np.store=Store('+repr(str(fixture))+','+repr(str(vault))+')\np.server.run(transport="stdio")\n',encoding='utf-8')
        env['CEREBRO_PESSOAL_ACESSO']='permitido'
        params=StdioServerParameters(command=sys.executable,args=[str(launcher)],cwd=str(REAL_SYSTEM),env=env)
        request={'operation_key':'fonte1','titulo':'Nota fictícia','conteudo':'Estudo fictício com acentuação.'}
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w) as s:
                await s.initialize(); a=await call(s,'registrar_fonte',request); assert a['status']=='confirmed'; ident=a['id']
                assert (await call(s,'ler_fonte',{'record_id':ident}))['record']['payload']['content']==request['conteudo']
                u={'operation_key':'correcao1','record_id':ident,'revisao_esperada':1,'conteudo':'Relato corrigido fictício.','motivo':'Retificação de teste'}
                b=await call(s,'retificar_fonte',u); assert b['revision']==2
                wrong=dict(u,operation_key='antiga'); assert (await call(s,'retificar_fonte',wrong))['status']=='conflict'
                assert (await call(s,'consultar_operacao',{'operation_key':'correcao1'}))['status']=='confirmed'
        async with stdio_client(params) as (r,w):
            async with ClientSession(r,w) as s:
                await s.initialize(); assert await call(s,'registrar_fonte',request)==a; assert await call(s,'retificar_fonte',u)==b
                assert len((await call(s,'listar_fontes',{}))['records'])==1
                ent=await call(s,'registrar_conhecimento',{'operation_key':'entidade','tipo':'entity','titulo':'Pessoa fictícia','payload':{'entity_kind':'person','display_name':'Pessoa fictícia','identity_status':'identified','origin_refs':[{'record_id':ident,'revision':2}]}})
                assert ent['status']=='confirmed'
                assert (await call(s,'ler_conhecimento',{'record_id':ent['id']}))['validity']=='current_within_scope'
                assert (await call(s,'buscar_contexto',{'consulta':'corrigido'}))['mode']=='lexical_and_graph'
                assert (await call(s,'verificar_fluxo',{}))['needs_revalidation']==[]
                assert (await call(s,'estado_executor',{}))['enabled'] is False
                from autonomia import Queue,DEFAULTS,atomic_json,code_hash
                q=Queue(Store(fixture,vault));atomic_json(q.config_path,dict(DEFAULTS,enabled=True,content_access='permitido',approved_code=code_hash()))
                queued=await call(s,'enfileirar_manutencao',{'operation_key':'auditoria_fixture','tipo':'audit_vault'})
                assert queued['status']=='queued';execution_id=queued['execution']['id']
                assert (await call(s,'consultar_execucao',{'execution_id':execution_id}))['execution']['execution_status']=='queued'
                assert (await call(s,'cancelar_execucao',{'execution_id':execution_id}))['execution']['execution_status']=='cancelled'
                options=[{'descricao':'Opção A fictícia','origem':'relatada_pelo_usuario','pros':[],'contras':[],'incertezas':[]}, {'descricao':'Opção B fictícia','origem':'sugerida_pela_ia','pros':[],'contras':[],'incertezas':['Falta contexto']}]
                decision=await call(s,'preparar_decisao',{'operation_key':'decisao_fixture','titulo':'Decisão fictícia','situacao':'Comparar alternativas fictícias','opcoes':options,'fontes':[{'record_id':ident,'revision':2}],'lacunas':[]})
                assert decision['status']=='confirmed' and decision['choice']=='not_made' and not decision['external_actions']
                deleted=await call(s,'excluir_fonte',{'operation_key':'excluir1','record_id':ident,'revisao_esperada':2}); assert deleted['status']=='confirmed'
                assert (await call(s,'ler_fonte',{'record_id':ident}))['status']=='invalid'
                assert (await call(s,'registrar_fonte',request))['status']=='invalid'
                assert len((await call(s,'listar_fontes',{}))['records'])==0
        print('Cliente MCP: fixture criada, lida, retificada, conflito rejeitado, retentativa após reinício e exclusão controlada: OK')
    print('Cofre pessoal: registros controlados',len(Store().list()))
if __name__=='__main__':asyncio.run(main())
