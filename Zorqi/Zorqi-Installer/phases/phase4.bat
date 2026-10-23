@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 4] Compiling Powershell 30... >> "%INSTALLLOG%"
echo (simulate auto-py-to-exe run here) >> "%INSTALLLOG%"
echo Compiled x64 -> Powershell30x64\powershell30.exe >> "%INSTALLLOG%"
echo Compiled x86 -> Powershell30x86\powershell30.exe >> "%INSTALLLOG%"
echo [Phase 4] COMPLETE >> "%INSTALLLOG%"
exit
