#!/usr/bin/env python3
"""
Texas Court PDF Scraper - Web App
Flask web application for downloading and converting Texas court documents.
"""

import os
import tempfile
import zipfile
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
from werkzeug.utils import secure_filename
import threading
import time
from pathlib import Path
from court_scraper import CourtPDFScraper

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Store active scraping jobs
active_jobs = {}

class WebScrapingJob:
    def __init__(self, job_id, url, merge_texts=False):
        self.job_id = job_id
        self.url = url
        self.merge_texts = merge_texts
        self.status = "starting"
        self.progress = 0
        self.total_files = 0
        self.processed_files = 0
        self.results = {}
        self.error = None
        self.temp_dir = None
    
    def run(self):
        """Run the scraping job in a separate thread."""
        try:
            self.status = "scraping"
            
            # Create temporary directory for this job
            self.temp_dir = tempfile.mkdtemp()
            output_dir = os.path.join(self.temp_dir, f"court_case_{self.job_id}")
            
            # Initialize scraper
            scraper = CourtPDFScraper(output_dir=output_dir, merge_texts=self.merge_texts)
            
            # Custom callback to update progress
            original_download = scraper.download_pdf
            def download_with_progress(pdf_info):
                result = original_download(pdf_info)
                if result:
                    self.processed_files += 1
                    self.progress = int((self.processed_files / self.total_files) * 100) if self.total_files > 0 else 0
                return result
            
            scraper.download_pdf = download_with_progress
            
            # Run the scraper
            self.status = "downloading"
            results = scraper.scrape_case_page(self.url)
            
            self.total_files = len(results.get('pdfs', []))
            self.results = results
            self.results['output_dir'] = output_dir
            
            if self.merge_texts and 'merged_file' in results:
                self.status = "completed"
            elif not self.merge_texts and results.get('txt_files'):
                self.status = "completed" 
            else:
                self.status = "error"
                self.error = "No documents were successfully processed"
                
        except Exception as e:
            self.status = "error"
            self.error = str(e)

@app.route('/')
def index():
    """Main page with scraping form."""
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """Start a new scraping job."""
    data = request.get_json()
    url = data.get('url', '').strip()
    merge_texts = data.get('merge_texts', False)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Generate job ID
    job_id = str(int(time.time() * 1000))
    
    # Create and start job
    job = WebScrapingJob(job_id, url, merge_texts)
    active_jobs[job_id] = job
    
    # Start scraping in background thread
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'started'
    })

@app.route('/status/<job_id>')
def job_status(job_id):
    """Get status of a scraping job."""
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    response = {
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'total_files': job.total_files,
        'processed_files': job.processed_files
    }
    
    if job.error:
        response['error'] = job.error
    
    if job.status == 'completed':
        if job.merge_texts:
            response['download_type'] = 'merged'
            response['file_count'] = 1
        else:
            response['download_type'] = 'separate'
            response['file_count'] = len(job.results.get('txt_files', []))
    
    return jsonify(response)

@app.route('/download/<job_id>')
def download_results(job_id):
    """Download the results of a completed job."""
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    try:
        if job.merge_texts:
            # Return single merged file
            merged_file = job.results.get('merged_file')
            if merged_file and os.path.exists(merged_file):
                @after_this_request
                def cleanup(response):
                    # Clean up temp directory after download
                    threading.Timer(60.0, lambda: cleanup_job(job_id)).start()
                    return response
                
                return send_file(
                    merged_file,
                    as_attachment=True,
                    download_name='merged_court_documents.txt',
                    mimetype='text/plain'
                )
        else:
            # Create ZIP file with all text files
            zip_path = os.path.join(job.temp_dir, f'court_documents_{job_id}.zip')
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                txt_files = job.results.get('txt_files', [])
                for txt_file in txt_files:
                    if os.path.exists(txt_file):
                        zipf.write(txt_file, os.path.basename(txt_file))
            
            @after_this_request
            def cleanup(response):
                # Clean up temp directory after download
                threading.Timer(60.0, lambda: cleanup_job(job_id)).start()
                return response
            
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f'court_documents_{job_id}.zip',
                mimetype='application/zip'
            )
            
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500
    
    return jsonify({'error': 'No files available for download'}), 404

def cleanup_job(job_id):
    """Clean up job data and temporary files."""
    if job_id in active_jobs:
        job = active_jobs[job_id]
        if job.temp_dir and os.path.exists(job.temp_dir):
            import shutil
            try:
                shutil.rmtree(job.temp_dir)
            except:
                pass
        del active_jobs[job_id]

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))