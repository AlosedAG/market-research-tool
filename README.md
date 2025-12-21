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
```text
market_research_tool/
├── main.py
│   └── Entry point (run this)
├── diagnose_gemini.py
│   └── Diagnostic script (use if the AI model fails)
├── requirements.txt
│   └── Required Python libraries
├── README.md
│   └── Project documentation
├── output/
│   └── Generated results (CSV files)
└── src/
    ├── __init__.py
    │   └── Package marker
    ├── analyzer.py
    │   └── Analysis logic
    ├── config.py
    │   └── Configuration and API keys
    ├── rate_limiter.py
    │   └── API usage and rate limiting
    ├── scraper.py
    │   └── Website scraping logic
    └── visualizer.py
        └── Data visualization and graphs


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
