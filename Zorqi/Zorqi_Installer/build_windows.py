"""Build the Zorqi terminal, command engine, control center, and installer."""
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != 'win32':
        print('Build requires Windows with Python. Run this script on Windows or use the GitHub Actions workflow.', file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    try:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--version'], check=True)
    except subprocess.CalledProcessError:
        print('Install the build dependency: python -m pip install pyinstaller', file=sys.stderr)
        return 1
    commands = [
        ['--clean', '--noconfirm', '--onefile', '--name', 'Zorqi-CLI',
         '--icon', 'Zorqi_Installer/zorqi.ico', 'Zorqi_Installer/zorqi.py'],
        ['--clean', '--noconfirm', '--onefile', '--windowed', '--name', 'Zorqi',
         '--icon', 'Zorqi_Installer/zorqi.ico', '--add-binary', 'dist/Zorqi-CLI.exe;.',
         'Zorqi_Installer/zorqi_terminal_gui.py'],
        ['--clean', '--noconfirm', '--onefile', '--windowed', '--name', 'Zorqi-Control',
         '--icon', 'Zorqi_Installer/zorqi.ico', '--add-binary', 'dist/Zorqi-CLI.exe;.',
         'Zorqi_Installer/zorqi_gui.py'],
        ['--clean', '--noconfirm', '--onefile', '--windowed', '--name', 'Zorqi-Apps',
         '--icon', 'Zorqi_Installer/zorqi.ico', '--add-binary', 'dist/Zorqi-CLI.exe;.',
         'Zorqi_Installer/zorqi_apps.py'],
        ['--clean', '--noconfirm', '--onefile', '--windowed', '--name', 'Zorqi-Setup',
         '--icon', 'Zorqi_Installer/zorqi.ico',
         '--add-binary', 'dist/Zorqi-CLI.exe;.',
         '--add-binary', 'dist/Zorqi.exe;.',
         '--add-binary', 'dist/Zorqi-Control.exe;.',
         '--add-binary', 'dist/Zorqi-Apps.exe;.',
         'Zorqi_Installer/windows_installer.py'],
    ]
    try:
        for arguments in commands:
            subprocess.run([sys.executable, '-m', 'PyInstaller', *arguments], cwd=root, check=True)
        for name in (
            'Zorqi-CLI.exe', 'Zorqi.exe', 'Zorqi-Control.exe', 'Zorqi-Apps.exe', 'Zorqi-Setup.exe',
        ):
            artifact = root / 'dist' / name
            if not artifact.is_file() or artifact.stat().st_size == 0:
                raise RuntimeError(f'Missing build output: {artifact}')
            print(f'Built: {artifact}')
        subprocess.run([str(root / 'dist' / 'Zorqi-CLI.exe'), 'version'], cwd=root, check=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Build failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
