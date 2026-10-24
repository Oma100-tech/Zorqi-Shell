# Zorqi Terminal

An interactive terminal command app for Windows, macOS, Linux and SteamOS, independent of Microsoft PowerShell. It runs in your native terminal with interactive input, sudo authentication, editors, process monitors and command exit codes. It is not a separate terminal emulator or a PowerShell language implementation.

## Install the app

Source installation requires Python 3.10+. From the repository:

```sh
cd Zorqi_Installer
python3 setup.py --cli
```

On Windows use `python` instead of `python3`. Run `python3 setup.py` for the optional Tkinter installer GUI. The source installer requires Python; Linux users who do not have Python can instead download and run the standalone `Zorqi-Setup-Linux` release asset. Installation no longer uses the old placeholder batch phases or reboots Windows.

- Linux/SteamOS: launcher `~/.local/bin/zorqi`, plus an application menu entry. Uses the existing terminal emulator. No sudo or SteamOS system modifications required.
- macOS source install: launcher `~/.local/bin/zorqi`; open `~/.local/Applications/Zorqi.app` to start it in Terminal. Optionally move the app to your Applications folder; leave the installed launcher in place.
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

Source installations support updates from https://github.com/Oma100-tech/Zorqi-Shell:

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

- `Zorqi.exe`: Zorqi's own tabbed terminal window with command history, separate working directories, selectable color themes, and adjustable saved transparency. It does not launch Windows Terminal.
- `Zorqi-CLI.exe`: command engine used by the graphical apps.
- `Zorqi-Control.exe`: graphical dashboard with system information, network tools, a Zorqi command runner, and update settings.
- `Zorqi-Apps.exe`: Zorqi Update Center, Settings, News, IDE (Beta), and GUI Modes.
- `Zorqi-Setup.exe`: guided per-user installer that lets users choose apps and shortcuts; no Python required on the target machine.

The installer is a Setup Center with **Install**, **Update my version**, **Repair/reinstall**, and **Uninstall** modes. It records the selected apps, install folder, shortcuts, and PATH preference for later updates; update and repair reuse the detected install folder and preserve user settings. Users can also choose individual apps, Start Menu shortcuts, a Desktop shortcut, launch-after-install, and whether to add the install folder to their user PATH. The PATH option is unchecked by default. Uninstall confirms before proceeding, removes app shortcuts and registration, and offers optional removal of Zorqi preferences and update cache (preserved by default). The uninstaller waits until it exits before cleaning its own files and leaves unrelated files in the installation folder untouched. Setup does not require administrator access. Builds are unsigned.

The Update Center checks the latest `Oma100-tech/Zorqi-Shell` release, displays its notes, downloads the official `Zorqi-Setup.exe` asset with progress, and launches setup so users can select components during an update. Pushing a `v*` tag builds the apps and publishes both the Windows setup executable and standalone Linux setup executable as GitHub Release assets. Zorqi News displays published release notes; the IDE (Beta) edits local text/source files; GUI Modes and Settings store per-user appearance and update preferences. See [`updates/`](./updates/) for the test-release steps.

Linux release builds include a standalone `Zorqi-Setup-Linux` executable that bundles its runtime and Zorqi command app; no Python installation is needed on the target machine. Download that file from the GitHub Release, then run `chmod +x Zorqi-Setup-Linux && ./Zorqi-Setup-Linux`. Alternatively, download `install-linux.sh` and run `sh install-linux.sh`; it fetches and launches the latest standalone setup (requires curl or wget and an internet connection). It installs `~/.local/bin/zorqi` and a terminal application menu entry. The Linux installer does not require sudo.

macOS release builds include `Zorqi-macOS.dmg`. Open the disk image, then drag `Zorqi.app` onto the `Applications` shortcut in the DMG window. Opening Zorqi starts the macOS Terminal with the bundled Zorqi command app; no Python installation is needed.

To build on Windows locally:

```text
python -m pip install pyinstaller
python Zorqi_Installer/build_windows.py
```

The setup executable is a single self-contained file that installs the terminal and selected graphical apps. The installer creates separately named shortcuts using the custom app icon. Zorqi Terminal runs Zorqi commands and direct native commands in its own window; it is not a general PowerShell/CMD shell, and commands requiring interactive prompts or a full-screen TTY are not supported. To run the Python installer entry point directly after building the apps, use `python Zorqi_Installer/windows-installer.py`. Build on the target OS. Windows and macOS executables cannot be validated by the Linux development checks.

## Development checks

```sh
python3 -m unittest discover -s tests -v
```

Uninstall by removing the installed launcher, `share/zorqi` directory, platform app/menu entry, and optionally the update settings/checkout. Windows EXE installs can be removed by deleting their install folder and Start Menu shortcut.

### One-command Windows build

After installing PyInstaller on Windows, run from the repository root:

```text
python Zorqi_Installer/build_windows.py
```

This builds `dist/Zorqi.exe`, `dist/Zorqi-CLI.exe`, `dist/Zorqi-Control.exe`, `dist/Zorqi-Apps.exe`, and `dist/Zorqi-Setup.exe`, checks that all five files exist, and smoke-tests the command engine. The **Build Zorqi apps** GitHub Actions workflow uses the same script. Download the `Zorqi-Windows` workflow artifact after a successful run. These changes must be pushed before GitHub can build them.

The app was previously called PowerShell30. Existing installations keep their old launchers until removed; install again to create the Zorqi launcher.
