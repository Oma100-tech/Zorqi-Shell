@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL>LOG

echo Phase 10  Finalizing after reboot >>"INSTALLLOG%"
echo Terminal Profile Applied Registry is ready! >>"INSTALLLOG%"
echo Cleaning up... >>%INSTALLLOG%
Echo Cleaning up progress is done >>"INSTALLLOG%"
echo Powershell 30 is now Ready! >> "NSTALLLOG%"

shutdown /r /t 0
exit