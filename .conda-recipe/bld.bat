@echo off
"%PYTHON%" -m pip install .
if errorlevel 1 exit 1

:: Add more build steps here, if they are necessary.
