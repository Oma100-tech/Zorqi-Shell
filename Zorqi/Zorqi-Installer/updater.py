"""GitHub updates using a dedicated checkout and fast-forward-only pulls."""
import json
import os
from pathlib import Path
import subprocess
import sys

REPOSITORY = 'https://github.com/Oma100-tech/PowerShell30.git'
STATE = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share')) / 'zorqi-updates'


def git(*args, cwd=None):
    return subprocess.run(['git', *args], cwd=cwd, check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60,
                          env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}).stdout.strip()


def config():
    path = STATE / 'settings.json'
    return json.loads(path.read_text()) if path.exists() else {'startup': 'off'}


def handle(name, args):
    try:
        if name == 'startup-updates':
            if len(args) != 1 or args[0] not in ('off', 'check', 'auto'):
                print('Usage: startup-updates off|check|auto')
                return 2
            STATE.mkdir(parents=True, exist_ok=True)
            (STATE / 'settings.json').write_text(json.dumps({'startup': args[0]}))
            print(f'Startup updates: {args[0]}')
            return 0
        if args:
            print(f'Usage: {name}')
            return 2
        if getattr(sys, 'frozen', False):
            print('EXE builds: download the latest installer from ' + REPOSITORY + '/releases')
            return 0
        if name == 'update-check':
            remote = git('ls-remote', REPOSITORY, 'HEAD').split()[0]
            metadata = Path(__file__).with_name('installation.json')
            installed = json.loads(metadata.read_text()).get('revision') if metadata.exists() else None
            print('Already up to date.' if installed == remote else f'GitHub revision: {remote}. Run update to install.')
            return 0
        STATE.mkdir(parents=True, exist_ok=True)
        checkout = STATE / 'checkout'
        if not checkout.exists():
            git('clone', '--depth', '1', REPOSITORY, str(checkout))
        else:
            if git('remote', 'get-url', 'origin', cwd=checkout) != REPOSITORY:
                raise RuntimeError('Update checkout has an unexpected origin.')
            if git('status', '--porcelain', cwd=checkout):
                raise RuntimeError('Update checkout has local changes; refusing to overwrite them.')
            git('pull', '--ff-only', cwd=checkout)
        installer = checkout / 'Powershell30_Installer_GUI' / 'linux_install.py'
        if not installer.is_file():
            raise RuntimeError('GitHub does not contain the new installer yet. Publish these changes first.')
        metadata = Path(__file__).with_name('installation.json')
        prefix = json.loads(metadata.read_text())['prefix'] if metadata.exists() else str(Path.home() / '.local')
        subprocess.run([sys.executable, str(installer), '--prefix', prefix], check=True)
        print('Update installed. Restart Zorqi to use it.')
        return 0
    except (OSError, ValueError, KeyError, IndexError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Update failed: {exc}', file=sys.stderr)
        return 1


def startup():
    try:
        mode = config().get('startup', 'off')
        if mode in ('check', 'auto'):
            handle('update' if mode == 'auto' else 'update-check', [])
    except (OSError, ValueError) as exc:
        print(f'Cannot read update settings: {exc}', file=sys.stderr)
