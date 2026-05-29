import logging
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class ScraperError(Exception):
    """Generic error raised when the scraper encounters an issue."""
    pass

def fetch_html(url: str) -> str:
    """
    Fetches raw HTML from a given URL.
    
    Args:
        url (str): The target URL.
        
    Returns:
        str: The raw HTML text of the page.
        
    Raises:
        ScraperError: If the URL is invalid, unreachable, or returns a 4xx/5xx error.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Note: Excluding specific handling for 403 for now (part of US-003)
        response.raise_for_status()
        return response.text
    except RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        raise ScraperError(f"Failed to fetch URL {url}: {str(e)}") from e
