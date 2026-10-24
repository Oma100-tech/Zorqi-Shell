import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'Zorqi_Installer'
sys.path.insert(0, str(SOURCE))
import linux_install
import zorqi


class LinuxTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux launcher integration')
    def test_install_and_launch_from_other_directory(self):
        with tempfile.TemporaryDirectory(prefix='ps30 space ') as directory:
            launcher = linux_install.install(Path(directory) / 'custom prefix')
            result = subprocess.run([str(launcher), 'help'], cwd='/tmp', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('steam-paths', result.stdout)

    def test_arguments_are_passed_literally_and_status_preserved(self):
        with patch('zorqi.shutil.which', return_value='/usr/bin/cat'), patch('zorqi.subprocess.run') as run:
            run.return_value.returncode = 7
            self.assertEqual(zorqi.run_command(['read', 'a b;$(example)']), 7)
            run.assert_called_once_with(['cat', 'a b;$(example)'], check=False)

    def test_missing_utility(self):
        with patch('zorqi.shutil.which', return_value=None), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(zorqi.run_command(['vulkan']), 127)
            self.assertEqual(zorqi.run_command(['unknown-command']), 2)

    def test_steamos_uses_flatpak(self):
        with patch('zorqi.sys.platform', 'linux'), patch('zorqi.distro_info', return_value={'ID': 'steamos'}):
            self.assertEqual(zorqi.package_command('packages'), ['flatpak', 'list'])
            self.assertEqual(zorqi.package_command('package-search'), ['flatpak', 'search'])

    def test_package_manager_detection(self):
        with patch('zorqi.sys.platform', 'linux'), patch('zorqi.distro_info', return_value={'ID': 'arch'}), patch('zorqi.shutil.which', side_effect=lambda name: name == 'pacman'):
            self.assertEqual(zorqi.package_command('package-search'), ['pacman', '-Ss'])

    def test_import_installer_without_opening_gui(self):
        spec = importlib.util.spec_from_file_location('installer_setup', SOURCE / 'setup.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.install))


if __name__ == '__main__':
    unittest.main()
