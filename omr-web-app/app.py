import os
import xml.etree.ElementTree as ET
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import base64
import uuid
from image_processor import process_image_to_musicxml

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
MUSICXML_FOLDER = 'musicxml_output'
PRELOADED_FOLDER = 'preloaded_musicxml'
HAND_COMMANDS_FOLDER = 'hand_commands'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSICXML_FOLDER'] = MUSICXML_FOLDER
app.config['PRELOADED_FOLDER'] = PRELOADED_FOLDER
app.config['HAND_COMMANDS_FOLDER'] = HAND_COMMANDS_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(MUSICXML_FOLDER):
    os.makedirs(MUSICXML_FOLDER)
if not os.path.exists(PRELOADED_FOLDER):
    os.makedirs(PRELOADED_FOLDER)
if not os.path.exists(HAND_COMMANDS_FOLDER):
    os.makedirs(HAND_COMMANDS_FOLDER)


def generate_hand_commands(musicxml_path):
    """Run the fingering optimizer for a generated MusicXML file.

    Returns a dict suitable for embedding in a JSON response. On success:
    {"left": ..., "right": ..., "output_dir": ..., "split_point": ..., "issues": [...]}
    On failure: {"error": "..."} — never raises, so a bad MusicXML doesn't
    poison the upstream MusicXML response.
    """
    from findOptimalHandPos import run_optimizer_for_app

    base = os.path.splitext(os.path.basename(musicxml_path))[0]
    output_dir = os.path.join(app.config['HAND_COMMANDS_FOLDER'], base)

    # Skip the optimizer if outputs already exist and are at least as new
    # as the source MusicXML. Preloaded files are deterministic, so this
    # avoids re-running on every Library click.
    left_path = os.path.join(output_dir, "left_hand_commands.txt")
    right_path = os.path.join(output_dir, "right_hand_commands.txt")
    if (os.path.exists(left_path) and os.path.exists(right_path)
            and os.path.getmtime(left_path) >= os.path.getmtime(musicxml_path)
            and os.path.getmtime(right_path) >= os.path.getmtime(musicxml_path)):
        return {
            "left": left_path,
            "right": right_path,
            "output_dir": output_dir,
            "cached": True,
        }

    try:
        result = run_optimizer_for_app(musicxml_path, output_dir)
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Unexpected optimizer failure: {e}"}

    return {
        "left": result["left_commands"],
        "right": result["right_commands"],
        "output_dir": output_dir,
        "split_point": result["split_point"],
        "issues": result["issues"],
        "cached": False,
    }

def _xml_local_tag(tag):
    return tag.rsplit('}', 1)[-1] if tag.startswith('{') else tag

def _prettify_filename(filename):
    base = os.path.splitext(filename)[0]
    name = base.replace('_', ' ').replace('-', ' ')
    return ' '.join(w.capitalize() for w in name.split()) if name.strip() else filename

def musicxml_display_title(file_path, filename):
    """Prefer movement-title / work-title / printed title credit; else a nicer filename."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
    except (ET.ParseError, OSError):
        return _prettify_filename(filename)

    movement_title = None
    work_title = None
    credit_title = None

    for el in root.iter():
        ln = _xml_local_tag(el.tag)
        # Metadata lives before the first <part>; skip the note data for speed.
        if ln == 'part':
            break
        if ln == 'movement-title' and el.text and el.text.strip():
            movement_title = el.text.strip()
            break
        if ln == 'work-title' and el.text and el.text.strip() and not work_title:
            work_title = el.text.strip()
        if ln == 'credit':
            ctype = None
            cwords = None
            for child in el:
                cln = _xml_local_tag(child.tag)
                if cln == 'credit-type' and child.text:
                    ctype = child.text.strip()
                if cln == 'credit-words':
                    cwords = ''.join(child.itertext()).strip()
            if ctype == 'title' and cwords and not credit_title:
                credit_title = cwords

    if movement_title:
        return movement_title

    generic = {'title', 'untitled', 'piece', 'new score', 'untitled score'}
    if work_title and work_title.lower() not in generic:
        return work_title
    if credit_title:
        return credit_title
    if work_title:
        return work_title
    return _prettify_filename(filename)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    preloaded_items = []
    if os.path.exists(app.config['PRELOADED_FOLDER']):
        for f in sorted(os.listdir(app.config['PRELOADED_FOLDER'])):
            if not (f.endswith('.musicxml') or f.endswith('.xml')):
                continue
            path = os.path.join(app.config['PRELOADED_FOLDER'], f)
            label = musicxml_display_title(path, f)
            preloaded_items.append({'filename': f, 'label': label})
    return render_template('index.html', preloaded_items=preloaded_items)

@app.route('/musicxml/<path:filename>')
def get_musicxml_file(filename):
    safe_name = os.path.basename(filename)
    if not safe_name.endswith('.musicxml'):
        abort(404)
    musicxml_path = os.path.join(app.config['MUSICXML_FOLDER'], safe_name)
    if os.path.exists(musicxml_path):
        return send_from_directory(app.config['MUSICXML_FOLDER'], safe_name)
    return send_from_directory(app.config['PRELOADED_FOLDER'], safe_name)

@app.route('/visualizer')
def visualizer():
    file_name = os.path.basename(request.args.get('file', ''))
    if not file_name.endswith('.musicxml'):
        abort(404)
    file_path = os.path.join(app.config['MUSICXML_FOLDER'], file_name)
    if not os.path.exists(file_path):
        file_path = os.path.join(app.config['PRELOADED_FOLDER'], file_name)
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
        if isinstance(result, dict) and result.get('musicxml_path'):
            result['hand_commands'] = generate_hand_commands(result['musicxml_path'])
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
        if isinstance(result, dict) and result.get('musicxml_path'):
            result['hand_commands'] = generate_hand_commands(result['musicxml_path'])
        return jsonify(result)

    return jsonify({'error': 'No image data received.'}), 400

@app.route('/piano_visualizer')
def piano_visualizer():
    return render_template('piano_visualizer.html')

import shutil

@app.route('/process_preloaded', methods=['POST'])
def process_preloaded():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided.'}), 400
    
    source_path = os.path.join(app.config['PRELOADED_FOLDER'], filename)
    if not os.path.exists(source_path):
        return jsonify({'error': 'File not found.'}), 404
        
    dest_path = os.path.join(app.config['MUSICXML_FOLDER'], filename)
    shutil.copy2(source_path, dest_path)

    return jsonify({
        'success': 'Loaded pre-loaded file.',
        'musicxml_path': dest_path,
        'hand_commands': generate_hand_commands(dest_path),
    })

if __name__ == '__main__':
    # Default 5001: macOS AirPlay Receiver uses port 5000 and returns HTTP 403 in the browser.
    port = int(os.environ.get('PORT', '5001'))
    app.run(debug=True, use_reloader=False, host='127.0.0.1', port=port)
