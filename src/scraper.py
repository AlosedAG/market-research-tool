import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import aiohttp

async def scrape_site(url):
    print(f"   🌐 Scraping {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
            await page.goto(url, timeout=25000, wait_until="domcontentloaded")
            content = await page.content()

            soup = BeautifulSoup(content, 'html.parser')
            for tag in soup(["script", "style", "footer", "nav", "svg", "noscript"]):
                tag.extract()
            text = soup.get_text(separator=' ', strip=True)
            return text[:30000]
        except Exception as e:
            print(f"   ❌ Error accessing {url}: {e}")
            return ""
        finally:
            await browser.close()

# --- Sitemap Logic ---

async def fetch_sitemap(domain):
    if not domain.startswith('http'):
        domain = 'https://' + domain
    base_domain = domain.rstrip('/')
    
    sitemap_urls = [
        f"{base_domain}/sitemap.xml",
        f"{base_domain}/sitemap_index.xml",
        f"{base_domain}/sitemap-index.xml",
        f"{base_domain}/wp-sitemap.xml",
        f"{base_domain}/page-sitemap.xml"
    ]

    print(f"   🔍 Looking for sitemap on {base_domain}...")
    async with aiohttp.ClientSession() as session:
        for sitemap_url in sitemap_urls:
            try:
                async with session.get(sitemap_url, timeout=15) as response:
                    if response.status == 200:
                        content = await response.text()
                        print(f"   ✅ Found sitemap at {sitemap_url}")
                        return content, base_domain
            except Exception:
                continue
    print(f"   ⚠️ No sitemap found, will try fallback method")
    return None, base_domain

def parse_sitemap_urls(xml_content):
    urls = []
    try:
        root = ET.fromstring(xml_content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        sitemaps = root.findall('.//ns:sitemap/ns:loc', namespaces)
        if sitemaps:
            return [sm.text for sm in sitemaps], True 

        url_elements = root.findall('.//ns:url/ns:loc', namespaces)
        urls = [url.text for url in url_elements if url.text]

        if not urls:
            for loc in root.iter('loc'):
                if loc.text:
                    urls.append(loc.text)
    except Exception as e:
        print(f"   ⚠️ Error parsing sitemap: {e}")
    return urls, False

async def fetch_multiple_sitemaps(sitemap_urls):
    all_urls = []
    async with aiohttp.ClientSession() as session:
        for sitemap_url in sitemap_urls:
            try:
                async with session.get(sitemap_url, timeout=15) as response:
                    if response.status == 200:
                        content = await response.text()
                        urls, _ = parse_sitemap_urls(content)
                        all_urls.extend(urls)
                        print(f"   📄 Parsed {len(urls)} URLs from {sitemap_url}")
            except Exception:
                print(f"   ⚠️ Could not fetch {sitemap_url}")
    return all_urls

def filter_relevant_pages(urls, base_domain):
    case_study_keywords = ['case-stud', 'customer-stor', 'success-stor', 'testimonial', 'client-stor', 'case_stud', 'reviews', 'customers/', '/stories', 'use-case']
    pricing_keywords = ['pricing', 'plans', 'price', 'cost', 'quote', 'get-started', 'buy', 'purchase']
    government_keywords = ['government', 'gov', 'public-sector', 'municipal', 'city', 'federal', 'state', 'agency', 'civic']

    results = {'case_studies': [], 'pricing': [], 'government_related': []}

    for url in urls:
        url_lower = url.lower()
        if any(k in url_lower for k in case_study_keywords):
            results['case_studies'].append(url)
            if any(k in url_lower for k in government_keywords):
                results['government_related'].append(url)
        if any(k in url_lower for k in pricing_keywords):
            results['pricing'].append(url)
    return results