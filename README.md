README_CONTENT = '''# Market Research & Competitive Analysis Tool

A comprehensive Python tool for analyzing competitor websites, extracting product information, and discovering case studies and pricing pages using AI-powered analysis.

## Features

- **Feature Analysis**: Detect specific features across competitor websites
- **Product Extraction**: Extract product names, descriptions, and key features
- **Sitemap Crawling**: Discover case studies, testimonials, and pricing pages
- **AI-Powered**: Uses Google Gemini for intelligent content analysis
- **CSV Export**: Export all results to structured CSV files

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Setup

1. Clone the repository:
```bash
git clone https://github.com/
cd market-research-tool
```

2. Create a virtual environment:
```bash
python -m venv venv

# On Windows
venv\\Scripts\\activate

# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
playwright install-deps
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Usage

### Basic Usage

Run the interactive tool:
```bash
python main.py
```

Follow the prompts to:
1. Enter your Google Gemini API key (or set it in .env)
2. Define your market landscape
3. Specify features to analyze
4. Provide URLs to scan

### Programmatic Usage

```python
from market_research import MarketResearchTool

# Initialize
tool = MarketResearchTool(
    api_key="your-api-key",
    landscape_name="Parking Management",
    landscape_desc="Software for parking operations"
)

# Analyze features
results = await tool.analyze_features(
    urls=["https://example.com"],
    features=["LPR", "Mobile App"]
)

# Extract product info
products = await tool.extract_products(urls=["https://example.com"])

# Crawl for case studies
case_studies = await tool.crawl_domains(urls=["https://example.com"])
```

## Output

The tool generates three CSV files in the `output/` directory:

1. **{landscape}_analysis.csv**: Feature presence analysis with reasons
2. **{landscape}_products.csv**: Extracted product information
3. **{landscape}_crawl_results.csv**: Case studies, pricing, and government links

## Configuration

### Environment Variables

Create a `.env` file:
```
GEMINI_API_KEY=your_api_key_here
DEFAULT_TIMEOUT=25000
MAX_CONCURRENT_REQUESTS=5
```

### Config File

Edit `config.py` to customize:
- Model selection
- Timeout settings
- Output formatting
- Logging levels

## Project Structure

```
market-research-tool/
├── main.py                      # Entry point
├── config.py                    # Configuration
├── market_research/             # Main package
│   ├── core/                    # Core functionality
│   ├── analyzers/               # Analysis modules
│   └── utils/                   # Utilities
├── tests/                       # Unit tests
└── output/                      # Generated reports
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project uses:
- Black for code formatting
- isort for import sorting
- pylint for linting

```bash
black .
isort .
pylint market_research/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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

## Support

For issues and questions:
- Open an issue on GitHub
- Email: support@yourcompany.com

## Changelog

### v1.0.0 (2024-01-XX)
- Initial release
- Feature analysis
- Product extraction
- Sitemap crawling

'''

This repository contains the original implementation authored by Aylín Altamirano.
Later internal adaptations are not included.
