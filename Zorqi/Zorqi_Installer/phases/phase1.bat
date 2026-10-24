@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 1] Starting setup... >> "%INSTALLLOG%"
mkdir "C:\Program Files\ent" >nul 2>&1
mkdir "C:\Program Files\ent\Powershell30Commands" >nul 2>&1
echo [Phase 1] Created core install folders >> "%INSTALLLOG%"

mkdir "C:\Program Files\ent\runtime" >nul 2>&1
echo DLL > "C:\Program Files\ent\runtime\core.dll"
echo SYS > "C:\Program Files\ent\runtime\terminal.sys"
echo [Phase 1] Added dummy runtime files >> "%INSTALLLOG%"

echo [Phase 1] COMPLETE >> "%INSTALLLOG%"
exit
