# -*- coding: utf-8 -*-
"""
PhotoCursor.exe 를 평소처럼(알림 창 켜고) 실행했을 때
"켜졌어요" 알림 창이 실제로 뜨는지, 몇 초 만에 뜨는지 확인.
사용: python start_test.py <PhotoCursor.exe 가 있는 폴더>
"""
import ctypes
import subprocess
import sys
import time
from ctypes import wintypes as wt

folder = sys.argv[1]
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowW.restype = wt.HWND
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
kernel32.OpenEventW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
kernel32.OpenEventW.restype = wt.HANDLE
kernel32.SetEvent.argtypes = [wt.HANDLE]
EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

start = time.time()
proc = subprocess.Popen([folder + "\\PhotoCursor.exe"], cwd=folder)

box = None
while time.time() - start < 20 and not box:
    box = user32.FindWindowW("#32770", "사진 커서")      # 알림 창(대화 상자)
    time.sleep(0.1)

ok = bool(box)
if box:
    print(f"알림 창이 {time.time() - start:.1f}초 만에 떴어요. 내용:")
    texts = []

    def each(h, _):
        buf = ctypes.create_unicode_buffer(1024)
        user32.GetWindowTextW(h, buf, 1024)
        if buf.value:
            texts.append(buf.value)
        return True

    user32.EnumChildWindows(box, EnumProc(each), 0)
    for t in texts:
        print("   ", t.replace("\n", "\n    "))
    user32.PostMessageW(box, 0x0010, 0, 0)               # 창 닫기
else:
    print("20초 동안 알림 창이 안 떴어요. 프로그램 상태:", "실행 중" if proc.poll() is None else f"종료됨(코드 {proc.returncode})")

ev = kernel32.OpenEventW(0x0002, False, "Local\\PhotoCursorQuit")
if ev:
    kernel32.SetEvent(ev)
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.kill()
sys.exit(0 if ok else 1)
