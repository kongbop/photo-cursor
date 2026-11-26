# -*- coding: utf-8 -*-
"""
GitHub의 Windows 컴퓨터에서 PhotoCursor.exe 를 켜 두고 진짜로 클릭을 보낸 뒤,
화면에 '지금 보이는 커서'가 클릭 사진으로 바뀌는지 확인하는 점검.

두 사진은 클릭 기준점 높이(y)가 달라서 구분할 수 있음:
  평소 사진 normal.png → y = 7,  클릭 사진 click.png → y = 1   (크기 64, 기준점 top)
사용: python click_test.py <PhotoCursor.exe 가 있는 폴더>
"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes as wt

folder = sys.argv[1]
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class CURSORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("flags", wt.DWORD), ("hCursor", wt.HANDLE), ("pt", wt.POINT)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("x", wt.DWORD), ("y", wt.DWORD), ("mask", wt.HBITMAP), ("color", wt.HBITMAP)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("data", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("extra", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("mi", MOUSEINPUT)]


user32.GetIconInfo.argtypes = [wt.HANDLE, ctypes.POINTER(ICONINFO)]
gdi32.DeleteObject.argtypes = [wt.HANDLE]
user32.SendInput.argtypes = [wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
kernel32.OpenEventW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
kernel32.OpenEventW.restype = wt.HANDLE
kernel32.SetEvent.argtypes = [wt.HANDLE]


user32.LoadCursorW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wt.HANDLE


def now_cursor():
    # 화면에 보이는 커서 대신, Windows가 기억하는 '기본 화살표' 커서의 지금 모양
    h = user32.LoadCursorW(None, 32512)
    if not h:
        return None
    ii = ICONINFO()
    if not user32.GetIconInfo(h, ctypes.byref(ii)):
        return None
    for b in (ii.mask, ii.color):
        if b:
            gdi32.DeleteObject(b)
    return (ii.x, ii.y)


def name(c):
    if c is None:
        return "알 수 없음"
    return {(32, 7): "평소 사진", (32, 1): "클릭 사진"}.get(c, f"다른 커서{c}")


def mouse(flags):
    i = INPUT(type=0, mi=MOUSEINPUT(0, 0, 0, flags, 0, 0))
    n = user32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    print(f"    SendInput {flags:#x} → {n} (err {ctypes.get_last_error()})")


def watch(label, seconds):
    seen = []
    end = time.time() + seconds
    while time.time() < end:
        n = name(now_cursor())
        if not seen or seen[-1] != n:
            seen.append(n)
        time.sleep(0.01)
    print(f"  {label}: {' → '.join(seen)}")
    return seen


print("SetCursorPos:", user32.SetCursorPos(600, 400), ctypes.get_last_error())
time.sleep(0.5)
print("켜기 전:", name(now_cursor()))

proc = subprocess.Popen([folder + "\\PhotoCursor.exe"], cwd=folder)
time.sleep(3)
user32.SetCursorPos(601, 400)       # 한 번 움직여서 새 커서가 보이게
time.sleep(0.3)
print("켠 뒤(움직인 다음):", name(now_cursor()))

results = []
for attempt in range(1, 4):
    print(f"[클릭 {attempt}] 마우스를 움직이지 않고 클릭")
    mouse(0x0002)                    # 왼쪽 누름
    pressed = watch("누르고 있는 0.15초", 0.15)
    mouse(0x0004)                    # 왼쪽 뗌
    after = watch("뗀 뒤 0.6초", 0.6)
    results.append("클릭 사진" in pressed + after)
    time.sleep(0.5)

ev = kernel32.OpenEventW(0x0002, False, "Local\\PhotoCursorQuit")
if ev:
    kernel32.SetEvent(ev)
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
user32.SetCursorPos(602, 400)
time.sleep(0.3)
print("끈 뒤:", name(now_cursor()))

ok = all(results)
print("결과:", "클릭할 때 사진이 바뀜" if ok else f"클릭해도 안 바뀐 경우 있음 {results}")
sys.exit(0 if ok else 1)
