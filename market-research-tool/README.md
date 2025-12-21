# Market Research Tool (AI-Powered)

## Introduction
This tool is a "Digital Detective." It visits company websites, reads their content using Google's Gemini AI, and tells you if they have specific features, what their pricing is, and if they work with the government.


## Setup 

Before running the engine, you must gather the tools. Open your terminal and run:

1. **Install Python Libraries:**
   `pip install -r requirements.txt`

2. **Install the Ghost Browser:**
   `playwright install chromium`


### How to read the logs:
Check the `market_research.log` file. You will see three levels of messages:
- `INFO`: General updates (e.g., "Starting scrape of Google.com").
- `WARNING`: Something went wrong, but the program kept going.
- `ERROR`: A major failure (e.g., "API Key is invalid").

## Operation (Running the Script)

1. **Start the program:**
   `python main.py`

2. **Provide your API Key:** 
   When prompted, paste your Gemini API Key.

3. **Input details:**
   - **Landscape Name:** e.g., "Cybersecurity"
   - **Features:** e.g., "AES-256, SOC2, SSO"
   - **URLs:** Paste the website addresses separated by spaces or commas.


## Output

Once the "Detective" finishes its work, look in the `/output` folder:
- **`_analysis.csv`**: A spreadsheet of every feature found.
- **`_products.csv`**: A list of product names and summaries.
- **`_graphs.png`**: A graph showing which features are most common.
- **`_ranking.png`**: A leaderboard of which companies have the most features.

## Project Structure

market_research_tool/

├── main.py                    <-- Run this one

├── diagnose_gemini.py         <-- Run this if the AI breaks

├── requirements.txt           <-- Libraries required

├── README.md                  <-- Manual

├── output/                    <-- (Empty for now, will fill with CSVs)

└── src/                       <-- Origin
    
    ├── __init__.py            <-- (Empty file)
   
    ├── analyzer.py            <-- Analysis function
    
    ├── config.py              <-- Configuration
   
    ├── rate_limiter.py        <-- Limits key usage
   
    ├── scraper.py             <-- Scraper
    
    └── visualizer.py          <-- Graph generatpr


## License

MIT License - see LICENSE file for details

## Troubleshooting

### Common Issues

**Issue**: "Could not find a working Gemini model"
- Solution: Check your API key and ensure it's valid

**Issue**: Playwright browser fails to launch
- Solution: Run `playwright install` again

**Issue**: "ModuleNotFoundError"
- Solution: Ensure virtual environment is activated and dependencies are installed

## Changelog

### v1.0.0 (2025-12-01)
- Initial release
- Feature analysis
- Product extraction
- Sitemap crawling

'''
