# -*- coding: utf-8 -*-
import re
import logging
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from scrapy import Spider, Request, signals
from scrapy.exceptions import NotConfigured, CloseSpider
from scrapy.linkextractors import LinkExtractor

class WebCrawlerSpider(Spider):
    """
    A Scrapy spider that crawls websites, attempts to extract specified
    patterns (potentially personal information), stores them in MongoDB,
    and follows links within allowed domains.

    WARNING: Scraping personal information (phone numbers, addresses, SSNs, etc.)
    carries significant ethical and legal risks. Ensure you have explicit
    consent or a clear legal basis before collecting and storing such data.
    Comply with all relevant privacy laws (e.g., GDPR, CCPA) and website
    Terms of Service. Storing this data creates security risks.
    This code is for educational demonstration of Scrapy techniques ONLY.
    """
    name = "web_crawler"

    # --- Regex Patterns (Consider refining these carefully) ---
    # Basic US/International phone number pattern (can be improved)
    PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    # Basic US Address pattern (very simplified, prone to false positives/negatives)
    ADDRESS_REGEX = re.compile(r'\b\d{1,6}\s+[A-Za-z0-9\s.,#-]+(?:Street|St|Avenue|Ave|Road|Rd|Highway|Hwy|Square|Sq|Trail|Trl|Drive|Dr|Court|Ct|Park|Parkway|Pkwy|Circle|Cir|Boulevard|Blvd)[.,]?\s+[A-Za-z\s]+(?:,\s*[A-Z]{2})?\s+\d{5}(?:-\d{4})?\b', re.IGNORECASE)
    # US Social Security Number format
    SSN_REGEX = re.compile(r'\b(?!(000|666|9\d{2}))\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b') # Avoids some invalid SSNs
    # UK National Insurance Number format
    NI_REGEX = re.compile(r'\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}\d{6}[A-D ]\b', re.IGNORECASE) # Excludes temporary/invalid prefixes

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_uri = None
        self.mongo_db = None
        self.mongo_collection = None
        self.client = None
        self.db = None
        self.collection = None
        self.allowed_domains = None
        self.start_urls = None
        self.logger.warning(
            "Initializing PII Scraping Spider. REMINDER: Ensure you have legal "
            "and ethical justification for scraping personal data."
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Factory method to access Scrapy settings and signals.
        Initializes MongoDB connection and registers signal handlers.
        """
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler) # Gives access to crawler object (settings, signals etc.)

        # --- Get configuration from settings.py ---
        spider.mongo_uri = crawler.settings.get('MONGO_URI')
        spider.mongo_db = crawler.settings.get('MONGO_DATABASE', 'web_crawler')
        spider.mongo_collection = crawler.settings.get('MONGO_COLLECTION', 'personal_info')
        spider.start_urls = crawler.settings.getlist('START_URLS')
        spider.allowed_domains = crawler.settings.getlist('ALLOWED_DOMAINS')

        if not spider.mongo_uri:
            raise NotConfigured("MONGO_URI setting is missing. Cannot connect to MongoDB.")
        if not spider.start_urls:
            raise NotConfigured("START_URLS setting is missing. No starting point for crawl.")
        if not spider.allowed_domains:
             # Derive allowed_domains from start_urls if not explicitly set
             spider.allowed_domains = list(set(urlparse(url).netloc for url in spider.start_urls))
             spider.logger.info(f"ALLOWED_DOMAINS not set, derived from START_URLS: {spider.allowed_domains}")


        # --- Connect to MongoDB ---
        try:
            spider.client = MongoClient(spider.mongo_uri)
            # The ismaster command is cheap and does not require auth.
            spider.client.admin.command('ismaster')
            spider.db = spider.client[spider.mongo_db]
            spider.collection = spider.db[spider.mongo_collection]
            spider.logger.info(f"Successfully connected to MongoDB: {spider.mongo_uri}, DB: {spider.mongo_db}, Collection: {spider.mongo_collection}")
        except ConnectionFailure as e:
            spider.logger.error(f"MongoDB connection failed: {e}")
            raise NotConfigured(f"Could not connect to MongoDB at {spider.mongo_uri}")

        # --- Connect signal for closing connection ---
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        return spider

    def start_requests(self):
        """
        Generates initial requests from start_urls.
        """
        if not self.start_urls:
            self.logger.error("No start URLs configured.")
            return # Don't yield anything if no start URLs

        for url in self.start_urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        """
        Processes the response: extracts data, stores it, and follows links.
        """
        self.logger.info(f"Parsing: {response.url} (Status: {response.status})")

        try:
            # Use response.text for regex matching on the decoded HTML content
            content = response.text
        except AttributeError:
            # Handle cases where response.text might not be available (e.g., non-HTML response)
            self.logger.warning(f"Could not get text content for {response.url}, skipping regex extraction.")
            content = "" # Set content to empty string to avoid errors below

        # --- Extract information using regular expressions ---
        # Use setdefault to ensure keys exist even if no matches are found
        extracted_info = {
            'url': response.url,
            'phone_numbers': [],
            'addresses': [],
            'social_security_numbers': [],
            'national_insurance_numbers': [],
        }

        if content: # Only run regex if content exists
            try:
                # Findall returns a list of strings
                extracted_info['phone_numbers'] = self.PHONE_REGEX.findall(content)
                extracted_info['addresses'] = [addr.strip() for addr in self.ADDRESS_REGEX.findall(content)] # Clean whitespace
                extracted_info['social_security_numbers'] = self.SSN_REGEX.findall(content)
                extracted_info['national_insurance_numbers'] = self.NI_REGEX.findall(content)
            except Exception as e:
                self.logger.error(f"Regex extraction failed for {response.url}: {e}")
                # Decide if you want to continue or stop processing this page

        # --- Log and Store extracted information in MongoDB if any data was found ---
        found_data = any(
            extracted_info['phone_numbers'] or
            extracted_info['addresses'] or
            extracted_info['social_security_numbers'] or
            extracted_info['national_insurance_numbers']
        )

        if found_data:
            self.logger.info(f"Found potential PII on {response.url}: "
                             f"Phones={len(extracted_info['phone_numbers'])}, "
                             f"Addresses={len(extracted_info['addresses'])}, "
                             f"SSNs={len(extracted_info['social_security_numbers'])}, "
                             f"NINs={len(extracted_info['national_insurance_numbers'])}")
            try:
                # Use update_one with upsert=True to avoid duplicate entries for the same URL
                # Alternatively, use insert_one if you want multiple records per URL visit (less common)
                self.collection.update_one(
                    {'url': response.url},
                    {'$set': extracted_info},
                    upsert=True
                )
                # Or: self.collection.insert_one(extracted_info) if duplicates are okay
            except OperationFailure as e:
                self.logger.error(f"MongoDB operation failed for {response.url}: {e}")
            except Exception as e:
                 self.logger.error(f"An unexpected error occurred during MongoDB interaction for {response.url}: {e}")
        else:
            self.logger.debug(f"No specified patterns found on {response.url}")

        # --- Yield next URLs to crawl ---
        # Use LinkExtractor for more robust link finding and filtering
        link_extractor = LinkExtractor(allow_domains=self.allowed_domains, deny_extensions=[
            # Common non-HTML file extensions to ignore
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'ico',
            'css', 'js',
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            'zip', 'rar', 'gz', 'tar', 'bz2',
            'mp3', 'mp4', 'avi', 'mov', 'wmv',
            'xml', 'json', 'atom', 'rss'
        ])

        links = link_extractor.extract_links(response)
        self.logger.debug(f"Found {len(links)} links to follow on {response.url}")

        for link in links:
            yield response.follow(link, callback=self.parse)

    def spider_closed(self, spider, reason):
        """
        Signal handler called when the spider finishes.
        Closes the MongoDB connection.
        """
        self.logger.info(f"Spider closed: {reason}. Closing MongoDB connection.")
        if self.client:
            try:
                self.client.close()
                self.logger.info("MongoDB connection closed successfully.")
            except Exception as e:
                self.logger.error(f"Error closing MongoDB connection: {e}")