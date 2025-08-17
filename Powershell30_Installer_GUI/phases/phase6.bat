@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 6] Injecting custom commands... >> "%INSTALLLOG%"
echo updat /id:12345 > "C:\Program Files\ent\Powershell30Commands\updat.cmd"
echo crashkernel > "C:\Program Files\ent\Powershell30Commands\crash.cmd"
echo godmode > "C:\Program Files\ent\Powershell30Commands\godmode.cmd"
echo [Phase 6] Commands installed >> "%INSTALLLOG%"
echo [Phase 6] COMPLETE >> "%INSTALLLOG%"
exit
