# Piano Hand Web App

A web application to upload an image or capture a photo with your camera. The application will process the image using `homr` and convert it into a valid MusicXML file.

## Setup and Installation

### Quick Setup (Automated)

**Windows:**
- **Command Prompt (cmd.exe):** Run `setup.bat`
- **PowerShell:** Run `.\setup.ps1`

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

This will automatically create a virtual environment and install all dependencies.

### Manual Setup

If you prefer to set up manually:

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Run the Application

1.  **Start the Flask server:**
    ```bash
    python app.py
    ```

2.  Open your web browser and go to `http://127.0.0.1:5001` (port 5001 avoids a conflict with macOS AirPlay on 5000, which can show HTTP 403). Override with `PORT=8080 python app.py` if needed.

## How to Use

-   **Upload Image File:** Click "Choose File", select a PNG, JPG, or JPEG file, and click "Upload & Process Image". The image will be sent directly to `homr` for processing.
-   **Capture Image:** Allow camera access, then click "Capture Photo". The image will first be processed to correct perspective and then sent to `homr`.