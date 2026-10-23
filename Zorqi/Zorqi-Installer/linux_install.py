"""Per-user terminal app installation for Linux, SteamOS, macOS and Windows."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def install(prefix=None):
    prefix = Path(prefix).expanduser().resolve() if prefix else (
        Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Zorqi'
        if sys.platform == 'win32' else Path.home() / '.local')
    data = prefix / 'share' / 'zorqi'
    data.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parent
    for name in ('zorqi.py', 'updater.py', 'linux_install.py'):
        shutil.copy2(source / name, data / name)
    revision = None
    try:
        revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=source,
                                  check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    (data / 'installation.json').write_text(json.dumps({'prefix': str(prefix), 'revision': revision}))
    binary = prefix / 'bin' / ('zorqi.cmd' if sys.platform == 'win32' else 'zorqi')
    binary.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        binary.write_text(f'@echo off\n"{sys.executable}" "{data / "zorqi.py"}" %*\n')
    else:
        binary.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' ' +
                          shlex.quote(str(data / 'zorqi.py')) + ' "$@"\n')
        binary.chmod(0o755)
    if sys.platform.startswith('linux'):
        applications = prefix / 'share' / 'applications'
        applications.mkdir(parents=True, exist_ok=True)
        escaped = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        (applications / 'zorqi.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Zorqi Terminal\n'
            f'Exec="{escaped}"\nTerminal=true\nIcon=utilities-terminal\nCategories=System;TerminalEmulator;\n')
    elif sys.platform == 'darwin':
        app = prefix / 'Applications' / 'Zorqi.app' / 'Contents'
        (app / 'MacOS').mkdir(parents=True, exist_ok=True)
        (app / 'Info.plist').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict><key>CFBundleExecutable</key><string>Zorqi</string>
<key>CFBundleIdentifier</key><string>tech.oma100.zorqi</string>
<key>CFBundleName</key><string>Zorqi</string>
<key>CFBundlePackageType</key><string>APPL</string></dict></plist>''')
        command = shlex.quote(str(binary))
        apple_string = json.dumps(command)
        script = 'tell application "Terminal"\nactivate\ndo script ' + apple_string + '\nend tell'
        entry = app / 'MacOS' / 'Zorqi'
        entry.write_text('#!/bin/sh\nexec /usr/bin/osascript -e ' + shlex.quote(script) + '\n')
        entry.chmod(0o755)
    return binary


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', help='Installation prefix')
    args = parser.parse_args()
    launcher = install(args.prefix)
    print(f'Installed: {launcher}\nRun: "{launcher}" help')
    print(f'Add {launcher.parent} to PATH for terminal access.')
