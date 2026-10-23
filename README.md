# Zorqi Terminal

An interactive terminal command app for Windows, macOS, Linux and SteamOS, independent of Microsoft PowerShell. It runs in your native terminal with interactive input, sudo authentication, editors, process monitors and command exit codes. It is not a separate terminal emulator or a PowerShell language implementation.

## Install the app

Requires Python 3.10+. From the repository:

```sh
cd Powershell30_Installer_GUI
python3 setup.py --cli
```

On Windows use `python` instead of `python3`. Run `python3 setup.py` for the optional Tkinter installer GUI. Installation no longer uses the old placeholder batch phases or reboots Windows.

- Linux/SteamOS: launcher `~/.local/bin/zorqi`, plus an application menu entry. Uses the existing terminal emulator. No sudo or SteamOS system modifications required.
- macOS: launcher `~/.local/bin/zorqi`; open `~/.local/Applications/Zorqi.app` to start it in Terminal. Optionally move the app to your Applications folder; leave the installed launcher in place.
- Windows source installation: `%LOCALAPPDATA%\Zorqi\bin\zorqi.cmd`.

Add the launcher's folder to PATH. A custom prefix is supported with `python3 linux_install.py --prefix PATH`.

Run `zorqi` for the interactive prompt, or `zorqi help` to list commands. Source can also run directly: `python3 zorqi.py`.

## Commands

Over 140 named commands and aliases cover system diagnostics, files, networking, packages, development and Steam. Utilities must already exist on your system; missing utilities produce an error. Examples inside the app:

```text
help
sysinfo
cpu
memory
network
list
cd "my folder"
read notes.txt
sudo apt update
sudo apt install git
brew install tree
winget search Python
flatpak-install flathub org.mozilla.firefox
git status
ssh user@host
python3 --version
steam-paths
version
exit
```

`sudo apt` works on distributions that provide apt, not on macOS or SteamOS. Use Homebrew on macOS and Flatpak on SteamOS. Native commands retain their normal effects, prompts, and permissions. Nothing automatically grants administrator privileges. Package discovery uses apt/dnf/pacman/zypper/apk, Homebrew, or winget depending on the platform.

macOS has native mappings for CPU, memory, disks, battery, USB/GPU, networking, checksums, services, logs and Steam. SteamOS-specific `desktop` and `gamemode` switch sessions. Windows has mappings for system info, processes, networking, DNS and checksums; Unix-only commands still require their tools.

Quoted arguments are supported. Shell pipes, redirections and expansion are not interpreted; launch `bash`, `zsh`, `cmd`, or `pwsh` for full shell syntax.

## GitHub updates

Source installations support updates from https://github.com/Oma100-tech/PowerShell30:

```text
update-check
update
startup-updates check
startup-updates auto
startup-updates off
```

Startup mode defaults to `off`; `check` checks on interactive startup, and `auto` downloads and installs on startup. Restart the terminal after installation to load changed code. Updates require Git and network access, use a dedicated checkout, refuse dirty checkouts, and pull with `--ff-only`. Each Git operation has a 60-second timeout. Settings live in `~/.local/share/zorqi-updates` (Windows: `%LOCALAPPDATA%\zorqi-updates`). Updates install trusted repository code for the current user. The new implementation must be published to GitHub before updates can install it.

Frozen EXE/binary builds direct users to GitHub Releases for replacement installers; automatic source updates apply to Python installations.

## Windows EXE installer and standalone builds

The **Build Zorqi apps** GitHub Actions workflow builds on Windows, macOS and Linux. Trigger it manually or push a `v*` tag. Download the OS artifact from the workflow run. Windows contains:

- `Zorqi.exe`: interactive console app.
- `Zorqi-Setup.exe`: per-user installer with a Start Menu shortcut; no Python required on the target machine.

The Windows installer bundles the terminal EXE, installs under `%LOCALAPPDATA%\Programs\Zorqi`, and does not require administrator access. Builds are unsigned. The workflow uploads artifacts; it does not publish a GitHub Release automatically.

To build on Windows locally:

```text
python -m pip install pyinstaller
python -m PyInstaller --clean --onefile --name Zorqi Powershell30_Installer_GUI/zorqi.py
python -m PyInstaller --clean --onefile --windowed --name Zorqi-Setup --add-binary "dist/Zorqi.exe;." Powershell30_Installer_GUI/windows_installer.py
```

Build on the target OS. Windows and macOS executables cannot be validated by the Linux development checks.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

Uninstall by removing the installed launcher, `share/zorqi` directory, platform app/menu entry, and optionally the update settings/checkout. Windows EXE installs can be removed by deleting their install folder and Start Menu shortcut.

### One-command Windows build

After installing PyInstaller on Windows, run from the repository root:

```text
python Powershell30_Installer_GUI/build_windows.py
```

This builds `dist/Zorqi.exe` and `dist/Zorqi-Setup.exe`, checks that both files exist, and smoke-tests the terminal executable. The **Build Zorqi apps** GitHub Actions workflow uses the same script. Download the `Zorqi-Windows` workflow artifact after a successful run. These changes must be pushed before GitHub can build them.

The app was previously called PowerShell30. Existing installations keep their old launchers until removed; install again to create the Zorqi launcher. The GitHub repository URL remains unchanged.
