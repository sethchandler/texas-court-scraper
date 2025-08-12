#!/usr/bin/env python3
"""
Texas Court PDF Scraper - CLI Tool
Downloads PDFs from Texas court case pages and converts them to text files.
Interactive terminal interface with options for separate or merged output.
"""

import os
import re
import time
import requests
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import PyPDF2
from typing import List, Dict, Optional

class CourtPDFScraper:
    def __init__(self, output_dir: str = "court_documents", merge_texts: bool = False):
        self.session = requests.Session()
        self.output_dir = Path(output_dir)
        self.pdf_dir = self.output_dir / "pdfs"
        self.txt_dir = self.output_dir / "txt_files"
        self.merge_texts = merge_texts
        self.merged_content = []
        
        # Create directories
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        if not merge_texts:
            self.txt_dir.mkdir(parents=True, exist_ok=True)
        
        # Bot-friendly headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Respectful delays (seconds)
        self.delay_between_requests = 2
        self.delay_between_downloads = 1
    
    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page content with proper delays and error handling."""
        try:
            print(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Add delay to be respectful
            time.sleep(self.delay_between_requests)
            
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def find_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract PDF links from the page."""
        pdf_links = []
        
        # Look for PDF links in various patterns
        # Pattern 1: Direct links to SearchMedia.aspx
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if 'SearchMedia.aspx' in href and 'MediaVersionID' in href:
                # Extract file info from link text
                text = link.get_text(strip=True)
                size_match = re.search(r'PDF/(\d+)\s*KB', text)
                size = size_match.group(1) if size_match else 'unknown'
                
                pdf_info = {
                    'url': urljoin(base_url, href),
                    'text': text,
                    'size_kb': size,
                    'filename': f"document_{len(pdf_links)+1}_{size}KB.pdf"
                }
                pdf_links.append(pdf_info)
        
        # Pattern 2: Look for any PDF references in tables or divs
        for element in soup.find_all(['td', 'div'], string=re.compile(r'PDF', re.I)):
            parent = element.find_parent()
            if parent:
                link = parent.find('a', href=True)
                if link and 'SearchMedia.aspx' in link.get('href', ''):
                    href = link.get('href')
                    if href not in [p['url'] for p in pdf_links]:  # Avoid duplicates
                        pdf_info = {
                            'url': urljoin(base_url, href),
                            'text': element.get_text(strip=True),
                            'size_kb': 'unknown',
                            'filename': f"document_{len(pdf_links)+1}.pdf"
                        }
                        pdf_links.append(pdf_info)
        
        return pdf_links
    
    def download_pdf(self, pdf_info: Dict[str, str]) -> Optional[Path]:
        """Download a single PDF file."""
        try:
            print(f"Downloading: {pdf_info['text']} ({pdf_info['size_kb']} KB)")
            
            response = self.session.get(pdf_info['url'], timeout=60, stream=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                print(f"Warning: Content type is {content_type}, not PDF")
            
            # Save PDF
            pdf_path = self.pdf_dir / pdf_info['filename']
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"Saved: {pdf_path}")
            time.sleep(self.delay_between_downloads)
            
            return pdf_path
            
        except Exception as e:
            print(f"Error downloading {pdf_info['url']}: {e}")
            return None
    
    def pdf_to_text(self, pdf_path: Path, doc_id: int) -> Optional[Path]:
        """Convert PDF to text file or add to merged content."""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_content = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content.append(page.extract_text())
                    text_content.append("\n")
            
            full_text = ''.join(text_content).strip()
            
            if self.merge_texts:
                # Add to merged content with document separators
                self.merged_content.append(f"<document id={doc_id}>\n{full_text}\n</document>")
                print(f"Added to merged content: document {doc_id}")
                return None
            else:
                # Write to individual text file
                txt_filename = pdf_path.stem + '.txt'
                txt_path = self.txt_dir / txt_filename
                
                with open(txt_path, 'w', encoding='utf-8') as txt_file:
                    txt_file.write(full_text)
                
                print(f"Converted to text: {txt_path}")
                return txt_path
            
        except Exception as e:
            print(f"Error converting {pdf_path} to text: {e}")
            return None
    
    def save_merged_file(self) -> Optional[Path]:
        """Save all merged content to a single file."""
        if not self.merged_content:
            return None
            
        merged_path = self.output_dir / "merged_documents.txt"
        try:
            with open(merged_path, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(self.merged_content))
            
            print(f"Saved merged file: {merged_path}")
            return merged_path
        except Exception as e:
            print(f"Error saving merged file: {e}")
            return None
    
    def scrape_case_page(self, url: str) -> Dict[str, List[Path]]:
        """Main method to scrape a case page and download all PDFs."""
        results = {
            'pdfs': [],
            'txt_files': []
        }
        
        print(f"Starting scrape of: {url}")
        
        # Get the main page
        soup = self.get_page_content(url)
        if not soup:
            print("Failed to fetch main page")
            return results
        
        # Find PDF links
        pdf_links = self.find_pdf_links(soup, url)
        print(f"Found {len(pdf_links)} PDF links")
        
        if not pdf_links:
            print("No PDF links found. The page structure might have changed.")
            return results
        
        # Download each PDF and convert to text
        for i, pdf_info in enumerate(pdf_links, 1):
            print(f"\nProcessing PDF {i}/{len(pdf_links)}")
            
            # Download PDF
            pdf_path = self.download_pdf(pdf_info)
            if pdf_path:
                results['pdfs'].append(pdf_path)
                
                # Convert to text (pass document ID)
                txt_path = self.pdf_to_text(pdf_path, i)
                if txt_path:
                    results['txt_files'].append(txt_path)
        
        # Save merged file if using merge mode
        if self.merge_texts:
            merged_path = self.save_merged_file()
            if merged_path:
                results['merged_file'] = merged_path
        
        if self.merge_texts:
            print(f"\nCompleted! Downloaded {len(results['pdfs'])} PDFs and created 1 merged text file.")
        else:
            print(f"\nCompleted! Downloaded {len(results['pdfs'])} PDFs and converted {len(results['txt_files'])} to text.")
        print(f"Files saved in: {self.output_dir}")
        
        return results


def interactive_mode():
    """Run in interactive terminal mode."""
    print("=== Texas Court PDF Scraper ===")
    print()
    
    # Get URL from user
    while True:
        url = input("Enter the Texas court case URL: ").strip()
        if url:
            if "search.txcourts.gov" not in url:
                print("⚠️  Warning: This doesn't appear to be a Texas court URL")
                confirm = input("Continue anyway? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
            break
        else:
            print("Please enter a valid URL.")
    
    # Get output format preference
    print("\nChoose output format:")
    print("1. Separate text files (one per PDF)")
    print("2. Single merged file with document separators")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ['1', '2']:
            merge_texts = (choice == '2')
            break
        else:
            print("Please enter 1 or 2.")
    
    # Generate output directory name from URL
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        query = urllib.parse.parse_qs(parsed.query)
        case_num = query.get('cn', ['unknown'])[0]
        output_dir = f"court_case_{case_num}".replace('-', '_')
    except:
        output_dir = "court_case_documents"
    
    print(f"\nStarting scraper...")
    print(f"Output directory: {output_dir}")
    print(f"Output format: {'Merged file' if merge_texts else 'Separate files'}")
    print()
    
    # Initialize and run scraper
    scraper = CourtPDFScraper(output_dir=output_dir, merge_texts=merge_texts)
    results = scraper.scrape_case_page(url)
    
    # Print summary
    print(f"\n=== SUMMARY ===")
    print(f"PDFs downloaded: {len(results['pdfs'])}")
    if merge_texts:
        print(f"Merged file created: {'Yes' if 'merged_file' in results else 'No'}")
        if 'merged_file' in results:
            print(f"Merged file: {results['merged_file']}")
    else:
        print(f"Text files created: {len(results.get('txt_files', []))}")
    print(f"Output directory: {scraper.output_dir}")


def main():
    """Main function with CLI argument support."""
    parser = argparse.ArgumentParser(
        description="Texas Court PDF Scraper - Download and convert court documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python court_scraper.py                    # Interactive mode
  python court_scraper.py --url "https://..." --separate
  python court_scraper.py --url "https://..." --merged
        """
    )
    
    parser.add_argument('--url', 
                       help='Court case URL to scrape')
    parser.add_argument('--output-dir', 
                       help='Output directory name (default: auto-generated)')
    
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument('--separate', action='store_true',
                             help='Create separate text files (default)')
    output_group.add_argument('--merged', action='store_true',
                             help='Create single merged text file')
    
    args = parser.parse_args()
    
    if not args.url:
        # Run in interactive mode
        interactive_mode()
    else:
        # Run with command line arguments
        merge_texts = args.merged
        
        # Generate output directory if not provided
        if args.output_dir:
            output_dir = args.output_dir
        else:
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(args.url)
                query = urllib.parse.parse_qs(parsed.query)
                case_num = query.get('cn', ['unknown'])[0]
                output_dir = f"court_case_{case_num}".replace('-', '_')
            except:
                output_dir = "court_case_documents"
        
        print(f"Scraping: {args.url}")
        print(f"Output directory: {output_dir}")
        print(f"Output format: {'Merged file' if merge_texts else 'Separate files'}")
        print()
        
        # Initialize and run scraper
        scraper = CourtPDFScraper(output_dir=output_dir, merge_texts=merge_texts)
        results = scraper.scrape_case_page(args.url)
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"PDFs downloaded: {len(results['pdfs'])}")
        if merge_texts:
            print(f"Merged file created: {'Yes' if 'merged_file' in results else 'No'}")
        else:
            print(f"Text files created: {len(results.get('txt_files', []))}")
        print(f"Output directory: {scraper.output_dir}")


if __name__ == "__main__":
    main()