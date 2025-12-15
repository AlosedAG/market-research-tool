# -*- coding: utf-8 -*-
import os
import asyncio
import nest_asyncio
import pandas as pd
from urllib.parse import urlparse

from src.config import setup_api_key, get_working_model
from src.scraper import scrape_site, fetch_sitemap, parse_sitemap_urls, fetch_multiple_sitemaps, filter_relevant_pages
from src.analyzer import analyze_features_with_ai, extract_product_info, deep_scan_page, extract_pricing_details

# Apply asyncio patch
nest_asyncio.apply()

# --- INPUT SECTION ---
def get_user_inputs():
    print("\nStep 2: Define the Landscape")
    landscape_name = input("Landscape Name (e.g., Parking Management): ") or "Parking Management"
    landscape_desc = input("Description: ") or "Software for parking operations"

    print("\nStep 3: Define Features")
    feat_input = input("Enter features (comma separated): ")
    features_list = [f.strip() for f in feat_input.split(',') if f.strip()]
    if not features_list: features_list = ["LPR", "Mobile App"]

    print("\nStep 4: Define Websites")
    url_input = input("Enter URLs (comma or space separated): ")
    urls_list = [u.strip() for u in url_input.replace(',', ' ').split() if u.strip()]
    
    return landscape_name, landscape_desc, features_list, urls_list

# --- MAIN ORCHESTRATOR ---
async def main():
    setup_api_key()
    landscape_name, landscape_desc, features_list, urls_list = get_user_inputs()
    
    print("🔧 Finding compatible Gemini model...")
    try:
        model = get_working_model()
    except Exception as e:
        print(f"❌ {e}")
        return

    # 1. FEATURE ANALYSIS
    print(f"\n🚀 Starting Feature Analysis for: {landscape_name}")
    results_data = []
    
    for url in urls_list:
        site_text = await scrape_site(url)
        if site_text:
            answers, reasons = analyze_features_with_ai(url, site_text, landscape_name, landscape_desc, features_list, model)
            row_data = {'URL': url}
            row_data.update(answers)
            row_data.update(reasons)
            results_data.append(row_data)
        else:
            error_row = {'URL': url}
            for f in features_list:
                error_row[f] = "Scrape Failed"
                error_row[f"{f}_reason"] = "Could not retrieve website content"
            results_data.append(error_row)

    if results_data:
        df = pd.DataFrame(results_data)
        ordered_cols = ['URL'] + [col for f in features_list for col in (f, f"{f}_reason") if col in df.columns]
        df = df[[c for c in ordered_cols if c in df.columns]]
        
        outfile = os.path.join("output", f"{landscape_name.replace(' ', '_')}_analysis.csv")
        df.to_csv(outfile, index=False)
        print(f"📁 Analysis saved to {outfile}")

    # 2. PRODUCT EXTRACTION
    print(f"\n🔍 EXTRACTING PRODUCT INFORMATION")
    product_data = []
    for url in urls_list:
        site_text = await scrape_site(url)
        if site_text:
            info = extract_product_info(url, site_text, landscape_name, landscape_desc, model)
            product_data.append(info)
            print(f"   ✅ Extracted: {info['Product Name']}")
        else:
            product_data.append({"URL": url, "Product Name": "Scrape Failed"})

    if product_data:
        df_prod = pd.DataFrame(product_data)
        outfile_prod = os.path.join("output", f"{landscape_name.replace(' ', '_')}_products.csv")
        df_prod.to_csv(outfile_prod, index=False)
        print(f"📁 Product data saved to {outfile_prod}")

    # 3. SITEMAP CRAWLER
    print("\n🕷️ STARTING DOMAIN CRAWL")
    domains = set(f"{urlparse(u).scheme}://{urlparse(u).netloc}" for u in urls_list)
    all_crawl_results = []
    summary_data = []

    for domain in domains:
        sitemap_content, base_domain = await fetch_sitemap(domain)
        if not sitemap_content: continue

        urls, is_index = parse_sitemap_urls(sitemap_content)
        if is_index: urls = await fetch_multiple_sitemaps(urls)
        
        filtered = filter_relevant_pages(urls, base_domain)
        
        # Deep scans
        gov_cases = []
        if filtered['case_studies']:
            print(f"   🔍 Deep scanning case studies...")
            for url in filtered['case_studies'][:5]:
                txt = await scrape_site(url)
                analysis = await deep_scan_page(url, txt, model)
                if analysis and analysis.get('has_government_mention'):
                    gov_cases.append(analysis)

        pricing_details = []
        if filtered['pricing']:
            print(f"   💰 Analyzing pricing...")
            for url in filtered['pricing'][:3]:
                txt = await scrape_site(url)
                details = await extract_pricing_details(url, txt, model)
                if details: pricing_details.append(details)

        # Summarize for CSV
        pricing_str = "\n".join([f"Model: {p.get('pricing_model')}" for p in pricing_details])
        
        summary_data.append({
            'Domain': domain,
            'Total URLs': len(urls),
            'Case Studies': len(filtered['case_studies']),
            'Pricing Pages': len(filtered['pricing']),
            'Pricing Details': pricing_str,
            'Gov URLs': '\n'.join(filtered['government_related'])
        })

    if summary_data:
        df_crawl = pd.DataFrame(summary_data)
        outfile_crawl = os.path.join("output", f"{landscape_name.replace(' ', '_')}_crawl.csv")
        df_crawl.to_csv(outfile_crawl, index=False)
        print(f"📁 Crawl results saved to {outfile_crawl}")

    print("\n✅ PROCESS COMPLETE")

if __name__ == "__main__":
    # Ensure output directory exists
    if not os.path.exists("output"):
        os.makedirs("output")
    asyncio.run(main())