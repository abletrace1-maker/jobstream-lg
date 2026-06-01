import unittest
from unittest.mock import Mock, patch
from src.utils.scraper import fetch_url_stealth, ScraperError

class TestScraper(unittest.TestCase):

    @patch('src.utils.scraper.uc.Chrome')
    def test_fetch_url_stealth_success(self, mock_chrome):
        # Arrange
        mock_driver = Mock()
        mock_driver.page_source = "<html><body><h1>Test</h1></body></html>"
        
        # Simulate the scrolling by providing enough values for the loop
        side_effects = [1000, 800]  # Initial heights
        for _ in range(15): # Max attempts in the loop
            side_effects.append(1200) # New height

        mock_driver.execute_script.side_effect = side_effects
        mock_chrome.return_value = mock_driver

        url = "http://example.com"

        # Act
        result = fetch_url_stealth(mock_driver, url)

        # Assert
        self.assertIn("Test", result)
        mock_driver.get.assert_called_once_with(url)

    @patch('src.utils.scraper.uc.Chrome')
    def test_fetch_url_stealth_failure(self, mock_chrome):
        # Arrange
        mock_driver = Mock()
        mock_driver.get.side_effect = Exception("Test exception")
        mock_chrome.return_value = mock_driver

        url = "http://example.com"

        # Act & Assert
        with self.assertRaises(ScraperError):
            fetch_url_stealth(mock_driver, url)

if __name__ == '__main__':
    unittest.main()
