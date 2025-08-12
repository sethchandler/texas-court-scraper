#!/usr/bin/env python3
"""
Vercel Python API endpoint for court scraping
"""

import os
import sys
import json
import tempfile
import zipfile
from pathlib import Path

# Add the parent directory to the path so we can import court_scraper
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from court_scraper import CourtPDFScraper

def handler(request):
    """Vercel serverless function handler."""
    
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': ''
        }
    
    # Only allow POST requests for scraping
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': {
                'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Parse request body
        if hasattr(request, 'get_json'):
            data = request.get_json()
        else:
            # Vercel request format
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body) if body else {}
        
        url = data.get('url', '').strip()
        merge_texts = data.get('merge_texts', False)
        
        if not url:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'URL is required'})
            }
        
        # Security: Validate URL to prevent SSRF attacks
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'Invalid URL scheme'})
                }
            
            # Only allow Texas court websites
            allowed_hosts = ['search.txcourts.gov']
            if parsed.hostname not in allowed_hosts:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                        'Content-Type': 'application/json',
                    },
                    'body': json.dumps({'error': 'URL not allowed. Only Texas court websites are supported.'})
                }
        except Exception:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({'error': 'Invalid URL format'})
            }
        
        # Create temporary directory for this request
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "court_case")
        
        # Initialize scraper with our proven class
        scraper = CourtPDFScraper(output_dir=output_dir, merge_texts=merge_texts)
        
        # Run the scraper
        results = scraper.scrape_case_page(url)
        
        total_files = len(results.get('pdfs', []))
        
        if total_files == 0:
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'message': 'No PDF documents found on the page',
                    'pdf_count': 0
                })
            }
        
        # Prepare response based on output format
        if merge_texts and 'merged_file' in results:
            # Read merged file content
            merged_file = results['merged_file']
            with open(merged_file, 'r', encoding='utf-8') as f:
                merged_content = f.read()
            
            response_data = {
                'success': True,
                'format': 'merged',
                'pdf_count': total_files,
                'processed_count': len(results.get('txt_files', [])),
                'merged_content': merged_content,
                'filename': 'merged_court_documents.txt'
            }
        else:
            # Prepare separate files data
            documents = []
            txt_files = results.get('txt_files', [])
            
            for i, txt_file in enumerate(txt_files):
                if os.path.exists(txt_file):
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    documents.append({
                        'id': i + 1,
                        'filename': os.path.basename(txt_file),
                        'content': content
                    })
            
            response_data = {
                'success': True,
                'format': 'separate',
                'pdf_count': total_files,
                'processed_count': len(documents),
                'documents': documents
            }
        
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                'Content-Type': 'application/json',
            },
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        # Clean up temp directory on error
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://texas-court-scraper-5ve5.vercel.app',
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

# Vercel expects this format
def lambda_handler(event, context):
    """AWS Lambda compatible handler for Vercel."""
    class Request:
        def __init__(self, event):
            self.method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
            self.body = event.get('body', '')
            
    request = Request(event)
    response = handler(request)
    
    return {
        'statusCode': response['statusCode'],
        'headers': response['headers'],
        'body': response['body']
    }