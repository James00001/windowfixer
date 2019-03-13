# This is a minimalist wrapper around just a few Windows API calls.
# It more or less mimics a few of the same functions in pywin32's win32gui,
# but does not require anything but the built-in ctypes module.

import ctypes
from ctypes import wintypes
user32 = ctypes.windll.user32

#-----------------------------------------------------------------------

_EnumWindows_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [_EnumWindows_callback, wintypes.LPARAM]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
SW_SHOWMAXIMIZED = 3
SW_SHOWMINIMIZED = 2
SW_SHOWMINNOACTIVE = 7
SW_MAXIMIZE = 3
SW_MINIMIZE = 6
SW_RESTORE = 9

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
        ]

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]

user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOP = 0

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
        ]

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("showCmd", ctypes.c_uint),
        ("ptMinPosition", POINT),
        ("ptMaxPosition", POINT),
        ("rcNormalPosition", RECT),
        ]
    def __getitem__(self, index):
        if index == 0: return self.length
        if index == 1: return self.flags
        if index == 2: return self.showCmd
        if index == 3: return self.ptMinPosition
        if index == 4: return self.ptMaxPosition
        if index == 5: return self.rcNormalPosition
        raise IndexError
user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.POINTER(WINDOWPLACEMENT)]

#-----------------------------------------------------------------------

def EnumWindows(callback):
    if not user32.EnumWindows(_EnumWindows_callback(callback), 42):
        raise ctypes.WinError()

def GetWindowText(hwnd):
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buffer = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buffer, length)
    title = str(buffer.value)
    return title

def GetWindowRect(hwnd):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)

def SetWindowPos(hwnd, after_hwnd, x, y, w, h, flags):
    user32.SetWindowPos(hwnd, after_hwnd, x, y, w, h, flags)

def ShowWindow(hwnd, show_type):
    user32.ShowWindow(hwnd, show_type)
    
def GetWindowPlacement(hwnd):
    wp = WINDOWPLACEMENT()
    wp.length = ctypes.sizeof(wp)
    user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
    return wp


