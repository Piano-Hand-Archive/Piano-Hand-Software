import cv2
import subprocess
import os
import numpy as np
import imutils
from PIL import Image
import uuid
from MusicXMLChecker import MusicXMLChecker
import shutil

PROCESSED_IMAGES_FOLDER = 'processed_images'
MUSICXML_FOLDER = 'musicxml_output'

os.makedirs(PROCESSED_IMAGES_FOLDER, exist_ok=True)
os.makedirs(MUSICXML_FOLDER, exist_ok=True)

def order_points(pts):
	rect = np.zeros((4, 2), dtype = "float32")
	s = pts.sum(axis = 1)
	rect[0] = pts[np.argmin(s)]
	rect[2] = pts[np.argmax(s)]
	diff = np.diff(pts, axis = 1)
	rect[1] = pts[np.argmin(diff)]
	rect[3] = pts[np.argmax(diff)]
	return rect

def four_point_transform(image, pts):
	rect = order_points(pts)
	(tl, tr, br, bl) = rect
	widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
	widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
	maxWidth = max(int(widthA), int(widthB))
	heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
	heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
	maxHeight = max(int(heightA), int(heightB))
	dst = np.array([
		[0, 0],
		[maxWidth - 1, 0],
		[maxWidth - 1, maxHeight - 1],
		[0, maxHeight - 1]], dtype = "float32")
	M = cv2.getPerspectiveTransform(rect, dst)
	warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
	return warped

def process_image_to_musicxml(input_image_path, perform_processing=True):
    if perform_processing:
        print("\n--- Starting Full Image Processing (Camera Capture) ---")
        print(f"1. Reading input image: {input_image_path}")
        image = cv2.imread(input_image_path)
        if image is None:
            print(f"   - Error: Could not read image from {input_image_path}")
            return {"error": f"Could not read image from {input_image_path}"}
        
        print("1a. Rotating captured image 90 degrees...")
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        
        print("2. Converting image to grayscale and detecting edges...")
        orig = image.copy()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        edged = cv2.Canny(gray, 75, 200)

        print("3. Finding contours to detect paper...")
        cnts = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:5]
        
        screenCnt = None
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                screenCnt = approx
                break

        if screenCnt is None:
            print("   - No 4-point contour found. Using original image boundaries.")
            warped = orig
        else:
            print("   - Found paper contour. Applying perspective transform.")
            warped = four_point_transform(orig, screenCnt.reshape(4, 2))

        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        unique_id = str(uuid.uuid4())
        processed_image_filename = f"{unique_id}.png"
        image_to_process = os.path.join(PROCESSED_IMAGES_FOLDER, processed_image_filename)
        print(f"4. Saving processed image to: {image_to_process}")
        cv2.imwrite(image_to_process, warped_gray, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        
        im = Image.open(image_to_process)
        im.save(image_to_process, dpi=(300, 300))
    else:
        print("\n--- Skipping Image Processing (File Upload) ---")
        image_to_process = input_image_path
        # Use the uploaded filename (without extension) as the basis for the output filename
        unique_id = os.path.splitext(os.path.basename(input_image_path))[0]

    # --- OMR Processing ---
    # The homr tool saves the output in the same directory as the input image.
    input_dir = os.path.dirname(image_to_process)
    expected_output_filename = os.path.splitext(os.path.basename(image_to_process))[0] + '.musicxml'
    generated_musicxml_path = os.path.join(input_dir, expected_output_filename)

    command = f'homr "{image_to_process}"'
    print("5. Running OMR (Optical Music Recognition) with homr...")
    print(f"   - Command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("   - homr execution successful.")
        if result.stdout:
            print("--- homr Output ---\n" + result.stdout + "\n--------------------")
        if result.stderr:
            print("--- homr Stderr ---\n" + result.stderr + "\n--------------------")
    except subprocess.CalledProcessError as e:
        print(f"   - Error: homr execution failed with exit code {e.returncode}.")
        if e.stdout:
            print("--- homr Output ---\n" + e.stdout + "\n--------------------")
        if e.stderr:
            print("--- homr Stderr ---\n" + e.stderr + "\n--------------------")
        return {"error": f"homr tool failed. See terminal for details."}

    print(f"6. Checking for generated MusicXML file at: {generated_musicxml_path}")
    if not os.path.exists(generated_musicxml_path) or os.path.getsize(generated_musicxml_path) == 0:
        print("   - Error: homr ran but did not produce a valid MusicXML file.")
        return {"error": "homr ran but did not produce a valid MusicXML file."}

    # Move the file to the final output directory to keep things organized
    final_musicxml_filename = f"{unique_id}.musicxml"
    final_musicxml_path = os.path.join(MUSICXML_FOLDER, final_musicxml_filename)
    shutil.move(generated_musicxml_path, final_musicxml_path)
    print(f"   - Moved generated file to: {final_musicxml_path}")


    print("7. Verifying MusicXML file with MusicXMLChecker...")
    checker = MusicXMLChecker(final_musicxml_path)
    isValidXML = checker.verifyAll()
    
    if not isValidXML:
        print("   - Error: The generated MusicXML file is not valid.")
        return {"error": "The generated MusicXML file is not valid according to MusicXMLChecker."}

    print("   - MusicXML file is valid.")
    print("--- Processing Complete ---")
    return {"success": "Successfully generated valid MusicXML file.", "musicxml_path": final_musicxml_path}
