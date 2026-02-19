"""Set up ReadLater to run automatically when the computer starts."""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

PLIST_NAME = "com.readlater.watch.plist"
TASK_NAME = "ReadLaterWatch"


def _find_readlater_bin() -> str:
    """Find the full path to the readlater command."""
    path = shutil.which("readlater")
    if path:
        return path
    # Fallback: use python -m
    return f"{sys.executable} -m readlater.cli"


def install_autostart():
    system = platform.system()
    if system == "Darwin":
        _install_macos()
    elif system == "Windows":
        _install_windows()
    elif system == "Linux":
        _install_linux()
    else:
        print(f"Autostart not supported on {system}.")


def uninstall_autostart():
    system = platform.system()
    if system == "Darwin":
        _uninstall_macos()
    elif system == "Windows":
        _uninstall_windows()
    elif system == "Linux":
        _uninstall_linux()
    else:
        print(f"Autostart not supported on {system}.")


def check_autostart():
    system = platform.system()
    if system == "Darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME
        if plist.exists():
            print(f"Autostart is INSTALLED (macOS launchd)")
            print(f"  Config: {plist}")
        else:
            print("Autostart is NOT installed.")
    elif system == "Windows":
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("Autostart is INSTALLED (Windows Task Scheduler)")
        else:
            print("Autostart is NOT installed.")
    elif system == "Linux":
        service = Path.home() / ".config" / "systemd" / "user" / "readlater.service"
        if service.exists():
            print(f"Autostart is INSTALLED (systemd user service)")
            print(f"  Config: {service}")
        else:
            print("Autostart is NOT installed.")


# ── macOS (launchd) ─────────────────────────────────────────────

def _install_macos():
    readlater_bin = _find_readlater_bin()
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist = launch_agents / PLIST_NAME

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.readlater.watch</string>
    <key>ProgramArguments</key>
    <array>
        <string>{readlater_bin}</string>
        <string>watch</string>
        <string>--with-server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home() / ".readlater" / "watch.log"}</string>
    <key>StandardErrorPath</key>
    <string>{Path.home() / ".readlater" / "watch.log"}</string>
</dict>
</plist>
"""
    plist.write_text(content)
    subprocess.run(["launchctl", "load", str(plist)])
    print("Autostart installed! ReadLater will now:")
    print("  - Start automatically when you log in")
    print("  - Check email every 5 minutes")
    print("  - Run the Chrome extension server")
    print(f"\nLog file: {Path.home() / '.readlater' / 'watch.log'}")
    print(f"To stop: readlater autostart uninstall")


def _uninstall_macos():
    plist = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME
    if plist.exists():
        subprocess.run(["launchctl", "unload", str(plist)])
        plist.unlink()
        print("Autostart removed.")
    else:
        print("Autostart was not installed.")


# ── Windows (Task Scheduler) ────────────────────────────────────

def _install_windows():
    readlater_bin = _find_readlater_bin()

    # Create a small batch wrapper so Task Scheduler can run it cleanly
    wrapper = Path.home() / ".readlater" / "watch.bat"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(f'@echo off\n"{readlater_bin}" watch --with-server\n')

    subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", str(wrapper),
            "/SC", "ONLOGON",
            "/RL", "LIMITED",
            "/F",
        ],
        check=True,
    )
    print("Autostart installed! ReadLater will now:")
    print("  - Start automatically when you log in")
    print("  - Check email every 5 minutes")
    print("  - Run the Chrome extension server")
    print(f"\nTo stop: readlater autostart uninstall")


def _uninstall_windows():
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print("Autostart removed.")
        wrapper = Path.home() / ".readlater" / "watch.bat"
        wrapper.unlink(missing_ok=True)
    else:
        print("Autostart was not installed.")


# ── Linux (systemd user service) ────────────────────────────────

def _install_linux():
    readlater_bin = _find_readlater_bin()
    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_file = service_dir / "readlater.service"

    content = f"""[Unit]
Description=ReadLater - PDF reading collector
After=network.target

[Service]
Type=simple
ExecStart={readlater_bin} watch --with-server
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""
    service_file.write_text(content)
    subprocess.run(["systemctl", "--user", "daemon-reload"])
    subprocess.run(["systemctl", "--user", "enable", "--now", "readlater.service"])
    print("Autostart installed! ReadLater will now:")
    print("  - Start automatically when you log in")
    print("  - Check email every 5 minutes")
    print("  - Run the Chrome extension server")
    print(f"\nTo check status: systemctl --user status readlater")
    print(f"To stop: readlater autostart uninstall")


def _uninstall_linux():
    service_file = Path.home() / ".config" / "systemd" / "user" / "readlater.service"
    if service_file.exists():
        subprocess.run(["systemctl", "--user", "disable", "--now", "readlater.service"])
        service_file.unlink()
        subprocess.run(["systemctl", "--user", "daemon-reload"])
        print("Autostart removed.")
    else:
        print("Autostart was not installed.")
