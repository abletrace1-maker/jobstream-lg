# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "undetected-chromedriver",
#     "beautifulsoup4",
#     "markdownify",
#     "setuptools",
# ]
# ///
import argparse
import json
import os
import sys
import time
import random
import re
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import markdownify

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
    
    # Get total page height
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    
    current_position = 0
    scroll_attempts = 0
    max_attempts = 15 # safety limit
    
    # Scroll down the page in random chunks until we reach the bottom or hit the limit
    while current_position < total_height and scroll_attempts < max_attempts:
        # Scroll down by a random fraction of the viewport height (e.g. 1/3 to 3/4 of a screen)
        scroll_step = random.uniform(viewport_height * 0.3, viewport_height * 0.8)
        current_position += scroll_step
        
        # Don't scroll past the bottom
        if current_position > total_height:
            current_position = total_height
            
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        
        # Wait a random time between 0.5 and 2 seconds as if "reading"
        time.sleep(random.uniform(0.5, 2.0))
        
        # Periodically recalculate total_height in case scrolling loaded more content
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > total_height:
            total_height = new_height
            
        scroll_attempts += 1
    
    # Scroll back to top quickly to finish
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(random.uniform(0.5, 1.0))

def fetch_url_stealth(driver, url):
    print(f"\nFetching: {url}")
    try:
        driver.get(url)
        
        delay = random.uniform(4.0, 8.0)
        print(f"Page loaded. Waiting {delay:.2f} seconds for JavaScript challenges to clear...")
        time.sleep(delay)
        
        # Perform human-like scrolling before grabbing the source
        simulate_human_scrolling(driver)
        
        raw_html = driver.page_source
        
        soup = BeautifulSoup(raw_html, 'html.parser')
        
        # 1. Clean up noisy tags that we don't care about
        for element in soup(["script", "style", "noscript", "nav", "header", "footer"]):
            element.decompose()
            
        # 2. Annotate the HTML tags so they appear in the final markdown output
        for tag in soup.find_all(['div', 'section', 'ul', 'h1', 'h2', 'h3']):
            if tag.get('class'):
                text_content = tag.get_text(strip=True)
                if len(text_content) > 15:
                    class_attr = " ".join(tag['class'])
                    marker = soup.new_tag("p")
                    marker.string = f"\n👉 [SOURCE HTML TAG: <{tag.name} class=\"{class_attr}\">]\n"
                    tag.insert(0, marker)
            
        markdown_text = markdownify.markdownify(str(soup), heading_style="ATX").strip()
        
        print("Successfully fetched and processed page.")
        return {
            "success": True,
            "url": driver.current_url,
            "markdown_content": markdown_text
        }
        
    except Exception as e:
        print(f"An error occurred during stealth fetch: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def update_job_status(job_id, new_status, job_list_path="job_list.md"):
    if not os.path.exists(job_list_path):
        print(f"Warning: {job_list_path} not found. Status not updated.")
        return
        
    with open(job_list_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    in_target_job = False
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("## Job ID:"):
            if job_id in line:
                in_target_job = True
            else:
                in_target_job = False
                
        if in_target_job and "*Status:*" in line:
            import re
            lines[i] = re.sub(r'\[.*?\]', f'[{new_status}]', line)
            updated = True
            break
            
    if updated:
        with open(job_list_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Updated status for {job_id} to [{new_status}] in {job_list_path}")
    else:
        print(f"Warning: Could not find/update status for {job_id} in {job_list_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch LinkedIn Jobs Stealthily")
    parser.add_argument("urls", nargs="*", help="One or more LinkedIn Job URLs")
    parser.add_argument("--out-dir", default=".", help="Directory to save the output file")
    parser.add_argument("--out-file", default=None, help="Specific file name to save the output. If multiple URLs, this is ignored.")
    parser.add_argument("--headed", action="store_true", help="Run headed (visible browser) instead of headless")
    parser.add_argument("--jobs-file", default=None, help="Path to a JSON file containing [{'job_id': '...', 'url': '...'}]. Overrides urls/out-dir.")
    
    args = parser.parse_args()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    config_path = os.path.join(project_root, "agent-files", "config.md")
    job_list_path = os.path.join(project_root, "job_list.md")
    base_delay = get_delay_from_config(config_path)
    
    jobs_to_process = []
    if args.jobs_file:
        try:
            with open(args.jobs_file, 'r', encoding='utf-8') as f:
                jobs_to_process = json.load(f)
        except Exception as e:
            print(f"Error reading jobs file: {e}")
            sys.exit(1)
    elif args.urls:
        for url in args.urls:
            jobs_to_process.append({"url": url})
    else:
        parser.print_help()
        sys.exit(1)
        
    headless_mode = not args.headed
    options = uc.ChromeOptions()
    if headless_mode:
        options.add_argument('--headless')
        
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--window-size=1920,1080")
    
    print("Starting stealth browser session...")
    driver = None
    try:
        driver = uc.Chrome(options=options, version_main=148)
        
        for i, job in enumerate(jobs_to_process):
            url = job.get("url")
            job_id = job.get("job_id")
            
            if not url:
                continue
                
            if job_id:
                out_dir = os.path.join(project_root, "active", job_id)
                out_file = "raw_fetched_URL.md"
            else:
                out_dir = args.out_dir
                if args.out_file and len(jobs_to_process) == 1:
                    out_file = args.out_file
                else:
                    out_file = f"stealth_job_output_{i+1}.md"
                    
            os.makedirs(out_dir, exist_ok=True)
            
            max_retries = 3
            result = None
            for attempt in range(max_retries):
                result = fetch_url_stealth(driver, url)
                if result and result.get("success"):
                    break
                else:
                    print(f"Attempt {attempt + 1} failed for {url}. Retrying in 3 seconds...")
                    if attempt < max_retries - 1:
                        time.sleep(3)
            
            if result and result.get("success"):
                output_path = os.path.join(out_dir, out_file)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result["markdown_content"])
                    
                print(f"Saved full annotated output to {output_path}")
                
                if job_id:
                    update_job_status(job_id, "raw_job_details_fetched", job_list_path)
            
            if i < len(jobs_to_process) - 1:
                jitter = base_delay * 0.2
                actual_delay = base_delay + random.uniform(-jitter, jitter)
                actual_delay = max(3.0, actual_delay) # Never below 3s
                print(f"\nWaiting {actual_delay:.2f} seconds before the next fetch (configured base: {base_delay}s)...")
                time.sleep(actual_delay)
                
    except Exception as e:
        print(f"Critical error initializing browser: {e}")
    finally:
        if driver:
            print("Closing browser session.")
            driver.quit()
