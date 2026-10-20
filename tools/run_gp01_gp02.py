import os, sys
sys.stdout.reconfigure(encoding='utf-8')
import win32service
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
                # Use user32 directly without win32gui
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value.startswith('G*Power 3.'):
                    windows.append(hwnd)
                return True
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumDesktopWindows(int(hdesk), WNDENUMPROC(enum_cb), 0)
            if windows:
                return d, hdesk, windows[0]
        except Exception:
            pass
    return None, None, None

d, hdesk, gp_hwnd = find_gpower()
if not gp_hwnd:
    print('G*Power window not found!')
    sys.exit(1)

hdesk.SetThreadDesktop()

import win32gui, win32con, win32ui
from PIL import Image
from pywinauto import Application

app = Application(backend='win32').connect(handle=gp_hwnd)
dlg = app.window(handle=gp_hwnd)

# Ensure window is restored and foreground
try:
    win32gui.ShowWindow(gp_hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(gp_hwnd)
except Exception:
    pass
time.sleep(0.5)

def capture_screenshot(out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rect = win32gui.GetWindowRect(gp_hwnd)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]

    hwndDC = win32gui.GetWindowDC(gp_hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    user32.PrintWindow(gp_hwnd, saveDC.GetSafeHdc(), 2)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        'RGB',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRX', 0, 1)

    im.save(out_path)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(gp_hwnd, hwndDC)

def check_popup():
    popups = []
    def find_popups(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            cls = win32gui.GetClassName(hwnd)
            owner = user32.GetWindow(hwnd, 4) # GW_OWNER
            if cls == '#32770' and owner == gp_hwnd:
                popups.append(hwnd)
        return True
    win32gui.EnumDesktopWindows(hdesk, find_popups, 0)
    return popups

def run_vector(vec_id, mode, tails, dz, alpha, target_power=None, input_n=None):
    print(f"\n==========================================")
    print(f"Running {vec_id}: mode={mode}, tails={tails}, dz={dz}, alpha={alpha}, power={target_power}, n={input_n}")

    # Set Mode
    type_c = [c for c in dlg.descendants() if c.class_name() == 'ComboBox' and c.control_id() == 1002][0]
    if mode == 'a-priori':
        type_c.select('A priori: Compute required sample size - given α, power, and effect size')
    elif mode == 'post-hoc':
        type_c.select('Post hoc: Compute achieved power - given α, sample size, and effect size')
    time.sleep(0.3)

    # Set Tails
    tails_c = [c for c in dlg.descendants() if c.class_name() == 'ComboBox' and c.control_id() == 1040][0]
    tail_str = 'One' if str(tails) == '1' else 'Two'
    tails_c.select(tail_str)
    time.sleep(0.2)

    # Set dz
    dz_edit = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1021][0]
    dz_edit.set_text(str(dz))

    # Set alpha
    alpha_edit = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1022][0]
    alpha_edit.set_text(str(alpha))

    # Set 3rd parameter (power or n)
    param3_edit = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1023][0]
    if mode == 'a-priori':
        param3_edit.set_text(str(target_power))
    else:
        param3_edit.set_text(str(input_n))
    time.sleep(0.2)

    # Click Calculate
    calc_btns = [c for c in dlg.descendants() if c.class_name() == 'Button' and c.control_id() == 1009 and c.is_visible()]
    if not calc_btns:
        calc_btns = [c for c in dlg.descendants() if c.class_name() == 'Button' and c.window_text() == 'Calculate' and c.is_visible()]
    calc_btn = calc_btns[0]
    user32.SendMessageW(calc_btn.handle, 0x00F5, 0, 0) # BM_CLICK
    time.sleep(0.8)

    # Check for popup error
    popups = check_popup()
    message = ""
    if popups:
        popup_hwnd = popups[0]
        # Read text from static controls in popup
        msg_parts = []
        def get_popup_text(chwnd, extra):
            if win32gui.GetClassName(chwnd) == 'Static':
                t = win32gui.GetWindowText(chwnd)
                if t:
                    msg_parts.append(t)
            return True
        win32gui.EnumChildWindows(popup_hwnd, get_popup_text, None)
        message = " ".join(msg_parts).replace("\r", " ").replace("\n", " ").strip()
        print(f"POPUP DETECTED: {message}")

        # Capture screenshot of popup
        screenshot_path = f"oracle/screenshots/{vec_id}.png"
        capture_screenshot(screenshot_path)

        # Close popup (click OK)
        user32.SendMessageW(popup_hwnd, win32con.WM_COMMAND, 1, 0)
        time.sleep(0.3)

        return {
            'vec_id': vec_id,
            'delta': '',
            'critical': '',
            'df': '',
            'n_total': '',
            'actual_power': '',
            'message': message,
            'screenshot': screenshot_path,
        }

    # Read output edits
    # 1050: delta, 1051: critical t, 1052: df, 1053: total sample size / power, 1054: actual power
    edit_1050 = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1050 and c.is_visible()][0]
    edit_1051 = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1051 and c.is_visible()][0]
    edit_1052 = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1052 and c.is_visible()][0]
    edit_1053 = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1053 and c.is_visible()][0]

    delta = edit_1050.window_text().strip()
    critical = edit_1051.window_text().strip()
    df = edit_1052.window_text().strip()

    if mode == 'a-priori':
        n_total = edit_1053.window_text().strip()
        edits_1054 = [c for c in dlg.descendants() if c.class_name() == 'Edit' and c.control_id() == 1054 and c.is_visible()]
        actual_power = edits_1054[0].window_text().strip() if edits_1054 else ''
    else: # post-hoc
        n_total = str(input_n)
        actual_power = edit_1053.window_text().strip()

    screenshot_path = f"oracle/screenshots/{vec_id}.png"
    capture_screenshot(screenshot_path)

    print(f"RESULTS FOR {vec_id}:")
    print(f"  Noncentrality parameter δ (delta): {delta}")
    print(f"  Critical t:                        {critical}")
    print(f"  Df:                                {df}")
    print(f"  Total sample size (n_total):       {n_total}")
    print(f"  Actual power:                      {actual_power}")
    print(f"  Screenshot:                        {screenshot_path}")

    return {
        'vec_id': vec_id,
        'delta': delta,
        'critical': critical,
        'df': df,
        'n_total': n_total,
        'actual_power': actual_power,
        'message': '',
        'screenshot': screenshot_path,
    }

# Run GP01 and GP02 only
r1 = run_vector("GP01", "a-priori", 2, 0.5, 0.05, target_power=0.95)
r2 = run_vector("GP02", "a-priori", 2, 0.5, 0.05, target_power=0.80)
