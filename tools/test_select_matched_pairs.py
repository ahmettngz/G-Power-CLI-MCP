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

# Select 'Means: Difference between two dependent means (matched pairs)'
test_c = [c for c in dlg.descendants() if c.class_name() == 'ComboBox' and c.control_id() == 1001][0]
print('Selecting matched pairs...')
test_c.select('Means: Difference between two dependent means (matched pairs)')
time.sleep(1.0)

# Check Type combo (id 1002)
type_c = [c for c in dlg.descendants() if c.class_name() == 'ComboBox' and c.control_id() == 1002][0]
print('Type combo text:', type_c.window_text())

# Print all visible Edit controls and their labels
edits = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.is_visible()]
statics = [c for c in dlg.descendants() if c.class_name() == 'Static' and c.is_visible()]
print(f'Visible edits: {len(edits)}')
for e in edits:
    print(f'Edit ID {e.control_id()}: handle={e.handle}, rect={e.rectangle()}, text={e.window_text()!r}')
for s in statics:
    print(f'Static ID {s.control_id()}: handle={s.handle}, rect={s.rectangle()}, text={s.window_text()!r}')
