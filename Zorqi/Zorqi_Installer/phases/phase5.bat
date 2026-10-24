@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 5] Adding Windows Terminal profile... >> "%INSTALLLOG%"
reg import RFTERMPROFILE\add_terminal_profile.reg >nul 2>&1
echo [Phase 5] Terminal profile registered >> "%INSTALLLOG%"
echo [Phase 5] COMPLETE >> "%INSTALLLOG%"
exit
