@echo off
REM Setup script for Windows - Creates venv and installs dependencies
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! Virtual environment created and dependencies installed.
echo.
echo To activate the venv in the future, run:
echo   venv\Scripts\activate.bat
echo.
echo Then start the app with:
echo   python app.py
pause
