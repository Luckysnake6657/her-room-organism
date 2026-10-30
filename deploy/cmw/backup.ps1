# Daily backup: her body/notebook + bridge state
$stamp = (Get-Date).ToString('yyyyMMdd-HHmm')
$dst = "D:\deepseekharness\lab\dc\evidence\p3\backup\$stamp"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item 'D:\deepseekharness\lab\dc\evidence\p3\cmw_native' (Join-Path $dst 'cmw_native') -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item 'D:\qq-bridge\state\social-v2.json' (Join-Path $dst 'social-v2.json') -Force -ErrorAction SilentlyContinue
Write-Host "backup -> $dst"
