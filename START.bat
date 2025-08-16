@echo off
title First AI Utility Launcher

echo.
echo #######################################################
echo #        Starting First AI Utility...                 #
echo # The launcher will now verify the environment.       #
echo # This may take a moment on the first run.            #
echo #######################################################
echo.

REM This script calls the Python launcher, which handles all the
REM complex setup steps like creating a virtual environment and
REM installing dependencies from requirements.txt.

python run.py

echo.
echo Application has been closed.
