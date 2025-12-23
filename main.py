"""
Market Research Tool - Comprehensive Version
"""
import os
import asyncio
import nest_asyncio
import pandas as pd
import json
import logging
from urllib.parse import urlparse

from src.config import setup_api_key, get_working_model
from src.scraper import (scrape_site, fetch_sitemap, parse_sitemap_urls, fetch_multiple_sitemaps, filter_relevant_pages, crawl_homepage_links)
from src.analyzer import (extract_company_identity, analyze_features_with_ai, extract_product_info, deep_scan_page, extract_standardized_pricing)
from src.visualizer import generate_landscape_graphs

# Setup logging
logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s'
)

nest_asyncio.apply()

def save_checkpoint(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_user_inputs():
    print("\n" + "="*60)
    print("MARKET RESEARCH TOOL")
    print("="*60)
    
    landscape_name = input("\nLandscape Name (e.g., Drone Autonomy): ") or "Secure File Transfer"
    landscape_desc = input("Description: ") or "Secure file sharing systems"

    print("\n--- Feature Configuration ---")
    print("Define the features you want to verify. Leave 'Feature Name' blank to finish.")
    
    features_config = []
    while True:
        name = input(f"\nFeature Name #{len(features_config) + 1}: ").strip()
        if not name:
            if not features_config:
                print("Defaulting to basic features...")
                features_config = [
                    {"name": "Compliance", "description": "Security standards", "indicators": "SOC2, ISO, HIPAA", "exclusions": ""},
                    {"name": "Mobile App", "description": "Availability of iOS/Android apps", "indicators": "App Store, Play Store", "exclusions": "web-only"}
                ]
            break
            
        desc = input(f"  Description for '{name}': ").strip()
        ind = input(f"  Acceptable Indicators (Yes if mentions...): ").strip()
        exc = input(f"  Exclusion Indicators (No if mentions...): ").strip()
        
        features_config.append({
            "name": name,
            "description": desc,
            "indicators": ind,
            "exclusions": exc
        })
    
    url_input = input("\nURLs (comma or space separated): ")
    urls_list = [u.strip() for u in url_input.replace(',', ' ').split() if u.strip()]
    
    logging.info(f"\nWill analyze {len(urls_list)} URLs for {len(features_config)} features.")
    return landscape_name, landscape_desc, features_config, urls_list

async def main():
    setup_api_key()
    landscape_name, landscape_desc, features_config, urls_list = get_user_inputs()
    
    # Extract names only for visualizer/simple printing
    feature_names = [f['name'] for f in features_config]
    
    logging.info("\n Finding compatible Gemini model...")
    try:
        model = get_working_model()
    except Exception as e:
        logging.error(f"Not found {e}")
        return
    
    # ---------------------------------------------------------
    # 1. FEATURE ANALYSIS
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"FEATURE ANALYSIS")
    print(f"{'='*60}\n")
    
    results_data = []
    for i, url in enumerate(urls_list, 1):
        logging.info(f"[{i}/{len(urls_list)}] Analyzing {url}...")
        site_text = await scrape_site(url)
        
        if site_text:
            # Note: analyze_features_with_ai must be updated to handle the config list
            answers, reasons = analyze_features_with_ai(url, site_text, landscape_name, landscape_desc, features_config, model)
            
            # Combine results for DataFrame
            row_data = {'URL': url}
            row_data.update(answers)
            row_data.update(reasons)
            results_data.append(row_data)
            
            logging.info(f"Analysis complete for {url}")
            for fname in feature_names:
                print(f"      - {fname}: {answers.get(fname, 'Unsure')}")
        else:
            results_data.append({'URL': url, **{f: "Error" for f in feature_names}})
            
    if results_data:
        df_analysis = pd.DataFrame(results_data)
        outfile = os.path.join("output", f"{landscape_name.replace(' ', '_')}_analysis.csv")
        df_analysis.to_csv(outfile, index=False)
        logging.info(f"\nFeature analysis saved to {outfile}")
        
        print(f"\n{'-'*60}")
        vis_response = input("Generate landscape graphs? (y/n): ")
        if vis_response.lower() == 'y':
            # Visualizer uses the simple string names
            generate_landscape_graphs(df_analysis, landscape_name, feature_names)

    # ---------------------------------------------------------
    # 2. PRODUCT EXTRACTION
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    print("🔍 PRODUCT INFORMATION EXTRACTION")
    print(f"{'='*60}\n")
    
    product_data = []
    for i, url in enumerate(urls_list, 1):
        logging.info(f"Processing {url}...")
        site_text = await scrape_site(url)
        
        if site_text:
            info = extract_product_info(url, site_text, landscape_name, landscape_desc, model)
            product_data.append(info)
            logging.info(f"Extracted: {info['Product Name']}")
        else:
            product_data.append({"URL": url, "Product Name": "Scrape Failed", "Description": "", "Features": ""})
    
    if product_data:
        df_prod = pd.DataFrame(product_data)
        outfile_prod = os.path.join("output", f"{landscape_name.replace(' ', '_')}_products.csv")
        df_prod.to_csv(outfile_prod, index=False)

    # ---------------------------------------------------------
    # 3. SITEMAP CRAWLER & DEEP SCAN
    # ---------------------------------------------------------
    print(f"\n{'='*60}")
    response = input("Run sitemap crawler & deep scan? (y/n): ")
    if response.lower() == 'y':
        print(" DOMAIN CRAWL & DEEP SCAN")
        print(f"{'='*60}\n")
        
        domains = list(set(f"{urlparse(u).scheme}://{urlparse(u).netloc}" for u in urls_list))
        checkpoint_file = os.path.join("output", f"{landscape_name.replace(' ', '_')}_checkpoint.json")
        checkpoint_data = {"completed_domains": 0, "total_domains": len(domains), "results": []}
        csv_summary_data = []
        
        for i, domain in enumerate(domains, 1):
            logging.info(f"Crawling {domain} [{i}/{len(domains)}]...")
            
            sitemap_content, base_domain = await fetch_sitemap(domain)
            urls = []
            if sitemap_content:
                urls, is_index = parse_sitemap_urls(sitemap_content)
                if is_index: urls = await fetch_multiple_sitemaps(urls)
            
            if not urls: 
                urls = await crawl_homepage_links(domain)
            
            domain_result = {"domain": domain, "total_urls": len(urls), "scanned_case_studies": [], "pricing_info": []}
            filtered = filter_relevant_pages(urls, base_domain)
            
            # Deep Scan: Case Studies
            for cs_url in filtered['case_studies'][:2]:
                cs_text = await scrape_site(cs_url)
                if cs_text:
                    analysis = deep_scan_page(cs_url, cs_text, model)
                    if analysis:
                        domain_result["scanned_case_studies"].append({
                            "url": cs_url, 
                            "is_gov": "YES" if analysis.get('has_government_mention') else "NO", 
                            "summary": analysis.get('analysis', 'No summary')
                        })

            # Deep Scan: Pricing
            for p_url in filtered['pricing'][:3]:
                p_text = await scrape_site(p_url)
                if p_text:
                    details = extract_standardized_pricing(p_url, p_text, model)
                    if details:
                        domain_result["pricing_info"].append({
                            "url": p_url, 
                            "pricing_model": details.get('pricing_model','Unsure'),
                            "starting_price": details.get('starting_price', 'Unsure'),
                            "details": details.get('details', '')
                        })

            checkpoint_data["results"].append(domain_result)
            checkpoint_data["completed_domains"] += 1
            save_checkpoint(checkpoint_file, checkpoint_data)
            
            # CSV Formatting Logic
            cs_entries = [f"[{c['is_gov']}] {c['url']} - {c['summary']}" for c in domain_result["scanned_case_studies"]]
            pricing_entries = [f"{p['pricing_model']} ({p['starting_price']})" for p in domain_result["pricing_info"]]

            csv_summary_data.append({
                'Domain': domain,
                'Total URLs': len(urls),
                'Case Studies Found': len(filtered['case_studies']),
                'Verified Case Studies': " || ".join(cs_entries),
                'Pricing Pages': len(filtered['pricing']),
                'Pricing Info': " || ".join(pricing_entries)
            })

        if csv_summary_data:
            df_crawl = pd.DataFrame(csv_summary_data)
            outfile_crawl = os.path.join("output", f"{landscape_name.replace(' ', '_')}_deep_crawl.csv")
            df_crawl.to_csv(outfile_crawl, index=False)
            logging.info(f"\nFinal Deep Crawl results saved to {outfile_crawl}")

    logging.info("\nALL PROCESSES COMPLETE")

if __name__ == "__main__":
    if not os.path.exists("output"):
        os.makedirs("output")
    asyncio.run(main())