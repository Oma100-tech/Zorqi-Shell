"""Guided per-user graphical installer for Zorqi."""
import base64
import ctypes
import json
import ntpath
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = 'Zorqi'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Zorqi'
APP_OPTIONS = {
    'terminal': ('Zorqi Terminal', 'Zorqi.exe', '', True),
    'control': ('Zorqi Control Center', 'Zorqi-Control.exe', '', False),
    'update-center': ('Zorqi Update Center', 'Zorqi-Apps.exe', '--app update-center', False),
    'settings': ('Zorqi Settings', 'Zorqi-Apps.exe', '--app settings', False),
    'news': ('Zorqi News', 'Zorqi-Apps.exe', '--app news', False),
    'ide': ('Zorqi IDE (Beta)', 'Zorqi-Apps.exe', '--app ide', False),
    'gui-modes': ('Zorqi GUI Modes', 'Zorqi-Apps.exe', '--app gui-modes', False),
}
APP_DESCRIPTIONS = {
    'terminal': 'Run Zorqi commands',
    'control': 'System dashboard and network tools',
    'update-center': 'Check and install published releases',
    'settings': 'Update and appearance preferences',
    'news': 'Published release notes',
    'ide': 'Lightweight source and text editor',
    'gui-modes': 'Graphical appearance options',
}
START_MENU = Path('Microsoft') / 'Windows' / 'Start Menu' / 'Programs' / 'Zorqi'
PATH_SEPARATOR = ';'


def normalized_windows_path(path):
    return ntpath.normcase(ntpath.normpath(str(path)))


def add_path_entry(current, location):
    wanted = normalized_windows_path(location)
    existing = [entry for entry in current.split(PATH_SEPARATOR) if entry]
    if any(normalized_windows_path(entry) == wanted for entry in existing):
        return current
    return PATH_SEPARATOR.join([*existing, str(location)])


def write_user_path(location):
    import winreg
    key_path = r'Environment'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
        try:
            current, value_type = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            current, value_type = '', winreg.REG_EXPAND_SZ
        updated = add_path_entry(current, location)
        if updated != current:
            winreg.SetValueEx(key, 'Path', 0, value_type, updated)
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001A, 0, 'Environment', 2, 5000, None)


def remove_user_path(location):
    import winreg
    wanted = normalized_windows_path(location)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Environment') as key:
        try:
            current, value_type = winreg.QueryValueEx(key, 'Path')
        except FileNotFoundError:
            return
        entries = [entry for entry in current.split(PATH_SEPARATOR) if entry]
        updated_entries = [entry for entry in entries
                          if normalized_windows_path(entry) != wanted]
        if len(updated_entries) != len(entries):
            winreg.SetValueEx(key, 'Path', 0, value_type, PATH_SEPARATOR.join(updated_entries))
            ctypes.windll.user32.SendMessageTimeoutW(
                0xFFFF, 0x001A, 0, 'Environment', 2, 5000, None)


def payload_file(name):
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / name
    if bundled.is_file():
        return bundled
    if not getattr(sys, 'frozen', False):
        built = Path(__file__).resolve().parents[1] / 'dist' / name
        if built.is_file():
            return built
    raise FileNotFoundError(f'{name} is missing. Build the installer with python build_windows.py.')


def powershell_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcut(path, executable, description, arguments=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    script = ('$s=(New-Object -ComObject WScript.Shell).CreateShortcut(' + powershell_literal(path) + ');'
              '$s.TargetPath=' + powershell_literal(executable) + ';'
              '$s.WorkingDirectory=' + powershell_literal(Path(executable).parent) + ';'
              '$s.IconLocation=' + powershell_literal(str(executable) + ',0') + ';'
              '$s.Description=' + powershell_literal(description) + ';'
              '$s.Arguments=' + powershell_literal(arguments) + ';$s.Save()')
    subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], check=True)


def register_uninstaller(target, display_icon, selected_apps, start_menu, desktop, write_path):
    import winreg
    uninstall = target / 'uninstall.exe'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, 'DisplayName', 0, winreg.REG_SZ, 'Zorqi')
        winreg.SetValueEx(key, 'DisplayVersion', 0, winreg.REG_SZ, '0.2.0')
        winreg.SetValueEx(key, 'Publisher', 0, winreg.REG_SZ, 'Oma100-tech')
        winreg.SetValueEx(key, 'InstallLocation', 0, winreg.REG_SZ, str(target))
        winreg.SetValueEx(key, 'DisplayIcon', 0, winreg.REG_SZ, str(display_icon))
        winreg.SetValueEx(key, 'UninstallString', 0, winreg.REG_SZ, f'"{uninstall}" --uninstall')
        winreg.SetValueEx(key, 'SelectedApps', 0, winreg.REG_SZ, json.dumps(sorted(selected_apps)))
        winreg.SetValueEx(key, 'StartMenuShortcuts', 0, winreg.REG_DWORD, int(start_menu))
        winreg.SetValueEx(key, 'DesktopShortcut', 0, winreg.REG_DWORD, int(desktop))
        winreg.SetValueEx(key, 'WriteToPath', 0, winreg.REG_DWORD, int(write_path))


def installed_app_info():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            target = Path(winreg.QueryValueEx(key, 'InstallLocation')[0]).resolve()
            try:
                selected = json.loads(winreg.QueryValueEx(key, 'SelectedApps')[0])
            except (FileNotFoundError, ValueError, TypeError):
                selected = None
            try:
                start_menu = bool(winreg.QueryValueEx(key, 'StartMenuShortcuts')[0])
                desktop = bool(winreg.QueryValueEx(key, 'DesktopShortcut')[0])
                write_path = bool(winreg.QueryValueEx(key, 'WriteToPath')[0])
            except FileNotFoundError:
                start_menu, desktop, write_path = True, False, False
    except FileNotFoundError:
        target = (Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Programs' / 'Zorqi').resolve()
        if not (target / 'Zorqi-CLI.exe').is_file():
            return None
        selected = None
        start_menu, desktop, write_path = True, False, False

    if not (target / 'Zorqi-CLI.exe').is_file():
        return None
    if not isinstance(selected, list) or not selected or any(app not in APP_OPTIONS for app in selected):
        selected = ['terminal']
        if (target / 'Zorqi-Control.exe').is_file():
            selected.append('control')
        if (target / 'Zorqi-Apps.exe').is_file():
            selected.extend(('update-center', 'settings', 'news', 'ide', 'gui-modes'))
    selected = sorted(set(selected) | {'terminal'})
    return {
        'target': target,
        'selected_apps': selected,
        'start_menu': start_menu,
        'desktop': desktop,
        'write_path': write_path,
    }


def install_app(target, start_menu=True, desktop=False, selected_apps=None, write_path=False):
    target = Path(target).expanduser().resolve()
    selected = set(('terminal', 'control') if selected_apps is None else selected_apps)
    selected.add('terminal')
    invalid = selected - APP_OPTIONS.keys()
    if invalid:
        raise ValueError('Unknown Zorqi apps selected: ' + ', '.join(sorted(invalid)))
    setup = Path(sys.executable) if getattr(sys, 'frozen', False) else payload_file('Zorqi-Setup.exe')
    if target.exists():
        unexpected = [entry.name for entry in target.iterdir()
                      if entry.name not in (
                          'Zorqi.exe', 'Zorqi-CLI.exe', 'Zorqi-Control.exe',
                          'Zorqi-Apps.exe', 'uninstall.exe')]
        if unexpected:
            raise RuntimeError('Choose an empty folder or an existing Zorqi install folder.')
    target.mkdir(parents=True, exist_ok=True)
    selected_files = {APP_OPTIONS[app][1] for app in selected}
    shutil.copy2(payload_file('Zorqi-CLI.exe'), target / 'Zorqi-CLI.exe')
    for filename in ('Zorqi.exe', 'Zorqi-Control.exe', 'Zorqi-Apps.exe'):
        destination = target / filename
        if filename in selected_files:
            shutil.copy2(payload_file(filename), destination)
        else:
            destination.unlink(missing_ok=True)
    shutil.copy2(setup, target / 'uninstall.exe')

    start_menu_dir = Path(os.environ['APPDATA']) / START_MENU
    desktop_dir = Path(os.environ['USERPROFILE']) / 'Desktop'
    shortcuts = []
    for app_id in sorted(selected):
        name, executable, arguments, _required = APP_OPTIONS[app_id]
        shortcuts.append((f'{name}.lnk', target / executable, name, arguments))
    if start_menu:
        for shortcut_name, executable, description, arguments in shortcuts:
            create_shortcut(start_menu_dir / shortcut_name, executable, description, arguments)
        known_shortcuts = {entry[0] for entry in shortcuts}
        for app_name, *_ in APP_OPTIONS.values():
            old = start_menu_dir / f'{app_name}.lnk'
            if old.name not in known_shortcuts:
                old.unlink(missing_ok=True)
    else:
        for app_name, *_ in APP_OPTIONS.values():
            (start_menu_dir / f'{app_name}.lnk').unlink(missing_ok=True)
    if desktop:
        if 'control' in selected:
            create_shortcut(desktop_dir / 'Zorqi Control Center.lnk', target / 'Zorqi-Control.exe',
                            'Zorqi Control Center')
        elif selected - {'terminal'}:
            app = next(app for app in sorted(selected) if app != 'terminal')
            name, executable, arguments, _required = APP_OPTIONS[app]
            create_shortcut(desktop_dir / f'{name}.lnk', target / executable, name, arguments)
        else:
            create_shortcut(desktop_dir / 'Zorqi Terminal.lnk', target / 'Zorqi.exe', 'Zorqi Terminal')
    else:
        (desktop_dir / 'Zorqi Control Center.lnk').unlink(missing_ok=True)
        for app_name, *_ in APP_OPTIONS.values():
            (desktop_dir / f'{app_name}.lnk').unlink(missing_ok=True)

    icon_app = 'control' if 'control' in selected else next(iter(sorted(selected)))
    register_uninstaller(target, target / APP_OPTIONS[icon_app][1], selected, start_menu, desktop, write_path)
    if write_path:
        write_user_path(target)
    else:
        remove_user_path(target)
    return target


def remove_installation(target, remove_user_data=False):
    import winreg
    target = Path(target).resolve()
    if not (target / 'Zorqi-CLI.exe').is_file():
        raise RuntimeError('The selected folder does not contain a Zorqi installation.')
    start_menu_dir = Path(os.environ['APPDATA']) / START_MENU
    desktop_dir = Path(os.environ['USERPROFILE']) / 'Desktop'
    shortcuts = [start_menu_dir / f'{app_name}.lnk' for app_name, *_ in APP_OPTIONS.values()]
    shortcuts += [desktop_dir / f'{app_name}.lnk' for app_name, *_ in APP_OPTIONS.values()]
    for shortcut in shortcuts:
        shortcut.unlink(missing_ok=True)
    try:
        start_menu_dir.rmdir()
    except OSError:
        pass
    cleanup_commands = [
        f'Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2; '
    ]
    for filename in ('Zorqi.exe', 'Zorqi-CLI.exe', 'Zorqi-Control.exe', 'Zorqi-Apps.exe', 'uninstall.exe'):
        cleanup_commands.append(
            f'Remove-Item -LiteralPath {powershell_literal(target / filename)} -Force -ErrorAction SilentlyContinue; ')
    cleanup_commands.append(
        f'Remove-Item -LiteralPath {powershell_literal(target)} -Force -ErrorAction SilentlyContinue')
    if remove_user_data:
        settings = Path(os.environ.get('APPDATA', Path.home())) / 'Zorqi' / 'settings.json'
        update_cache = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'zorqi-updates'
        cleanup_commands.extend((
            f'; Remove-Item -LiteralPath {powershell_literal(settings)} -Force -ErrorAction SilentlyContinue',
            f'; Remove-Item -LiteralPath {powershell_literal(update_cache)} -Recurse -Force -ErrorAction SilentlyContinue',
        ))
    cleanup = ''.join(cleanup_commands)
    encoded_cleanup = base64.b64encode(cleanup.encode('utf-16le')).decode('ascii')
    launcher = (
        "$encoded=" + powershell_literal(encoded_cleanup) + ";"
        "Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-EncodedCommand',$encoded) "
        "-WindowStyle Hidden"
    )
    encoded_launcher = base64.b64encode(launcher.encode('utf-16le')).decode('ascii')
    process = subprocess.Popen(
        ['powershell.exe', '-NoProfile', '-EncodedCommand', encoded_launcher],
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        close_fds=True,
    )
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass
    remove_user_path(target)
    return process.pid


class SetupWizard:
    def __init__(self, root):
        self.root = root
        root.title('Zorqi Setup')
        root.geometry('740x700')
        root.minsize(680, 620)
        try:
            self.existing = installed_app_info()
        except (OSError, ValueError, TypeError) as exc:
            self.existing = None
            messagebox.showerror('Could not inspect existing installation', str(exc), parent=root)
        self.default_location = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'Programs' / 'Zorqi'
        initial_location = self.existing['target'] if self.existing else self.default_location
        self.location = tk.StringVar(value=str(initial_location))
        self.start_menu = tk.BooleanVar(value=self.existing['start_menu'] if self.existing else True)
        self.desktop = tk.BooleanVar(value=self.existing['desktop'] if self.existing else False)
        self.launch_after = tk.BooleanVar(value=True)
        self.write_path = tk.BooleanVar(value=self.existing['write_path'] if self.existing else False)
        selected_apps = set(self.existing['selected_apps']) if self.existing else {'terminal', 'control'}
        self.selected_apps = {app_id: tk.BooleanVar(value=app_id in selected_apps)
                              for app_id in APP_OPTIONS}
        self.remove_user_data = tk.BooleanVar(value=False)
        self.confirm_uninstall = tk.BooleanVar(value=False)
        initial_mode = 'update' if self.existing else 'install'
        if '--uninstall' in sys.argv and self.existing:
            initial_mode = 'uninstall'
        self.mode = tk.StringVar(value=initial_mode)
        self.page = 'welcome'
        self.frame = ttk.Frame(root, padding=24)
        self.frame.pack(fill='both', expand=True)
        self.show_page()

    def show_page(self):
        for child in self.frame.winfo_children():
            child.destroy()
        if self.page == 'welcome':
            self.welcome_page()
        elif self.page == 'options':
            self.options_page()
        elif self.page == 'install':
            self.install_page()
        elif self.page == 'uninstall-confirm':
            self.uninstall_confirmation_page()
        elif self.page == 'uninstall-progress':
            self.uninstall_page()
        else:
            self.finish_page()

    def heading(self, title, text):
        ttk.Label(self.frame, text=title, font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(self.frame, text=text, wraplength=550, justify='left').pack(anchor='w', pady=(12, 0))

    def buttons(self, back=None, next_text='Next', next_command=None):
        bar = ttk.Frame(self.frame)
        bar.pack(side='bottom', fill='x', pady=(20, 0))
        if back is not None:
            ttk.Button(bar, text='Back', command=back).pack(side='left')
        ttk.Button(bar, text=next_text, command=next_command).pack(side='right')

    def welcome_page(self):
        self.heading('Zorqi Setup Center', 'Install Zorqi, update or repair an existing version, or uninstall it.')
        if self.existing:
            ttk.Label(self.frame, text=f'Existing installation detected:\n{self.existing["target"]}',
                      wraplength=650, justify='left').pack(anchor='w', pady=(12, 4))
        else:
            ttk.Label(self.frame, text='No existing Zorqi installation was detected.',
                      wraplength=650).pack(anchor='w', pady=(12, 4))
        choices = (
            ('install', 'Install Zorqi'),
            ('update', 'Update my version — keep my apps and preferences'),
            ('repair', 'Repair / reinstall selected apps'),
            ('uninstall', 'Uninstall Zorqi'),
        )
        for value, label in choices:
            available = value == 'install' or self.existing is not None
            ttk.Radiobutton(self.frame, text=label, value=value, variable=self.mode,
                            state='normal' if available else 'disabled').pack(anchor='w', pady=5)
        ttk.Label(self.frame, text='No Python installation is required. Setup installs for your Windows user '
                  'and does not require administrator access.', wraplength=550, justify='left').pack(
            anchor='w', pady=(14, 0))
        self.buttons(next_text='Continue', next_command=self.next_page)

    def options_page(self):
        mode = self.mode.get()
        title = 'Update Zorqi' if mode == 'update' else 'Repair Zorqi' if mode == 'repair' else 'Choose install options'
        details = ('Selected apps and preferences are loaded from your existing installation. '
                   'Your settings and files outside the app folder are kept.')
        if mode == 'install':
            details = 'Choose which apps and shortcuts to install.'
        self.heading(title, details)
        ttk.Label(self.frame, text='Install location').pack(anchor='w', pady=(14, 5))
        row = ttk.Frame(self.frame)
        row.pack(fill='x')
        location_state = 'disabled' if mode in ('update', 'repair') else 'normal'
        ttk.Entry(row, textvariable=self.location, state=location_state).pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Browse...', command=self.browse,
                   state=location_state).pack(side='left', padx=(8, 0))
        ttk.Label(self.frame, text='Apps').pack(anchor='w', pady=(16, 4))
        for app_id, (name, _exe, _args, required) in APP_OPTIONS.items():
            suffix = ' — ' + APP_DESCRIPTIONS[app_id]
            ttk.Checkbutton(self.frame, text=name + suffix + (' (required)' if required else ''),
                            variable=self.selected_apps[app_id],
                            state='disabled' if required else 'normal').pack(anchor='w')
        ttk.Checkbutton(self.frame, text='Write to PATH? Add the Zorqi install folder to my user PATH',
                        variable=self.write_path).pack(anchor='w', pady=(8, 0))
        ttk.Checkbutton(self.frame, text='Create Start Menu shortcuts for selected apps',
                        variable=self.start_menu).pack(anchor='w', pady=(18, 0))
        ttk.Checkbutton(self.frame, text='Create a Desktop shortcut',
                        variable=self.desktop).pack(anchor='w', pady=(8, 0))
        ttk.Checkbutton(self.frame, text='Launch Zorqi after setup finishes',
                        variable=self.launch_after).pack(anchor='w', pady=(8, 0))
        self.buttons(self.previous_page, 'Continue', self.next_page)

    def install_page(self):
        mode = self.mode.get()
        verb = 'Updating' if mode == 'update' else 'Repairing' if mode == 'repair' else 'Installing'
        self.heading(f'{verb} Zorqi', 'Copying selected apps and refreshing shortcuts. Your preferences are preserved.')
        ttk.Label(self.frame, text=f'Install location:\n{self.location.get()}',
                  wraplength=550, justify='left').pack(anchor='w', pady=(24, 8))
        progress = ttk.Progressbar(self.frame, mode='indeterminate', length=520)
        progress.pack(anchor='w', pady=8)
        progress.start(12)
        self.root.update_idletasks()
        try:
            if mode in ('update', 'repair') and not self.existing:
                raise RuntimeError('No existing Zorqi installation was found. Choose Install Zorqi instead.')
            if mode in ('update', 'repair') and Path(self.location.get()).resolve() != self.existing['target']:
                raise RuntimeError('Updates and repairs must use the detected installation folder.')
            selected = [app_id for app_id, variable in self.selected_apps.items() if variable.get()]
            target = install_app(
                self.location.get(), self.start_menu.get(), self.desktop.get(), selected, self.write_path.get())
        except (OSError, RuntimeError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            progress.stop()
            messagebox.showerror(f'{verb} failed', str(exc), parent=self.root)
            self.page = 'options'
            self.show_page()
            return
        progress.stop()
        self.installed_path = target
        self.completed_action = verb
        self.page = 'finish'
        self.show_page()

    def finish_page(self):
        self.heading(f'Zorqi {self.completed_action.lower()} successfully',
                     f'Location:\n{self.installed_path}\n\n'
                     'Your selected apps and shortcuts are ready. User settings and files were preserved.')
        buttons = ttk.Frame(self.frame)
        buttons.pack(side='bottom', fill='x', pady=(20, 0))
        ttk.Button(buttons, text='Close', command=self.root.destroy).pack(side='right')
        if self.launch_after.get():
            ttk.Button(buttons, text='Launch Zorqi', command=self.launch).pack(side='right', padx=(0, 8))

    def launch(self):
        try:
            if self.selected_apps['control'].get():
                executable, arguments = self.installed_path / 'Zorqi-Control.exe', []
            else:
                app = next((app for app in self.selected_apps if app != 'terminal' and
                            self.selected_apps[app].get()), None)
                if app is None:
                    executable, arguments = self.installed_path / 'Zorqi.exe', []
                else:
                    _name, filename, arguments, _required = APP_OPTIONS[app]
                    executable = self.installed_path / filename
                    arguments = arguments.split()
            subprocess.Popen([str(executable), *arguments])
        except OSError as exc:
            messagebox.showerror('Could not launch Zorqi', str(exc), parent=self.root)

    def browse(self):
        selected = filedialog.askdirectory(
            title='Choose Zorqi install location',
            initialdir=self.location.get() or str(self.default_location.parent),
            parent=self.root,
        )
        if selected:
            self.location.set(selected)

    def next_page(self):
        if self.page == 'welcome':
            if self.mode.get() == 'uninstall':
                self.page = 'uninstall-confirm'
            else:
                self.page = 'options'
            self.show_page()
            return
        if self.page == 'options' and not self.location.get().strip():
            messagebox.showerror('Install location required', 'Choose a folder for the Zorqi installation.',
                                 parent=self.root)
            return
        if self.page == 'options':
            self.page = 'install'
        elif self.page == 'uninstall-confirm':
            if not self.confirm_uninstall.get():
                messagebox.showwarning('Please confirm', 'Check the confirmation box before uninstalling Zorqi.',
                                       parent=self.root)
                return
            self.page = 'uninstall-progress'
        self.show_page()

    def previous_page(self):
        self.page = 'welcome' if self.page in ('options', 'uninstall-confirm') else self.page
        self.show_page()

    def uninstall_confirmation_page(self):
        target = self.existing['target'] if self.existing else Path(self.location.get())
        self.heading('Uninstall Zorqi?', f'This removes the installed Zorqi apps and their shortcuts from:\n{target}')
        ttk.Label(self.frame, text='Your install folder will be removed only when it is empty after app files are '
                  'deleted. Other files in that folder are left untouched.',
                  wraplength=650, justify='left').pack(anchor='w', pady=(16, 8))
        ttk.Checkbutton(self.frame, text='Also remove Zorqi preferences and downloaded update cache',
                        variable=self.remove_user_data).pack(anchor='w', pady=8)
        ttk.Label(self.frame, text='By default, preferences and update data are kept so they can be used if you '
                  'install Zorqi again.', wraplength=650, justify='left').pack(anchor='w')
        ttk.Checkbutton(self.frame, text='I understand this will uninstall Zorqi',
                        variable=self.confirm_uninstall).pack(anchor='w', pady=(18, 8))
        self.buttons(self.previous_page, 'Uninstall', self.next_page)

    def uninstall_page(self):
        self.heading('Uninstalling Zorqi', 'Removing shortcuts and registration, then scheduling app-file cleanup.')
        progress = ttk.Progressbar(self.frame, mode='indeterminate', length=520)
        progress.pack(anchor='w', pady=(24, 12))
        progress.start(12)
        self.root.update_idletasks()
        target = self.existing['target'] if self.existing else Path(self.location.get()).resolve()
        try:
            process_id = remove_installation(target, self.remove_user_data.get())
        except (OSError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
            progress.stop()
            for child in self.frame.winfo_children():
                child.destroy()
            self.heading('Uninstall could not finish', str(exc))
            self.buttons(next_text='Close', next_command=self.root.destroy)
            return
        progress.stop()
        data_message = ('Removal of preferences and update cache was requested.'
                        if self.remove_user_data.get() else
                        'Preferences and update cache were preserved.')
        self.heading('Uninstall started',
                     f'App files are being removed from:\n{target}\n\n'
                     f'{data_message}\n\n'
                     f'If another app is open, Windows will finish deleting locked files after it closes. '
                     f'Cleanup process: {process_id}.')
        self.buttons(next_text='Close', next_command=self.root.destroy)


def main():
    if sys.platform != 'win32':
        raise RuntimeError('Run this installer on Windows.')
    root = tk.Tk()
    SetupWizard(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
