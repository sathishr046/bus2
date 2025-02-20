from flask import Flask, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/start-server', methods=['GET'])
def start_server():
    try:
        batch_file_path = os.path.join(os.path.dirname(__file__), 'run_app.bat')
        subprocess.Popen(batch_file_path, shell=True)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500