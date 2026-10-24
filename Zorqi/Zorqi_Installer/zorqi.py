"""Zorqi command launcher (independent of Microsoft PowerShell)."""
import argparse
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import json

# Argument lists deliberately avoid shell interpolation.
COMMANDS = {
    'sysinfo': ('System and kernel information', ['uname', '-a']),
    'distro': ('Linux distribution', ['cat', '/etc/os-release']),
    'hostname': ('Machine hostname', ['hostname']),
    'uptime': ('System uptime', ['uptime']),
    'cpu': ('CPU information', ['lscpu']),
    'memory': ('Memory usage', ['free', '-h']),
    'disks': ('Block devices', ['lsblk', '-f']),
    'diskusage': ('Filesystem space', ['df', '-h']),
    'folderusage': ('Folder space usage', ['du', '-sh']),
    'processes': ('Running processes', ['ps', 'aux']),
    'monitor': ('Interactive process monitor', ['top']),
    'services': ('User services', ['systemctl', '--user', 'list-units', '--type=service']),
    'logs': ('Recent user logs', ['journalctl', '--user', '-n', '100', '--no-pager']),
    'failed': ('Failed system services', ['systemctl', '--failed']),
    'battery': ('Battery and power devices', ['upower', '-d']),
    'sensors': ('Temperature sensors', ['sensors']),
    'gpu': ('PCI and GPU devices', ['lspci']),
    'usb': ('USB devices', ['lsusb']),
    'audio': ('Audio status', ['wpctl', 'status']),
    'volume': ('Default output volume', ['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']),
    'network': ('Network addresses', ['ip', '-brief', 'address']),
    'routes': ('Network routes', ['ip', 'route']),
    'connections': ('Listening TCP/UDP ports', ['ss', '-tuln']),
    'wifi': ('Available wireless networks', ['nmcli', 'device', 'wifi', 'list']),
    'netdevices': ('Network device status', ['nmcli', 'device', 'status']),
    'dns': ('DNS lookup; supply a hostname', ['getent', 'hosts']),
    'ping': ('Ping a host four times', ['ping', '-c', '4']),
    'download': ('Download a URL into the current directory', ['curl', '-fLO']),
    'list': ('List files, including hidden files', ['ls', '-lah']),
    'tree': ('Show a directory tree', ['tree']),
    'read': ('Print file contents', ['cat']),
    'head': ('First lines of a file', ['head']),
    'tail': ('Last lines of a file', ['tail']),
    'search': ('Search file contents', ['grep', '-rnI']),
    'find': ('Find files; accepts standard find arguments', ['find']),
    'mkdir': ('Create directories', ['mkdir', '-p']),
    'copy': ('Copy files with overwrite prompts', ['cp', '-i']),
    'move': ('Move files with overwrite prompts', ['mv', '-i']),
    'checksum': ('SHA-256 file checksum', ['sha256sum']),
    'archive': ('Create tar.gz: archive OUTPUT INPUT...', ['tar', '-czf']),
    'archive-list': ('List archive contents', ['tar', '-tf']),
    'flatpaks': ('Installed Flatpak applications', ['flatpak', 'list']),
    'flatpak-search': ('Search Flatpak applications', ['flatpak', 'search']),
    'flatpak-install': ('Install a Flatpak for this user', ['flatpak', '--user', 'install']),
    'flatpak-update': ('Update this user’s Flatpaks', ['flatpak', '--user', 'update']),
    'flatpak-run': ('Run a Flatpak application', ['flatpak', 'run']),
    'flatpak-info': ('Inspect a Flatpak application', ['flatpak', 'info']),
    'steam': ('Open Steam; accepts Steam launch arguments', ['steam']),
    'desktop': ('Return to SteamOS Desktop Mode', ['steamos-session-select', 'plasma']),
    'gamemode': ('Return to SteamOS Gaming Mode', ['steamos-session-select', 'gamescope']),
    'gamemode-status': ('GameMode performance service status', ['gamemoded', '-s']),
    'vulkan': ('Vulkan graphics summary', ['vulkaninfo', '--summary']),
    'glinfo': ('OpenGL graphics summary', ['glxinfo', '-B']),
    'controllers': ('Input devices and controllers', ['cat', '/proc/bus/input/devices']),
    'date': ('Current local date and time', ['date']),
    'whoami': ('Current user', ['whoami']),
}



# Native commands retain their normal prompts, sudo authentication and exit codes.
for _tool in (
    'sudo apt apt-get dnf pacman zypper apk brew winget git python3 python pip node npm '
    'ssh scp rsync curl wget tar unzip zip touch chmod chown ln less nano vim '
    'htop btop df du mount umount lsblk lsof file stat sort uniq wc diff '
    'sed awk cut tr tee which whereis env printenv id groups passwd uname '
    'systemctl journalctl flatpak snap docker podman make cmake cargo rustc '
    'go java javac dotnet pwsh bash zsh fish cmd powershell tasklist ipconfig '
    'nslookup traceroute tracepath netstat diskutil sw_vers sysctl pmset '
    'softwareupdate open launchctl screencapture defaults xcode-select'
).split():
    COMMANDS.setdefault(_tool, (f'Run native {_tool} (requires it to be installed)', [_tool]))

MAC_COMMANDS = {
    'distro': ['sw_vers'], 'cpu': ['sysctl', '-n', 'machdep.cpu.brand_string'],
    'memory': ['vm_stat'], 'disks': ['diskutil', 'list'],
    'battery': ['pmset', '-g', 'batt'], 'gpu': ['system_profiler', 'SPDisplaysDataType'],
    'usb': ['system_profiler', 'SPUSBDataType'], 'network': ['ifconfig'],
    'routes': ['netstat', '-rn'], 'connections': ['lsof', '-i', '-P', '-n'],
    'dns': ['dscacheutil', '-q', 'host', '-a', 'name'],
    'checksum': ['shasum', '-a', '256'], 'services': ['launchctl', 'list'],
    'logs': ['log', 'show', '--last', '5m', '--style', 'compact'],
    'steam': ['open', '-a', 'Steam', '--args'],
}
WINDOWS_COMMANDS = {
    'sysinfo': ['systeminfo'], 'hostname': ['hostname'], 'processes': ['tasklist'],
    'network': ['ipconfig'], 'routes': ['route', 'print'],
    'connections': ['netstat', '-ano'], 'dns': ['nslookup'],
    'ping': ['ping', '-n', '4'], 'checksum': ['certutil', '-hashfile'],
}


def parse_line(line):
    if os.name != 'nt':
        return shlex.split(line)
    # Preserve Windows backslashes while allowing quoted paths with spaces.
    lexer = shlex.shlex(line, posix=False)
    lexer.whitespace_split = True
    lexer.commenters = ''
    return [word[1:-1] if len(word) >= 2 and word[0] == word[-1] == '"' else word
            for word in lexer]


def distro_info():
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {}


def package_command(action):
    if sys.platform == 'darwin':
        return ['brew', 'search' if action == 'package-search' else 'list']
    if sys.platform == 'win32':
        return ['winget', 'search' if action == 'package-search' else 'list']
    info = distro_info()
    if info.get('ID') == 'steamos' or 'steamos' in info.get('ID_LIKE', '').split():
        return ['flatpak', 'search' if action == 'package-search' else 'list']
    for manager, search, listing in (
        ('apt', ['apt', 'search'], ['apt', 'list', '--installed']),
        ('dnf', ['dnf', 'search'], ['dnf', 'list', '--installed']),
        ('pacman', ['pacman', '-Ss'], ['pacman', '-Q']),
        ('zypper', ['zypper', 'search'], ['zypper', 'search', '--installed-only']),
        ('apk', ['apk', 'search'], ['apk', 'info']),
    ):
        if shutil.which(manager):
            return search if action == 'package-search' else listing
    return []


def run_command(words):
    if not words:
        return 0
    name, *args = words
    if name in ('update', 'update-check', 'startup-updates'):
        from updater import handle
        return handle(name, args)
    if name == 'clear':
        print('\033[2J\033[H', end='')
        return 0
    if name == 'version':
        print('Zorqi 0.2.0')
        return 0
    if name == 'help':
        print('Zorqi — Windows / macOS / Linux / SteamOS terminal\nUsage: zorqi COMMAND [ARGUMENTS]\n')
        for key, (description, _) in sorted(COMMANDS.items()):
            print(f'  {key:18} {description}')
        print('  update / update-check   Install / check GitHub updates\n'
              '  startup-updates MODE    off, check, or auto\n'
              '  clear / version         Clear screen / show version\n'
              '  packages           Installed distribution packages (Flatpaks on SteamOS)\n'
              '  package-search     Search distribution packages (Flatpaks on SteamOS)\n'
              '  steam-paths        Show existing Steam library/config directories\n'
              '  pwd / cd PATH      Show / change working directory\n'
              '  help / exit        Show commands / leave interactive mode')
        return 0
    if name == 'pwd':
        print(Path.cwd())
        return 0
    if name == 'cd':
        if len(args) > 1:
            print('Usage: cd [PATH]', file=sys.stderr)
            return 2
        try:
            os.chdir(Path(args[0]).expanduser() if args else Path.home())
            return 0
        except OSError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if name == 'steam-paths':
        for suffix in ('.steam/steam', '.local/share/Steam', '.var/app/com.valvesoftware.Steam/data/Steam'):
            path = Path.home() / suffix
            if path.exists():
                print(path)
        return 0
    if name in ('packages', 'package-search'):
        command = package_command(name)
    elif name in COMMANDS:
        overrides = MAC_COMMANDS if sys.platform == 'darwin' else WINDOWS_COMMANDS if sys.platform == 'win32' else {}
        command = overrides.get(name, COMMANDS[name][1])
    else:
        print(f'Unknown command: {name}. Run help to see commands.', file=sys.stderr)
        return 2
    if not command or not shutil.which(command[0]):
        print(f'{command[0] if command else "Package manager"} is unavailable on this system. '
              'This command requires its optional system utility.', file=sys.stderr)
        return 127
    try:
        return subprocess.run(command + args, check=False).returncode
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command:
        return run_command(args.command)
    from updater import startup
    startup()
    print('Zorqi — type help for commands, exit to leave.')
    while True:
        try:
            words = parse_line(input(f'Zorqi {Path.cwd()}> '))
            if words and words[0] in ('exit', 'quit'):
                return 0
            run_command(words)
        except ValueError as exc:
            print(f'Invalid input: {exc}', file=sys.stderr)
        except EOFError:
            return 0
        except KeyboardInterrupt:
            print()


if __name__ == '__main__':
    sys.exit(main())
