@ECHO OFF
IF EXIST windowfixer.py GOTO dirok
ECHO Run this batch file in the same folder as windowfixer.py
GOTO done

:dirok
RMDIR /S/Q build
RMDIR /S/Q dist
python setup.py py2exe
IF EXIST dist\windowfixer.exe GOTO exeok
ECHO FAILED: Unable to create windowfixer.exe is py2exe installed?
GOTO done

:exeok
MOVE /Y dist\windowfixer.exe windowfixer.exe
RMDIR /S/Q build
RMDIR /S/Q dist
ECHO OK: Done! windowfixer.exe was created.

:done
