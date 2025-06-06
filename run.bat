@echo off
echo Checking dependencies...
pip install --quiet --disable-pip-version-check pillow numpy
echo Complete opening application
python "%~dp0app.py"
pause
