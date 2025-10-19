import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import base64
import uuid
from image_processor import process_image_to_musicxml

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_image', methods=['POST'])
def process_image_endpoint():
    # Handle direct image file upload
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid or no file selected. Please upload a PNG, JPG, or JPEG.'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Call the processor WITHOUT performing the image manipulation steps
        result = process_image_to_musicxml(filepath, perform_processing=False)
        return jsonify(result)

    # Handle image data from camera (sent as JSON)
    data = request.json
    if data and 'image' in data:
        image_data = data['image'].split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
            
        # Call the processor WITH the image manipulation steps
        result = process_image_to_musicxml(filepath, perform_processing=True)
        return jsonify(result)

    return jsonify({'error': 'No image data received.'}), 400

if __name__ == '__main__':
    app.run(debug=True)
