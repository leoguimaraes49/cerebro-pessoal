"""Verifica o trabalhador já configurado; nunca altera autorização ou código."""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from nucleo import REAL_SYSTEM, config_file

SYSTEM = REAL_SYSTEM
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def workers():
    escaped = re.escape(str(SYSTEM))
    script = f'''$ErrorActionPreference='Stop'
$items = @(Get-CimInstance Win32_Process | Where-Object {{
  $_.Name -eq 'python.exe' -and $_.CommandLine -match '(?i){escaped}.*autonomia\\.py["\\s]+serve(?:\\s|$)'
}})
@($items | ForEach-Object {{ [int]$_.ProcessId }}) | ConvertTo-Json -Compress'''
    result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        capture_output=True,text=True,timeout=20,creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError('inventário de processos indisponível')
    text = result.stdout.strip()
    if not text:
        return []
    found = json.loads(text)
    return found if isinstance(found,list) else [found]


def start(root):
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + str(os.getpid())
    state = root / 'estado'
    state.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(root / 'src'))
    with (state / ('supervisor-worker-' + stamp + '.stdout.log')).open('ab') as out, \
         (state / ('supervisor-worker-' + stamp + '.stderr.log')).open('ab') as err:
        subprocess.Popen([sys.executable,
                          str(root / 'src' / 'autonomia.py'),'serve'],cwd=root,env=env,
                         stdin=subprocess.DEVNULL,stdout=out,stderr=err,creationflags=NO_WINDOW)


def check(root,find=workers,launch=start):
    root=Path(root)
    if (root/'estado'/'implantacao.lock').exists():return 'maintenance'
    cfg_path = config_file(root, 'autonomia.json')
    config=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
    if config.get('enabled') is not True or config.get('content_access')!='permitido':return 'disabled'
    if find():return 'running'
    # Revalidar após a consulta de processos; o trabalhador também usa trava exclusiva.
    if (root/'estado'/'implantacao.lock').exists():return 'maintenance'
    updated=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
    if updated.get('enabled') is not True or updated.get('content_access')!='permitido':return 'disabled'
    launch(root)
    return 'start_requested'


if __name__=='__main__':
    check(SYSTEM)
