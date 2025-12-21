# -*- coding: utf-8 -*-
"""
Market Research Tool - Final Robust Version
"""

import os
import asyncio
import nest_asyncio
import pandas as pd
import json
from urllib.parse import urlparse

from src.config import setup_api_key, get_working_model
from src.scraper import (scrape_site, fetch_sitemap, parse_sitemap_urls, 
                        fetch_multiple_sitemaps, filter_relevant_pages, crawl_homepage_links)
from src.analyzer import analyze_features_with_ai, extract_product_info, deep_scan_page, extract_pricing_details

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
    
    landscape_name = input("\nLandscape Name: ") or "Secure File Transfer"
    landscape_desc = input("Description: ") or "Secure file sharing systems"
    
    feat_input = input("\nFeatures (comma separated): ")
    features_list = [f.strip() for f in feat_input.split(',') if f.strip()]
    if not features_list: features_list = ["Encryption", "Audit Logs"]
    
    url_input = input("\nURLs (comma or space separated): ")
    urls_list = [u.strip() for u in url_input.replace(',', ' ').split() if u.strip()]
    
    print(f"\n✅ Will analyze {len(urls_list)} URLs")
    return landscape_name, landscape_desc, features_list, urls_list

async def main():
    setup_api_key()
    landscape_name, landscape_desc, features_list, urls_list = get_user_inputs()
    
    print("\n🔧 Finding compatible Gemini model...")
    try:
        model = get_working_model()
    except Exception as e:
        print(f"❌ {e}")
        return
    
    # 1. FEATURE ANALYSIS
    print(f"\n{'='*60}")
    print(f"🚀 FEATURE ANALYSIS")
    print(f"{'='*60}\n")
    
    results_data = []
    for i, url in enumerate(urls_list, 1):
        print(f"[{i}/{len(urls_list)}] 🌐 Scraping {url}...")
        site_text = await scrape_site(url)
        
        if site_text:
            answers, reasons = analyze_features_with_ai(url, site_text, landscape_name, landscape_desc, features_list, model)
            row_data = {'URL': url, **answers, **reasons}
            results_data.append(row_data)
            
            # --- NEW: PRINT BOOLEANS TO CONSOLE ---
            print(f"   ✅ Analysis complete:")
            for feat in features_list:
                val = answers.get(feat, 'Unknown')
                print(f"      - {feat}: {val}")
        else:
            results_data.append({'URL': url, **{f: "Error" for f in features_list}})
            
    if results_data:
        outfile = os.path.join("output", f"{landscape_name.replace(' ', '_')}_analysis.csv")
        pd.DataFrame(results_data).to_csv(outfile, index=False)
        print(f"\n📁 Feature analysis saved to {outfile}")

    # 2. PRODUCT EXTRACTION
    print(f"\n{'='*60}")
    print("🔍 PRODUCT INFORMATION EXTRACTION")
    print(f"{'='*60}\n")
    
    product_data = []
    for i, url in enumerate(urls_list, 1):
        print(f"Processing {url}...")
        print(f"   🌐 Scraping {url}...")
        site_text = await scrape_site(url)
        
        if site_text:
            info = extract_product_info(url, site_text, landscape_name, landscape_desc, model)
            product_data.append(info)
            print(f"   ✅ Extracted: {info['Product Name']}")
        else:
            product_data.append({"URL": url, "Product Name": "Scrape Failed", "Description": "", "Features": ""})

    print(f"\n{'='*50}")
    print("PRODUCT EXTRACTION COMPLETE")
    print(f"{'='*50}\n")

    print("Product Information Summary:\n")
    for row in product_data:
        print("="*60)
        print(f"URL: {row.get('URL')}")
        print(f"Product name: {row.get('Product Name')}")
        print(f"Description: {row.get('Description')}")
        print(f"Features:\n{row.get('Features')}")
        print() 
    
    if product_data:
        df_prod = pd.DataFrame(product_data)
        outfile_prod = os.path.join("output", f"{landscape_name.replace(' ', '_')}_products.csv")
        df_prod.to_csv(outfile_prod, index=False)

    # 3. SITEMAP CRAWLER
    print(f"\n{'='*60}")
    response = input("Run sitemap crawler & deep scan? (y/n): ")
    if response.lower() == 'y':
        print("🕷️ DOMAIN CRAWL & DEEP SCAN")
        print(f"{'='*60}\n")
        
        domains = list(set(f"{urlparse(u).scheme}://{urlparse(u).netloc}" for u in urls_list))
        checkpoint_file = os.path.join("output", f"{landscape_name.replace(' ', '_')}_checkpoint.json")
        checkpoint_data = {"completed_domains": 0, "total_domains": len(domains), "results": []}
        csv_summary_data = []
        
        for i, domain in enumerate(domains, 1):
            print(f"🔍 Processing {domain} [{i}/{len(domains)}]...")
            
            sitemap_content, base_domain = await fetch_sitemap(domain)
            urls = []
            if sitemap_content:
                urls, is_index = parse_sitemap_urls(sitemap_content)
                if is_index: urls = await fetch_multiple_sitemaps(urls)
            
            # Fallback
            if not urls: urls = await crawl_homepage_links(domain)
            
            domain_result = {"domain": domain, "total_urls": len(urls), "scanned_case_studies": [], "pricing_info": []}
            filtered = filter_relevant_pages(urls, base_domain)
            
            # Case Studies
            for cs_url in filtered['case_studies'][:6]:
                cs_text = await scrape_site(cs_url) 
                if cs_text:
                    analysis = deep_scan_page(cs_url, cs_text, model)
                    if analysis:
                        is_gov = analysis.get('has_government_mention', False)
                        summary = analysis.get('analysis', '')
                        
                        domain_result["scanned_case_studies"].append({
                            "url": cs_url, 
                            "is_gov": "YES" if is_gov else "NO", 
                            "summary": summary
                        })
                        if is_gov: print(f"      🏛️ Found Gov Case Study")

            # Pricing
            for p_url in filtered['pricing'][:3]:
                p_text = await scrape_site(p_url)
                if p_text:
                    details = extract_pricing_details(p_url, p_text, model)
                    if details:
                        domain_result["pricing_info"].append({"url": p_url, "model": details.get('pricing_model', 'Unknown')})

            checkpoint_data["results"].append(domain_result)
            checkpoint_data["completed_domains"] += 1
            save_checkpoint(checkpoint_file, checkpoint_data)
            
            cs_text = "\n\n".join([f"[{c['is_gov']}] {c['url']}\n{c['summary']}" for c in domain_result["scanned_case_studies"]])
            csv_summary_data.append({
                'Domain': domain,
                'Total URLs': len(urls),
                'Case Studies Found': len(filtered['case_studies']),
                'Detailed Case Studies': cs_text,
                'Pricing Found': len(filtered['pricing'])
            })

        if csv_summary_data:
            df_crawl = pd.DataFrame(csv_summary_data)
            outfile_crawl = os.path.join("output", f"{landscape_name.replace(' ', '_')}_deep_crawl.csv")
            df_crawl.to_csv(outfile_crawl, index=False)
            print(f"\n📁 Final CSV results saved to {outfile_crawl}")

    print("\n✅ PROCESS COMPLETE")

if __name__ == "__main__":
    if not os.path.exists("output"):
        os.makedirs("output")
    asyncio.run(main())