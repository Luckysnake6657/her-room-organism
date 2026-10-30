# 启动 native 服务（给桥接提供状态/记忆）
$root = "D:\deepseekharness\lab\dc"
Set-Location $root
python -m organism.service --data evidence\p3\cmw_native --import-dir evidence\p3\cmw_import --port 3210
