import json
from src.config import get_working_model

def analyze_features_with_ai(url, text, landscape, description, features, model=None):
    if not text:
        return {f: "Error" for f in features}, {f"{f}_reason": "No text to analyze" for f in features}

    if model is None:
        model = get_working_model()

    prompt = f"""
    Role: Expert Market Research Analyst.
    Task: Analyze the text from the website provided below.

    Context - Landscape: "{landscape}"
    Context - Definition: "{description}"

    Instructions:
    For each feature listed below, determine if this specific product/company offers it based ONLY on the website text.

    Return a valid JSON object with this structure:
    {{
        "feature_name": {{
            "answer": "YES" or "NO",
            "reason": "Brief explanation with relevant quote from the text if YES, or why it wasn't found if NO"
        }}
    }}

    Features to check: {features}

    Website Text:
    {text}
    """

    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.1})
        parsed = json.loads(response.text)
        answers, reasons = {}, {}

        for feature in features:
            if feature in parsed:
                answers[feature] = parsed[feature].get("answer", "AI Error")
                reasons[f"{feature}_reason"] = parsed[feature].get("reason", "No reason provided")
            else:
                answers[feature] = "AI Error"
                reasons[f"{feature}_reason"] = "Feature not found in response"
        return answers, reasons
    except Exception as e:
        print(f"   ⚠️ AI Analysis failed: {e}")
        return {f: "AI Error" for f in features}, {f"{f}_reason": f"Error: {str(e)}" for f in features}

def extract_product_info(url, text, landscape, description, model=None):
    if not text:
        return {"URL": url, "Product Name": "Error", "Description": "No content", "Features": ""}
    
    if model is None:
        model = get_working_model()

    prompt = f"""
    Role: Expert Product Analyst
    Task: Extract key product information from the website text below.
    Context: "{landscape}" - "{description}"

    Instructions:
    1. Identify the main product name
    2. Extract a concise description (1-2 sentences)
    3. List 3-8 key features

    Return ONLY JSON:
    {{
        "product_name": "Name",
        "description": "Summary",
        "features": ["F1", "F2"]
    }}

    Website URL: {url}
    Website Text: {text}
    """

    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.2})
        data = json.loads(response.text)
        features_str = "\n".join([f"• {feat}" for feat in data.get('features', [])])
        return {
            "URL": url,
            "Product Name": data.get('product_name', 'Not specified'),
            "Description": data.get('description', 'Not available'),
            "Features": features_str
        }
    except Exception as e:
        print(f"   ⚠️ Product extraction failed for {url}: {e}")
        return {"URL": url, "Product Name": "AI Error", "Description": "Extraction failed", "Features": ""}

async def deep_scan_page(url, text, model=None):
    if not text: return None
    if model is None: model = get_working_model()

    prompt = f"""
    Role: Content Analyst
    Task: Analyze this webpage:
    1. Does it contain case studies/testimonials?
    2. Does it mention government/public sector clients?
    3. If yes to #1, extract case study titles.

    Return ONLY JSON:
    {{
        "has_case_studies": true/false,
        "has_government_mention": true/false,
        "case_study_titles": ["Title 1"],
        "government_clients": ["Client 1"]
    }}

    Text: {text[:15000]}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.1})
        return json.loads(response.text)
    except Exception:
        return None

async def extract_pricing_details(url, text, model=None):
    if not text: return None
    if model is None: model = get_working_model()

    prompt = f"""
    Role: Pricing Analyst
    Task: Extract pricing info.
    1. Pricing model?
    2. Tiers/Plans?
    3. Notes?

    Return ONLY JSON:
    {{
        "pricing_model": "text",
        "has_public_pricing": true/false,
        "pricing_tiers": [{{"name": "text", "price": "text", "details": "text"}}],
        "notes": "text"
    }}
    
    URL: {url}
    Text: {text[:20000]}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 0.1})
        result = json.loads(response.text)
        result['url'] = url
        return result
    except Exception:
        return None