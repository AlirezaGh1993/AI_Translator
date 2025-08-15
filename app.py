# app.py

import os
import uuid
import threading
import json
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename

# Import custom modules
from modules.ai_handler import get_translator_func
from modules.doc_handler import translate_docx, translate_pdf, translate_txt
from modules.sub_handler import translate_subtitle

# --- Flask App Configuration ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max upload size

# --- In-memory Task Storage ---
# For a production app, use Redis or a database
tasks = {}

def update_task_progress(task_id, progress, message, status='processing'):
    """Updates the progress of a background task."""
    tasks[task_id]['progress'] = progress
    tasks[task_id]['message'] = message
    tasks[task_id]['status'] = status

def translation_worker(task_id, filepath, output_path, file_type, translator_config):
    """The actual translation function that runs in a background thread."""
    try:
        update_progress = lambda p, m: update_task_progress(task_id, p, m)
        
        translate_func = get_translator_func(translator_config['ai_provider'])
        
        final_output_path = output_path

        if file_type == 'subtitle':
            translate_subtitle(filepath, output_path, translate_func, **translator_config, update_progress=update_progress)
        elif file_type == 'document':
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.docx':
                translate_docx(filepath, output_path, translate_func, **translator_config, update_progress=update_progress)
            elif ext == '.txt':
                translate_txt(filepath, output_path, translate_func, **translator_config, update_progress=update_progress)
            elif ext == '.pdf':
                # PDF handler returns a new path since it converts to docx
                final_output_path = translate_pdf(filepath, output_path, translate_func, **translator_config, update_progress=update_progress)
        
        # Mark as completed
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['message'] = 'ترجمه کامل شد.'
        tasks[task_id]['download_url'] = f"/downloads/{os.path.basename(final_output_path)}"

    except Exception as e:
        print(f"Error in task {task_id}: {e}")
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = str(e)


# --- API Routes ---
@app.route('/')
def index():
    """Renders the main HTML page."""
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def handle_translation_request():
    """Handles the file upload and starts the translation process."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Create unique output filename
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_translated_{uuid.uuid4().hex[:6]}{ext}"
        output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], output_filename)

        # Get translator config from form
        provider = request.form.get('ai_provider')
        api_key = request.form.get('gemini_key') if provider == 'gemini' else request.form.get('deepseek_key')

        translator_config = {
            'api_key': api_key,
            'style': request.form.get('style'),
            'target_lang': request.form.get('target_lang'),
            'proxy_url': request.form.get('proxy_url'),
            'ai_provider': provider
        }
        
        if not api_key:
            return jsonify({'error': f'API key for {provider} is missing.'}), 400

        task_id = str(uuid.uuid4())
        tasks[task_id] = {'status': 'queued', 'progress': 0, 'message': 'در صف انتظار...'}
        
        # Run translation in a background thread
        thread = threading.Thread(
            target=translation_worker, 
            args=(task_id, filepath, output_path, request.form.get('file_type'), translator_config)
        )
        thread.start()
        
        return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def get_progress(task_id):
    """Provides progress updates using Server-Sent Events (SSE)."""
    def generate():
        while True:
            if task_id in tasks:
                task_data = tasks[task_id]
                yield f"data: {json.dumps(task_data)}\n\n"
                if task_data['status'] in ['completed', 'error']:
                    break
            time.sleep(1) # Send update every second

    return Response(generate(), mimetype='text/event-stream')

@app.route('/downloads/<filename>')
def download_file(filename):
    """Serves the translated file for download."""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)


# --- Main Execution ---
if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']) or not os.path.exists(app.config['DOWNLOAD_FOLDER']):
        print("ERROR: 'uploads' or 'downloads' directory not found.")
        print("Please run 'python setup.py' first to initialize the project.")
    else:
        # Use threaded=True for handling multiple requests (like SSE and main app)
        app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
