$ErrorActionPreference = 'Stop'
$runtimeDirectory = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pythonExecutable = Join-Path $runtimeDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path $pythonExecutable)) { $pythonExecutable = 'python' }
$workerScript = Join-Path $runtimeDirectory 'src\autonomia.py'
$env:PYTHONPATH = Join-Path $runtimeDirectory 'src'
$logDirectory = Join-Path $runtimeDirectory 'estado'
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$launchStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
Start-Process -FilePath $pythonExecutable -ArgumentList @(('"' + $workerScript + '"'), 'serve') -WorkingDirectory $runtimeDirectory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory ('worker-' + $launchStamp + '.stdout.log')) -RedirectStandardError (Join-Path $logDirectory ('worker-' + $launchStamp + '.stderr.log'))
