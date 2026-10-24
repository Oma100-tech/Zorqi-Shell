@echo off
setlocal
set INSTALLLOG=%~dp0..\INSTALL.LOG

echo [Phase 2] Verifying setup... >> "%INSTALLLOG%"
if not exist "C:\Program Files\ent" (
    echo [Phase 2] ERROR: 'ent' folder missing >> "%INSTALLLOG%"
    exit /b 1
)

mkdir RFTERMPROFILE >nul 2>&1
mkdir SYSTEM >nul 2>&1
mkdir AUTOPY >nul 2>&1
mkdir SHORTCUTS >nul 2>&1
mkdir PAYLOAD >nul 2>&1

echo Windows Registry Editor Version 5.00 > RFTERMPROFILE\add_terminal_profile.reg
echo [HKEY_CURRENT_USER\Software\Microsoft\Windows Terminal\Profiles\List] >> RFTERMPROFILE\add_terminal_profile.reg

echo REBOOT_REQUIRED=1 > RFTERMPROFILE\reboot_flag.txt
echo INSTALL_PHASE=2_COMPLETE > SYSTEM\flags.txt
echo { "auto_py_to_exe_settings": "example" } > AUTOPY\powershell30_config.json

echo [Phase 2] COMPLETE >> "%INSTALLLOG%"
exit
