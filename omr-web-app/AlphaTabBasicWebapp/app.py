from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Route to show the player
@app.route('/')
def index():
    return render_template('index.html')

# Route to serve the MusicXML file from the static folder
@app.route('/files/<path:filename>')
def get_file(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Ensure the static folder exists
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True, port=5000)