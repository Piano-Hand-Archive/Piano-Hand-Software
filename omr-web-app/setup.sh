#!/bin/bash
# Setup script for macOS/Linux - Creates venv and installs dependencies

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! Virtual environment created and dependencies installed."
echo ""
echo "To activate the venv in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "Then start the app with:"
echo "  python app.py"
