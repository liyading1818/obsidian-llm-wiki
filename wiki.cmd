@echo off
rem wiki CLI 入口（cmd / PowerShell 都能用）。
rem 用法：wiki <command> [args]
python "%~dp0tools\wiki.py" %*
