"""
HTML/JSON parsing utilities
Provides tools for extracting and parsing content from web pages
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from lxml import etree


class ContentParser:
    """Parser for HTML and JSON content"""

    def __init__(self, logger):
        """
        Initialize content parser

        Args:
            logger: Logger instance
        """
        self.logger = logger

    def parse_html(self, html: str, parser: str = "lxml") -> BeautifulSoup:
        """
        Parse HTML content with BeautifulSoup

        Args:
            html: HTML string
            parser: Parser to use ('lxml', 'html.parser', 'html5lib')

        Returns:
            BeautifulSoup object
        """
        try:
            return BeautifulSoup(html, parser)
        except Exception as e:
            self.logger.error(f"Failed to parse HTML: {e}")
            return BeautifulSoup("", parser)

    def parse_xml(self, xml: str) -> etree._Element:
        """
        Parse XML content with lxml

        Args:
            xml: XML string

        Returns:
            lxml Element
        """
        try:
            return etree.fromstring(xml.encode())
        except Exception as e:
            self.logger.error(f"Failed to parse XML: {e}")
            return etree.Element("root")

    def parse_json(self, json_str: str) -> Union[Dict, List, None]:
        """
        Parse JSON string

        Args:
            json_str: JSON string

        Returns:
            Parsed JSON object or None if failed
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {e}")
            return None

    def extract_json_from_script(self, html: str, pattern: Optional[str] = None) -> Optional[Dict]:
        """
        Extract JSON data from script tags

        Args:
            html: HTML content
            pattern: Regex pattern to match JSON data

        Returns:
            Extracted JSON data or None
        """
        try:
            soup = self.parse_html(html)
            script_tags = soup.find_all("script")

            for script in script_tags:
                content = script.string
                if not content:
                    continue

                # Use custom pattern or default pattern
                if pattern:
                    match = re.search(pattern, content)
                    if match:
                        json_str = match.group(1)
                        return self.parse_json(json_str)
                else:
                    # Try to find JSON-like content
                    # Look for objects or arrays
                    json_matches = re.findall(r'\{[^{}]*\}|\[[^\[\]]*\]', content)
                    for json_match in json_matches:
                        data = self.parse_json(json_match)
                        if data:
                            return data

            return None

        except Exception as e:
            self.logger.error(f"Failed to extract JSON from script: {e}")
            return None

    def extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """
        Extract text content using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector

        Returns:
            Extracted text or None
        """
        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract text from {selector}: {e}")
            return None

    def extract_texts(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """
        Extract multiple text contents using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector

        Returns:
            List of extracted texts
        """
        try:
            elements = soup.select(selector)
            return [elem.get_text(strip=True) for elem in elements]
        except Exception as e:
            self.logger.error(f"Failed to extract texts from {selector}: {e}")
            return []

    def extract_attribute(
        self,
        soup: BeautifulSoup,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        """
        Extract attribute value using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector
            attribute: Attribute name

        Returns:
            Attribute value or None
        """
        try:
            element = soup.select_one(selector)
            if element:
                return element.get(attribute)
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract attribute {attribute} from {selector}: {e}")
            return None

    def extract_attributes(
        self,
        soup: BeautifulSoup,
        selector: str,
        attribute: str,
    ) -> List[str]:
        """
        Extract multiple attribute values using CSS selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector
            attribute: Attribute name

        Returns:
            List of attribute values
        """
        try:
            elements = soup.select(selector)
            return [elem.get(attribute) for elem in elements if elem.get(attribute)]
        except Exception as e:
            self.logger.error(f"Failed to extract attributes {attribute} from {selector}: {e}")
            return []

    def extract_links(self, soup: BeautifulSoup, base_url: str = "") -> List[str]:
        """
        Extract all links from page

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs
        """
        try:
            links = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if base_url:
                    href = urljoin(base_url, href)
                links.append(href)
            return links
        except Exception as e:
            self.logger.error(f"Failed to extract links: {e}")
            return []

    def extract_images(self, soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]:
        """
        Extract all images from page

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links

        Returns:
            List of image dictionaries with 'src' and 'alt'
        """
        try:
            images = []
            for img_tag in soup.find_all("img"):
                src = img_tag.get("src") or img_tag.get("data-src")
                if src:
                    if base_url:
                        src = urljoin(base_url, src)
                    images.append({
                        "src": src,
                        "alt": img_tag.get("alt", ""),
                    })
            return images
        except Exception as e:
            self.logger.error(f"Failed to extract images: {e}")
            return []

    def extract_videos(self, soup: BeautifulSoup, base_url: str = "") -> List[Dict[str, str]]:
        """
        Extract all videos from page

        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links

        Returns:
            List of video dictionaries with 'src' and 'poster'
        """
        try:
            videos = []
            for video_tag in soup.find_all("video"):
                src = video_tag.get("src")
                if not src:
                    source_tag = video_tag.find("source")
                    if source_tag:
                        src = source_tag.get("src")

                if src:
                    if base_url:
                        src = urljoin(base_url, src)
                    videos.append({
                        "src": src,
                        "poster": video_tag.get("poster", ""),
                    })
            return videos
        except Exception as e:
            self.logger.error(f"Failed to extract videos: {e}")
            return []

    def clean_text(self, text: str) -> str:
        """
        Clean text by removing extra whitespace and special characters

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def extract_numbers(self, text: str) -> List[float]:
        """
        Extract all numbers from text

        Args:
            text: Text to extract numbers from

        Returns:
            List of numbers
        """
        if not text:
            return []

        # Handle Chinese numbers
        text = self._convert_chinese_numbers(text)

        # Extract numbers
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return [float(n) for n in numbers]

    def _convert_chinese_numbers(self, text: str) -> str:
        """Convert Chinese numbers to Arabic numbers"""
        chinese_map = {
            '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
            '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
            '十': '10', '百': '100', '千': '1000', '万': '10000',
            '亿': '100000000',
        }

        for chinese, arabic in chinese_map.items():
            text = text.replace(chinese, arabic)

        return text

    def extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extract phone numbers from text

        Args:
            text: Text to extract phone numbers from

        Returns:
            List of phone numbers
        """
        if not text:
            return []

        # Chinese phone number pattern
        patterns = [
            r'1[3-9]\d{9}',  # Mobile
            r'0\d{2,3}-?\d{7,8}',  # Landline
        ]

        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)

        return list(set(phones))  # Remove duplicates

    def extract_emails(self, text: str) -> List[str]:
        """
        Extract email addresses from text

        Args:
            text: Text to extract emails from

        Returns:
            List of email addresses
        """
        if not text:
            return []

        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(pattern, text)
        return list(set(emails))  # Remove duplicates

    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text

        Args:
            text: Text to extract URLs from

        Returns:
            List of URLs
        """
        if not text:
            return []

        pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(pattern, text)
        return list(set(urls))  # Remove duplicates

    def extract_hashtags(self, text: str) -> List[str]:
        """
        Extract hashtags from text

        Args:
            text: Text to extract hashtags from

        Returns:
            List of hashtags
        """
        if not text:
            return []

        # Support both # and Chinese #
        pattern = r'[#＃](\w+)'
        hashtags = re.findall(pattern, text)
        return list(set(hashtags))  # Remove duplicates

    def extract_mentions(self, text: str) -> List[str]:
        """
        Extract user mentions from text

        Args:
            text: Text to extract mentions from

        Returns:
            List of usernames
        """
        if not text:
            return []

        # Support both @ and Chinese @
        pattern = r'[@＠](\w+)'
        mentions = re.findall(pattern, text)
        return list(set(mentions))  # Remove duplicates

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object

        Args:
            date_str: Date string to parse

        Returns:
            datetime object or None if parsing failed
        """
        if not date_str:
            return None

        # Common date formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
            "%Y年%m月%d日 %H:%M:%S",
            "%Y年%m月%d日 %H:%M",
            "%Y年%m月%d日",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try to parse relative dates
        now = datetime.now()

        if "刚刚" in date_str or "just now" in date_str.lower():
            return now
        elif "分钟前" in date_str or "minutes ago" in date_str.lower():
            minutes = self.extract_numbers(date_str)
            if minutes:
                from datetime import timedelta
                return now - timedelta(minutes=int(minutes[0]))
        elif "小时前" in date_str or "hours ago" in date_str.lower():
            hours = self.extract_numbers(date_str)
            if hours:
                from datetime import timedelta
                return now - timedelta(hours=int(hours[0]))
        elif "天前" in date_str or "days ago" in date_str.lower():
            days = self.extract_numbers(date_str)
            if days:
                from datetime import timedelta
                return now - timedelta(days=int(days[0]))

        self.logger.warning(f"Failed to parse date: {date_str}")
        return None

    def parse_count(self, count_str: str) -> int:
        """
        Parse count string with units (e.g., '1.2万', '3.5K')

        Args:
            count_str: Count string

        Returns:
            Parsed count as integer
        """
        if not count_str:
            return 0

        count_str = count_str.strip()

        # Remove non-numeric characters except decimal point and units
        units = {
            'k': 1000, 'K': 1000,
            'w': 10000, 'W': 10000, '万': 10000,
            'm': 1000000, 'M': 1000000,
            'b': 1000000000, 'B': 1000000000, '亿': 100000000,
        }

        # Extract number and unit
        match = re.match(r'([\d.]+)\s*([kKwWmMbB万亿]?)', count_str)
        if match:
            number = float(match.group(1))
            unit = match.group(2)

            if unit in units:
                return int(number * units[unit])
            else:
                return int(number)

        # Try to extract just numbers
        numbers = self.extract_numbers(count_str)
        if numbers:
            return int(numbers[0])

        return 0

    def parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds (e.g., '01:23', '1:23:45')

        Args:
            duration_str: Duration string

        Returns:
            Duration in seconds
        """
        if not duration_str:
            return 0

        parts = duration_str.split(':')
        parts = [int(p) for p in parts]

        if len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:  # HH:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        else:
            return 0

    def extract_table_data(self, soup: BeautifulSoup, selector: str = "table") -> List[List[str]]:
        """
        Extract data from HTML table

        Args:
            soup: BeautifulSoup object
            selector: Table selector

        Returns:
            List of rows, each row is a list of cell values
        """
        try:
            table = soup.select_one(selector)
            if not table:
                return []

            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)

            return rows

        except Exception as e:
            self.logger.error(f"Failed to extract table data: {e}")
            return []

    def remove_elements(self, soup: BeautifulSoup, selector: str) -> BeautifulSoup:
        """
        Remove elements matching selector

        Args:
            soup: BeautifulSoup object
            selector: CSS selector

        Returns:
            Modified BeautifulSoup object
        """
        try:
            for element in soup.select(selector):
                element.decompose()
            return soup
        except Exception as e:
            self.logger.error(f"Failed to remove elements {selector}: {e}")
            return soup

    def get_domain(self, url: str) -> Optional[str]:
        """
        Get domain from URL

        Args:
            url: URL string

        Returns:
            Domain or None
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return None
