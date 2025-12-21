import logging
import time
import json
import re
from urllib.parse import urlparse
from src.rate_limiter import rate_limited_sync

def clean_text(text):
    if not text: return ""
    text = text.replace('\n', ' ').replace('\r', '')
    return re.sub(' +', ' ', text).strip()

@rate_limited_sync
def extract_company_identity(url, site_text, model):
#Specifically seeks the company name looking at header, footer, and domain logic.
    domain = urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()
    
    try:
        prompt = f"""
        Task: Identify the official Company Name.
        URL: {url}
        Domain Hint: {domain}
        
        Instructions:
        1. Look at the Header area for brand names.
        2. Look at the Footer for Copyright notices (e.g., "© 2024 [Company Name] Inc.").
        3. If the brand name differs from the domain, prioritize the brand name found in the content.
        
        Return JSON:
        {{
            "company_name": "The official name",
            "confidence_source": "header/footer/domain/content"
        }}

        Content (Focusing on Header and Footer):
        {site_text[:2000]} 
        ...
        {site_text[-2000:]}
        """
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        return data.get("company_name", domain)
    except:
        return domain

@rate_limited_sync
def analyze_features_with_ai(url, site_text, landscape_name, landscape_desc, features_config, model):
    """Analyze website features using AI based on configured criteria."""
    logger = logging.getLogger(__name__)
    
    try:
        # Extract feature names for later use
        features_list = [f['name'] for f in features_config]
        
        # Construct a clear rubric for the AI
        criteria_rubric = ""
        for f in features_config:
            criteria_rubric += f"""
        FEATURE: {f['name']}
        - Definition: {f['description']}
        - "Yes" Indicators: {f['indicators']}
        - "No" Indicators/Exclusions: {f['exclusions']}
        """
        
        # Build the prompt (FIXED: moved outside the loop)
        prompt = f"""
        Role: Professional Market Researcher
        Context: Analyzing companies for the "{landscape_name}" landscape.
        
        Task: Determine if the website provides the following features based on the criteria below.
        
        {criteria_rubric}
        
        Evaluation Rules:
        1. Answer "Yes" only if the "Yes Indicators" are found.
        2. Answer "No" if the "Exclusion Indicators" are found or the feature is explicitly absent.
        3. Answer "Unsure" if the text is vague or does not provide enough specific evidence.
        
        Return ONLY valid JSON in this exact format:
        {{
            "results": {{
                "Feature Name": {{ "answer": "Yes/No/Unsure", "reason": "Max 10 words reason" }}
            }}
        }}
        
        Website Content:
        {site_text[:8000]}
        """
        
        # Call AI model
        logger.info(f"Analyzing features for {url}")
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        
        # Process results
        answers = {}
        reasons = {}
        results = data.get("results", {})
        
        for feature in features_list:
            feat_data = results.get(feature)
            
            # Fuzzy match fallback
            if not feat_data:
                for k, v in results.items():
                    if feature.lower() in k.lower():
                        feat_data = v
                        break
            
            if feat_data:
                answers[feature] = feat_data.get("answer", "Unsure")
                reasons[f"{feature}_reason"] = clean_text(feat_data.get("reason", ""))
            else:
                answers[feature] = "Unsure"
                reasons[f"{feature}_reason"] = "AI data missing"
                
        logger.info(f"Successfully analyzed {len(features_list)} features for {url}")
        return answers, reasons
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response for {url}: {e}")
        answers = {f['name']: "Unsure" for f in features_config}
        reasons = {f"{f['name']}_reason": "Invalid AI response format" for f in features_config}
        return answers, reasons
        
    except Exception as e:
        logger.error(f"Error analyzing features for {url}: {e}")
        answers = {f['name']: "Unsure" for f in features_config}
        reasons = {f"{f['name']}_reason": "Error during analysis" for f in features_config}
        return answers, reasons

@rate_limited_sync
def extract_product_info(url, site_text, landscape_name, landscape_desc, model):
    try:
        # Use the specialized company identity logic
        company_name = extract_company_identity(url, site_text, model)
        
        prompt = f"""
        Analyze content for "{landscape_name}", "{landscape_desc}".
        URL: {url}
        Content: {site_text[:10000]}

        Based on the content, extract the product information. 
        For the "Features" section, list ONLY the names of the core capabilities or modules mentioned (e.g., "Flight Automation"). Do not include descriptions, explanations, or long sentences.

        Format EXACTLY as follows:
        Product Name: [Name]
        Description: [One single concise sentence summary]
        Features:
        • [Feature Name 1]
        • [Feature Name 2]
        • [Feature Name 3]
        """
        response = model.generate_content(prompt)
        text = response.text.strip()

        info = {
            'URL': url, 
            'Company Name': company_name, 
            'Product Name': 'Not specified', 
            'Description': '', 
            'Features': ''
        }
        
        lines = text.split('\n')
        feature_list = []
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("Product Name:"):
                info['Product Name'] = line.replace("Product Name:", "").strip()
            elif line.startswith("Description:"):
                info['Description'] = clean_text(line.replace("Description:", "").strip())
            elif line.startswith("Features:"):
                current_section = "features"
            elif current_section == "features" and (line.startswith("•") or line.startswith("-")):
                feature_name = line.replace('•', '').split(':')[0].strip()
                feature_list.append(f"• {feature_name}")
        
        if feature_list:
            info['Features'] = " | ".join(feature_list)
        
        return info
    except:
        return {'URL': url, 'Company Name': 'Error', 'Product Name': 'Error', 'Description': '', 'Features': ''}

@rate_limited_sync
def deep_scan_page(url, text, model):
    try:
        prompt = f"""
Analyze this case study: {url}
Content: {text[:6000]}

1. Does it explicitly mention Government, Municipality, County, Town, City, State or Public Sector clients? (boolean)
2. Provide a 1-sentence summary of the client and result (Max 25 words).

Return JSON:
{{ 
    "has_government_mention": boolean, 
    "analysis": "Short 1-sentence summary." 
}}
"""
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        data = json.loads(response.text)
        data['analysis'] = clean_text(data.get('analysis', ''))
        return data
    except:
        return None

@rate_limited_sync
def extract_standardized_pricing(url, site_text, model):
    mapping_instructions = """
    Map the website's pricing model to these 'Standardized Formats':
    - Add-on based -> Change To: Add-on pricing | Other: Add-ons available. | Billing: Quarterly or annual billing.
    - All in one platform -> Change To: All-in-one platform pricing | Other: Price per device | Billing: Monthly or Annually.
    - All-in-one -> Change To: All-in-one platform pricing | Billing: Annual Billing.
    - Annual -> Change To: Subscription-based. | Billing: Monthly.
    - Consumption-based -> Change To: Usage-based pricing
    - Custom / Custom model / N/A / Unknown -> Change To: Custom pricing
    - Device-based -> Change To: Device-based pricing
    - Enterprise -> Change To: Custom pricing (enterprise)
    - Feature and user based -> Change To: Hybrid pricing (features + users)
    - Feature based / Features-based -> Change To: Feature-based pricing
    - Fee for each transaction / Per transaction -> Change To: Transaction-based pricing
    - Free -> Change To: Free tier available
    - Freemium -> Change To: Freemium model
    - Hybrid -> Change To: Hybrid pricing model
    - Lifetime / One-time -> Change To: One-time license
    - Module based -> Change To: Module-based pricing
    - Monthly / Recurring / SaaS / SAAS / Subscription -> Change To: Subscription-based.
    - Package with add-ons / Packages + add-ons -> Change To: Packages with optional add-ons
    - Package-based -> Change To: Package-based pricing
    - Pay-as-you-go / Usage-based -> Change To: Usage-based pricing
    - Per site pricing -> Change To: Site-based pricing
    - Per user / Per-user / User-based -> Change To: Per-user pricing
    - Tiered / Tiered model / Tiered pricing -> Change To: Tiered pricing
    """

    try:
        prompt = f"""
        Analyze the pricing for: {url}
        Content: {site_text[:8000]}

        Step 1: Determine the actual pricing model used on the site.
        Step 2: Use the Mapping Instructions below to translate it into the target format.

        Mapping Instructions:
        {mapping_instructions}

        Return JSON:
        {{
            "original_found": "Brief description of what you found on site",
            "standardized_change_to": "The 'Change To...' value from mapping",
            "standardized_other": "The 'Other...' value from mapping if applicable, else null",
            "standardized_billing_type": "The 'Billing Type' value from mapping if applicable, else null",
            "starting_price": "e.g. $10/mo or 'Contact Sales'"
        }}
        """
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except:
        return None
    
