import time
import random
import re
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import markdownify

class ScraperError(Exception):
    """Custom exception for scraper errors."""
    pass

def get_delay_from_config(config_path):
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'\*\s*\*\*stealth_fetch_delay_seconds:\*\*\s*(\d+)', content)
            if match:
                return int(match.group(1))
    except Exception as e:
        print(f"Could not read delay from config: {e}. Defaulting to 15 seconds.")
    return 15

def simulate_human_scrolling(driver):
    """Simulates a human reading the page by scrolling down in random increments."""
    print("Simulating human scrolling...")
    
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    current_position = 0
    scroll_attempts = 0
    max_attempts = 15 # safety limit
    
    while current_position < total_height and scroll_attempts < max_attempts:
        scroll_step = random.uniform(viewport_height * 0.3, viewport_height * 0.8)
        current_position += scroll_step
        
        if current_position > total_height:
            current_position = total_height
            
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        
        time.sleep(random.uniform(0.5, 2.0))
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > total_height:
            total_height = new_height
            
        scroll_attempts += 1
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(random.uniform(0.5, 1.0))

def fetch_url_stealth(driver, url):
    print(f"\nFetching: {url}")
    try:
        driver.get(url)
        
        delay = random.uniform(4.0, 8.0)
        print(f"Page loaded. Waiting {delay:.2f} seconds for JavaScript challenges to clear...")
        time.sleep(delay)
        
        simulate_human_scrolling(driver)
        
        raw_html = driver.page_source
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        for element in soup(["script", "style", "noscript", "nav", "header", "footer"]):
            element.decompose()
            
        for tag in soup.find_all(['div', 'section', 'ul', 'h1', 'h2', 'h3']):
            if tag.get('class'):
                text_content = tag.get_text(strip=True)
                if len(text_content) > 15:
                    class_attr = " ".join(tag['class'])
                    marker = soup.new_tag("p")
                    marker.string = f"\n👉 [SOURCE HTML TAG: <{tag.name} class=\"{class_attr}\">]\n"
                    tag.insert(0, marker)
            
        markdown_text = markdownify.markdownify(str(soup), heading_style="ATX").strip()
        
        return markdown_text
        
    except Exception as e:
        print(f"An error occurred while fetching {url}: {e}")
        raise ScraperError(f"Failed to fetch URL {url}: {str(e)}") from e

