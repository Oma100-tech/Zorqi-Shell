"""Graphical control panel for Zorqi."""
from pathlib import Path
import platform
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import zorqi


class ZorqiControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title('Zorqi Control Center')
        self.root.geometry('920x640')
        self.root.minsize(760, 520)
        self.busy = False
        self.page = None

        style = ttk.Style(root)
        settings_path = Path(os.environ.get('APPDATA', Path.home())) / 'Zorqi' / 'settings.json'
        try:
            saved_theme = json.loads(settings_path.read_text(encoding='utf-8')).get('theme')
        except (OSError, ValueError):
            saved_theme = None
        if saved_theme in style.theme_names():
            style.theme_use(saved_theme)
        if 'vista' in style.theme_names():
            if saved_theme not in style.theme_names():
                style.theme_use('vista')

        shell = ttk.Frame(root, padding=16)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='ZORQI', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(shell, text='Terminal Control Center', font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 14))

        body = ttk.Frame(shell)
        body.pack(fill='both', expand=True)
        self.nav = ttk.Frame(body, width=180)
        self.nav.pack(side='left', fill='y', padx=(0, 16))
        self.content = ttk.Frame(body)
        self.content.pack(side='left', fill='both', expand=True)

        for label, page in (
            ('Zorqi Terminal', self.open_terminal),
            ('Dashboard', self.show_dashboard),
            ('Network', self.show_network),
            ('Commands', self.show_commands),
            ('Updates & Settings', self.show_settings),
            ('More Zorqi apps', self.show_apps),
        ):
            ttk.Button(self.nav, text=label, command=page).pack(fill='x', pady=4)

        self.status = tk.StringVar(value='Ready')
        ttk.Label(shell, textvariable=self.status, anchor='w', relief='sunken', padding=5).pack(fill='x', pady=(12, 0))
        self.show_dashboard()

    def show_page(self, title):
        for child in self.content.winfo_children():
            child.destroy()
        ttk.Label(self.content, text=title, font=('Segoe UI', 18, 'bold')).pack(anchor='w', pady=(0, 12))

    def output_box(self, parent=None, height=16):
        host = parent or self.content
        frame = ttk.Frame(host)
        frame.pack(fill='both', expand=True, pady=(10, 0))
        output = tk.Text(frame, wrap='word', height=height, state='disabled', font=('Consolas', 10))
        scroll = ttk.Scrollbar(frame, orient='vertical', command=output.yview)
        output.configure(yscrollcommand=scroll.set)
        output.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        return output

    def execute(self, words, output=None):
        if self.busy:
            self.status.set('A command is already running.')
            return
        if not words:
            return
        self.busy = True
        self.status.set('Running: ' + ' '.join(words))
        self.set_output(output, 'Running command...\n' if output else '')

        def worker():
            try:
                executable = self.cli_executable()
                result = subprocess.run(
                    [str(executable), *words],
                    capture_output=True,
                    text=True,
                    errors='replace',
                    timeout=120,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    check=False,
                )
                text = result.stdout
                if result.stderr:
                    text += ('\n' if text else '') + result.stderr
                if result.returncode:
                    text += f'\n[Exit code: {result.returncode}]'
                status = 'Finished' if result.returncode == 0 else f'Finished with exit code {result.returncode}'
            except subprocess.TimeoutExpired:
                text = 'Command timed out after 120 seconds.'
                status = 'Command timed out'
            except OSError as exc:
                text = f'Could not run command: {exc}'
                status = 'Command failed'
            try:
                if self.root.winfo_exists():
                    self.root.after(0, self.finish_command, output, text or '(No output)', status)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def cli_executable():
        if getattr(sys, 'frozen', False):
            bundled = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'Zorqi-CLI.exe'
            if bundled.is_file():
                return bundled
            installed = Path(sys.executable).with_name('Zorqi-CLI.exe')
            if installed.is_file():
                return installed
            raise FileNotFoundError('The Zorqi command engine was not found.')
        return Path(__file__).with_name('zorqi.py')

    def set_output(self, output, text):
        if output is None or not output.winfo_exists():
            return
        output.configure(state='normal')
        output.delete('1.0', 'end')
        output.insert('end', text)
        output.see('end')
        output.configure(state='disabled')

    def finish_command(self, output, text, status):
        self.set_output(output, text)
        self.status.set(status)
        self.busy = False

    def show_dashboard(self):
        self.show_page('System Dashboard')
        card = ttk.LabelFrame(self.content, text='This device', padding=12)
        card.pack(fill='x')
        ttk.Label(card, text=f'{platform.node()}  •  {platform.system()} {platform.release()}',
                  font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(card, text=f'Zorqi 0.2.0  •  {platform.machine()}').pack(anchor='w', pady=(4, 0))
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=12)
        output = self.output_box(height=14)
        for label, command in (
            ('System info', ['sysinfo']),
            ('Memory', ['memory']),
            ('Disk space', ['diskusage']),
            ('Processes', ['processes']),
        ):
            ttk.Button(actions, text=label, command=lambda words=command: self.execute(words, output)).pack(
                side='left', padx=(0, 8))
        self.set_output(output, 'Choose a dashboard action to inspect your system.')

    def show_network(self):
        self.show_page('Network Tools')
        actions = ttk.Frame(self.content)
        actions.pack(fill='x')
        output = self.output_box(height=16)
        for label, command in (
            ('Network adapters', ['network']),
            ('Routes', ['routes']),
            ('Connections', ['connections']),
        ):
            ttk.Button(actions, text=label, command=lambda words=command: self.execute(words, output)).pack(
                side='left', padx=(0, 8))
        lookup = ttk.Frame(self.content)
        lookup.pack(fill='x', pady=(12, 0))
        host = tk.StringVar()
        ttk.Label(lookup, text='Look up host:').pack(side='left')
        entry = ttk.Entry(lookup, textvariable=host)
        entry.pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(lookup, text='DNS lookup', command=lambda: self.execute(
            ['dns', host.get().strip()], output) if host.get().strip() else messagebox.showwarning(
                'Host required', 'Enter a host name to look up.')).pack(side='left')
        entry.bind('<Return>', lambda _event: self.execute(['dns', host.get().strip()], output) if host.get().strip() else None)
        self.set_output(output, 'Network checks use the same platform-native commands as the Zorqi terminal.')

    def show_commands(self):
        self.show_page('Run a Zorqi Command')
        ttk.Label(self.content, text='Enter a Zorqi command. Shell pipes and expansions are not evaluated.').pack(anchor='w')
        command = tk.StringVar()
        line = ttk.Frame(self.content)
        line.pack(fill='x', pady=(10, 0))
        entry = ttk.Entry(line, textvariable=command)
        entry.pack(side='left', fill='x', expand=True)
        output = self.output_box(height=18)

        def run():
            try:
                words = zorqi.parse_line(command.get())
            except ValueError as exc:
                messagebox.showerror('Invalid command', str(exc))
                return
            self.execute(words, output)

        ttk.Button(line, text='Run', command=run).pack(side='left', padx=(8, 0))
        entry.bind('<Return>', lambda _event: run())
        entry.focus_set()
        self.set_output(output, 'Try: help, sysinfo, network, or update-check')

    def show_settings(self):
        self.show_page('Updates & Settings')
        ttk.Label(self.content, text='Startup update behavior').pack(anchor='w')
        mode = tk.StringVar(value='off')
        try:
            import updater
            mode.set(updater.config().get('startup', 'off'))
        except (OSError, ValueError):
            mode.set('off')
        for value, label in (
            ('off', 'Off'),
            ('check', 'Check for updates when Zorqi starts'),
            ('auto', 'Install source updates when Zorqi starts'),
        ):
            ttk.Radiobutton(self.content, text=label, value=value, variable=mode).pack(anchor='w', pady=3)
        output = self.output_box(height=14)
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=12)
        ttk.Button(actions, text='Save preference', command=lambda: self.execute(
            ['startup-updates', mode.get()], output)).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='Check source updates', command=lambda: self.execute(['update-check'], output)).pack(
            side='left', padx=(0, 8))
        ttk.Button(actions, text='Open Update Center', command=lambda: self.open_app('update-center')).pack(
            side='left')
        self.set_output(output, 'Updates require Git and an internet connection. EXE builds use GitHub Releases.')

    def show_apps(self):
        self.show_page('Zorqi Apps')
        ttk.Label(self.content, text='Open a separate Zorqi app. Each app has its own Start Menu shortcut when '
                  'selected during setup.', wraplength=620).pack(anchor='w', pady=(0, 12))
        for title, app_id in (
            ('Zorqi Update Center', 'update-center'),
            ('Zorqi Settings', 'settings'),
            ('Zorqi News', 'news'),
            ('Zorqi IDE (Beta)', 'ide'),
            ('Zorqi GUI Modes', 'gui-modes'),
        ):
            ttk.Button(self.content, text=title, command=lambda value=app_id: self.open_app(value)).pack(
                fill='x', pady=4)

    def open_app(self, app_id):
        try:
            if getattr(sys, 'frozen', False):
                executable = Path(sys.executable).with_name('Zorqi-Apps.exe')
                command = [str(executable), '--app', app_id]
            else:
                command = [sys.executable, str(Path(__file__).with_name('zorqi_apps.py')), '--app', app_id]
            subprocess.Popen(command, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as exc:
            messagebox.showerror('Could not open app', str(exc), parent=self.root)

    def open_terminal(self):
        try:
            if getattr(sys, 'frozen', False):
                executable = Path(sys.executable).with_name('Zorqi.exe')
                command = [str(executable)]
            else:
                command = [sys.executable, str(Path(__file__).with_name('zorqi_terminal_gui.py'))]
            subprocess.Popen(command, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as exc:
            messagebox.showerror('Could not open Zorqi Terminal', str(exc), parent=self.root)


def main():
    root = tk.Tk()
    ZorqiControlPanel(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
