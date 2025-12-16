import time
import json
from src.rate_limiter import rate_limited_sync

@rate_limited_sync
def analyze_features_with_ai(url, site_text, landscape_name, landscape_desc, features_list, model):
    """
    Analyzes features using JSON mode for reliability.
    """
    try:
        # Construct a JSON example structure dynamically
        example_structure = {feat: "YES/NO" for feat in features_list}
        
        prompt = f"""
        Role: Market Research Analyst
        Task: Analyze the website content below and determine if the product offers the specific features listed.
        
        Context: "{landscape_name}" ({landscape_desc})
        Website: {url}
        
        Instructions:
        For each feature, answer "Yes" or "No".
        Also provide a very short reason (max 10 words) for the answer.
        
        Features to check: {features_list}
        
        Return ONLY valid JSON in this format:
        {{
            "results": {{
                "Feature Name 1": {{ "answer": "Yes", "reason": "Mentioned on homepage" }},
                "Feature Name 2": {{ "answer": "No", "reason": "Not found in text" }}
            }}
        }}

        Website Text:
        {site_text[:15000]}
        """
        
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        answers = {}
        reasons = {}
        
        results = data.get("results", {})
        
        for feature in features_list:
            # Handle potential key mismatches or missing keys
            feat_data = results.get(feature)
            
            # If AI hallucinated a slightly different key, try to find partial match
            if not feat_data:
                for k, v in results.items():
                    if feature.lower() in k.lower():
                        feat_data = v
                        break
            
            if feat_data:
                answers[feature] = feat_data.get("answer", "Unknown")
                reasons[f"{feature}_reason"] = feat_data.get("reason", "")
            else:
                answers[feature] = "Unknown"
                reasons[f"{feature}_reason"] = "AI did not return data"
                
        return answers, reasons
        
    except Exception as e:
        print(f"   ⚠️ AI Feature Analysis Error: {e}")
        return {f: "Error" for f in features_list}, {}

@rate_limited_sync
def extract_product_info(url, site_text, landscape_name, landscape_desc, model):
    try:
        prompt = f"""
Analyze this website content for the "{landscape_name}" landscape.

Website URL: {url}
Content: {site_text[:12000]}

Task:
1. Identify the specific Product Name (if not found, use Company Name).
2. Write a 1-2 sentence Description of what the product does.
3. List 5-7 Key Features mentioned.

Format your response EXACTLY like this:
Product Name: [Name]
Description: [1-2 sentence summary]
Features:
• [Feature 1]
• [Feature 2]
• [Feature 3]
"""
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        info = {
            'URL': url,
            'Product Name': 'Not specified',
            'Description': 'Not specified',
            'Features': ''
        }
        
        lines = text.split('\n')
        current_section = None
        feature_list = []
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("Product Name:"):
                info['Product Name'] = line.replace("Product Name:", "").strip()
            elif line.startswith("Description:"):
                info['Description'] = line.replace("Description:", "").strip()
            elif line.startswith("Features:"):
                current_section = "features"
            elif current_section == "features" and (line.startswith("•") or line.startswith("-") or line[0].isdigit()):
                clean_feat = line.lstrip("•-1234567890. ").strip()
                feature_list.append(f"• {clean_feat}")
        
        if feature_list:
            info['Features'] = "\n".join(feature_list)
        elif "Features:" in text:
            try:
                info['Features'] = text.split("Features:")[1].strip()
            except: pass

        return info
    except:
        return {'URL': url, 'Product Name': 'Error', 'Description': '', 'Features': ''}

@rate_limited_sync
def deep_scan_page(url, text, model):
    try:
        prompt = f"""
Analyze this page: {url}
Content: {text[:10000]}

1. Does it mention Government/Municipality clients? (Yes/No)
2. Summarize the Case Study/Success Story (if present).

Return JSON:
{{ "has_government_mention": boolean, "analysis": "string summary" }}
"""
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        return None

@rate_limited_sync
def extract_pricing_details(url, text, model):
    try:
        prompt = f"""
Extract pricing model from: {text[:5000]}
Return JSON: {{ "pricing_model": "string" }}
"""
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        return None