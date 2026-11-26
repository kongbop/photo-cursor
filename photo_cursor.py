# -*- coding: utf-8 -*-
"""
사진 커서 (Windows 전용)
- 컴퓨터 전체의 마우스 커서를 내 사진으로 바꾸고
- 클릭하는 순간 잠깐 다른 사진으로 바뀌게 합니다.
- 설정은 같은 폴더의 settings.txt 에서 바꿉니다.
- 끄기: Ctrl + Alt + Q, 또는 프로그램을 한 번 더 실행해서 "예"
"""

import os
import sys
import struct
import queue
import threading

APP = "사진 커서"

# exe로 묶였을 때는 exe가 있는 폴더, 아니면 이 .py 파일이 있는 폴더
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(os.path.abspath(sys.executable))
else:
    HERE = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(HERE, "settings.txt")

DEFAULTS = {
    "NORMAL_IMAGE": "normal.png",
    "CLICK_IMAGE": "click.png",
    "TEXT_IMAGE": "text.png",
    "LINK_IMAGE": "link.png",
    "SIZE": "64",
    "CLICK_TIME": "0.3",
    "OPACITY": "1.0",
    "CLICK_OPACITY": "1.0",
    "HOTSPOT": "top",
    "HOLD_WHILE_PRESSED": "no",
    "RIGHT_CLICK_TOO": "yes",
    "SHOW_START_MESSAGE": "yes",
    "DEBUG": "no",
}

SETTINGS_TEMPLATE = """\
# ───────────── 사진 커서 설정 ─────────────
# '=' 오른쪽 값만 바꾸고 저장(Ctrl + S)하세요.
# 바꾼 뒤에는 Ctrl + Alt + Q 로 끄고 PhotoCursor.exe 를 다시 실행해야 적용돼요.
# '#' 으로 시작하는 줄은 설명이라 프로그램이 읽지 않아요.

# [사진 파일] 이 폴더 안에 있는 사진 이름. 투명 배경 PNG가 가장 자연스러워요.
# 평소(화살표) 커서 사진
NORMAL_IMAGE = normal.png
# 클릭하는 순간 잠깐 보이는 사진 (어디서 클릭하든 이 사진)
CLICK_IMAGE = click.png
# 글자 입력칸 위(I자 커서)일 때 사진. 파일이 없거나 비워 두면 Windows 원래 I자 커서
TEXT_IMAGE = text.png
# 링크·버튼 위(손가락 커서)일 때 사진. 파일이 없거나 비워 두면 Windows 원래 손가락
LINK_IMAGE = link.png

# [크기] 커서 크기(픽셀). 16 ~ 256. Windows 기본 커서는 32 정도예요.
SIZE = 64

# [클릭 시간] 클릭 사진이 보이는 시간(초). 0.3 이면 0.3초 동안 보였다가 돌아와요.
CLICK_TIME = 0.3

# [불투명도] 1.0 = 선명, 0.5 = 반쯤 비침, 0.2 = 거의 투명
# OPACITY 는 평소·글자칸·링크 사진에, CLICK_OPACITY 는 클릭 사진에 적용돼요.
OPACITY = 1.0
CLICK_OPACITY = 1.0

# [클릭 기준점] 사진의 어느 지점이 실제로 클릭되는지 정해요.
#   top     = 사진 맨 위 가운데 (머리 꼭대기)
#   center  = 사진 정가운데
#   topleft = 사진 왼쪽 위 끝 (보통 화살표 커서와 같은 위치)
#   50, 10  = 숫자로 직접: 가로 50%(0 왼쪽 ~ 100 오른쪽), 세로 10%(0 위 ~ 100 아래)
# 기준은 배경을 뺀, 실제로 사진이 있는 부분이에요.
HOTSPOT = top

# [누르고 있을 때] yes 면 마우스를 누르고 있는 동안 계속 클릭 사진을 보여 줘요.
HOLD_WHILE_PRESSED = no

# [오른쪽 클릭] yes 면 오른쪽 클릭에도 사진이 바뀌어요.
RIGHT_CLICK_TOO = yes

# [시작 알림] yes 면 켤 때 "켜졌어요" 창을 띄워요. 귀찮으면 no.
SHOW_START_MESSAGE = yes

# [문제 기록] yes 면 이 폴더에 debug.txt 를 만들어, 클릭할 때마다 무슨 일이 있었는지 적어요.
# 잘 안 될 때 원인을 찾는 용도예요. 평소에는 no.
DEBUG = no
"""


def load_settings():
    """settings.txt 를 읽어서 dict 로. 없으면 기본 설정 파일을 만들어 둠."""
    cfg = dict(DEFAULTS)
    if not os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                f.write(SETTINGS_TEMPLATE)
        except OSError:
            pass
        return cfg
    with open(SETTINGS_FILE, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip().upper()
            v = v.split("#", 1)[0].strip().strip('"').strip("'")
            if k in cfg:
                cfg[k] = v
    return cfg


def as_bool(v):
    return str(v).strip().lower() in ("yes", "y", "true", "1", "on", "예", "네")


def as_num(v, default, lo, hi, cast=float):
    try:
        n = cast(float(v))
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def parse_hotspot(v):
    v = str(v).strip().lower().strip("()")
    if v in ("top", "center", "topleft"):
        return v
    try:
        a, b = [float(x) for x in v.replace(" ", "").split(",")]
        return (max(0.0, min(100.0, a)), max(0.0, min(100.0, b)))
    except ValueError:
        return "top"


def make_cur(src, dst, size, hotspot, opacity=1.0):
    """PNG/JPG 사진을 Windows 커서(.cur) 파일로 변환"""
    from PIL import Image
    img = Image.open(src).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    opacity = max(0.05, min(1.0, float(opacity)))
    if opacity < 1.0:
        canvas.putalpha(canvas.getchannel("A").point(lambda v: int(v * opacity)))
    px = canvas.load()
    w = h = size
    left, top, right, bottom = canvas.getbbox() or (0, 0, w, h)   # 사진이 실제로 있는 범위
    if hotspot == "center":
        hx, hy = w // 2, h // 2
    elif hotspot == "top":
        hx, hy = (left + right) // 2, top
    elif hotspot == "topleft":
        hx, hy = left, top
    else:
        px_, py_ = hotspot
        hx = left + int((right - left) * px_ / 100)
        hy = top + int((bottom - top) * py_ / 100)
    hx, hy = max(0, min(w - 1, hx)), max(0, min(h - 1, hy))

    xor = bytearray()
    for y in range(h - 1, -1, -1):          # 아래 줄부터 저장 (BMP 규칙)
        for x in range(w):
            r, g, b, a = px[x, y]
            xor += bytes((b, g, r, a)) if a else b"\0\0\0\0"
    row = ((w + 31) // 32) * 4
    andm = bytearray()
    for y in range(h - 1, -1, -1):
        bits = bytearray(row)
        for x in range(w):
            if px[x, y][3] == 0:
                bits[x // 8] |= 0x80 >> (x % 8)
        andm += bits

    body = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0,
                       len(xor) + len(andm), 0, 0, 0, 0) + xor + andm
    head = struct.pack("<HHH", 0, 2, 1)
    entry = struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, hx, hy, len(body), 22)
    with open(dst, "wb") as f:
        f.write(head + entry + body)


def main():
    check_mode = "--check" in sys.argv          # 자동 점검용: 창 없이 확인만 하고 종료
    log_lines = []

    dbg = [os.environ.get("PHOTOCURSOR_DEBUG")]     # 기록 파일 경로 (없으면 기록 안 함)

    def log(msg):
        log_lines.append(msg)
        if dbg[0]:
            try:
                with open(dbg[0], "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
            except OSError:
                pass
        try:
            print(msg)
        except Exception:
            pass

    if os.name != "nt":
        log("이 프로그램은 Windows에서만 작동해요.")
        return 1

    import ctypes
    from ctypes import wintypes as wt

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
    user32.SetWindowsHookExW.restype = wt.HHOOK
    user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = [wt.HHOOK]
    user32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT, ctypes.c_int, ctypes.c_int, wt.UINT]
    user32.LoadImageW.restype = wt.HANDLE
    user32.CopyIcon.argtypes = [wt.HANDLE]
    user32.CopyIcon.restype = wt.HANDLE
    user32.SetSystemCursor.argtypes = [wt.HANDLE, wt.DWORD]
    user32.SetSystemCursor.restype = wt.BOOL
    user32.SystemParametersInfoW.argtypes = [wt.UINT, wt.UINT, ctypes.c_void_p, wt.UINT]
    user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
    user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
    user32.RegisterHotKey.restype = wt.BOOL
    user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
    user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.MessageBoxW.argtypes = [wt.HWND, wt.LPCWSTR, wt.LPCWSTR, wt.UINT]
    user32.MessageBoxW.restype = ctypes.c_int
    kernel32.GetCurrentThreadId.restype = wt.DWORD

    class CURSORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hCursor", wt.HANDLE), ("pt", wt.POINT)]

    user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursor.argtypes = [wt.HANDLE]
    user32.SetCursor.restype = wt.HANDLE
    user32.GetForegroundWindow.restype = wt.HWND
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.AttachThreadInput.argtypes = [wt.DWORD, wt.DWORD, wt.BOOL]
    user32.AttachThreadInput.restype = wt.BOOL
    user32.PeekMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]

    class ICONINFO(ctypes.Structure):
        _fields_ = [("fIcon", wt.BOOL), ("x", wt.DWORD), ("y", wt.DWORD),
                    ("mask", wt.HBITMAP), ("color", wt.HBITMAP)]

    gdi32 = ctypes.WinDLL("gdi32")
    user32.GetIconInfo.argtypes = [wt.HANDLE, ctypes.POINTER(ICONINFO)]
    gdi32.GetBitmapBits.argtypes = [wt.HBITMAP, wt.LONG, ctypes.c_void_p]
    gdi32.GetBitmapBits.restype = wt.LONG
    gdi32.DeleteObject.argtypes = [wt.HANDLE]
    user32.LoadCursorW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]
    user32.LoadCursorW.restype = wt.HANDLE
    user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]

    def fingerprint(h):
        """커서 그림의 지문 (같은 그림이면 같은 숫자)"""
        import zlib
        ii = ICONINFO()
        if not h or not user32.GetIconInfo(h, ctypes.byref(ii)):
            return None
        crc = zlib.crc32(struct.pack("<II", ii.x, ii.y))
        for b in (ii.color, ii.mask):
            if b:
                buf = ctypes.create_string_buffer(256 * 256 * 4 * 2)
                n = gdi32.GetBitmapBits(b, len(buf), buf)
                crc = zlib.crc32(buf.raw[:max(0, n)], crc)
                gdi32.DeleteObject(b)
        return crc
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
    kernel32.CreateMutexW.restype = wt.HANDLE
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.BOOL, wt.LPCWSTR]
    kernel32.CreateEventW.restype = wt.HANDLE
    kernel32.SetEvent.argtypes = [wt.HANDLE]
    kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    kernel32.WaitForSingleObject.restype = wt.DWORD

    MB_OK_INFO = 0x40 | 0x40000           # 정보 아이콘 + 맨 앞에 띄우기
    MB_ERROR = 0x10 | 0x40000
    MB_YESNO_Q = 0x04 | 0x20 | 0x40000
    IDYES = 6

    def restore_cursors():
        user32.SystemParametersInfoW(0x0057, 0, None, 0)   # SPI_SETCURSORS: 원래 커서로

    def alert(msg):
        log(msg)
        if not check_mode:
            user32.MessageBoxW(None, msg, APP, MB_ERROR)

    # ── 이미 켜져 있으면: 끌지 물어보기 ──
    quit_event = kernel32.CreateEventW(None, True, False, "Local\\PhotoCursorQuit")
    mutex = kernel32.CreateMutexW(None, False, "Local\\PhotoCursorRunning")
    if ctypes.get_last_error() == 183 and not check_mode:   # ERROR_ALREADY_EXISTS
        ans = user32.MessageBoxW(None, "사진 커서가 이미 켜져 있어요.\n끌까요?", APP, MB_YESNO_Q)
        if ans == IDYES:
            kernel32.SetEvent(quit_event)
            restore_cursors()
        return 0

    # ── 1) 설정 읽기 ──
    cfg = load_settings()
    size = int(as_num(cfg["SIZE"], 64, 16, 256, int))
    click_time = as_num(cfg["CLICK_TIME"], 0.3, 0.02, 10)
    opacity = as_num(cfg["OPACITY"], 1.0, 0.05, 1.0)
    click_opacity = as_num(cfg["CLICK_OPACITY"], 1.0, 0.05, 1.0)
    hotspot = parse_hotspot(cfg["HOTSPOT"])
    hold = as_bool(cfg["HOLD_WHILE_PRESSED"])
    right_too = as_bool(cfg["RIGHT_CLICK_TOO"])
    show_start = as_bool(cfg["SHOW_START_MESSAGE"])
    if as_bool(cfg["DEBUG"]) and not dbg[0]:
        dbg[0] = os.path.join(HERE, "debug.txt")
        try:
            open(dbg[0], "w", encoding="utf-8").close()     # 켤 때마다 새로 적기
        except OSError:
            dbg[0] = None
    log(f"설정: 크기 {size}, 클릭 시간 {click_time}, 불투명도 {opacity}/{click_opacity}, 기준점 {hotspot}")

    # ── 2) 사진 → 커서 파일 만들기 ──
    cur_dir = os.path.join(os.environ.get("LOCALAPPDATA") or HERE, "PhotoCursor")
    os.makedirs(cur_dir, exist_ok=True)
    paths = {}
    jobs = [("normal", cfg["NORMAL_IMAGE"], opacity, True),
            ("click", cfg["CLICK_IMAGE"], click_opacity, True),
            ("text", cfg["TEXT_IMAGE"], opacity, False),
            ("link", cfg["LINK_IMAGE"], opacity, False)]
    for key, name, op, required in jobs:
        if not name:
            continue
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            if required:
                alert(f"사진 파일을 찾을 수 없어요: {name}\n\n"
                      f"PhotoCursor.exe 와 같은 폴더에 넣거나,\n"
                      f"settings.txt 의 파일 이름을 확인해 주세요.")
                return 2
            log(f"{name} 없음 → 그 자리는 Windows 원래 커서")
            continue
        dst = os.path.join(cur_dir, key + ".cur")
        try:
            make_cur(src, dst, size, hotspot, op)
        except Exception as e:
            alert(f"사진을 커서로 바꾸지 못했어요: {name}\n{e}")
            return 2
        paths[key] = dst

    cursors = {}
    for key, p in paths.items():
        h = user32.LoadImageW(None, p, 2, size, size, 0x0010)   # IMAGE_CURSOR, LR_LOADFROMFILE
        if not h:
            alert(f"커서를 불러오지 못했어요: {p}")
            return 2
        cursors[key] = h
    log(f"커서 준비 완료: {', '.join(cursors)}")

    prints = {fingerprint(h): key for key, h in cursors.items()}

    def on_screen():
        ci = CURSORINFO(cbSize=ctypes.sizeof(CURSORINFO))
        if not user32.GetCursorInfo(ctypes.byref(ci)):
            return f"읽기 실패(err {ctypes.get_last_error()})"
        if not ci.hCursor:
            return f"커서 숨김(flags {ci.flags})"
        return prints.get(fingerprint(ci.hCursor), "Windows 다른 커서")

    slots = {32512: "normal"}                 # 기본 화살표
    if "text" in cursors:
        slots[32513] = "text"                 # I자(글자)
    if "link" in cursors:
        slots[32649] = "link"                 # 손가락(링크)

    lock = threading.Lock()

    def set_cursor(mode):
        with lock:
            ok = True
            for cid, key in slots.items():
                c = user32.CopyIcon(cursors["click" if mode == "click" else key])
                r = user32.SetSystemCursor(c, cid)
                if dbg[0]:
                    now = prints.get(fingerprint(user32.LoadCursorW(None, cid)), "다른 그림")
                    log(f"{mode} 로 바꾸기 (자리 {cid}): {'성공' if r else '실패'} err={ctypes.get_last_error()} → 저장된 그림: {now}")
                ok &= bool(r)
            return ok

    def refresh_screen():
        """커서 그림을 바꿔도 Windows는 마우스가 움직이기 전까지 화면에 예전 그림을 보여 줌.
        그래서 지금 보이는 커서를 다시 그리게 만든다."""
        ci = CURSORINFO(cbSize=ctypes.sizeof(CURSORINFO))
        shown = ci.hCursor if user32.GetCursorInfo(ctypes.byref(ci)) else None
        attached = False
        # 1) 지금 앞에 있는 창의 입력에 잠깐 연결해서, 같은 커서를 다시 설정 → 바로 다시 그려짐
        #    (마우스를 누르고 있는 동안처럼 창이 마우스를 붙잡고 있을 때도 통함)
        me = kernel32.GetCurrentThreadId()
        fg = user32.GetForegroundWindow()
        tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        if shown and tid and tid != me:
            attached = bool(user32.AttachThreadInput(me, tid, True))
            if attached:
                user32.SetCursor(None)
                user32.SetCursor(shown)
                user32.AttachThreadInput(me, tid, False)
        # 2) 마우스를 제자리로 한 번 옮겨서, 창이 커서를 새로 고르게 함
        pt = wt.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            user32.SetCursorPos(pt.x, pt.y)
        if dbg[0]:
            cls = ctypes.create_unicode_buffer(64)
            if fg:
                user32.GetClassNameW(fg, cls, 64)
            log(f"  다시 그리기: 앞 창={cls.value or '-'} 연결={'성공' if attached else '실패'} "
                f"→ 화면 커서: {on_screen()}")
            threading.Timer(0.08, lambda: log(f"  0.08초 뒤 화면 커서: {on_screen()}")).start()

    # 자동 점검: 커서를 한 번 바꿔 보고 되돌린 뒤 종료
    if check_mode:
        a = set_cursor("normal")
        b = set_cursor("click")
        restore_cursors()
        log(f"커서 바꾸기 {'성공' if a and b else '실패'}")
        test_hook = user32.SetWindowsHookExW(14, HOOKPROC(lambda n, w, l: user32.CallNextHookEx(None, n, w, l)), None, 0)
        log(f"마우스 감지 {'성공' if test_hook else '실패(점검 환경 제한일 수 있음)'}")
        if test_hook:
            user32.UnhookWindowsHookEx(test_hook)
        try:
            with open(os.path.join(HERE, "check_result.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(log_lines) + "\n")
        except OSError:
            pass
        return 0 if (a and b) else 3

    # ── 3) 커서 바꾸는 일꾼 스레드 (마우스 감지는 빨리 끝나야 해서 따로) ──
    q = queue.Queue()

    def worker():
        user32.PeekMessageW(ctypes.byref(wt.MSG()), None, 0, 0, 0)   # 이 스레드에 입력 큐 만들기
        pressed = False
        expired = True
        gen = 0
        while True:
            cmd, arg = q.get()
            if dbg[0]:
                log({"down": "▼ 누름", "up": "▲ 뗌", "timeout": "⏱ 시간 끝", "quit": "끄기"}.get(cmd, cmd) + (f" #{arg}" if arg else ""))
            if cmd == "quit":
                break
            if cmd == "down":
                pressed = True
                expired = False
                gen += 1
                set_cursor("click")
                refresh_screen()
                threading.Timer(click_time, q.put, args=(("timeout", gen),)).start()
            elif cmd == "up":
                pressed = False
                if hold and expired:
                    set_cursor("normal")
                refresh_screen()      # 손을 떼면 창이 마우스를 놓아 주므로 한 번 더 다시 그리기
            elif cmd == "timeout" and arg == gen:
                expired = True
                if not (hold and pressed):
                    set_cursor("normal")
                    refresh_screen()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # ── 4) 컴퓨터 전체 마우스 클릭 감지 ──
    DOWN = {0x0201} | ({0x0204} if right_too else set())
    UP = {0x0202} | ({0x0205} if right_too else set())

    @HOOKPROC
    def mouse_proc(n, wparam, lparam):
        if n == 0:
            if wparam in DOWN:
                q.put(("down", None))
            elif wparam in UP:
                q.put(("up", None))
        return user32.CallNextHookEx(None, n, wparam, lparam)

    hook = user32.SetWindowsHookExW(14, mouse_proc, None, 0)   # WH_MOUSE_LL
    if not hook:
        alert("마우스 감지를 시작하지 못했어요.")
        return 2

    main_tid = kernel32.GetCurrentThreadId()

    # 프로그램을 한 번 더 실행해서 "끄기"를 고르면 여기로 신호가 옴
    def wait_quit():
        kernel32.WaitForSingleObject(quit_event, 0xFFFFFFFF)
        user32.PostThreadMessageW(main_tid, 0x0012, 0, 0)       # WM_QUIT
    threading.Thread(target=wait_quit, daemon=True).start()

    # Ctrl + Alt + Q 로 끄기
    hotkey_ok = user32.RegisterHotKey(None, 1, 0x0002 | 0x0001 | 0x4000, ord("Q"))

    set_cursor("normal")

    if show_start:
        how = "Ctrl + Alt + Q" if hotkey_ok else "PhotoCursor.exe 한 번 더 실행 → 예"
        msg = f"사진 커서가 켜졌어요.\n\n끄기: {how}"
        if not hotkey_ok:
            msg += "\n(Ctrl + Alt + Q 는 다른 프로그램이 쓰고 있어서 못 써요)"
        # 알림 창이 떠 있는 동안에도 마우스 감지가 멈추지 않게 따로 띄움
        threading.Thread(target=user32.MessageBoxW, args=(None, msg, APP, MB_OK_INFO), daemon=True).start()

    msg = wt.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312:   # WM_HOTKEY
                break
    finally:
        user32.UnhookWindowsHookEx(hook)
        if hotkey_ok:
            user32.UnregisterHotKey(None, 1)
        q.put(("quit", None))
        t.join(timeout=1)
        restore_cursors()
    return 0


if __name__ == "__main__":
    sys.exit(main())
