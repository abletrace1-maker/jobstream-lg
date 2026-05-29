import pytest
import requests
import requests_mock

from src.utils.scraper import fetch_html, ScraperError

def test_fetch_html_success(requests_mock):
    url = "https://example.com/job/123"
    html_content = "<html><body>Job Details</body></html>"
    requests_mock.get(url, text=html_content, status_code=200)
    
    result = fetch_html(url)
    assert result == html_content
    # Verify standard headers are sent
    assert requests_mock.last_request.headers["User-Agent"].startswith("Mozilla")

def test_fetch_html_404_error(requests_mock):
    url = "https://example.com/not-found"
    requests_mock.get(url, status_code=404)
    
    with pytest.raises(ScraperError, match="Failed to fetch URL"):
        fetch_html(url)

def test_fetch_html_dns_error(requests_mock):
    url = "https://this-does-not-exist.com"
    requests_mock.get(url, exc=requests.exceptions.ConnectionError("DNS lookup failed"))
    
    with pytest.raises(ScraperError, match="Failed to fetch URL"):
        fetch_html(url)
