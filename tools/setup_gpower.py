import sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service, win32gui, win32con
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
hdesk.SetThreadDesktop()

# Find combo by ID
def get_control_by_id(parent, target_id):
    res = []
    def cb(hwnd, extra):
        if user32.GetDlgCtrlID(hwnd) == target_id:
            res.append(hwnd)
        return True
    win32gui.EnumChildWindows(parent, cb, None)
    return res[0] if res else None

def get_combo_items(combo):
    count = user32.SendMessageW(combo, 0x0146, 0, 0)
    items = []
    for i in range(count):
        length = user32.SendMessageW(combo, 0x0149, i, 0)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(combo, 0x0148, i, buf)
        items.append(buf.value)
    return items

def select_combo_item(combo, text_substring):
    items = get_combo_items(combo)
    target_idx = -1
    for idx, item in enumerate(items):
        if text_substring.lower() in item.lower():
            target_idx = idx
            break
    if target_idx == -1:
        raise ValueError(f"Could not find '{text_substring}' in {items}")
    
    parent = win32gui.GetParent(combo)
    ctrl_id = user32.GetDlgCtrlID(combo)
    user32.SendMessageW(combo, 0x014E, target_idx, 0) # CB_SETCURSEL
    user32.SendMessageW(parent, win32con.WM_COMMAND, (1 << 16) | (ctrl_id & 0xFFFF), combo)
    time.sleep(0.3)
    return items[target_idx]

combo_family = get_control_by_id(gp_hwnd, 1000)
print('Family items:', get_combo_items(combo_family))
selected_fam = select_combo_item(combo_family, 't tests')
print('Selected family:', selected_fam)

time.sleep(1.0)
combo_test = get_control_by_id(gp_hwnd, 1001)
print('Test items after family change:', get_combo_items(combo_test))
selected_test = select_combo_item(combo_test, 'two dependent means')
print('Selected test:', selected_test)

time.sleep(1.0)
combo_type = get_control_by_id(gp_hwnd, 1002)
print('Type items:', get_combo_items(combo_type))
selected_type = select_combo_item(combo_type, 'A priori')
print('Selected type:', selected_type)
