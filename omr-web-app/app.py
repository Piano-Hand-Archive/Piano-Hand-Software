import os
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import base64
import uuid
from image_processor import process_image_to_musicxml

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
MUSICXML_FOLDER = 'musicxml_output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSICXML_FOLDER'] = MUSICXML_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(MUSICXML_FOLDER):
    os.makedirs(MUSICXML_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/musicxml/<path:filename>')
def get_musicxml_file(filename):
    safe_name = os.path.basename(filename)
    if not safe_name.endswith('.musicxml'):
        abort(404)
    return send_from_directory(app.config['MUSICXML_FOLDER'], safe_name)

@app.route('/visualizer')
def visualizer():
    file_name = os.path.basename(request.args.get('file', ''))
    if not file_name.endswith('.musicxml'):
        abort(404)
    file_path = os.path.join(app.config['MUSICXML_FOLDER'], file_name)
    if not os.path.exists(file_path):
        abort(404)
    return render_template('visualizer.html', file_name=file_name)

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

@app.route('/piano_visualizer')
def piano_visualizer():
    return render_template('piano_visualizer.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
