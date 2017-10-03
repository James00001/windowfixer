description = """
This tool can save and restore the window positions of specific programs.
"""

# This only works on Windows, but could be extended for Mac and Linux
# support by adding platform-specific replacements for Fixer.each_window()
# and the WindowObj class.

#-----------------------------------------------------------------------

# Standard packages
import os
from ConfigParser import RawConfigParser
import re
import time
import subprocess

# Pip packages
# (from pywin32)
import win32gui
import win32con

#-----------------------------------------------------------------------

class BadMatchError(Exception): pass
class BadStateError(Exception): pass
class IniFileNotFoundError(Exception): pass
class IniFileNotWriteableError(Exception): pass
class SkipSaveWindowNotFoundError(Exception): pass

#-----------------------------------------------------------------------

class WindowObj(object):
    
    """
    This object encapsulates a window handle, and provides
    convenience functions to get the properties we need.
    """
    
    def __init__(self, hwnd):
        self.hwnd = hwnd
    
    def title(self):
        return win32gui.GetWindowText(self.hwnd)
    
    def rect(self):
        return win32gui.GetWindowRect(self.hwnd)
    
    def get_position(self):
        r = self.rect()
        return (r[0], r[1], r[2] - r[0], r[3] - r[1])
    
    def set_position(self, x, y, w, h):
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, x, y, w, h, 0)

    def maximize(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)

    def minimize(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_MINIMIZE)

    def restore(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
    
    def get_state(self):
        st = win32gui.GetWindowPlacement(self.hwnd)[1]
        if st in (win32con.SW_MAXIMIZE, win32con.SW_SHOWMINIMIZED):
            return "minimized"
        if st in (win32con.SW_MAXIMIZE, win32con.SW_SHOWMAXIMIZED):
            return "maximized"
        return "normal"

    def __str__(self):
        return "{}:{}".format(self.hwnd, self.title())

#-----------------------------------------------------------------------

class Fixer(object):
    
    """
    Given a pattern that matches one or more window titles, this class
    can adjust the state of all matching windows, including support for
    launching an executable if the desired window is not found.
    """
    
    def __init__(self, name, title, match, state, x, y, w, h, command, run_wait):
        if match not in ["first", "all"]:
            raise BadMatchError("Invalid match mode '{}'; Should be 'first' or 'all'".format(match))
        if state not in ["normal", "maximized", "minimized"]:
            raise BadStateError("Invalid state '{}' should be 'normal', 'minimized' or 'maximized'".format(state))
        self.name = name
        self.title = title
        self.match = match
        self.state = state
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.command = command
        self.run_wait = run_wait
    
    def each_window(self):
        window_list = []
        def callback(hwnd, extra):
            window = WindowObj(hwnd)
            if self.title.match(window.title()):
                window_list.append(window)
        win32gui.EnumWindows(callback, None)
        if self.match == "first":
            return window_list[0:1]
        return window_list
    
    def save(self):
        print "Save current position..."
        for win in self.each_window():
            return win
        raise SkipSaveWindowNotFoundError("Window title was not found, skipping...")
    
    def fix(self):
        if self.state == "normal" and (self.x is None or self.y is None or self.w is None or self.h is None):
            print "x={} y={} w={} h={}".format(self.x, self.y, self.w, self.h)
            print "WARNING: Incomplete saved position. Edit the config file, or run with -s after manually positioning the window"
            return
        found = self._fix_matching_windows()
        if not found:
            if self.command:
                print self.command
                subprocess.Popen([self.command])
                start = time.time()
                while time.time() < start + self.run_wait:
                    time.sleep(0.2)
                    found = self._fix_matching_windows()
                    if found: break
                if not found:
                    print "Started command, waited {} seconds, and gave up.".format(self.run_wait)
        if not found:
            print "Unable to find matching window. Skipping."
    
    def _fix_matching_windows(self):
        found = False
        for win in self.each_window():
            if self.state == "maximized":
                print "Maximize window"
                win.maximize()
            elif self.state == "minimized":
                win.minimize()
            elif self.state == "normal":
                print "Move window to x={} y={} w={} h={}".format(self.x, self.y, self.w, self.h)
                win.restore()
                win.set_position(self.x, self.y, self.w, self.h)
            else:
                raise BadStateError("Invalid state '{}' should be 'normal', 'minimized' or 'maximized'".format(state))
            found = True
        return found

#-----------------------------------------------------------------------

class WindowFixer(object):
    
    """
    This class takes a windowfixer.ini file, reads it in, and creates
    a Fixer object for each section. The options are documented in
    windowfixer.ini.example
    
    It also has an option save mode that reads the current locations
    of matching windows, and saves them, re-writing the ini file.
    """
    
    def __init__(self, ini_file="windowfixer.ini", save_mode=False):
        self.save_mode = save_mode
        self.ini_file = ini_file
        if not os.path.isfile(ini_file):
            raise IniFileNotFoundError("Config file '{}' does not exist yet. See windowfixer.ini.example".format(ini_file))
        if self.save_mode and not os.access(ini_file, os.W_OK):
            raise IniFileNotWriteableError("Config file '{}' exists, but is not writeable, ans save mode was requested.".format(ini_file))
        self.conf = RawConfigParser()
        self.conf.read(ini_file)
    
    def run(self):
        for section in self.conf.sections():
            self.handle_section(section)
        if self.save_mode:
            with open(self.ini_file, "w") as f:
                self.conf.write(f)
    
    def handle_section(self, section):
        print "[{}]".format(section)
        if not self.conf.has_option(section, "title"):
            print "Section [{}] has no title pattern.".format(section)
            return
        known_options = [
            "title",
            "match",
            "state",
            "x",
            "y",
            "w",
            "h",
            "run_if_not_found",
            "run_keep_trying",
            ]
        for opt in self.conf.options(section):
            if opt not in known_options:
                print "WARNING: Unknown option {}= in section [{}]".format(opt, section)
        try:
            fixer = Fixer(
                name=section,
                title=re.compile(self.read(section, "title")),
                match=self.read(section, "match", "all"),
                state=self.read(section, "state", "normal"),
                x=self.readint(section, "x", None),
                y=self.readint(section, "y", None),
                w=self.readint(section, "w", None),
                h=self.readint(section, "h", None),
                command=self.read(section, "run_if_not_found", None),
                run_wait=self.readfloat(section, "run_keep_trying", 5.0)
                )
        except BadMatchError, e:
            print e
            return
        if self.save_mode:
            try:
                win = fixer.save()
                state = win.get_state()
                self.conf.set(section, "state", state)
                if state == "normal":
                    (x, y, w, h) = win.get_position()
                    print (x, y, w, h)
                    self.conf.set(section, "x", x)
                    self.conf.set(section, "y", y)
                    self.conf.set(section, "w", w)
                    self.conf.set(section, "h", h)
                else:
                    print state
                    self.delete_xywh(section)
            except SkipSaveWindowNotFoundError, e:
                print e
        else:
            fixer.fix()
    
    def read(self, section, opt, default=None):
        if self.conf.has_option(section, opt):
            return self.conf.get(section, opt)
        return default

    def readint(self, section, opt, default=None):
        if self.conf.has_option(section, opt):
            val = self.conf.get(section, opt)
            if val.strip() == "": return default
            return self.conf.getint(section, opt)
        return default

    def readfloat(self, section, opt, default=None):
        if self.conf.has_option(section, opt):
            val = self.conf.get(section, opt)
            if val.strip() == "": return default
            return self.conf.getfloat(section, opt)
        return default
    
    def delete_xywh(self, section):
        for opt in ["x", "y", "w", "h"]:
            self.delete_opt(section, opt)
    
    def delete_opt(self, section, opt):
        if self.conf.has_option(section, opt):
            self.conf.remove_option(section, opt)
            

#-----------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser= argparse.ArgumentParser(description=description)
    parser.add_argument("--conf", default="windowfixer.ini", metavar="INIFILE", help="Provide an alternate location for the config file. By default, look for windowfixer.ini in the current working directory.")
    parser.add_argument("-s", "--save", action="store_true", help="Instead of moving windows, save their current locations in the config file to be restored later.")
    args = parser.parse_args()
    app = WindowFixer(ini_file = args.conf, save_mode=args.save)
    app.run()
    