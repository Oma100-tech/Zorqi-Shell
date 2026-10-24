"""Graphical installer with a headless Linux installation option."""
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
PHASES = [BASE / 'phases' / f'phase{i}.bat' for i in range(1, 11)]


def install(log=print):
    from linux_install import install as install_app
    launcher = install_app()
    log(f'Installed terminal app: {launcher}')
    log(f'Run "{launcher}" help to see commands.')
    log(f'Add {launcher.parent} to PATH for terminal access.')


def main():
    if '--cli' in sys.argv:
        try:
            install()
            return 0
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f'Installation failed: {exc}', file=sys.stderr)
            return 1
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
    except (ImportError, RuntimeError) as exc:
        print(f'GUI unavailable: {exc}. Use python3 setup.py --cli.', file=sys.stderr)
        return 1
    except Exception as exc:
        # Tk raises TclError when no graphical display is available.
        print(f'Cannot open GUI: {exc}. Use python3 setup.py --cli.', file=sys.stderr)
        return 1
    root.title('Zorqi Installer')
    root.geometry('660x420')
    tk.Label(root, text='Zorqi — Windows / macOS / Linux / SteamOS', font=('', 14)).pack(pady=12)
    log_text = tk.Text(root, height=16, width=78)

    def log(message):
        log_text.insert(tk.END, message + '\n')
        log_text.see(tk.END)
        root.update_idletasks()

    def start():
        button.config(state=tk.DISABLED)
        try:
            install(log)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            log(f'Installation failed: {exc}')
            messagebox.showerror('Installation failed', str(exc))
        else:
            messagebox.showinfo('Installed', 'Zorqi installation completed.')
        finally:
            button.config(state=tk.NORMAL)

    button = tk.Button(root, text='Start Installation', command=start)
    button.pack(pady=8)
    log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    log('Ready. Linux / SteamOS installs into ~/.local without sudo.')
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
