import base64
import contextlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Zorqi_Installer'))
import linux_install
import linux_setup
import macos_package
import zorqi
import updater
import windows_installer
import zorqi_gui
import zorqi_apps
import zorqi_terminal_gui


class AppTests(unittest.TestCase):
    def test_macos_app_bundle_contains_terminal_launcher_and_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'Zorqi'
            binary.write_bytes(b'self-contained executable')
            bundle = macos_package.create_app_bundle(binary, root / 'Zorqi.app')
            self.assertEqual((bundle / 'Contents/Resources/Zorqi').read_bytes(), binary.read_bytes())
            self.assertEqual((bundle / 'Contents/Info.plist').exists(), True)
            launcher = bundle / 'Contents/MacOS/Zorqi'
            self.assertIn('Terminal', launcher.read_text(encoding='utf-8'))
            if os.name != 'nt':
                self.assertTrue(launcher.stat().st_mode & 0o111)

    def test_standalone_linux_setup_installs_binary_without_python_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            payload = bundle / 'Zorqi'
            payload.write_bytes(b'self-contained executable')
            prefix = root / 'install prefix'
            with patch.object(linux_setup.sys, '_MEIPASS', str(bundle), create=True):
                launcher = linux_setup.install(prefix)
            self.assertEqual(launcher.read_bytes(), payload.read_bytes())
            if os.name != 'nt':
                self.assertTrue(launcher.stat().st_mode & 0o111)
            desktop = prefix / 'share' / 'applications' / 'zorqi.desktop'
            escaped_launcher = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
            self.assertIn(f'Exec="{escaped_launcher}"', desktop.read_text(encoding='utf-8'))

    def test_macos_app_and_commands(self):
        with tempfile.TemporaryDirectory() as directory, patch('linux_install.sys.platform', 'darwin'):
            launcher = linux_install.install(directory)
            self.assertTrue(launcher.exists())
            self.assertTrue((Path(directory) / 'Applications/Zorqi.app/Contents/MacOS/Zorqi').exists())
            self.assertEqual(zorqi.package_command('packages'), ['brew', 'list'])
            with patch('zorqi.shutil.which', return_value='/usr/bin/sw_vers'), patch('zorqi.subprocess.run') as run:
                run.return_value.returncode = 0
                zorqi.run_command(['distro'])
                run.assert_called_once_with(['sw_vers'], check=False)

    def test_startup_mode_persists(self):
        with tempfile.TemporaryDirectory() as directory, patch('updater.STATE', Path(directory)), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(updater.handle('startup-updates', ['auto']), 0)
            self.assertEqual(updater.config()['startup'], 'auto')
            with patch('updater.handle') as handle:
                updater.startup()
                handle.assert_called_once_with('update', [])
            self.assertEqual(updater.handle('startup-updates', ['bad']), 2)
            self.assertEqual(updater.config()['startup'], 'auto')

    def test_offline_update_failure_returns_status(self):
        with patch('updater.git', side_effect=OSError('offline')), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(updater.handle('update-check', []), 1)

    def test_updates_use_zorqi_shell_repository(self):
        self.assertEqual(updater.REPOSITORY, 'https://github.com/Oma100-tech/Zorqi-Shell.git')

    def test_update_uses_nested_zorqi_shell_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            def fake_git(*args, cwd=None):
                if args[0] == 'clone':
                    installer = Path(args[-1]) / 'Zorqi' / 'Zorqi-Installer' / 'linux_install.py'
                    installer.parent.mkdir(parents=True)
                    installer.touch()
                return ''

            with patch('updater.STATE', Path(directory)), patch('updater.git', side_effect=fake_git), \
                    patch('updater.subprocess.run') as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(updater.handle('update', []), 0)
            self.assertTrue(Path(run.call_args.args[0][1]).is_file())

    def test_source_installer_finds_built_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / 'Zorqi_Installer' / 'windows_installer.py'
            script.parent.mkdir()
            executable = root / 'dist' / 'Zorqi-CLI.exe'
            executable.parent.mkdir()
            executable.touch()
            with patch.object(windows_installer, '__file__', str(script)), \
                    patch.object(windows_installer.sys, 'frozen', False, create=True):
                self.assertEqual(windows_installer.payload_file('Zorqi-CLI.exe'), executable.resolve())

    def test_start_menu_shortcut_uses_app_icon(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'Zorqi-CLI.exe'
            shortcut = Path(directory) / 'Zorqi.lnk'
            with patch('windows_installer.subprocess.run') as run:
                windows_installer.create_shortcut(shortcut, executable, 'Zorqi Control Center')
            command = run.call_args.args[0]
            self.assertEqual(command[:3], ['powershell.exe', '-NoProfile', '-Command'])
            self.assertIn("$s.IconLocation='" + str(executable) + ",0'", command[3])

    def test_installer_copies_apps_and_optional_shortcuts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payloads = {}
            for name in ('Zorqi.exe', 'Zorqi-CLI.exe', 'Zorqi-Apps.exe', 'Zorqi-Setup.exe'):
                payload = root / name
                payload.touch()
                payloads[name] = payload
            target = root / 'installed'
            with patch.dict('os.environ', {'APPDATA': str(root / 'appdata'), 'USERPROFILE': str(root)}), \
                    patch('windows_installer.payload_file', side_effect=lambda name: payloads[name]), \
                    patch('windows_installer.register_uninstaller') as register, \
                    patch('windows_installer.remove_user_path') as remove_path, \
                    patch('windows_installer.subprocess.run') as run:
                windows_installer.install_app(target, start_menu=True, desktop=True,
                                              selected_apps=['terminal', 'update-center'])
            self.assertTrue((target / 'Zorqi.exe').is_file())
            self.assertTrue((target / 'Zorqi-CLI.exe').is_file())
            self.assertTrue((target / 'Zorqi-Apps.exe').is_file())
            self.assertFalse((target / 'Zorqi-Control.exe').exists())
            self.assertTrue((target / 'uninstall.exe').is_file())
            self.assertEqual(run.call_count, 3)
            self.assertTrue(any('--app update-center' in call.args[0][3] for call in run.call_args_list))
            register.assert_called_once_with(
                target.resolve(), target.resolve() / 'Zorqi.exe',
                {'terminal', 'update-center'}, True, True, False)
            remove_path.assert_called_once_with(target.resolve())

    def test_install_metadata_restores_selected_apps_and_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / 'Zorqi-CLI.exe').touch()
            winreg = types.ModuleType('winreg')
            winreg.HKEY_CURRENT_USER = object()
            winreg.OpenKey = lambda *_args: contextlib.nullcontext(object())
            values = {
                'InstallLocation': str(target),
                'SelectedApps': '["terminal", "news"]',
                'StartMenuShortcuts': 0,
                'DesktopShortcut': 1,
                'WriteToPath': 1,
            }
            winreg.QueryValueEx = lambda _key, name: (values[name], 1)
            with patch.dict(sys.modules, {'winreg': winreg}):
                info = windows_installer.installed_app_info()
            self.assertEqual(info, {
                'target': target.resolve(),
                'selected_apps': ['news', 'terminal'],
                'start_menu': False,
                'desktop': True,
                'write_path': True,
            })

    def test_uninstall_preserves_or_explicitly_removes_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'Programs' / 'Zorqi'
            target.mkdir(parents=True)
            (target / 'Zorqi-CLI.exe').touch()
            appdata = root / 'Roaming'
            localappdata = root / 'Local'
            winreg = types.ModuleType('winreg')
            winreg.HKEY_CURRENT_USER = object()
            winreg.DeleteKey = lambda *_args: None
            env = {'APPDATA': str(appdata), 'LOCALAPPDATA': str(localappdata), 'USERPROFILE': str(root)}
            for remove_data in (False, True):
                with patch.dict('os.environ', env), patch.dict(sys.modules, {'winreg': winreg}), \
                        patch('windows_installer.remove_user_path'), \
                        patch('windows_installer.subprocess.Popen', return_value=types.SimpleNamespace(pid=4321)) as popen:
                    pid = windows_installer.remove_installation(target, remove_data)
                self.assertEqual(pid, 4321)
                encoded = popen.call_args.args[0][-1]
                launcher = base64.b64decode(encoded).decode('utf-16le')
                match = re.search(r"\$encoded='([^']+)'", launcher)
                self.assertIsNotNone(match)
                cleanup = base64.b64decode(match.group(1)).decode('utf-16le')
                self.assertIn('Programs\\Zorqi\\Zorqi-CLI.exe', cleanup)
                self.assertEqual('settings.json' in cleanup, remove_data)
                self.assertEqual('zorqi-updates' in cleanup, remove_data)

    def test_terminal_command_uses_argument_list_without_shell(self):
        with patch.object(zorqi_terminal_gui.sys, 'frozen', False, create=True):
            command = zorqi_terminal_gui.command_line(['list', 'C:\\my files'])
        self.assertEqual(command[-2:], ['list', 'C:\\my files'])
        self.assertEqual(Path(command[1]), Path(zorqi_terminal_gui.__file__).with_name('zorqi.py'))

    def test_frozen_terminal_uses_bundled_cli_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = Path(directory) / 'Zorqi-CLI.exe'
            engine.touch()
            with patch.object(zorqi_terminal_gui.sys, 'frozen', True, create=True), \
                    patch.object(zorqi_terminal_gui.sys, '_MEIPASS', directory, create=True):
                self.assertEqual(zorqi_terminal_gui.command_line(['version']),
                                 [str(engine), 'version'])

    def test_terminal_change_directory_is_per_tab_path_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / 'child'
            child.mkdir()
            self.assertEqual(zorqi_terminal_gui.change_directory(root, ['child']), child.resolve())
            self.assertEqual(zorqi_terminal_gui.change_directory(root, []), Path.home())
            with self.assertRaises(NotADirectoryError):
                zorqi_terminal_gui.change_directory(root, ['missing'])

    def test_terminal_settings_preserve_other_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / 'settings.json'
            settings_path.write_text('{"theme": "vista"}', encoding='utf-8')
            with patch.object(zorqi_terminal_gui, 'SETTINGS_PATH', settings_path):
                zorqi_terminal_gui.save_settings({'terminal_opacity': 72, 'terminal_theme': 'forest'})
                self.assertEqual(zorqi_terminal_gui.settings(), {
                    'theme': 'vista', 'terminal_opacity': 72, 'terminal_theme': 'forest',
                })

    def test_path_choice_is_idempotent(self):
        location = r'C:\Tools\Zorqi'
        existing = ';'.join((r'C:\Windows', location.lower()))
        self.assertEqual(windows_installer.add_path_entry(existing, location), existing)
        self.assertEqual(windows_installer.add_path_entry(r'C:\Windows', location),
                         ';'.join((r'C:\Windows', location)))

    def test_release_installer_must_be_official_asset(self):
        asset = {
            'name': 'Zorqi-Setup.exe',
            'browser_download_url': 'https://github.com/Oma100-tech/Zorqi-Shell/releases/download/v1/Zorqi-Setup.exe',
        }
        self.assertEqual(zorqi_apps.latest_windows_installer({'assets': [asset]}), asset)
        asset['browser_download_url'] = 'https://example.com/Zorqi-Setup.exe'
        with self.assertRaises(ValueError):
            zorqi_apps.latest_windows_installer({'assets': [asset]})

    def test_release_version_comparison(self):
        self.assertGreater(zorqi_apps.version_tuple('v0.3.0'), zorqi_apps.version_tuple('0.2.0'))
        self.assertEqual(zorqi_apps.version_tuple('v0.2.0'), zorqi_apps.version_tuple('0.2.0'))

    def test_control_center_uses_installed_terminal_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'Zorqi-CLI.exe'
            executable.touch()
            with patch.object(zorqi_gui.sys, 'frozen', True, create=True), \
                    patch.object(zorqi_gui.sys, '_MEIPASS', directory, create=True):
                self.assertEqual(zorqi_gui.ZorqiControlPanel.cli_executable(), executable)

    def test_windows_setup_main_opens_wizard(self):
        with patch('windows_installer.tk.Tk') as tk_factory, \
                patch.object(windows_installer.sys, 'platform', 'win32'), \
                patch.object(windows_installer.sys, 'argv', ['windows_installer.py']), \
                patch.object(windows_installer, 'SetupWizard') as wizard:
            root = tk_factory.return_value
            self.assertEqual(windows_installer.main(), 0)
        wizard.assert_called_once_with(root)
        root.mainloop.assert_called_once()

    def test_windows_quotes(self):
        with patch('zorqi.os.name', 'nt'):
            self.assertEqual(zorqi.parse_line('read "C:\\My Files\\notes.txt"'), ['read', 'C:\\My Files\\notes.txt'])

    def test_sudo_dispatch_preserves_authentication(self):
        with patch('zorqi.shutil.which', return_value='/usr/bin/sudo'), patch('zorqi.subprocess.run') as run:
            run.return_value.returncode = 0
            zorqi.run_command(['sudo', 'apt', 'install', 'git'])
            run.assert_called_once_with(['sudo', 'apt', 'install', 'git'], check=False)
