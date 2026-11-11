"""Testes em fixtures após alteração de código, sob demanda do cliente.

Pode ser acionado pelo trabalhador; não autoaprova código. O resultado
vale para o hash verificado; ausência de execução é declarada, nunca sucesso.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from nucleo import REAL_SYSTEM, NOW, Invalid,exclusive,Locked

from autonomia import CODE_FILES
FILES=CODE_FILES
SUITES=('testes.py', 'testes_conhecimento.py', 'testes_autonomia.py', 'testes_decisao.py', 'testes_esquemas.py', 'testes_recuperacao.py', 'testes_coordenador.py', 'testes_execucao.py', 'testes_runtime.py', 'testes_provedores.py','testes_mcp_vetores.py')

SUITES += ('testes_evidencias.py', 'testes_persistencia05.py', 'testes_mcp05.py')
SUITES += ('testes_recuperacao_fila.py', 'testes_melhorias_seguranca.py', 'testes_operacao_melhorias.py')
SUITES += ('testes_atribuicao.py', 'testes_continuacoes07.py')
SUITE_TIMEOUT_SECONDS=300


def fingerprint():
    h=hashlib.sha256()
    for name in FILES:
        h.update(name.encode());h.update((REAL_SYSTEM/name).read_bytes())
    return h.hexdigest()

def run_tests(force=False):
    state=REAL_SYSTEM/'estado';state.mkdir(exist_ok=True)
    lock=state/'autoteste.lock'
    try:handle=exclusive(lock,create=not lock.exists())
    except Locked:return {'status':'running','scope':'há outra execução de testes; nenhuma nova suíte iniciada'}
    with handle:return _run_tests(force)

def _run_tests(force=False):
    path=REAL_SYSTEM/'estado'/'autoteste.json'; current=fingerprint()
    if path.exists() and not force:
        report=json.loads(path.read_text(encoding='utf-8'))
        if report.get('fingerprint')==current and report.get('status')=='passed': return report
    checks=[]
    for name in SUITES:
        try:
            env=dict(os.environ,CEREBRO_AUTOTESTE='1',PYTHONPATH=str(REAL_SYSTEM/'src'))
            result=subprocess.run([sys.executable,str(REAL_SYSTEM/'tests'/name)],cwd=REAL_SYSTEM,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=SUITE_TIMEOUT_SECONDS)
            output=result.stdout+result.stderr
            count=re.search(r'Ran (\d+) tests? in ',output)
            checks.append({'suite':name,'passed':result.returncode==0,
                           'tests_run':int(count.group(1)) if count else None,'output':output[-20000:]})
        except subprocess.TimeoutExpired:
            checks.append({'suite':name,'passed':False,'output':'tempo de teste excedido ('+str(SUITE_TIMEOUT_SECONDS)+' s)'})
    report={'status':'passed' if all(x['passed'] for x in checks) else 'failed','fingerprint':current,'checked_at':NOW(),'suites':checks,'scope':'fixtures fictícias; não valida todo o manual'}
    if fingerprint()!=current: report['status']='changed_during_test'
    path.parent.mkdir(exist_ok=True)
    history=path.parent/'autotestes';history.mkdir(exist_ok=True)
    archive=history/(current[:16]+'-'+str(uuid.uuid4())+'.json')
    archive.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    temp=path.with_suffix('.tmp-'+str(uuid.uuid4()));temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)
    return report

def gate(sources):
    if sources.root != REAL_SYSTEM or os.environ.get('CEREBRO_AUTOTESTE')=='1': return
    report=run_tests()
    if report['status']!='passed':raise Invalid('autoteste não aprovado para o código atual; verificar relatório')
