import asyncio
import logging
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
import aiohttp

async def scrape_site(url):
    logging.debug(f"Scraping {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            # Launch context with specific user agent to avoid bot detection
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Remove clutter
            await page.evaluate("""
                document.querySelectorAll('script, style, footer, nav, svg, noscript').forEach(el => el.remove());
            """)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
            return text[:30000]
        except Exception as e:
            logging.error(f"Error accessing {url}: {e}")
            return ""
        finally:
            await browser.close()

# --- Sitemap & Crawling Logic ---

async def fetch_sitemap(domain):
    if not domain.startswith('http'):
        domain = 'https://' + domain
    base_domain = domain.rstrip('/')
    
    # Common locations
    sitemap_urls = [
        f"{base_domain}/sitemap.xml",
        f"{base_domain}/sitemap_index.xml",
        f"{base_domain}/wp-sitemap.xml",
        f"{base_domain}/page-sitemap.xml",
        f"{base_domain}/sitemap.php"
    ]

    logging.debug(f"Looking for sitemap on {base_domain}...")
    async with aiohttp.ClientSession() as session:
        for sitemap_url in sitemap_urls:
            try:
                async with session.get(sitemap_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        # specific check to ensure it's not a 404 HTML page
                        if "xml" in response.headers.get('Content-Type', '') or "<?xml" in content[:50]:
                            logging.info(f"Found sitemap at {sitemap_url}")
                            return content, base_domain
            except Exception:
                continue
    return None, base_domain

def parse_sitemap_urls(xml_content):
    urls = []
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        
        # 1. Check for Sitemap Index (nested sitemaps)
        sitemaps = soup.find_all('sitemap')
        if sitemaps:
            nested_urls = [loc.text.strip() for loc in soup.select('sitemap > loc') if loc.text]
            if nested_urls:
                return nested_urls, True 

        # 2. Check for Standard URLs
        locs = soup.find_all('loc')
        urls = [loc.text.strip() for loc in locs if loc.text]
        
    except Exception as e:
        logging.warning(f"Error parsing sitemap: {e}")
    
    return urls, False

async def fetch_multiple_sitemaps(sitemap_urls):
    all_urls = []
    async with aiohttp.ClientSession() as session:
        for sitemap_url in sitemap_urls:
            try:
                async with session.get(sitemap_url, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        urls, _ = parse_sitemap_urls(content)
                        all_urls.extend(urls)
                        logging.info(f"Parsed {len(urls)} URLs from {sitemap_url}")
            except Exception:
                pass
    return all_urls

async def crawl_homepage_links(domain):
    logging.debug(f"Sitemap failed. Crawling homepage for links...")
    found_urls = set()
    base_domain = urlparse(domain).netloc
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(domain, timeout=25000, wait_until="domcontentloaded")
            
            # Get all hrefs
            hrefs = await page.evaluate("""
                Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
            """)
            
            for href in hrefs:
                # Filter for internal links only
                parsed = urlparse(href)
                if parsed.netloc == base_domain or parsed.netloc == "":
                    # Clean URL (remove fragments/queries for cleaner matching)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    found_urls.add(clean_url)

            logging.info(f"Found {len(found_urls)} internal links via crawl.")
            return list(found_urls)
            
        except Exception as e:
            logging.error(f"Crawl failed: {e}")
            return []
        finally:
            await browser.close()

def filter_relevant_pages(urls, base_domain):
    case_study_keywords = [
        'case-stud', 'customer-stor', 'success-stor', 'testimonial', 
        'client', 'project', 'portfolio', 'use-case', 'reviews', 
        '/work', '/results'
    ]
    pricing_keywords = ['pricing', 'plans', 'price', 'cost', 'quote', 'get-started', 'buy']
    government_keywords = ['government', 'gov', 'public-sector', 'municipal', 'city', 'federal', 'state', 'agency', 'council']

    results = {'case_studies': [], 'pricing': [], 'government_related': []}

    for url in urls:
        url_lower = url.lower()
        
        # Check for case studies
        if any(k in url_lower for k in case_study_keywords):
            results['case_studies'].append(url)
            # Check if Gov is in the URL itself (strong signal)
            if any(k in url_lower for k in government_keywords):
                results['government_related'].append(url)
        
        # Check for pricing
        if any(k in url_lower for k in pricing_keywords):
            results['pricing'].append(url)
            
    return results