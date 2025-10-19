let cvReady = false;

function onOpenCvReady() {
    cv['onRuntimeInitialized'] = () => {
        console.log("OpenCV.js is ready.");
        cvReady = true;
        startApp();
    };
}

function startApp() {
    if (!cvReady) { return; }

    const video = document.getElementById('video');
    const captureCanvas = document.getElementById('canvas');
    const overlayCanvas = document.getElementById('canvas-overlay');
    const snap = document.getElementById('snap');
    const messageDiv = document.getElementById('message');

    // --- State variables for capture workflow ---
    let streaming = false;
    let detectionActive = false;
    let isCapturing = false;
    let stableFrames = 0;
    let largestContour = null;
    const CAPTURE_THRESHOLD = 300; // Approx. 10 seconds of stability at 30fps

    const constraints = {
        audio: false,
        video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "environment"
        }
    };

    async function startCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            window.stream = stream;
            video.srcObject = stream;
            video.play();
        } catch (e) {
            console.error(e);
            showMessage(`Could not start camera: ${e.toString()}`, 'error');
        }
    }
    
    video.addEventListener('canplay', function(ev){
        if (!streaming) {
            const videoWidth = video.videoWidth;
            const videoHeight = video.videoHeight;
            video.setAttribute('width', videoWidth);
            video.setAttribute('height', videoHeight);
            overlayCanvas.width = videoWidth;
            overlayCanvas.height = videoHeight;
            streaming = true;
            requestAnimationFrame(processVideo); // Start the render loop
        }
    }, false);

    function processVideo() {
        if (!streaming) {
            requestAnimationFrame(processVideo);
            return;
        }

        const overlayCtx = overlayCanvas.getContext('2d');
        overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

        // Only run expensive detection logic if it has been activated by the user
        if (!detectionActive) {
            requestAnimationFrame(processVideo);
            return;
        }
        
        let src = new cv.Mat(video.videoHeight, video.videoWidth, cv.CV_8UC4);
        let cap = new cv.VideoCapture(video);
        cap.read(src);

        let gray = new cv.Mat();
        cv.cvtColor(src, gray, cv.COLOR_RGBA2GRAY);
        let blurred = new cv.Mat();
        cv.GaussianBlur(gray, blurred, new cv.Size(5, 5), 0, 0, cv.BORDER_DEFAULT);
        let edged = new cv.Mat();
        cv.Canny(blurred, edged, 75, 200);

        let contours = new cv.MatVector();
        let hierarchy = new cv.Mat();
        cv.findContours(edged, contours, hierarchy, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE);

        let maxArea = -1;
        let foundContour = null;
        for (let i = 0; i < contours.size(); ++i) {
            let cnt = contours.get(i);
            let area = cv.contourArea(cnt, false);
            if (area > maxArea) {
                let peri = cv.arcLength(cnt, true);
                let approx = new cv.Mat();
                cv.approxPolyDP(cnt, approx, 0.02 * peri, true);
                if (approx.rows == 4) {
                    maxArea = area;
                    foundContour = approx.clone();
                }
                approx.delete();
            }
        }
        largestContour = foundContour;

        if (largestContour && !isCapturing) {
            stableFrames++;
            snap.textContent = `Hold steady... (${CAPTURE_THRESHOLD - stableFrames})`;
            snap.classList.add('ready');

            overlayCtx.strokeStyle = 'rgba(0, 255, 0, 0.7)';
            overlayCtx.lineWidth = 5;
            overlayCtx.beginPath();
            let d = largestContour.data32S;
            overlayCtx.moveTo(d[0], d[1]);
            for (let i = 2; i < d.length; i+=2) overlayCtx.lineTo(d[i], d[i+1]);
            overlayCtx.closePath();
            overlayCtx.stroke();
            
            if (stableFrames >= CAPTURE_THRESHOLD) {
                snap.click(); // Programmatically click button to trigger capture
            }
        } else if (!isCapturing) {
            stableFrames = 0;
            snap.textContent = 'Detecting paper...';
            snap.classList.remove('ready');
        }

        src.delete(); gray.delete(); blurred.delete(); edged.delete(); contours.delete(); hierarchy.delete();
        requestAnimationFrame(processVideo);
    }
    
    startCamera();

    snap.addEventListener('click', () => {
        // Case 1: User clicks "Start Capture". We begin the detection process.
        if (!detectionActive && !isCapturing) {
            detectionActive = true;
            snap.textContent = 'Detecting paper...';
            return;
        }

        // Case 2: Programmatic click for auto-capture.
        if (detectionActive && !isCapturing && largestContour) {
            isCapturing = true;
            detectionActive = false; // Stop detection
            snap.textContent = 'Captured! Processing...';
            snap.classList.remove('ready');

            const context = captureCanvas.getContext('2d');
            captureCanvas.width = video.videoWidth;
            captureCanvas.height = video.videoHeight;
            context.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
            
            const dataURL = captureCanvas.toDataURL('image/png');
            
            fetch('/process_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: dataURL })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage(`${data.success} Path: ${data.musicxml_path}`, 'success');
                } else {
                    showMessage(`Error: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('An error occurred while uploading the image.', 'error');
            })
            .finally(() => {
                isCapturing = false;
                stableFrames = 0;
                snap.textContent = 'Start Capture'; // Reset for next time
            });
        }
    });

    // -- Image File Upload --
    const imageForm = document.getElementById('upload-image-form');
    imageForm.addEventListener('submit', (event) => {
        event.preventDefault();
        const formData = new FormData(imageForm);
        
        fetch('/process_image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage(`${data.success} Path: ${data.musicxml_path}`, 'success');
            } else {
                showMessage(`Error: ${data.error}`, 'error');
            }
            imageForm.reset();
        })
        .catch(error => {
            console.error('Error:', error);
            showMessage('An error occurred while uploading the image file.', 'error');
        });
    });

    function showMessage(message, type) {
        messageDiv.textContent = message;
        messageDiv.className = `message-${type}`;
        messageDiv.style.display = 'block';
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}

document.addEventListener('DOMContentLoaded', onOpenCvReady);
