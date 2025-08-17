@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 3] Creating x64/x86 folders... >> "%INSTALLLOG%"
mkdir "C:\Program Files\Powershell30x64" >nul 2>&1
mkdir "C:\Program Files (x86)\Powershell30x86" >nul 2>&1
echo ARCH=X64 > SYSTEM\arch.txt
echo [Phase 3] COMPLETE >> "%INSTALLLOG%"
exit
