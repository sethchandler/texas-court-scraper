# Texas Court PDF Scraper

A web application for downloading and converting Texas court case documents from PDFs to text files. Built with Netlify Functions for simple deployment.

## Features

- **Simple Web Interface**: Clean, responsive UI that works on any device
- **Serverless Backend**: Uses Netlify Functions to bypass CORS restrictions
- **Batch Processing**: Finds and processes all PDFs from a court case page
- **Flexible Output**: Choose between separate files or merged document
- **Instant Download**: Files download directly in your browser
- **Bot-Friendly**: Respectful delays and headers to avoid blocking

## Live Demo

Visit: `https://your-site-name.netlify.app`

## Usage

### Web App (Recommended)

1. Visit the web application
2. Enter a Texas court case URL (e.g., `https://search.txcourts.gov/Case.aspx?cn=25-0674&coa=cossup`)
3. Choose output format:
   - **Separate files**: Individual text files (click to download each)
   - **Merged file**: Single file with `<document id=X>content</document>` separators
4. Click "Start Scraping" and wait for completion
5. Download your files directly in the browser

### Command Line (Alternative)

```bash
# Interactive mode
python court_scraper.py

# Direct command
python court_scraper.py --url "https://search.txcourts.gov/Case.aspx?cn=25-0674&coa=cossup" --merged
```

## Deployment to Netlify

### Quick Deploy

1. **Fork this repo** on GitHub
2. **Connect to Netlify**:
   - Go to [netlify.com](https://netlify.com)
   - Click "New site from Git"
   - Choose your forked repository
   - Deploy settings are automatic (uses `netlify.toml`)
3. **Your site is live!** Get a URL like `https://amazing-name-123.netlify.app`

### Custom Domain (Optional)

In Netlify dashboard:
1. Go to Site settings → Domain management
2. Add your custom domain
3. Follow DNS setup instructions

### Local Development

```bash
git clone https://github.com/yourusername/court-scraper.git
cd court-scraper
npm install netlify-cli -g
netlify dev
```

Visit `http://localhost:8888`

## File Structure

```
court-scraper/
├── public/
│   └── index.html          # Web interface
├── netlify/
│   └── functions/
│       └── scrape.js       # Serverless function
├── court_scraper.py        # CLI version (optional)
├── netlify.toml           # Netlify configuration
├── package.json           # Node.js metadata
└── README.md             # This file
```

## How It Works

1. **Frontend**: Static HTML/JS hosted on Netlify
2. **Backend**: Serverless function runs when you submit a URL
3. **Processing**: Function scrapes court site, extracts PDF links, processes content
4. **Download**: Results sent back to browser for instant download

**No servers to manage!** Everything runs on Netlify's infrastructure.

## Output Formats

### Separate Files
Click individual download buttons for each document.

### Merged File
Single `.txt` file with document separators:
```
<document id=1>
Content of first PDF...
</document>

<document id=2>
Content of second PDF...
</document>
```

## Technical Details

- **Serverless**: Uses Netlify Functions (AWS Lambda under the hood)
- **CORS Solution**: Server-side requests bypass browser restrictions
- **Rate Limiting**: Built-in delays to respect court website
- **Error Handling**: Graceful handling of network issues
- **Security**: Input validation and secure processing

## Contributing

1. Fork the repository
2. Make your changes
3. Test locally with `netlify dev`
4. Submit a pull request

## Alternative: Python CLI

If you prefer command-line tools:

```bash
pip install -r requirements.txt
python court_scraper.py
```

## License

MIT License - feel free to modify and distribute.

## Disclaimer

This tool is for legitimate research and legal purposes only. Please respect the terms of service of the websites you scrape.