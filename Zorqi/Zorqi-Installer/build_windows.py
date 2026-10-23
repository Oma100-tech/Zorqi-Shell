"""Build Zorqi.exe and Zorqi-Setup.exe on Windows with PyInstaller."""
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
        ['--clean', '--noconfirm', '--onefile', '--name', 'Zorqi', 'Powershell30_Installer_GUI/zorqi.py'],
        ['--clean', '--noconfirm', '--onefile', '--windowed', '--name', 'Zorqi-Setup',
         '--add-binary', 'dist/Zorqi.exe;.', 'Powershell30_Installer_GUI/windows_installer.py'],
    ]
    try:
        for arguments in commands:
            subprocess.run([sys.executable, '-m', 'PyInstaller', *arguments], cwd=root, check=True)
        for name in ('Zorqi.exe', 'Zorqi-Setup.exe'):
            artifact = root / 'dist' / name
            if not artifact.is_file() or artifact.stat().st_size == 0:
                raise RuntimeError(f'Missing build output: {artifact}')
            print(f'Built: {artifact}')
        subprocess.run([str(root / 'dist' / 'Zorqi.exe'), 'version'], cwd=root, check=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Build failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
