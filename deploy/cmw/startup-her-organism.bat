@echo off
netstat -ano | findstr ":3210" | findstr LISTENING >nul
if errorlevel 1 powershell -WindowStyle Hidden -Command "Start-Process -FilePath 'C:\Program Files\Python312\python.exe' -ArgumentList '-m','organism.service','--port','3210','--rerank' -WorkingDirectory 'D:\deepseekharness\lab\dc' -WindowStyle Hidden"
powershell -WindowStyle Hidden -Command "if (-not (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*monitor.ps1*' })) { Start-Process powershell -ArgumentList '-ExecutionPolicy','Bypass','-File','D:\deepseekharness\lab\dc\deploy\cmw\monitor.ps1' -WindowStyle Hidden }"
