"""
Real Oracle Collector for G*Power 3.1.9.7 (`tools/run_real_oracle_collector.py`).

Automates G*Power 3.1.9.7 on the Windows desktop, runs GP01-GP36 and selected scale vectors,
extracts exact on-screen text, saves screenshots to oracle/screenshots/<id>.png,
and writes oracle/gpower_real_vectors.csv.
"""

from __future__ import annotations

import csv
import ctypes
import os
import sys
import time
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8")

import win32service

user32 = ctypes.windll.user32
DESKTOPENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.LPWSTR, wintypes.LPARAM)
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def find_gpower_window():
    hwinsta = win32service.GetProcessWindowStation()
    desktops = []
    user32.EnumDesktopsW(
        int(hwinsta),
        DESKTOPENUMPROC(lambda name, extra: desktops.append(name) or True),
        0,
    )

    for d in desktops:
        try:
            hdesk = win32service.OpenDesktop(d, 0, False, 0x02000000)
            windows = []

            def enum_cb(hwnd, extra):
                l = user32.GetWindowTextLengthW(hwnd)
                b = ctypes.create_unicode_buffer(l + 1)
                user32.GetWindowTextW(hwnd, b, l + 1)
                if b.value.startswith("G*Power 3."):
                    windows.append(hwnd)
                return True

            user32.EnumDesktopWindows(int(hdesk), WNDENUMPROC(enum_cb), 0)
            if windows:
                return d, hdesk, windows[0]
        except Exception:
            pass
    return None, None, None


d, hdesk, gp_hwnd = find_gpower_window()
if not gp_hwnd:
    print("ERROR: G*Power 3.1.9.7 window could not be found on any desktop!")
    sys.exit(1)

print(f"[INIT] Located G*Power 3.1.9.7 on desktop: '{d}', HWND: {gp_hwnd}")
hdesk.SetThreadDesktop()

# Import Win32 GUI modules now that desktop is bound
import win32con
import win32gui
import win32ui
from PIL import Image
from pywinauto import Application

app = Application(backend="win32").connect(handle=gp_hwnd)
dlg = app.window(handle=gp_hwnd)

try:
    win32gui.ShowWindow(gp_hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(gp_hwnd)
except Exception:
    pass
time.sleep(0.5)


def ensure_test_selection():
    """Ensures 't tests' and 'Means: Difference between two dependent means (matched pairs)' are selected."""
    combos = [c for c in dlg.descendants() if c.class_name() == "ComboBox" and c.is_visible()]
    fam_c = [c for c in combos if c.control_id() == 1000]
    if fam_c and "t tests" not in fam_c[0].window_text():
        print("[SETUP] Selecting Test family -> t tests")
        fam_c[0].select("t tests")
        time.sleep(0.5)

    test_c = [c for c in dlg.descendants() if c.class_name() == "ComboBox" and c.control_id() == 1001 and c.is_visible()]
    if test_c and "two dependent means" not in test_c[0].window_text():
        print("[SETUP] Selecting Statistical test -> Means: Difference between two dependent means (matched pairs)")
        test_c[0].select("Means: Difference between two dependent means (matched pairs)")
        time.sleep(0.5)


ensure_test_selection()


def capture_window_screenshot(out_path: str):
    """Captures screenshot of G*Power main window (and any child/popup)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    rect = win32gui.GetWindowRect(gp_hwnd)
    w = max(10, rect[2] - rect[0])
    h = max(10, rect[3] - rect[1])

    hwndDC = win32gui.GetWindowDC(gp_hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # 2 = PW_CLIENTONLY/PW_RENDERFULLCONTENT
    user32.PrintWindow(gp_hwnd, saveDC.GetSafeHdc(), 2)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)

    im = Image.frombuffer(
        "RGB",
        (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
        bmpstr,
        "raw",
        "BGRX",
        0,
        1,
    )
    im.save(out_path)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(gp_hwnd, hwndDC)


def check_popup():
    """Checks for any modal popup dialogs owned by G*Power or on desktop."""
    popups = []

    def enum_cb(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            cls = win32gui.GetClassName(hwnd)
            owner = user32.GetWindow(hwnd, 4)  # GW_OWNER
            if cls == "#32770" and (owner == gp_hwnd or hwnd != gp_hwnd):
                # Ensure it's not one of G*Power's internal child panes
                parent = win32gui.GetParent(hwnd)
                if parent == 0 or parent == gp_hwnd or owner == gp_hwnd:
                    title = win32gui.GetWindowText(hwnd)
                    if title != "" and "G*Power" not in title:
                        popups.append((hwnd, title))
        return True

    win32gui.EnumDesktopWindows(hdesk, enum_cb, 0)
    return popups


def run_one_vector(
    vec_id: str,
    category: str,
    mode: str,
    tails: int | str,
    dz: float | str,
    alpha: float | str,
    target_power: float | str | None = None,
    input_n: int | str | None = None,
) -> dict:
    print(f"\n>>> Running {vec_id} [{category}] ({mode}, tails={tails}, dz={dz}, alpha={alpha}, power={target_power}, n={input_n})")

    # 1. Set Mode (Type of power analysis)
    type_c = [c for c in dlg.descendants() if c.class_name() == "ComboBox" and c.control_id() == 1002 and c.is_visible()][0]
    if mode == "a-priori":
        type_c.select("A priori: Compute required sample size - given α, power, and effect size")
    elif mode == "post-hoc":
        type_c.select("Post hoc: Compute achieved power - given α, sample size, and effect size")
    time.sleep(0.3)

    # 2. Set Tails
    tails_c = [c for c in dlg.descendants() if c.class_name() == "ComboBox" and c.control_id() == 1040 and c.is_visible()][0]
    tail_str = "One" if str(tails) == "1" else "Two"
    tails_c.select(tail_str)
    time.sleep(0.2)

    # 3. Set dz
    dz_edit = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1021 and c.is_visible()][0]
    dz_edit.set_text(str(dz))

    # 4. Set alpha
    alpha_edit = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1022 and c.is_visible()][0]
    alpha_edit.set_text(str(alpha))

    # 5. Set 3rd parameter (power or n)
    param3_edit = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1023 and c.is_visible()][0]
    if mode == "a-priori":
        param3_edit.set_text(str(target_power))
    else:
        param3_edit.set_text(str(input_n))
    time.sleep(0.2)

    # 6. Click Calculate via PostMessage so it never hangs if a modal error popup opens
    calc_btns = [c for c in dlg.descendants() if c.class_name() == "Button" and c.control_id() == 1009 and c.is_visible()]
    if not calc_btns:
        calc_btns = [c for c in dlg.descendants() if c.class_name() == "Button" and c.window_text() == "Calculate" and c.is_visible()]
    calc_btn = calc_btns[0]
    user32.PostMessageW(calc_btn.handle, 0x00F5, 0, 0)  # BM_CLICK
    time.sleep(0.7)

    # 7. Check for popup error dialog
    popups = check_popup()
    screenshot_path = f"oracle/screenshots/{vec_id}.png"

    if popups:
        popup_hwnd, popup_title = popups[0]
        # Collect all text from static elements inside popup
        msg_parts = []

        def get_popup_text(chwnd, extra):
            if win32gui.GetClassName(chwnd) == "Static":
                t = win32gui.GetWindowText(chwnd)
                if t:
                    msg_parts.append(t)
            return True

        win32gui.EnumChildWindows(popup_hwnd, get_popup_text, None)
        raw_msg = " ".join(msg_parts).replace("\r\n", " ").replace("\n", " ").strip()
        full_msg = f"[{popup_title}] {raw_msg}" if popup_title else raw_msg
        print(f"  [POPUP DETECTED] {full_msg}")

        # Capture screenshot of popup
        capture_window_screenshot(screenshot_path)

        # Dismiss popup (click OK / send BM_CLICK and WM_COMMAND)
        btn_hwnds = []
        def find_btns(ch, ex):
            if win32gui.GetClassName(ch) == "Button":
                btn_hwnds.append(ch)
            return True
        win32gui.EnumChildWindows(popup_hwnd, find_btns, None)

        if btn_hwnds:
            user32.SendMessageW(btn_hwnds[0], 0x00F5, 0, 0) # BM_CLICK
            user32.SendMessageW(popup_hwnd, win32con.WM_COMMAND, 1, btn_hwnds[0])
        else:
            user32.SendMessageW(popup_hwnd, win32con.WM_COMMAND, 1, 0)
        
        time.sleep(0.3)
        if win32gui.IsWindow(popup_hwnd):
            user32.SendMessageW(popup_hwnd, win32con.WM_CLOSE, 0, 0)
        time.sleep(0.3)

        return {
            "id": vec_id,
            "category": category,
            "mode": mode,
            "tails": str(tails),
            "dz": str(dz),
            "alpha": str(alpha),
            "target_power": str(target_power) if target_power is not None else "",
            "input_n": str(input_n) if input_n is not None else "",
            "gpower_n_total": "",
            "gpower_df": "",
            "gpower_critical": "",
            "gpower_ncp": "",
            "gpower_power": "",
            "gpower_message": full_msg,
            "screenshot": screenshot_path,
        }

    # 8. Normal calculation: read the 5 output edits
    # 1050: delta, 1051: critical t, 1052: df, 1053: total sample size / power, 1054: actual power
    edit_1050 = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1050 and c.is_visible()][0]
    edit_1051 = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1051 and c.is_visible()][0]
    edit_1052 = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1052 and c.is_visible()][0]
    edit_1053 = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1053 and c.is_visible()][0]

    delta = edit_1050.window_text().strip()
    critical = edit_1051.window_text().strip()
    df = edit_1052.window_text().strip()

    if mode == "a-priori":
        n_total = edit_1053.window_text().strip()
        edits_1054 = [c for c in dlg.descendants() if c.class_name() == "Edit" and c.control_id() == 1054 and c.is_visible()]
        actual_power = edits_1054[0].window_text().strip() if edits_1054 else ""
    else:  # post-hoc
        n_total = str(input_n)
        actual_power = edit_1053.window_text().strip()

    # Capture screenshot
    capture_window_screenshot(screenshot_path)

    print(f"  -> delta:        {delta}")
    print(f"  -> critical:     {critical}")
    print(f"  -> df:           {df}")
    print(f"  -> total N:      {n_total}")
    print(f"  -> actual power: {actual_power}")
    print(f"  -> screenshot:   {screenshot_path}")

    return {
        "id": vec_id,
        "category": category,
        "mode": mode,
        "tails": str(tails),
        "dz": str(dz),
        "alpha": str(alpha),
        "target_power": str(target_power) if target_power is not None else "",
        "input_n": str(input_n) if input_n is not None else "",
        "gpower_n_total": n_total,
        "gpower_df": df,
        "gpower_critical": critical,
        "gpower_ncp": delta,
        "gpower_power": actual_power,
        "gpower_message": "",
        "screenshot": screenshot_path,
    }


def main():
    # Load all GP01-GP36 reference vectors
    ref_path = "oracle/gpower_reference_vectors.csv"
    with open(ref_path, "r", encoding="utf-8") as f:
        gp_vectors = list(csv.DictReader(f))

    # Also pick 20 scale vectors with extreme rounding jumps (10 near 0, 10 near 1)
    scale_path = "oracle/scale_500_vectors.csv"
    scale_vectors_selected = []
    if os.path.exists(scale_path):
        with open(scale_path, "r", encoding="utf-8") as f:
            all_scale = [r for r in csv.DictReader(f) if r["mode"] == "a-priori"]
        near_0 = sorted(all_scale, key=lambda r: float(r["rounding_jump_n"]))[:10]
        near_1 = sorted(all_scale, key=lambda r: float(r["rounding_jump_n"]), reverse=True)[:10]
        for r in near_0:
            r["category"] = f"scale_near0_jump_{float(r['rounding_jump_n']):.4f}"
            scale_vectors_selected.append(r)
        for r in near_1:
            r["category"] = f"scale_near1_jump_{float(r['rounding_jump_n']):.4f}"
            scale_vectors_selected.append(r)

    all_targets = gp_vectors + scale_vectors_selected
    print(f"Total vectors to collect: {len(all_targets)} (36 GP + {len(scale_vectors_selected)} scale)")

    fieldnames = [
        "id",
        "category",
        "mode",
        "tails",
        "dz",
        "alpha",
        "target_power",
        "input_n",
        "gpower_n_total",
        "gpower_df",
        "gpower_critical",
        "gpower_ncp",
        "gpower_power",
        "gpower_message",
        "screenshot",
    ]

    out_csv = "oracle/gpower_real_vectors.csv"
    results = []

    for vec in all_targets:
        vid = vec["id"]
        vcat = vec.get("category", "")
        vmode = vec["mode"]
        vtails = vec["tails"]
        vdz = vec["dz"]
        valpha = vec["alpha"]
        vpower = vec.get("target_power")
        vn = vec.get("input_n")

        # Skip empty strings
        vpower = float(vpower) if vpower not in [None, ""] else None
        vn = int(vn) if vn not in [None, ""] else None

        res = run_one_vector(
            vec_id=vid,
            category=vcat,
            mode=vmode,
            tails=vtails,
            dz=vdz,
            alpha=valpha,
            target_power=vpower,
            input_n=vn,
        )
        results.append(res)

        # Write incrementally to CSV so progress is saved even if interrupted
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"\n[DONE] Successfully collected {len(results)} vectors into {out_csv}!")


if __name__ == "__main__":
    main()
