import sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service, win32gui, win32process
import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32

DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.LPWSTR, wintypes.LPARAM)

def find_gpower():
    hwinsta = win32service.GetProcessWindowStation()
    desktops = []
    def enum_desks(name, extra):
        desktops.append(name)
        return True
    user32.EnumDesktopsW(int(hwinsta), DESKTOPENUMPROC(enum_desks), 0)

    for d in desktops:
        try:
            hdesk = win32service.OpenDesktop(d, 0, False, 0x02000000)
            windows = []
            def enum_cb(hwnd, extra):
                txt = win32gui.GetWindowText(hwnd)
                if txt.startswith('G*Power 3.'):
                    windows.append(hwnd)
                return True
            win32gui.EnumDesktopWindows(hdesk, enum_cb, 0)
            if windows:
                return d, hdesk, windows[0]
        except Exception:
            pass
    return None, None, None

d, hdesk, hwnd = find_gpower()
print(f'Found: Desktop={d}, HWND={hwnd}')
