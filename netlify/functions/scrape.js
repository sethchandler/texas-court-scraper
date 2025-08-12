const https = require('https');
const http = require('http');
const { parse } = require('url');

// Simple fetch implementation for Node.js
function fetch(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlParsed = parse(url);
    const lib = urlParsed.protocol === 'https:' ? https : http;
    
    const requestOptions = {
      hostname: urlParsed.hostname,
      port: urlParsed.port,
      path: urlParsed.path,
      method: options.method || 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        ...options.headers
      }
    };

    const req = lib.request(requestOptions, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        resolve({
          ok: res.statusCode >= 200 && res.statusCode < 300,
          status: res.statusCode,
          text: () => Promise.resolve(data),
          json: () => Promise.resolve(JSON.parse(data))
        });
      });
    });

    req.on('error', (err) => {
      reject(err);
    });

    if (options.body) {
      req.write(options.body);
    }
    
    req.end();
  });
}

// Simple HTML parser to extract PDF links
function extractPDFLinks(html, baseUrl) {
  const pdfLinks = [];
  
  // Look for PDF links using regex (simplified approach)
  const linkRegex = /<a[^>]+href=['"]([^'"]*SearchMedia\.aspx[^'"]*MediaVersionID[^'"]*?)['"][^>]*>([^<]*PDF[^<]*)/gi;
  
  let match;
  while ((match = linkRegex.exec(html)) !== null) {
    const href = match[1];
    const text = match[2].trim();
    
    // Extract file size if present
    const sizeMatch = text.match(/(\d+)\s*KB/i);
    const size = sizeMatch ? sizeMatch[1] : 'unknown';
    
    // Create full URL
    const fullUrl = href.startsWith('http') ? href : `${baseUrl.origin}/${href.replace(/^\//, '')}`;
    
    pdfLinks.push({
      url: fullUrl,
      text: text,
      size_kb: size,
      id: pdfLinks.length + 1
    });
  }
  
  return pdfLinks;
}

// Download PDF and convert to text (simplified - just returns metadata for now)
async function processPDF(pdfInfo) {
  try {
    console.log(`Processing: ${pdfInfo.text}`);
    
    const response = await fetch(pdfInfo.url);
    if (!response.ok) {
      throw new Error(`Failed to download PDF: ${response.status}`);
    }
    
    const pdfData = await response.text();
    
    // For demo purposes, we'll return a simple text representation
    // In a real implementation, you'd use a PDF parsing library
    return {
      id: pdfInfo.id,
      filename: `document_${pdfInfo.id}_${pdfInfo.size_kb}KB.txt`,
      content: `Document ${pdfInfo.id} Content\n\nOriginal PDF: ${pdfInfo.text}\nSize: ${pdfInfo.size_kb} KB\nURL: ${pdfInfo.url}\n\n[PDF content would be extracted here using a proper PDF library]`,
      size: pdfInfo.size_kb
    };
  } catch (error) {
    console.error(`Error processing PDF ${pdfInfo.id}:`, error);
    return null;
  }
}

exports.handler = async (event, context) => {
  // Enable CORS
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Content-Type': 'application/json'
  };
  
  // Handle preflight requests
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: ''
    };
  }
  
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }
  
  try {
    const body = JSON.parse(event.body);
    const { url, merge_texts = false } = body;
    
    if (!url) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'URL is required' })
      };
    }
    
    console.log(`Scraping: ${url}`);
    
    // Fetch the main page
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch page: ${response.status}`);
    }
    
    const html = await response.text();
    const baseUrl = new URL(url);
    
    // Extract PDF links
    const pdfLinks = extractPDFLinks(html, baseUrl);
    
    if (pdfLinks.length === 0) {
      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
          success: false,
          message: 'No PDF links found on the page',
          pdf_count: 0,
          documents: []
        })
      };
    }
    
    console.log(`Found ${pdfLinks.length} PDF links`);
    
    // Process a limited number of PDFs (to avoid timeout)
    const maxPDFs = Math.min(pdfLinks.length, 5); // Limit for demo
    const processedDocs = [];
    
    for (let i = 0; i < maxPDFs; i++) {
      const doc = await processPDF(pdfLinks[i]);
      if (doc) {
        processedDocs.push(doc);
      }
      
      // Add delay to be respectful
      if (i < maxPDFs - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    // Format output based on merge_texts preference
    let result;
    if (merge_texts) {
      const mergedContent = processedDocs
        .map(doc => `<document id=${doc.id}>\n${doc.content}\n</document>`)
        .join('\n\n');
      
      result = {
        success: true,
        format: 'merged',
        pdf_count: pdfLinks.length,
        processed_count: processedDocs.length,
        merged_content: mergedContent,
        filename: 'merged_court_documents.txt'
      };
    } else {
      result = {
        success: true,
        format: 'separate',
        pdf_count: pdfLinks.length,
        processed_count: processedDocs.length,
        documents: processedDocs.map(doc => ({
          id: doc.id,
          filename: doc.filename,
          content: doc.content,
          size: doc.size
        }))
      };
    }
    
    if (processedDocs.length < pdfLinks.length) {
      result.note = `Processed ${processedDocs.length} of ${pdfLinks.length} PDFs (limited for demo)`;
    }
    
    return {
      statusCode: 200,
      headers,
      body: JSON.stringify(result)
    };
    
  } catch (error) {
    console.error('Scraping error:', error);
    
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({
        success: false,
        error: error.message || 'Internal server error'
      })
    };
  }
};