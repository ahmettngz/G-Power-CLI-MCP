import sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service, win32con
hdesk = win32service.OpenDesktop('default', 0, False, win32con.MAXIMUM_ALLOWED)
hdesk.SetThreadDesktop()

import win32gui, ctypes
user32 = ctypes.windll.user32

gp_hwnd = None
def find_gp(hwnd, extra):
    global gp_hwnd
    t = win32gui.GetWindowText(hwnd)
    if t.startswith('G*Power 3.'):
        gp_hwnd = hwnd
    return True

win32gui.EnumDesktopWindows(hdesk, find_gp, 0)
print('gp_hwnd:', gp_hwnd)

def dump_tree(hwnd, indent=0):
    cls = win32gui.GetClassName(hwnd)
    txt = win32gui.GetWindowText(hwnd)
    ctrl_id = user32.GetDlgCtrlID(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    vis = win32gui.IsWindowVisible(hwnd)
    print('  '*indent + f'[{ctrl_id}] {cls} "{txt}" vis={vis} rect={rect}')
    children = []
    win32gui.EnumChildWindows(hwnd, lambda ch, ex: children.append(ch) if win32gui.GetParent(ch) == hwnd else True, None)
    for ch in children:
        dump_tree(ch, indent+1)

dump_tree(gp_hwnd)
