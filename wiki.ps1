# wiki CLI 入口（PowerShell 版）。
# 用法：.\wiki.ps1 <command> [args]   或   wiki <command> [args]（若 . 在 PATH）
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\tools\wiki.py" @args
