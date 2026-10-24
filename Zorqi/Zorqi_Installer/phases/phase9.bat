
@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 8] Enabling hidden features... >> "%INSTALLLOG%"
echo glitchboot > SYSTEM\features.txt
echo fpsboost >> SYSTEM\features.txt
echo matrix >> SYSTEM\features.txt
echo [Phase 8] Features written >> "%INSTALLLOG%"
echo [Phase 8] COMPLETE >> "%INSTALLLOG%"
exit
