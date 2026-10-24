"""Package the self-contained Zorqi command app as a drag-to-Applications DMG."""
import argparse
import plistlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def create_app_bundle(binary, destination):
    binary = Path(binary).resolve()
    destination = Path(destination)
    if not binary.is_file():
        raise FileNotFoundError(f'Zorqi executable is missing: {binary}')

    contents = destination / 'Contents'
    resources = contents / 'Resources'
    macos = contents / 'MacOS'
    resources.mkdir(parents=True, exist_ok=True)
    macos.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, resources / 'Zorqi')
    (macos / 'Zorqi').write_text(
        '#!/bin/sh\n'
        'RESOURCES="$(CDPATH= cd -- "$(dirname -- "$0")/../Resources" && pwd)"\n'
        '/usr/bin/osascript '
        '-e \'on run argv\' '
        '-e \'tell application "Terminal" to activate\' '
        '-e \'tell application "Terminal" to do script "exec " & quoted form of (item 1 of argv)\' '
        '-e \'end run\' "$RESOURCES/Zorqi"\n',
        encoding='utf-8',
    )
    (macos / 'Zorqi').chmod(0o755)
    with (contents / 'Info.plist').open('wb') as info:
        plistlib.dump({
            'CFBundleExecutable': 'Zorqi',
            'CFBundleIdentifier': 'tech.oma100.zorqi',
            'CFBundleName': 'Zorqi',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '0.2.0',
        }, info)
    return destination


def create_dmg(binary, output):
    if sys.platform != 'darwin':
        raise RuntimeError('DMG creation requires macOS.')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='zorqi-dmg-') as directory:
        staging = Path(directory)
        create_app_bundle(binary, staging / 'Zorqi.app')
        (staging / 'Applications').symlink_to('/Applications', target_is_directory=True)
        subprocess.run([
            'hdiutil', 'create', '-volname', 'Zorqi',
            '-srcfolder', str(staging), '-ov', '-format', 'UDZO', str(output),
        ], check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f'DMG was not created: {output}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, help='Path to the self-contained Zorqi executable')
    parser.add_argument('--output', required=True, help='Output DMG path')
    args = parser.parse_args()
    try:
        output = create_dmg(args.binary, args.output)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f'Mac installer build failed: {exc}', file=sys.stderr)
        return 1
    print(f'Built: {output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
