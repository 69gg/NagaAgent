# list_apps.py - 列出所有找到的应用
import asyncio
import sys
import os

# 添加路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append('H:\\NagaAgent')

from simple_scanner import SimpleAppLauncher

async def list_all_apps():
    """列出所有应用"""
    launcher = SimpleAppLauncher()
    apps = await launcher.get_apps()
    
    print("=== 找到的所有应用 ===")
    print(f"总计: {len(apps)} 个应用\n")
    
    for i, app in enumerate(apps, 1):
        print(f"{i:2d}. {app['display_name']}")
        print(f"     路径: {app['path']}")
        if app.get('type') == 'shortcut':
            print(f"     类型: 桌面快捷方式")
        print()

if __name__ == "__main__":
    asyncio.run(list_all_apps())