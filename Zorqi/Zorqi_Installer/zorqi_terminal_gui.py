"""Tabbed graphical terminal for Zorqi."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import zorqi


SETTINGS_PATH = Path(os.environ.get('APPDATA', Path.home())) / 'Zorqi' / 'settings.json'
PALETTES = {
    'dark': {'background': '#111827', 'foreground': '#e5e7eb', 'prompt': '#67e8b5', 'accent': '#93c5fd'},
    'light': {'background': '#ffffff', 'foreground': '#172033', 'prompt': '#047857', 'accent': '#1d4ed8'},
    'midnight': {'background': '#09090b', 'foreground': '#e4e4e7', 'prompt': '#c4b5fd', 'accent': '#67e8f9'},
    'forest': {'background': '#102019', 'foreground': '#e1f2e8', 'prompt': '#86efac', 'accent': '#a7f3d0'},
}


def settings():
    try:
        value = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise ValueError('Zorqi settings must be a JSON object.')
    return value


def save_settings(changes):
    current = settings()
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps({**current, **changes}, indent=2), encoding='utf-8')


def command_line(words):
    if getattr(sys, 'frozen', False):
        executable = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)) / 'Zorqi-CLI.exe'
        if not executable.is_file():
            executable = Path(sys.executable).with_name('Zorqi-CLI.exe')
        if not executable.is_file():
            raise FileNotFoundError('The Zorqi command engine was not found beside the terminal app.')
        return [str(executable), *words]
    return [sys.executable, str(Path(__file__).with_name('zorqi.py')), *words]


def change_directory(current, arguments):
    if len(arguments) > 1:
        raise ValueError('Usage: cd [PATH]')
    destination = Path(arguments[0]).expanduser() if arguments else Path.home()
    if not destination.is_absolute():
        destination = current / destination
    destination = destination.resolve()
    if not destination.is_dir():
        raise NotADirectoryError(f'Not a directory: {destination}')
    return destination


class TerminalTab:
    def __init__(self, app, page, start_directory):
        self.app = app
        self.page = page
        self.directory = start_directory
        self.history = []
        self.history_position = 0
        self.busy = False
        self.frame = ttk.Frame(page)
        self.frame.pack(fill='both', expand=True)

        output_frame = ttk.Frame(self.frame)
        output_frame.pack(fill='both', expand=True)
        palette = app.palette
        self.output = tk.Text(
            output_frame,
            wrap='word',
            state='disabled',
            undo=False,
            padx=12,
            pady=10,
            font=('Cascadia Mono', 10),
            background=palette['background'],
            foreground=palette['foreground'],
            insertbackground=palette['foreground'],
            selectbackground=palette['accent'],
            relief='flat',
        )
        scroll = ttk.Scrollbar(output_frame, orient='vertical', command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        self.output.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        self.output.tag_configure('prompt', foreground=palette['prompt'])
        self.output.tag_configure('error', foreground='#f87171')
        self.output.tag_configure('accent', foreground=palette['accent'])

        prompt_row = ttk.Frame(self.frame, padding=(8, 6))
        prompt_row.pack(fill='x')
        self.prompt = ttk.Label(prompt_row, text=self.prompt_text(), width=34, anchor='w')
        self.prompt.pack(side='left', padx=(0, 8))
        self.entry = ttk.Entry(prompt_row)
        self.entry.pack(side='left', fill='x', expand=True)
        self.entry.bind('<Return>', self.submit)
        self.entry.bind('<Up>', self.history_up)
        self.entry.bind('<Down>', self.history_down)
        self.entry.bind('<Control-l>', self.clear)
        self.entry.focus_set()
        self.write('Zorqi Terminal ready. Type "help" for commands.\n', 'accent')
        self.write(self.prompt_text(), 'prompt')

    def prompt_text(self):
        return f'Zorqi {self.directory}>'

    def write(self, text, tag=None):
        try:
            if not self.output.winfo_exists():
                return
            self.output.configure(state='normal')
            self.output.insert('end', text, tag or ())
            self.output.see('end')
            self.output.configure(state='disabled')
        except tk.TclError:
            pass

    def submit(self, _event=None):
        if self.busy:
            return 'break'
        line = self.entry.get()
        self.entry.delete(0, 'end')
        self.write(line + '\n')
        try:
            words = zorqi.parse_line(line)
        except ValueError as exc:
            self.write(f'Invalid input: {exc}\n', 'error')
            self.write(self.prompt_text(), 'prompt')
            return 'break'
        if not words:
            self.write(self.prompt_text(), 'prompt')
            return 'break'
        self.history.append(line)
        self.history_position = len(self.history)
        name, *arguments = words
        if name in ('exit', 'quit'):
            self.app.close_tab(self)
        elif name == 'clear':
            self.output.configure(state='normal')
            self.output.delete('1.0', 'end')
            self.output.configure(state='disabled')
            self.write(self.prompt_text(), 'prompt')
        elif name == 'cd':
            try:
                self.directory = change_directory(self.directory, arguments)
                self.prompt.configure(text=self.prompt_text())
            except (OSError, ValueError) as exc:
                self.write(f'{exc}\n', 'error')
            self.write(self.prompt_text(), 'prompt')
        else:
            self.run(words)
        return 'break'

    def run(self, words):
        self.busy = True
        self.app.status.set('Running: ' + ' '.join(words))

        def worker():
            try:
                result = subprocess.run(
                    command_line(words),
                    cwd=self.directory,
                    capture_output=True,
                    text=True,
                    errors='replace',
                    timeout=120,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    check=False,
                )
                stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
                error, status = None, 'Ready' if returncode == 0 else f'Exited with code {returncode}'
            except subprocess.TimeoutExpired:
                stdout, stderr, error, status = '', '', 'Command timed out after 120 seconds.', 'Command timed out'
            except (OSError, subprocess.SubprocessError) as exc:
                stdout, stderr, error, status = '', '', str(exc), 'Command failed'
            self.app.post(self.finish, stdout, stderr, error, status)

        threading.Thread(target=worker, daemon=True).start()

    def finish(self, stdout, stderr, error, status):
        if stdout:
            self.write(stdout)
            if not stdout.endswith('\n'):
                self.write('\n')
        if stderr:
            self.write(stderr, 'error')
            if not stderr.endswith('\n'):
                self.write('\n')
        if error:
            self.write(error + '\n', 'error')
        if self.output.winfo_exists():
            self.write(self.prompt_text(), 'prompt')
        self.busy = False
        self.app.status.set(status)

    def history_up(self, _event=None):
        if self.history:
            self.history_position = max(0, self.history_position - 1)
            self.entry.delete(0, 'end')
            self.entry.insert(0, self.history[self.history_position])
        return 'break'

    def history_down(self, _event=None):
        if self.history_position < len(self.history) - 1:
            self.history_position += 1
            value = self.history[self.history_position]
        else:
            self.history_position = len(self.history)
            value = ''
        self.entry.delete(0, 'end')
        self.entry.insert(0, value)
        return 'break'

    def clear(self, _event=None):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.configure(state='disabled')
        self.write(self.prompt_text(), 'prompt')
        return 'break'


class ZorqiTerminal:
    def __init__(self, root):
        self.root = root
        root.title('Zorqi Terminal')
        root.geometry('1000x680')
        root.minsize(700, 440)
        try:
            config = settings()
        except (OSError, ValueError) as exc:
            messagebox.showerror('Settings unavailable', str(exc), parent=root)
            config = {}
        theme = config.get('terminal_theme', 'dark')
        self.palette = PALETTES.get(theme, PALETTES['dark'])
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=8, pady=(8, 0))
        self.tabs = []
        self.tab_number = 0
        self.status = tk.StringVar(value='Ready')

        controls = ttk.Frame(root, padding=8)
        controls.pack(fill='x')
        ttk.Button(controls, text='New tab  +', command=self.new_tab).pack(side='left')
        ttk.Button(controls, text='Close tab  x', command=self.close_current).pack(side='left', padx=6)
        ttk.Label(controls, text='Theme').pack(side='left', padx=(12, 4))
        self.theme = tk.StringVar(value=theme if theme in PALETTES else 'dark')
        theme_picker = ttk.Combobox(controls, textvariable=self.theme, values=tuple(PALETTES),
                                    state='readonly', width=11)
        theme_picker.pack(side='left')
        theme_picker.bind('<<ComboboxSelected>>', self.change_theme)
        ttk.Label(controls, text='Opacity').pack(side='left', padx=(12, 4))
        opacity = int(config.get('terminal_opacity', 100))
        self.opacity = tk.IntVar(value=max(45, min(100, opacity)))
        slider = ttk.Scale(controls, from_=45, to=100, variable=self.opacity, command=self.change_opacity)
        slider.pack(side='left', fill='x', expand=True, padx=4)
        slider.bind('<ButtonRelease-1>', self.save_opacity)
        self.opacity_label = ttk.Label(controls, text=f'{self.opacity.get()}%', width=5)
        self.opacity_label.pack(side='left')
        self.status_label = ttk.Label(root, textvariable=self.status, anchor='w', relief='sunken')
        self.status_label.pack(fill='x', padx=8, pady=(0, 8))

        root.bind('<Control-t>', self.new_tab_from_event)
        root.bind('<Control-w>', self.close_from_event)
        self.change_opacity()
        self.new_tab(Path.home())

    def post(self, callback, *args):
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback, *args)
        except tk.TclError:
            pass

    def new_tab(self, start_directory=None):
        self.tab_number += 1
        page = ttk.Frame(self.notebook)
        self.notebook.add(page, text=f'Terminal {self.tab_number}')
        tab = TerminalTab(self, page, Path(start_directory or Path.cwd()).resolve())
        self.tabs.append(tab)
        self.notebook.select(page)
        return tab

    def new_tab_from_event(self, _event=None):
        self.new_tab()
        return 'break'

    def close_from_event(self, _event=None):
        self.close_current()
        return 'break'

    def close_current(self):
        selected = self.notebook.select()
        tab = next((item for item in self.tabs if str(item.page) == selected), None)
        if tab:
            self.close_tab(tab)

    def close_tab(self, tab):
        if tab not in self.tabs:
            return
        if tab.busy:
            messagebox.showwarning('Command running', 'Wait for the command to finish before closing this tab.',
                                   parent=self.root)
            return
        self.notebook.forget(tab.page)
        self.tabs.remove(tab)
        if not self.tabs:
            self.new_tab()

    def change_opacity(self, _value=None):
        opacity = max(45, min(100, int(float(self.opacity.get()))))
        try:
            self.root.attributes('-alpha', opacity / 100)
            self.opacity_label.configure(text=f'{opacity}%')
        except tk.TclError:
            self.opacity.set(100)
            self.opacity_label.configure(text='100%')

    def save_opacity(self, _event=None):
        try:
            save_settings({'terminal_opacity': int(float(self.opacity.get()))})
        except (OSError, ValueError) as exc:
            messagebox.showerror('Could not save opacity', str(exc), parent=self.root)

    def change_theme(self, _event=None):
        theme = self.theme.get()
        self.palette = PALETTES[theme]
        for tab in self.tabs:
            tab.output.configure(
                background=self.palette['background'],
                foreground=self.palette['foreground'],
                insertbackground=self.palette['foreground'],
                selectbackground=self.palette['accent'],
            )
            tab.output.tag_configure('prompt', foreground=self.palette['prompt'])
            tab.output.tag_configure('accent', foreground=self.palette['accent'])
        try:
            save_settings({'terminal_theme': theme})
        except (OSError, ValueError) as exc:
            messagebox.showerror('Could not save theme', str(exc), parent=self.root)


def main():
    root = tk.Tk()
    ZorqiTerminal(root)
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
