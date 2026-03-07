# Setup script for Windows PowerShell - Creates venv and installs dependencies
Write-Host "Creating virtual environment..." -ForegroundColor Green
python -m venv venv

Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Setup complete! Virtual environment created and dependencies installed." -ForegroundColor Green
Write-Host ""
Write-Host "To activate the venv in the future, run:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Then start the app with:" -ForegroundColor Cyan
Write-Host "  python app.py" -ForegroundColor White
