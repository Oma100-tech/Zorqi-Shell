@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 7] Setting environment lock... >> "%INSTALLLOG%"
echo FAKEMODE=ON > SYSTEM\protection.flag
echo [Phase 7] Simulated protection mode enabled >> "%INSTALLLOG%"
echo [Phase 7] COMPLETE >> "%INSTALLLOG%"
exit
