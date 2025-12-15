import asyncio
import aiohttp
import csv
import json
import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
import google.generativeai as genai
import os

# ============================================================
# CONFIGURATION
# ============================================================

# Rate limiting configuration
LAST_API_CALL_TIME = 0
MIN_API_CALL_INTERVAL = 4.5  # seconds (15 requests/min = ~4s between calls)
MAX_RETRIES = 3
BATCH_SIZE = 5

# Model configuration
WORKING_MODEL = None

def get_api_key():
    """Get API key from user input or environment"""
    api_key = input("Step 1: Paste your Google Gemini API Key: ").strip()
    if not api_key:
        raise ValueError("API key is required")
    return api_key

def configure_api(api_key):
    """Configure the Gemini API"""
    genai.configure(api_key=api_key)

def get_working_model():
    """Find a working Gemini model"""
    global WORKING_MODEL
    
    if WORKING_MODEL:
        return WORKING_MODEL
    
    print("🔧 Finding compatible Gemini model...")
    models_to_try = [
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro'
    ]
    
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple request
            response = model.generate_content("Hi")
            if response:
                print(f"   ✓ Using model: {model_name}")
                WORKING_MODEL = model
                return model
        except Exception as e:
            continue
    
    raise Exception("Could not find a working Gemini model. Please check your API key and available models.")

# ============================================================
# RATE LIMITING & RETRY LOGIC
# ============================================================

async def rate_limited_delay():
    """Ensure minimum time between API calls"""
    global LAST_API_CALL_TIME
    current_time = time.time()
    time_since_last_call = current_time - LAST_API_CALL_TIME
    
    if time_since_last_call < MIN_API_CALL_INTERVAL:
        wait_time = MIN_API_CALL_INTERVAL - time_since_last_call
        await asyncio.sleep(wait_time)
    
    LAST_API_CALL_TIME = time.time()

async def api_call_with_retry(prompt, max_retries=MAX_RETRIES):
    """Make API call with retry logic and rate limiting"""
    for attempt in range(max_retries):
        try:
            await rate_limited_delay()
            model = get_working_model()
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e).lower()
            if "quota" in error_str or "429" in error_str or "rate" in error_str:
                if attempt < max_retries - 1:
                    wait_time = min(60 * (2 ** attempt), 300)  # Max 5 min wait
                    print(f"   ⏳ Quota exceeded, waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"   ❌ Max retries reached for API call")
                    raise
            else:
                raise
    
    raise Exception("API call failed after all retries")

# ============================================================
# CHECKPOINT MANAGEMENT
# ============================================================

def save_checkpoint(data, filename):
    """Save intermediate results"""
    checkpoint_file = f"{filename}_checkpoint.json"
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Checkpoint saved to {checkpoint_file}")
    except Exception as e:
        print(f"   ⚠️ Could not save checkpoint: {e}")

def load_checkpoint(filename):
    """Load saved checkpoint"""
    checkpoint_file = f"{filename}_checkpoint.json"
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"   ⚠️ Could not load checkpoint: {e}")
        return None

# ============================================================
# WEB SCRAPING
# ============================================================

async def scrape_url(url, session):
    """Scrape a URL and return its text content"""
    try:
        print(f"   🔍 Scraping {url}...")
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer"]):
                    script.decompose()
                
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text[:50000]  # Limit text length
            else:
                print(f"   ⚠️ HTTP {response.status} for {url}")
                return None
    except Exception as e:
        print(f"   ⚠️ Error scraping {url}: {e}")
        return None

# ============================================================
# FEATURE ANALYSIS
# ============================================================

async def analyze_feature(url, feature, text):
    """Analyze if a feature exists on a page"""
    try:
        if not text:
            return {
                'feature': feature,
                'present': 'AI Error',
                'reason': 'Could not scrape page content'
            }
        
        prompt = f"""Analyze this website content and determine if it mentions the feature: "{feature}"

Website content (truncated):
{text[:4000]}

Respond with EXACTLY this format:
YES or NO
Reason: [one sentence explanation]

Be specific and look for clear evidence of the feature."""
        
        response = await api_call_with_retry(prompt)
        
        lines = response.strip().split('\n')
        present = lines[0].strip().upper()
        reason = lines[1].replace('Reason:', '').strip() if len(lines) > 1 else "Analysis completed"
        
        if present not in ['YES', 'NO']:
            present = 'NO' if 'no' in response.lower()[:50] else 'AI Error'
        
        return {
            'feature': feature,
            'present': present,
            'reason': reason
        }
    except Exception as e:
        print(f"   ⚠️ Feature analysis error: {e}")
        return {
            'feature': feature,
            'present': 'AI Error',
            'reason': str(e)
        }

async def analyze_features_for_url(url, features, session):
    """Analyze all features for a single URL"""
    text = await scrape_url(url, session)
    
    results = {'URL': url}
    
    for feature in features:
        result = await analyze_feature(url, feature, text)
        results[feature] = result['present']
        results[f"{feature}_reason"] = result['reason']
    
    return results

async def analyze_all_features(urls, features):
    """Analyze features across all URLs"""
    print("\n" + "="*60)
    print("STARTING FEATURE ANALYSIS")
    print("="*60 + "\n")
    
    async with aiohttp.ClientSession() as session:
        results = []
        
        for i, url in enumerate(urls, 1):
            print(f"📄 Processing URL {i}/{len(urls)}: {url}")
            try:
                result = await analyze_features_for_url(url, features, session)
                results.append(result)
            except Exception as e:
                print(f"   ❌ Failed to process {url}: {e}")
                # Add error result
                error_result = {'URL': url}
                for feature in features:
                    error_result[feature] = 'Error'
                    error_result[f"{feature}_reason"] = str(e)
                results.append(error_result)
    
    return results

# ============================================================
# PRODUCT EXTRACTION
# ============================================================

async def extract_product_info(url, text):
    """Extract product information from a webpage"""
    try:
        if not text:
            return {
                'url': url,
                'name': 'Not specified',
                'description': 'Could not scrape content',
                'features': []
            }
        
        prompt = f"""Extract product information from this website content:

{text[:4000]}

Provide the response in this EXACT format:
PRODUCT NAME: [name]
DESCRIPTION: [one sentence description]
FEATURES:
• [feature 1]
• [feature 2]
• [feature 3]
[etc.]

Be specific and extract actual features mentioned on the page."""
        
        response = await api_call_with_retry(prompt)
        
        # Parse response
        lines = response.strip().split('\n')
        product_name = "Not specified"
        description = "Not specified"
        features = []
        
        in_features = False
        for line in lines:
            line = line.strip()
            if line.startswith('PRODUCT NAME:'):
                product_name = line.replace('PRODUCT NAME:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                description = line.replace('DESCRIPTION:', '').strip()
            elif line.startswith('FEATURES:'):
                in_features = True
            elif in_features and line.startswith('•'):
                features.append(line)
        
        return {
            'url': url,
            'name': product_name,
            'description': description,
            'features': features
        }
    except Exception as e:
        print(f"   ⚠️ Product extraction error: {e}")
        return {
            'url': url,
            'name': 'Error',
            'description': str(e),
            'features': []
        }

async def extract_all_products(urls):
    """Extract product information from all URLs"""
    print("\n" + "="*60)
    print("EXTRACTING PRODUCT INFORMATION")
    print("="*60 + "\n")
    
    products = []
    
    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(urls, 1):
            print(f"📄 Processing {i}/{len(urls)}: {url}")
            try:
                text = await scrape_url(url, session)
                product = await extract_product_info(url, text)
                products.append(product)
                print(f"   ✓ Extracted: {product['name']}")
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                products.append({
                    'url': url,
                    'name': 'Error',
                    'description': str(e),
                    'features': []
                })
    
    return products

# ============================================================
# SITEMAP CRAWLING
# ============================================================

async def fetch_sitemap(domain, session):
    """Fetch and parse sitemap"""
    sitemap_urls = [
        f"{domain}/sitemap.xml",
        f"{domain}/sitemap_index.xml",
        f"{domain}/sitemap-index.xml"
    ]
    
    for sitemap_url in sitemap_urls:
        try:
            async with session.get(sitemap_url, timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    return content, sitemap_url
        except:
            continue
    
    return None, None

def parse_sitemap(xml_content):
    """Parse sitemap XML and extract URLs"""
    urls = []
    try:
        root = ET.fromstring(xml_content)
        
        # Handle sitemap index
        for sitemap in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
            loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None:
                urls.append(('sitemap_index', loc.text))
        
        # Handle regular sitemap
        for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None:
                urls.append(('url', loc.text))
        
        return urls
    except Exception as e:
        print(f"   ⚠️ Error parsing sitemap: {e}")
        return []

async def analyze_pricing_page(url, text):
    """Analyze pricing page and extract structured pricing information"""
    try:
        if not text:
            return {
                'url': url,
                'pricing_model': 'Could not scrape',
                'tiers': 'N/A',
                'starting_price': 'N/A',
                'free_trial': 'N/A',
                'contact_for_quote': 'N/A',
                'details': 'Could not scrape content'
            }
        
        prompt = f"""Extract pricing information from this page:

{text[:6000]}

Provide EXACTLY this format:
PRICING MODEL: [subscription/one-time/per-adoption/usage-based/custom/freemium/etc]
TIERS: [list tier names if any, e.g., "Basic, Pro, Enterprise" or "Single tier"]
STARTING PRICE: [lowest price mentioned, e.g., "$99/month" or "Contact for pricing"]
FREE TRIAL: YES or NO
CONTACT FOR QUOTE: YES or NO
DETAILS: [2-3 sentence summary of pricing structure and what's included]"""
        
        response = await api_call_with_retry(prompt)
        
        # Parse response
        pricing_info = {
            'url': url,
            'pricing_model': 'Not specified',
            'tiers': 'N/A',
            'starting_price': 'N/A',
            'free_trial': 'N/A',
            'contact_for_quote': 'N/A',
            'details': 'Not specified'
        }
        
        for line in response.strip().split('\n'):
            line = line.strip()
            if line.startswith('PRICING MODEL:'):
                pricing_info['pricing_model'] = line.replace('PRICING MODEL:', '').strip()
            elif line.startswith('TIERS:'):
                pricing_info['tiers'] = line.replace('TIERS:', '').strip()
            elif line.startswith('STARTING PRICE:'):
                pricing_info['starting_price'] = line.replace('STARTING PRICE:', '').strip()
            elif line.startswith('FREE TRIAL:'):
                pricing_info['free_trial'] = line.replace('FREE TRIAL:', '').strip()
            elif line.startswith('CONTACT FOR QUOTE:'):
                pricing_info['contact_for_quote'] = line.replace('CONTACT FOR QUOTE:', '').strip()
            elif line.startswith('DETAILS:'):
                pricing_info['details'] = line.replace('DETAILS:', '').strip()
        
        return pricing_info
        
    except Exception as e:
        print(f"   ⚠️ Pricing analysis error: {e}")
        return {
            'url': url,
            'pricing_model': 'Error',
            'tiers': 'Error',
            'starting_price': 'Error',
            'free_trial': 'Error',
            'contact_for_quote': 'Error',
            'details': str(e)
        }

async def crawl_domain(domain, landscape_name, session):
    """Crawl a domain for case studies and pricing"""
    print(f"\n{'='*60}")
    print(f"🕷️  CRAWLING: {domain}")
    print("="*60 + "\n")
    
    result = {
        'domain': domain,
        'total_urls': 0,
        'case_studies': [],
        'pricing_pages': [],
        'government_urls': []
    }
    
    # Fetch sitemap
    print(f"   🔍 Looking for sitemap on {domain}...")
    sitemap_content, sitemap_url = await fetch_sitemap(domain, session)
    
    if not sitemap_content:
        print("   ⚠️ No sitemap found, will try fallback method")
        return result
    
    print(f"   ✓ Found sitemap at {sitemap_url}")
    
    # Parse sitemap
    entries = parse_sitemap(sitemap_content)
    all_urls = []
    
    # If sitemap index, fetch child sitemaps
    sitemap_indices = [url for type, url in entries if type == 'sitemap_index']
    if sitemap_indices:
        print(f"   📑 Found sitemap index with {len(sitemap_indices)} sitemaps")
        for sitemap_url in sitemap_indices[:20]:  # Limit to 20 sitemaps
            try:
                async with session.get(sitemap_url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        child_urls = parse_sitemap(content)
                        page_urls = [url for type, url in child_urls if type == 'url']
                        all_urls.extend(page_urls)
                        print(f"   ✓ Parsed {len(page_urls)} URLs from {sitemap_url}")
            except Exception as e:
                print(f"   ⚠️ Error fetching {sitemap_url}: {e}")
    else:
        all_urls = [url for type, url in entries if type == 'url']
    
    result['total_urls'] = len(all_urls)
    print(f"   📊 Total URLs found: {len(all_urls)}")
    
    # IMPROVED: Enhanced patterns for case studies, testimonials, and customer stories
    case_study_patterns = [
        r'case[-_]stud',
        r'customer[-_]stor',
        r'success[-_]stor',
        r'testimonial',
        r'review',
        r'/case/',
        r'/customer/',
        r'/success/',
        r'/stories/',
        r'/clients/',
        r'/portfolio/'
    ]
    
    # IMPROVED: Enhanced patterns for pricing pages
    pricing_patterns = [
        r'pricing',
        r'price',
        r'cost',
        r'/plans',
        r'/plan/',
        r'/quote',
        r'/fees',
        r'/packages',
        r'/subscription'
    ]
    
    gov_patterns = [
        r'government',
        r'municipal',
        r'city',
        r'county',
        r'public[-_]sector'
    ]
    
    for url in all_urls:
        url_lower = url.lower()
        
        if any(re.search(pattern, url_lower) for pattern in case_study_patterns):
            result['case_studies'].append(url)
        
        if any(re.search(pattern, url_lower) for pattern in pricing_patterns):
            result['pricing_pages'].append(url)
        
        if any(re.search(pattern, url_lower) for pattern in gov_patterns):
            result['government_urls'].append(url)
    
    print(f"   📚 Case study/testimonial pages found: {len(result['case_studies'])}")
    print(f"   💰 Pricing pages found: {len(result['pricing_pages'])}")
    print(f"   🏛️  Government-related URLs: {len(result['government_urls'])}")
    
    # Deep scan case studies (in batches)
    if result['case_studies']:
        print(f"\n   🔬 Deep scanning up to {min(10, len(result['case_studies']))} case study/testimonial pages...")
        case_studies_to_scan = result['case_studies'][:10]
        
        scanned_cases = []
        for i, url in enumerate(case_studies_to_scan, 1):
            try:
                print(f"   🔬 Deep scanning ({i}/{len(case_studies_to_scan)}): {url}...")
                text = await scrape_url(url, session)
                
                if text:
                    prompt = f"""Analyze this case study/testimonial and determine:
1. Is this a government/municipal case study? (YES/NO)
2. What is the client/customer name?
3. What was the problem/challenge?
4. What was the solution?
5. What were the results/benefits?

Content:
{text[:4000]}

Format your response as:
GOVERNMENT: YES/NO
CLIENT: [name]
PROBLEM: [brief description]
SOLUTION: [brief description]
RESULTS: [brief description]"""
                    
                    response = await api_call_with_retry(prompt)
                    
                    case_info = {
                        'url': url,
                        'analysis': response
                    }
                    
                    if 'GOVERNMENT: YES' in response:
                        print(f"   ✓ Found government case study: {url}")
                    
                    scanned_cases.append(case_info)
                    
                    # Small delay between scans
                    if i < len(case_studies_to_scan):
                        await asyncio.sleep(2)
                        
            except Exception as e:
                print(f"   ⚠️ Deep scan failed: {e}")
                continue
        
        result['scanned_case_studies'] = scanned_cases
    
    # IMPROVED: Analyze pricing pages with structured data extraction
    if result['pricing_pages']:
        print(f"\n   💰 Analyzing up to {min(5, len(result['pricing_pages']))} pricing pages...")
        pricing_to_scan = result['pricing_pages'][:5]
        
        pricing_info = []
        for i, url in enumerate(pricing_to_scan, 1):
            try:
                print(f"   💰 Extracting pricing ({i}/{len(pricing_to_scan)}): {url}...")
                text = await scrape_url(url, session)
                
                if text:
                    pricing_data = await analyze_pricing_page(url, text)
                    pricing_info.append(pricing_data)
                    print(f"   ✓ Pricing model: {pricing_data['pricing_model']}")
                    
                    # Small delay between analyses
                    if i < len(pricing_to_scan):
                        await asyncio.sleep(2)
                        
            except Exception as e:
                print(f"   ⚠️ Pricing analysis failed: {e}")
                continue
        
        result['pricing_info'] = pricing_info
    
    return result

async def crawl_all_domains(urls, landscape_name):
    """Crawl all domains"""
    print("\n" + "="*60)
    print("PHASE 3: SITEMAP CRAWL")
    print("="*60 + "\n")
    
    print("="*60)
    print("STARTING DOMAIN CRAWL FOR CASE STUDIES & PRICING")
    print("="*60 + "\n")
    
    # Extract domains from URLs
    domains = []
    for url in urls:
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain not in domains:
            domains.append(domain)
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        for i, domain in enumerate(domains, 1):
            print(f"\n🌐 Processing domain {i}/{len(domains)}")
            try:
                result = await crawl_domain(domain, landscape_name, session)
                results.append(result)
                
                # Save checkpoint after each domain
                save_checkpoint({
                    'completed_domains': i,
                    'total_domains': len(domains),
                    'results': results
                }, f"{landscape_name}_crawl")
                
            except Exception as e:
                print(f"   ❌ Failed to crawl {domain}: {e}")
                print(f"   ➡️  Continuing with next domain...")
                results.append({
                    'domain': domain,
                    'error': str(e)
                })
                continue
    
    return results

# ============================================================
# OUTPUT & SAVING
# ============================================================

def ensure_output_directory():
    """Create output directory if it doesn't exist"""
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    return output_dir

def save_feature_analysis(results, landscape_name):
    """Save feature analysis results to CSV"""
    if not results:
        return
    
    output_dir = ensure_output_directory()
    filename = os.path.join(output_dir, f"{landscape_name}_analysis.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n💾 Results saved to {filename}")

def save_products(products, landscape_name):
    """Save product information"""
    output_dir = ensure_output_directory()
    filename = os.path.join(output_dir, f"{landscape_name}_products.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Product Name', 'Description', 'Features'])
        
        for product in products:
            writer.writerow([
                product['url'],
                product['name'],
                product['description'],
                '\n'.join(product['features'])
            ])
    
    print(f"\n💾 Product data saved to {filename}")

def save_case_studies(crawl_results, landscape_name):
    """Save case study information to CSV"""
    output_dir = ensure_output_directory()
    filename = os.path.join(output_dir, f"{landscape_name}_case_studies.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Domain', 'URL', 'Is Government', 'Client', 'Problem', 'Solution', 'Results'])
        
        for domain_result in crawl_results:
            domain = domain_result.get('domain', 'Unknown')
            scanned_cases = domain_result.get('scanned_case_studies', [])
            
            for case in scanned_cases:
                url = case['url']
                analysis = case['analysis']
                
                # Parse the analysis
                is_gov = 'YES' if 'GOVERNMENT: YES' in analysis else 'NO'
                
                # Extract fields
                client = 'N/A'
                problem = 'N/A'
                solution = 'N/A'
                results = 'N/A'
                
                for line in analysis.split('\n'):
                    line = line.strip()
                    if line.startswith('CLIENT:'):
                        client = line.replace('CLIENT:', '').strip()
                    elif line.startswith('PROBLEM:'):
                        problem = line.replace('PROBLEM:', '').strip()
                    elif line.startswith('SOLUTION:'):
                        solution = line.replace('SOLUTION:', '').strip()
                    elif line.startswith('RESULTS:'):
                        results = line.replace('RESULTS:', '').strip()
                
                writer.writerow([domain, url, is_gov, client, problem, solution, results])
    
    print(f"\n💾 Case studies saved to {filename}")

def save_pricing(crawl_results, landscape_name):
    """Save pricing information to CSV"""
    output_dir = ensure_output_directory()
    filename = os.path.join(output_dir, f"{landscape_name}_pricing.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Domain', 'URL', 'Pricing Model', 'Tiers', 'Starting Price', 
                        'Free Trial', 'Contact for Quote', 'Details'])
        
        for domain_result in crawl_results:
            domain = domain_result.get('domain', 'Unknown')
            pricing_info = domain_result.get('pricing_info', [])
            
            for pricing in pricing_info:
                writer.writerow([
                    domain,
                    pricing['url'],
                    pricing['pricing_model'],
                    pricing['tiers'],
                    pricing['starting_price'],
                    pricing['free_trial'],
                    pricing['contact_for_quote'],
                    pricing['details']
                ])
    
    print(f"\n💾 Pricing data saved to {filename}")

def save_url_summary(crawl_results, landscape_name):
    """Save URL summary to CSV"""
    output_dir = ensure_output_directory()
    filename = os.path.join(output_dir, f"{landscape_name}_url_summary.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Domain', 'Total URLs Found', 'Case Study URLs', 'Pricing URLs', 'Government URLs'])
        
        for result in crawl_results:
            if 'error' not in result:
                writer.writerow([
                    result['domain'],
                    result['total_urls'],
                    len(result.get('case_studies', [])),
                    len(result.get('pricing_pages', [])),
                    len(result.get('government_urls', []))
                ])
    
    print(f"\n💾 URL summary saved to {filename}")

def print_summary(crawl_results):
    """Print summary of findings"""
    print("\n" + "="*60)
    print("CRAWL SUMMARY")
    print("="*60 + "\n")
    
    total_case_studies = sum(len(r.get('case_studies', [])) for r in crawl_results)
    total_pricing = sum(len(r.get('pricing_pages', [])) for r in crawl_results)
    total_gov = sum(len(r.get('government_urls', [])) for r in crawl_results)
    
    print(f"📚 Total case study/testimonial pages found: {total_case_studies}")
    print(f"💰 Total pricing pages found: {total_pricing}")
    print(f"🏛️  Total government-related URLs: {total_gov}")


# ============================================================
# MAIN
# ============================================================

async def main():
    """Main execution function"""
    print("="*60)
    print("MARKET RESEARCH & COMPETITIVE ANALYSIS TOOL")
    print("="*60 + "\n")
    
    try:
        # Configuration
        print("="*60)
        print("CONFIGURATION")
        print("="*60)
        
        api_key = get_api_key()
        configure_api(api_key)
        
        # Get landscape info
        landscape_name = input("\nStep 2: Define the Landscape\nLandscape Name: ").strip()
        landscape_description = input("Description: ").strip()
        
        # Get features
        features_input = input("\nStep 3: Define Features\nEnter features (comma separated): ").strip()
        features = [f.strip() for f in features_input.split(',')]
        
        # Get URLs
        urls_input = input("\nStep 4: Define Websites\nEnter URLs (comma or space separated): ").strip()
        urls = [u.strip() for u in re.split(r'[,\s]+', urls_input) if u.strip()]
        
        print(f"\n{'='*60}")
        print(f"Starting Analysis for: {landscape_name}")
        print(f"Looking for {len(features)} features on {len(urls)} websites...")
        print("="*60 + "\n")
        
        # Phase 1: Feature Analysis
        print("\n" + "="*60)
        print("PHASE 1: FEATURE ANALYSIS")
        print("="*60 + "\n")
        
        feature_results = await analyze_all_features(urls, features)
        
        print("\n" + "="*60)
        print("FEATURE ANALYSIS COMPLETE")
        print("="*60 + "\n")
        
        # Display results
        for result in feature_results:
            print(f"\n{result['URL']}")
            for feature in features:
                print(f"  {feature}: {result.get(feature, 'N/A')}")
        
        save_feature_analysis(feature_results, landscape_name)
        
        # Phase 2: Product Extraction
        print("\n" + "="*60)
        print("PHASE 2: PRODUCT INFORMATION EXTRACTION")
        print("="*60 + "\n")
        
        products = await extract_all_products(urls)
        
        print("\n" + "="*60)
        print("PRODUCT EXTRACTION COMPLETE")
        print("="*60 + "\n")
        
        print("Product Information Summary:\n")
        for product in products:
            print("="*60)
            print(f"URL: {product['url']}")
            print(f"Product Name: {product['name']}")
            print(f"Description: {product['description']}")
            print("Features:")
            for feature in product['features']:
                print(f"{feature}")
            print()
        
        save_products(products, landscape_name)
        
        # Phase 3: Sitemap Crawl
        crawl_results = await crawl_all_domains(urls, landscape_name)
        
        print_summary(crawl_results)
        
        # Save all results to CSV files
        save_case_studies(crawl_results, landscape_name)
        save_pricing(crawl_results, landscape_name)
        save_url_summary(crawl_results, landscape_name)
        
        print("\n" + "="*60)
        print("📊 OUTPUT FILES GENERATED")
        print("="*60)
        print(f"✓ {landscape_name}_analysis.csv - Feature analysis")
        print(f"✓ {landscape_name}_products.csv - Product information")
        print(f"✓ {landscape_name}_case_studies.csv - Case studies & testimonials")
        print(f"✓ {landscape_name}_pricing.csv - Pricing details")
        print(f"✓ {landscape_name}_url_summary.csv - URL summary by domain")
        
        print("\n" + "="*60)
        print("✅ ANALYSIS COMPLETE")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())