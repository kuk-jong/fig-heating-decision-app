$ErrorActionPreference = "Stop"

$PythonExe = "C:\Users\kukjong\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

Set-Location $PSScriptRoot
& $PythonExe -m streamlit run app.py
