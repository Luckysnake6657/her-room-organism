# 回滚 v2：还原 bridge.js、去掉 organism 开关、重启桥接
# 用法：$env:QQ_BRIDGE_ROOT='<你的桥接目录>'; .\rollback-v2.ps1
$ErrorActionPreference = 'Stop'
$root = $env:QQ_BRIDGE_ROOT
if (-not $root) { throw '先设置 QQ_BRIDGE_ROOT（桥接仓库目录）' }
Copy-Item (Join-Path $root 'src\bridge.js.bak-v2') (Join-Path $root 'src\bridge.js') -Force
$env:QQ_BRIDGE_ROOT = $root
node -e "const fs=require('fs');const p=process.env.QQ_BRIDGE_ROOT+'/config.json';const c=JSON.parse(fs.readFileSync(p,'utf8'));delete c.organism;fs.writeFileSync(p,JSON.stringify(c,null,2)+'\n','utf8');"
$c = Get-NetTCPConnection -LocalPort 3100 -State Listen -ErrorAction SilentlyContinue
if ($c) { Stop-Process -Id $c.OwningProcess -Force }
Start-Sleep -Seconds 8
Write-Host "rolled back; bridge restarting"
