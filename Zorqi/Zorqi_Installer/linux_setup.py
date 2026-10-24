"""Install the bundled, self-contained Zorqi executable on Linux."""
import argparse
from pathlib import Path
import shutil
import sys


def install(prefix=None):
    prefix = Path(prefix).expanduser().resolve() if prefix else Path.home() / '.local'
    bundle = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    payload = bundle / 'Zorqi'
    if not payload.is_file():
        raise FileNotFoundError(f'Bundled Zorqi executable is missing: {payload}')

    binary = prefix / 'bin' / 'zorqi'
    binary.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(payload, binary)
    binary.chmod(0o755)

    applications = prefix / 'share' / 'applications'
    applications.mkdir(parents=True, exist_ok=True)
    escaped_binary = str(binary).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    (applications / 'zorqi.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Zorqi Terminal\n'
        f'Exec="{escaped_binary}"\nTerminal=true\nIcon=utilities-terminal\n'
        'Categories=System;TerminalEmulator;\n',
        encoding='utf-8',
    )
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', help='Installation prefix (default: ~/.local)')
    args = parser.parse_args()
    try:
        launcher = install(args.prefix)
    except (OSError, RuntimeError) as exc:
        print(f'Installation failed: {exc}', file=sys.stderr)
        return 1
    print(f'Installed: {launcher}')
    print(f'Run: "{launcher}" help')
    print(f'Add {launcher.parent} to PATH for terminal access.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
