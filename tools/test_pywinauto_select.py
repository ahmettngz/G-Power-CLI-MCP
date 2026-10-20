import sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service, win32gui, win32process
import ctypes, time
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

d, hdesk, gp_hwnd = find_gpower()
print(f'Desktop: {d}, HWND: {gp_hwnd}')
hdesk.SetThreadDesktop()

from pywinauto import Application

app = Application(backend='win32').connect(handle=gp_hwnd)
dlg = app.window(handle=gp_hwnd)

# Find ComboBox controls
combos = [c for c in dlg.descendants() if c.class_name() == 'ComboBox']
print(f'Total combos: {len(combos)}')
for idx, c in enumerate(combos):
    print(f'Combo {idx}: handle={c.handle}, id={c.control_id()}, text={c.window_text()!r}, items={c.item_texts()[:3]}')

# Select 't tests' in family combo (id 1000)
fam = [c for c in combos if c.control_id() == 1000][0]
print('Selecting t tests...')
fam.select('t tests')
time.sleep(1.0)

# Check test combo (id 1001)
test_c = [c for c in dlg.descendants() if c.class_name() == 'ComboBox' and c.control_id() == 1001][0]
print('Test combo items:', test_c.item_texts())
