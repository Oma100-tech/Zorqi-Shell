"""Optional graphical apps bundled with Zorqi."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser

import zorqi_gui


RELEASES_API = 'https://api.github.com/repos/Oma100-tech/Zorqi-Shell/releases'
LATEST_RELEASE_API = RELEASES_API + '/latest'
CURRENT_VERSION = '0.2.0'
USER_SETTINGS = Path(os.environ.get('APPDATA', Path.home())) / 'Zorqi' / 'settings.json'


def load_settings():
    if not USER_SETTINGS.is_file():
        return {}
    value = json.loads(USER_SETTINGS.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Zorqi settings must be a JSON object.')
    return value


def save_settings(values):
    USER_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    USER_SETTINGS.write_text(json.dumps(values, indent=2), encoding='utf-8')


def github_json(url):
    request = Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Zorqi-Update-Center',
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def latest_windows_installer(release):
    for asset in release.get('assets', []):
        if asset.get('name', '').lower() == 'zorqi-setup.exe':
            url = asset.get('browser_download_url', '')
            if url.startswith('https://github.com/Oma100-tech/Zorqi-Shell/releases/download/'):
                return asset
            raise ValueError('The release installer link is not from the official Zorqi-Shell release page.')
    return None


def version_tuple(version):
    values = re.findall(r'\d+', version)
    if not values:
        raise ValueError(f'Unrecognized Zorqi release version: {version}')
    normalized = [int(value) for value in values]
    while len(normalized) > 1 and normalized[-1] == 0:
        normalized.pop()
    return tuple(normalized)


class UpdateCenter:
    def __init__(self, root):
        self.root = root
        root.title('Zorqi Update Center')
        root.geometry('660x460')
        root.minsize(560, 400)
        self.release = None
        self.asset = None
        self.busy = False

        frame = ttk.Frame(root, padding=24)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Zorqi Update Center', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Check, download, and install official Zorqi releases.',
                  wraplength=590).pack(anchor='w', pady=(8, 16))
        self.steps = tk.StringVar(value='1. Check for updates    2. Download installer    3. Install')
        ttk.Label(frame, textvariable=self.steps, wraplength=590).pack(anchor='w', pady=(0, 16))
        self.details = tk.Text(frame, height=11, wrap='word', state='disabled')
        self.details.pack(fill='both', expand=True)
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=(12, 8))
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x')
        self.check_button = ttk.Button(buttons, text='Check for updates', command=self.check)
        self.check_button.pack(side='left')
        self.download_button = ttk.Button(buttons, text='Download installer', command=self.download, state='disabled')
        self.download_button.pack(side='left', padx=8)
        self.install_button = ttk.Button(buttons, text='Run downloaded installer',
                                         command=self.run_installer, state='disabled')
        self.install_button.pack(side='left')
        self.status = tk.StringVar(value='Ready')
        ttk.Label(frame, textvariable=self.status, anchor='w').pack(fill='x', pady=(12, 0))
        self.downloaded = None

    def set_details(self, text):
        self.details.configure(state='normal')
        self.details.delete('1.0', 'end')
        self.details.insert('end', text)
        self.details.configure(state='disabled')

    def post(self, callback, *args):
        try:
            if self.root.winfo_exists():
                self.root.after(0, callback, *args)
        except tk.TclError:
            pass

    def check(self):
        if self.busy:
            return
        self.busy = True
        self.check_button.configure(state='disabled')
        self.status.set('Checking GitHub releases...')
        self.progress.start(12)

        def worker():
            try:
                release = github_json(LATEST_RELEASE_API)
                asset = latest_windows_installer(release)
                error = None
            except (OSError, ValueError, URLError) as exc:
                release, asset, error = None, None, str(exc)
            self.post(self.finish_check, release, asset, error)

        threading.Thread(target=worker, daemon=True).start()

    def finish_check(self, release, asset, error):
        self.progress.stop()
        self.busy = False
        self.check_button.configure(state='normal')
        if error:
            self.status.set('Update check failed')
            self.set_details(f'Could not check GitHub releases.\n\n{error}')
            return
        self.release, self.asset = release, asset
        if release is None:
            self.status.set('No release information received')
            return
        title = release.get('name') or release.get('tag_name', 'Latest release')
        details = f'{title}\nPublished: {release.get("published_at", "Unknown")}\n\n'
        details += release.get('body') or 'No release notes were provided.'
        self.set_details(details[:12000])
        tag = release.get('tag_name', '')
        if tag:
            try:
                up_to_date = version_tuple(tag) <= version_tuple(CURRENT_VERSION)
            except ValueError as exc:
                self.status.set(str(exc))
                return
            if up_to_date:
                self.status.set(f'Zorqi {CURRENT_VERSION} is up to date')
                self.steps.set('1. Update check complete    2. No download needed    3. You are up to date')
                return
        if asset is None:
            self.status.set('Release found, but no Windows setup asset is published yet')
            self.steps.set('1. Release found    2. Windows installer not published    3. Waiting for release asset')
            return
        self.download_button.configure(state='normal')
        self.status.set(f'Update available: {asset.get("name")} ({asset.get("size", 0):,} bytes)')
        self.steps.set('1. Update found    2. Download the installer    3. Run setup to update Zorqi')

    def download(self):
        if self.busy or not self.asset:
            return
        self.busy = True
        self.download_button.configure(state='disabled')
        self.status.set('Downloading the official Windows installer...')
        self.progress.stop()
        self.progress.configure(mode='determinate', maximum=max(int(self.asset.get('size', 1)), 1), value=0)
        download_dir = Path.home() / 'Downloads'
        destination = download_dir / 'Zorqi-Setup.exe'

        def worker():
            temporary = destination.with_suffix('.exe.part')
            try:
                download_dir.mkdir(parents=True, exist_ok=True)
                request = Request(self.asset['browser_download_url'], headers={'User-Agent': 'Zorqi-Update-Center'})
                with urlopen(request, timeout=60) as response, temporary.open('wb') as output:
                    downloaded = 0
                    while True:
                        chunk = response.read(1024 * 256)
                        if not chunk:
                            break
                        output.write(chunk)
                        downloaded += len(chunk)
                        self.post(self.progress.configure, value=downloaded)
                if temporary.stat().st_size != int(self.asset.get('size', -1)):
                    raise ValueError('Downloaded file size did not match the GitHub release asset.')
                temporary.replace(destination)
                error = None
            except (OSError, ValueError, KeyError, URLError) as exc:
                temporary.unlink(missing_ok=True)
                error = str(exc)
            self.post(self.finish_download, destination, error)

        threading.Thread(target=worker, daemon=True).start()

    def finish_download(self, destination, error):
        self.progress.stop()
        self.busy = False
        if error:
            self.download_button.configure(state='normal')
            self.status.set('Download failed')
            self.set_details(f'The installer was not saved.\n\n{error}')
            return
        self.downloaded = destination
        self.install_button.configure(state='normal')
        self.status.set(f'Downloaded to {destination}')
        self.steps.set('1. Update found    2. Download complete    3. Run the installer')
        self.set_details(f'The official installer has been downloaded:\n\n{destination}\n\n'
                         'Run it to choose which Zorqi apps to update. Close the Update Center first if Windows '
                         'asks to replace a file that is currently in use.')

    def run_installer(self):
        if not self.downloaded or not self.downloaded.is_file():
            messagebox.showerror('Installer not found', 'Download the update installer first.', parent=self.root)
            return
        try:
            subprocess.Popen([str(self.downloaded)], cwd=str(self.downloaded.parent))
        except OSError as exc:
            messagebox.showerror('Could not start setup', str(exc), parent=self.root)
            return
        self.status.set('Setup started. This window will close so setup can update Zorqi files.')
        self.root.after(1200, self.root.destroy)


class ReleaseNews:
    def __init__(self, root):
        self.root = root
        root.title('Zorqi News')
        root.geometry('720x520')
        frame = ttk.Frame(root, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Zorqi News', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        self.items = tk.Listbox(frame, height=8)
        self.items.pack(fill='x', pady=12)
        self.notes = tk.Text(frame, wrap='word', state='disabled')
        self.notes.pack(fill='both', expand=True)
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=(12, 0))
        ttk.Button(buttons, text='Refresh news', command=self.refresh).pack(side='left')
        ttk.Button(buttons, text='Open release page', command=self.open_release).pack(side='left', padx=8)
        self.releases = []
        self.items.bind('<<ListboxSelect>>', self.show_release)
        self.refresh()

    def refresh(self):
        self.items.delete(0, 'end')
        self.items.insert('end', 'Loading Zorqi releases...')

        def worker():
            try:
                result = github_json(RELEASES_API + '?per_page=10')
                error = None
            except (OSError, ValueError, URLError) as exc:
                result, error = [], str(exc)
            try:
                if self.root.winfo_exists():
                    self.root.after(0, self.finish_refresh, result, error)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def finish_refresh(self, releases, error):
        self.items.delete(0, 'end')
        if error:
            self.items.insert('end', 'Could not load news')
            self.set_notes(error)
            return
        self.releases = releases
        for release in releases:
            self.items.insert('end', release.get('name') or release.get('tag_name', 'Release'))
        if not releases:
            self.items.insert('end', 'No published releases')

    def set_notes(self, text):
        self.notes.configure(state='normal')
        self.notes.delete('1.0', 'end')
        self.notes.insert('end', text)
        self.notes.configure(state='disabled')

    def show_release(self, _event=None):
        selected = self.items.curselection()
        if selected and selected[0] < len(self.releases):
            release = self.releases[selected[0]]
            self.set_notes(release.get('body') or 'No release notes were provided.')

    def open_release(self):
        selected = self.items.curselection()
        if selected and selected[0] < len(self.releases):
            url = self.releases[selected[0]].get('html_url')
            if url:
                webbrowser.open(url)


class TextEditor:
    def __init__(self, root):
        self.root = root
        root.title('Zorqi IDE (Beta)')
        root.geometry('900x640')
        self.path = None
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Zorqi IDE (Beta) — lightweight file editor',
                  font=('Segoe UI', 16, 'bold')).pack(anchor='w')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=10)
        ttk.Button(buttons, text='Open file', command=self.open_file).pack(side='left')
        ttk.Button(buttons, text='Save', command=self.save_file).pack(side='left', padx=8)
        ttk.Button(buttons, text='Save as...', command=self.save_as).pack(side='left')
        self.editor = tk.Text(frame, wrap='none', undo=True, font=('Consolas', 11))
        self.editor.pack(fill='both', expand=True)
        self.status = tk.StringVar(value='New file')
        ttk.Label(frame, textvariable=self.status, anchor='w').pack(fill='x', pady=(8, 0))

    def open_file(self):
        path = filedialog.askopenfilename(parent=self.root, title='Open a text or source file')
        if not path:
            return
        try:
            content = Path(path).read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            messagebox.showerror('Could not open file', str(exc), parent=self.root)
            return
        self.path = Path(path)
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', content)
        self.status.set(str(self.path))

    def save_file(self):
        if self.path is None:
            self.save_as()
            return
        try:
            self.path.write_text(self.editor.get('1.0', 'end-1c'), encoding='utf-8')
        except OSError as exc:
            messagebox.showerror('Could not save file', str(exc), parent=self.root)
            return
        self.status.set(f'Saved {self.path}')

    def save_as(self):
        path = filedialog.asksaveasfilename(parent=self.root, title='Save source file')
        if path:
            self.path = Path(path)
            self.save_file()


def open_settings(root):
    root.title('Zorqi Settings')
    root.geometry('560x400')
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Zorqi Settings', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    try:
        settings = load_settings()
    except (OSError, ValueError) as exc:
        settings = {}
        messagebox.showerror('Settings unavailable', str(exc), parent=root)
    try:
        import updater
        startup_value = updater.config().get('startup', 'off')
    except (OSError, ValueError):
        startup_value = 'off'
    startup = tk.StringVar(value=startup_value)
    ttk.Label(frame, text='Startup update behavior').pack(anchor='w', pady=(20, 5))
    for value, label in (
        ('off', 'Do not check automatically'),
        ('check', 'Check for updates on startup'),
        ('auto', 'Install source updates on startup'),
    ):
        ttk.Radiobutton(frame, text=label, value=value, variable=startup).pack(anchor='w')
    theme = tk.StringVar(value=settings.get('theme', 'vista'))
    ttk.Label(frame, text='Appearance').pack(anchor='w', pady=(16, 5))
    ttk.Combobox(frame, textvariable=theme, values=('vista', 'clam', 'alt', 'default'),
                 state='readonly').pack(anchor='w')
    status = tk.StringVar(value='Changes apply to the graphical apps.')
    ttk.Label(frame, textvariable=status, wraplength=500).pack(anchor='w', pady=12)

    def save():
        try:
            save_settings({**settings, 'theme': theme.get()})
            import contextlib
            import io
            import updater
            with contextlib.redirect_stdout(io.StringIO()):
                result = updater.handle('startup-updates', [startup.get()])
            if result:
                raise RuntimeError('Could not save the startup update preference.')
        except OSError as exc:
            messagebox.showerror('Could not save settings', str(exc), parent=root)
            return
        except RuntimeError as exc:
            messagebox.showerror('Could not save settings', str(exc), parent=root)
            return
        status.set('Settings saved.')

    ttk.Button(frame, text='Save settings', command=save).pack(anchor='w')


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    app = args[args.index('--app') + 1] if '--app' in args and args.index('--app') + 1 < len(args) else 'control'
    root = tk.Tk()
    try:
        theme = load_settings().get('theme')
    except (OSError, ValueError):
        theme = None
    style = ttk.Style(root)
    if theme in style.theme_names():
        style.theme_use(theme)
    if app == 'control':
        zorqi_gui.ZorqiControlPanel(root)
    elif app == 'update-center':
        UpdateCenter(root)
    elif app == 'news':
        ReleaseNews(root)
    elif app == 'ide':
        TextEditor(root)
    elif app in ('settings', 'gui-modes'):
        open_settings(root)
        if app == 'gui-modes':
            root.title('Zorqi GUI Modes')
    else:
        root.destroy()
        raise ValueError(f'Unknown Zorqi app: {app}')
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
