# API Documentation

## Overview
This document describes the internal APIs used in the Market Research Tool for analyzing company websites and extracting feature data.

## Core Functions

### `analyze_features_with_ai()`

Analyzes website content using Google's Gemini AI to determine feature presence.

**Module:** `src.api_client`

**Signature:**
```python
def analyze_features_with_ai(
    url: str,
    site_text: str,
    landscape_name: str,
    landscape_desc: str,
    features_config: List[Dict],
    model: genai.GenerativeModel
) -> Tuple[Dict[str, str], Dict[str, str]]
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | str | Yes | Website URL being analyzed (for logging) |
| `site_text` | str | Yes | Extracted website text (max 8000 chars used) |
| `landscape_name` | str | Yes | Market landscape name (e.g., "CRM Tools") |
| `landscape_desc` | str | Yes | Description of the market landscape |
| `features_config` | List[Dict] | Yes | Feature definitions (see schema below) |
| `model` | GenerativeModel | Yes | Configured Gemini model instance |

**Feature Config Schema:**
```json
{
  "name": "Feature Name",
  "description": "What this feature means",
  "indicators": "Patterns that mean Yes",
  "exclusions": "Patterns that mean No"
}
```

**Returns:**

Tuple containing two dictionaries:
1. **answers** - Maps feature names to "Yes"/"No"/"Unsure"
2. **reasons** - Maps "{feature}_reason" to explanation strings

**Example:**
```python
features = [{
    'name': 'Live Chat',
    'description': 'Real-time customer support',
    'indicators': 'chat widget, live support',
    'exclusions': 'email only'
}]

answers, reasons = analyze_features_with_ai(
    url="https://example.com",
    site_text="We offer 24/7 live chat...",
    landscape_name="Support Tools",
    landscape_desc="Customer service platforms",
    features_config=features,
    model=model
)

# Result:
# answers = {'Live Chat': 'Yes'}
# reasons = {'Live Chat_reason': 'Mentions 24/7 live chat support'}
```

**Error Handling:**

Function never raises exceptions. On error, returns:
- All features marked as "Unsure"
- Reasons set to "Error during analysis"

**Rate Limiting:**

Decorated with `@rate_limited_sync` - maximum 10 calls per minute.

---

### `setup_api_key()`

Configures Google Gemini API authentication.

**Module:** `src.config`

**Signature:**
```python
def setup_api_key() -> str
```

**Parameters:** None

**Returns:**
- `str`: The configured API key

**Raises:**
- `ValueError`: If no API key is provided when prompted

**Behavior:**
1. Checks `GEMINI_API_KEY` environment variable
2. If not found, prompts user for input
3. Configures the genai client
4. Returns the API key

**Example:**
```python
# Set via environment
export GEMINI_API_KEY="your-key-here"

# Or interactive
api_key = setup_api_key()
# Prompts: "Paste your Gemini API key: "
```

---

## Data Models

### Company Analysis Result

Output format for company analysis:
```python
{
    "company_name": str,
    "website": str,
    "description": str,
    "feature_name": "Yes" | "No" | "Unsure",
    "feature_name_reason": str,
    # ... (repeated for each feature)
}
```

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Gemini API calls | 10 requests | 60 seconds |
| Web scraping | 5 requests | 60 seconds |

---

## Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| API key missing | No GEMINI_API_KEY found | Set environment variable or provide when prompted |
| Invalid JSON | AI returned malformed data | Feature marked as "Unsure", logged as error |
| Rate limit hit | Too many requests | Wait and retry automatically |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | None | Google Gemini API authentication key |
| `GEMINI_MODEL` | No | Interactive | Skip model selection prompt |
| `LOG_LEVEL` | No | INFO | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |
```

---

## Project Structure
```
docs/
├── API.md           # API reference (technical details)
├── USAGE.md         # How to use the tool (user guide)
└── ARCHITECTURE.md  # System design and flow

README.md            # Quick start guide