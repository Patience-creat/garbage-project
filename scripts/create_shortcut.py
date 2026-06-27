"""在桌面创建智分宝快捷方式，设置自定义图标"""
import os, sys
from win32com.client import Dispatch

desktop = os.path.join(os.path.expanduser("~"), "Desktop")
project = r"C:\Users\15300\Desktop\garbage_project"
icon = os.path.join(project, "icon.ico")
pythonw = r"D:\Anaconda\pythonw.exe"

shortcut_path = os.path.join(desktop, "智分宝.lnk")

shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortcut(shortcut_path)
shortcut.TargetPath = pythonw
shortcut.Arguments = "main.py"
shortcut.WorkingDirectory = project
shortcut.IconLocation = f"{icon},0"
shortcut.Description = "智分宝 · 智能垃圾分类检测系统"
shortcut.Save()

print(f"[OK] 桌面快捷方式已创建: {shortcut_path}")
print(f"[OK] 目标: {pythonw}")
print(f"[OK] 图标: {icon}")
