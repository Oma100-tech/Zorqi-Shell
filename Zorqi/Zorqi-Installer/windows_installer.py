"""Entry point for the Windows EXE installer built by CI."""
import os
from pathlib import Path
import shutil
import sys


def main():
    if sys.platform != 'win32':
        raise RuntimeError('Run this installer on Windows.')
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    try:
        source = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'Zorqi.exe'
        target = Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Zorqi'
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / source.name)
        # User Start Menu shortcut, using PowerShell with literal paths.
        menu = Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Zorqi.lnk'
        import subprocess
        def literal(value):
            return "'" + str(value).replace("'", "''") + "'"
        script = ('$s=(New-Object -ComObject WScript.Shell).CreateShortcut(' + literal(menu) + ');'
                  '$s.TargetPath=' + literal(target / source.name) + ';$s.Save()')
        subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], check=True)
        messagebox.showinfo('Zorqi installed', f'Installed to {target}. Open Zorqi from the Start Menu.')
    except Exception as exc:
        messagebox.showerror('Installation failed', str(exc))
        return 1
    finally:
        root.destroy()
    return 0


if __name__ == '__main__':
    sys.exit(main())
