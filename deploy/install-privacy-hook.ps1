# 安装 pre-push 隐私检查：命中 QQ 号/本机路径/名字/密钥就阻止推送
# 用法：.\deploy\install-privacy-hook.ps1
$ErrorActionPreference = 'Stop'
$gitDir = (git rev-parse --git-dir).Trim()
$hook = Join-Path $gitDir 'hooks\pre-push'
$lines = @(
  '#!/bin/sh',
  'python deploy/privacy_scan.py . || { echo "privacy scan failed: push blocked"; exit 1; }'
)
Set-Content -Path $hook -Value ($lines -join "`n") -Encoding UTF8
Write-Host "installed: $hook"
