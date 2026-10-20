import sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service, win32gui, win32process

hwinsta = win32service.GetProcessWindowStation()
import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32

DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.LPWSTR, wintypes.LPARAM)

desktops = []
def enum_desks(name, extra):
    desktops.append(name)
    return True

proc = DESKTOPENUMPROC(enum_desks)
user32.EnumDesktopsW(int(hwinsta), proc, 0)
print('Desktops in WinSta0:', desktops)

for d in desktops:
    try:
        hdesk = win32service.OpenDesktop(d, 0, False, 0x02000000)
        windows = []
        def enum_cb(hwnd, extra):
            tid, pid = win32process.GetWindowThreadProcessId(hwnd)
            txt = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            if pid == 5220 or 'G*Power' in txt or 'GPower' in cls:
                windows.append((hwnd, pid, cls, txt))
            return True
        win32gui.EnumDesktopWindows(hdesk, enum_cb, 0)
        if windows:
            print(f'Found in desktop "{d}": {windows}')
    except Exception as e:
        print(f'Error on desktop {d}: {e}')
