import subprocess
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import PyPDF2
import re
from werkzeug.utils import secure_filename

# Function to start the backend if not running
def start_backend():
    try:
        subprocess.Popen(["run_app.bat"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Error starting backend: {e}")

# Start the backend when the script runs
start_backend()

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                page_text = ' '.join(page_text.split())
                text += page_text + "\n"
            text = text.replace('\x00', '').strip()
            return text
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")

def analyze_receipt(text):
    try:
        result = {
            'student_details': {
                'name': None,
                'usn': None,
                'branch': None,
                'father_name': None,
                'receipt_no': None
            },
            'fees': [],
            'total_amount': 0,
            'transport_fee_found': False,
            'warnings': [],
            'errors': []
        }
        
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('Closure: ()=>String from Function toString..', '')

        receipt_match = re.search(r'Receipt No\s*:\s*(NCET/\d+/\d+-\d+)', text, re.IGNORECASE)
        if receipt_match:
            result['student_details']['receipt_no'] = receipt_match.group(1).strip()

        usn_match = re.search(r'Adm No\s*:\s*(\w+)', text, re.IGNORECASE)
        if usn_match:
            result['student_details']['usn'] = usn_match.group(1).strip()

        name_match = re.search(r'Name\s*:\s*([^C]+?)(?=\s+Class|$)', text, re.IGNORECASE)
        if name_match:
            result['student_details']['name'] = name_match.group(1).strip()

        branch_match = re.search(r'Class/sec\s*:([^F]+?)(?=\s+Father|$)', text, re.IGNORECASE)
        if branch_match:
            result['student_details']['branch'] = branch_match.group(1).strip()

        father_match = re.search(r"Father(?:'s)?\s*Name\s*:\s*([^D]+?)(?=\s+DType|$)", text, re.IGNORECASE)
        if father_match:
            result['student_details']['father_name'] = father_match.group(1).strip()

        transport_match = re.search(r'Transport Fees\s+IInstallment\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if transport_match:
            result['transport_fee_found'] = True
            concession, amount = transport_match.groups()
            result['fees'].append({
                'sno': '1',
                'particular': 'Transport Fees',
                'concession': float(concession),
                'amount': float(amount)
            })
            result['total_amount'] = float(amount)

        if not result['transport_fee_found']:
            result['warnings'].append("Transport fee not found in the receipt")

        return result
    except Exception as e:
        raise Exception(f"Error analyzing receipt: {str(e)}")

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path)
                text = extract_text_from_pdf(file_path)
                analysis_result = analyze_receipt(text)
                
                return jsonify(analysis_result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        
        return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        return jsonify({'error': f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
