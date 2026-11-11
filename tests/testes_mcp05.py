"""Cliente MCP e CLI reais para a integração 0.5, usando somente fixture."""
import asyncio
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from nucleo import Store, REAL_SYSTEM, REAL_VAULT, config_file
from execucao import DEFAULT


def decoded(result):
    assert not result.isError, result
    return json.loads('\n'.join(item.text for item in result.content if getattr(item, 'type', None) == 'text'))


async def check():
    runtime = Path(__file__).resolve().parent.parent / 'src'
    with tempfile.TemporaryDirectory(prefix='mcp05-', dir=REAL_SYSTEM / 'testes_temporarios') as folder:
        root = Path(folder)
        sources = Store(root / 'system', root / 'vault')
        manual = sources.vault / '00_Manual'
        manual.mkdir()
        manifest = json.loads(config_file(REAL_SYSTEM, 'manual_manifest.json').read_text(encoding='utf-8'))
        for name in manifest:
            src_manual = REAL_SYSTEM / '00_Manual' / name
            (manual / name).write_bytes((src_manual if src_manual.exists() else REAL_VAULT / '00_Manual' / name).read_bytes())
        (sources.root / 'manual_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        (sources.root / 'execucao.json').write_text(json.dumps(dict(DEFAULT, enabled=True)), encoding='utf-8')
        launcher = root / 'launch.py'
        launcher.write_text(
            'import sys\nsys.path.insert(0,' + repr(str(runtime)) + ')\n'
            'import ponte_pessoal as p\nfrom nucleo import Store\n'
            'p.store=Store(' + repr(str(sources.root)) + ',' + repr(str(sources.vault)) + ')\n'
            'p.run_server()\n', encoding='utf-8')
        env = dict(os.environ, CEREBRO_PESSOAL_ACESSO='permitido', PYTHONUTF8='1')
        params = StdioServerParameters(command=sys.executable, args=[str(launcher)], env=env, cwd=str(runtime))
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                assert {'avaliar_resposta', 'consultar_comprovante'} <= tools
                state = decoded(await session.call_tool('estado', {}))
                assert state['version'] == '0.5' and state['vault'] == str(sources.vault)
                first = decoded(await session.call_tool('registrar_fonte', {'operation_key': 'first',
                    'titulo': 'Dados fictícios', 'conteudo': '{"state":"planned","values":[1,2],"edges":[["a","requires","b"]]}'}))
                second = decoded(await session.call_tool('registrar_fonte', {'operation_key': 'second',
                    'titulo': 'Dependência fictícia', 'conteudo': '{"edges":[["b","requires","c"]]}'}))
                ref = {'record_id': first['id'], 'revision': 1}
                draft = {'answer': 'Resposta natural fictícia.', 'claims': [{'id': 'c1', 'kind': 'chain',
                    'refs': [dict(ref, path='/edges/0'), {'record_id': second['id'], 'revision': 1, 'path': '/edges/0'}],
                    'value': ['a', 'requires', 'c']}], 'citations': [dict(ref, quote='planned')]}
                request = {'operation_key': 'proof', 'resposta': draft, 'contexto_ids': [first['id']], 'limite_contexto': 2}
                result = decoded(await session.call_tool('avaliar_resposta', request))
                assert result['status'] == 'claims_verified' and result['route'] == 'supplemented'
                assert result['claims_verified'] and not result['answer_verified']
                repeat = decoded(await session.call_tool('avaliar_resposta', request))
                assert repeat['receipt_id'] == result['receipt_id']
                checked = decoded(await session.call_tool('consultar_comprovante', {'receipt_id': result['receipt_id']}))
                assert checked['status'] == 'claims_verified'
                maintenance = sources.root / 'estado' / 'implantacao.lock'
                maintenance.write_text('fixture', encoding='ascii')
                blocked = decoded(await session.call_tool('avaliar_resposta', request))
                assert blocked['status'] == 'denied' and 'Atualização' in blocked['reason']
                maintenance.unlink()
                wrong = copy.deepcopy(draft)
                wrong['claims'][0] = {'id': 'c1', 'kind': 'sum',
                    'refs': [dict(ref, path='/values/0'), dict(ref, path='/values/1')], 'value': 4}
                rejected = decoded(await session.call_tool('avaliar_resposta', {'operation_key': 'wrong', 'resposta': wrong}))
                assert rejected['status'] == 'rejected'
                await session.call_tool('retificar_fonte', {'operation_key': 'correction', 'record_id': first['id'],
                    'revisao_esperada': 1, 'conteudo': '{"state":"executed","values":[2,2]}', 'motivo': 'Correção fictícia'})
                stale = decoded(await session.call_tool('consultar_comprovante', {'receipt_id': result['receipt_id']}))
                assert stale['status'] == 'stale'

        cli_launcher = root / 'cli_fixture.py'
        cli_launcher.write_text('import sys\nsys.path.insert(0,' + repr(str(runtime)) + ')\n'
            'import cli\nfrom nucleo import Store\ncli.p.store=Store(' + repr(str(sources.root)) + ',' + repr(str(sources.vault)) + ')\n'
            'cli.main()\n', encoding='utf-8')
        request_file = root / 'request.json'
        request_file.write_text(json.dumps({'operation_key': 'cli', 'resposta': {'answer': 'c1 = "executed"',
            'answer_format': 'controlled', 'claims': [{'id': 'c1', 'kind': 'field',
                'refs': [{'record_id': first['id'], 'revision': 2, 'path': '/state'}], 'value': 'executed'}], 'citations': []}}), encoding='utf-8')
        cli_result = subprocess.run([sys.executable, str(cli_launcher), 'avaliar-resposta', '--pedido', str(request_file)],
            capture_output=True, text=True, encoding='utf-8', env=env, timeout=30)
        assert cli_result.returncode == 0, cli_result.stderr
        assert json.loads(cli_result.stdout)['status'] == 'verified'

        denied_params = StdioServerParameters(command=sys.executable, args=[str(launcher)],
            env=dict(env, CEREBRO_PESSOAL_ACESSO='bloqueado'), cwd=str(runtime))
        async with stdio_client(denied_params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                denied = decoded(await session.call_tool('consultar_comprovante', {'receipt_id': result['receipt_id']}))
                assert denied['status'] == 'denied'
        return {'status': 'passed', 'version': '0.5', 'scope': 'MCP e CLI reais em fixture fictícia',
                'checks': ['tools', 'supplement', 'repeat', 'maintenance', 'wrong_sum', 'correction', 'stale', 'cli', 'access_denied'],
                'model_calls': 0}


if __name__ == '__main__':
    print(json.dumps(asyncio.run(check()), ensure_ascii=False))
