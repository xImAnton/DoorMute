import json
import os
import os.path
import shutil
import subprocess
import sys
import winreg
import ctypes
import win32com.client


def is_admin_():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def elevate():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)


def main():
    if not is_admin_():
        print("Elevating")
        elevate()
        return

    try:
        exe_path = os.path.join(sys._MEIPASS, "client.exe")
    except AttributeError:
        exe_path = "./dist/client.exe"

    dist_dir = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "DoorMute")

    if input(f"Install into {dist_dir}? [y/n] ").lower() not in ["y", "yes"]:
        print("Aborting..")
        return

    try:
        os.mkdir(dist_dir)
    except FileExistsError:
        shutil.rmtree(dist_dir)
        os.mkdir(dist_dir)

    dist_path = os.path.join(dist_dir, "client.exe")

    print("Installing executable")
    shutil.copyfile(exe_path, dist_path)

    config_data = {
        "password": input("Server Password?: "),
        "server_host": input("Server Host?: ")
    }

    print("Generating Configuration")
    with open(os.path.join(dist_dir, "client.json"), "w") as f:
        f.write(json.dumps(config_data))

    print("Copying resources")
    try:
        resources = os.path.join(sys._MEIPASS, "resources")
    except AttributeError:
        resources = "./resources"
    dist_resources = os.path.join(dist_dir, "resources")
    shutil.copytree(resources, dist_resources)

    runner_path = os.path.join(dist_dir, "runner.vbs")
    with open(runner_path, "w") as f:
        f.write(f"Set shl = CreateObject(\"Wscript.Shell\")\nshl.CurrentDirectory = \"{dist_dir}\"\nshl.Run \"\"\"\" & \"client.exe\" & \"\"\"\", 0, False")

    print("Adding to Autostart")
    system32 = os.path.join(os.getenv("WINDIR", "C:\\Windows"), "System32")
    cmd = f"\"{os.path.join(system32, 'wscript.exe')}\" \"{runner_path}\""

    reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    run = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(run, "DoorMute", 0, winreg.REG_SZ, cmd)
    winreg.CloseKey(run)
    winreg.CloseKey(reg)

    print("Creating start menu shortcut")
    shl = win32com.client.Dispatch("Wscript.Shell")
    path = os.path.join(os.getenv("APPDATA"), "Microsoft/Windows/Start Menu/Programs/DoorMute.lnk")
    shortcut = shl.CreateShortCut(path)
    shortcut.Targetpath = runner_path
    shortcut.IconLocation = os.path.join(dist_resources, "icon.ico")
    shortcut.WindowStyle = 1
    shortcut.save()

    subprocess.call(cmd)
    print("Installation done")


if __name__ == '__main__':
    main()
