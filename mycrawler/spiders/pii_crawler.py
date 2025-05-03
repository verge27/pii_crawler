# -*- coding: utf-8 -*-
import re
import logging
from urllib.parse import urlparse, urljoin # Added urljoin

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from scrapy import Spider, Request, signals
from scrapy.exceptions import NotConfigured, CloseSpider
from scrapy.linkextractors import LinkExtractor # Using LinkExtractor for better link finding

class WebCrawlerSpider(Spider):
    """
    A Scrapy spider designed to crawl websites, attempt to extract specific
    patterns potentially representing personal information (PII), store findings
    in MongoDB, and follow links within allowed domains.

    *** EXTREMELY IMPORTANT WARNING ***
    Scraping personal information (phone numbers, addresses, SSNs, NI numbers, etc.)
    carries SIGNIFICANT ethical and legal risks. You MUST ensure you have explicit
    consent or a clear, verifiable legal basis before collecting, processing,
    or storing such data. Strictly comply with all relevant privacy laws (e.g., GDPR,
    Data Protection Act 2018 in the UK, CCPA) and respect website Terms of Service.
    Storing PII creates major security risks and responsibilities.
    This code is provided for EDUCATIONAL DEMONSTRATION of Scrapy techniques ONLY.
    DO NOT USE FOR ACTUAL PII SCRAPING WITHOUT LEGAL COMPLIANCE AND ETHICAL CONSIDERATION.
    """
    name = "web_crawler" # The name used to run the spider (scrapy crawl web_crawler)

    # --- Pre-compiled Regular Expression Patterns ---
    # Compile regex for efficiency. Consider refining these patterns carefully
    # as they can easily produce false positives or miss variations.

    # Basic US/International phone number pattern (can be complex to get right globally)
    PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')

    # Basic US Address pattern (highly simplified, prone to errors, difficult to make robust)
    # This regex is illustrative and likely needs significant improvement for real-world use.
    ADDRESS_REGEX = re.compile(
        r'\b\d{1,6}\s+' # House number
        r'[A-Za-z0-9\s.,#-]+' # Street name part 1 (allows numbers, dots, hashes, commas)
        r'(?:Street|St|Avenue|Ave|Road|Rd|Highway|Hwy|Square|Sq|Trail|Trl|Drive|Dr|Court|Ct|Park|Parkway|Pkwy|Circle|Cir|Boulevard|Blvd|Lane|Ln)\b' # Street type
        r'[.,]?\s+' # Optional punctuation and space
        r'(?:[A-Za-z\s]+,\s*)?' # Optional City name
        r'(?:[A-Z]{2}\s+)?' # Optional State abbreviation
        r'\d{5}(?:-\d{4})?\b', # Zip code (5 or 5-4 format)
        re.IGNORECASE # Make pattern case-insensitive
    )

    # US Social Security Number format (attempts to exclude some invalid ranges)
    SSN_REGEX = re.compile(r'\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b')

    # UK National Insurance Number format (excludes temporary/invalid prefixes)
    # See official UK government guidance for exact valid formats.
    NI_REGEX = re.compile(r'\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b', re.IGNORECASE)

    def __init__(self, *args, **kwargs):
        """
        Basic spider initialization. Configuration and resource setup
        are handled in `from_crawler`.
        """
        super().__init__(*args, **kwargs)
        # Placeholders for configuration and resources
        self.mongo_uri = None
        self.mongo_db_name = None
        self.mongo_collection_name = None
        self.client = None
        self.db = None
        self.collection = None
        self.allowed_domains_list = None
        self.start_urls_list = None
        self.link_extractor = None # Initialize later with allowed_domains
        self.logger.warning(
            "Initializing PII Scraping Spider. "
            "REMINDER: Ensure you have legal and ethical justification and have "
            "obtained necessary consents BEFORE running this spider on any target."
        )

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Factory method to create a spider instance.
        This is the preferred way to access Scrapy settings, signals, and stats.
        It initializes the MongoDB connection and registers signal handlers.
        """
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler) # Provides access to the Crawler object

        # --- Load configuration from settings.py ---
        spider.mongo_uri = crawler.settings.get('MONGO_URI')
        spider.mongo_db_name = crawler.settings.get('MONGO_DATABASE', 'web_crawler_db') # Default DB name
        spider.mongo_collection_name = crawler.settings.get('MONGO_COLLECTION', 'personal_info') # Default collection

        if not spider.mongo_uri:
            spider.logger.error("MONGO_URI setting is missing in settings.py. Spider cannot start.")
            raise NotConfigured("MONGO_URI setting is required for MongoDB connection.")

        spider.start_urls_list = crawler.settings.getlist('START_URLS')
        if not spider.start_urls_list:
            spider.logger.error("START_URLS setting is missing or empty in settings.py. Spider needs starting points.")
            raise NotConfigured("START_URLS setting is required.")

        # Get allowed domains or derive them from start URLs if not explicitly set
        spider.allowed_domains_list = crawler.settings.getlist('ALLOWED_DOMAINS')
        if not spider.allowed_domains_list:
             spider.allowed_domains_list = list(set(urlparse(url).netloc for url in spider.start_urls_list if urlparse(url).netloc))
             spider.logger.info(f"ALLOWED_DOMAINS not set, derived from START_URLS: {spider.allowed_domains_list}")
        if not spider.allowed_domains_list:
             spider.logger.error("Could not determine allowed domains from START_URLS. Please set ALLOWED_DOMAINS in settings.py.")
             raise NotConfigured("ALLOWED_DOMAINS must be configured or derivable from START_URLS.")

        # --- Initialize Link Extractor ---
        # Configure LinkExtractor to respect allowed_domains and deny common file extensions
        spider.link_extractor = LinkExtractor(
            allow_domains=spider.allowed_domains_list,
            deny_extensions=[
                # Common non-HTML file types to avoid downloading
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'ico', 'webp',
                'css', 'js', # Usually not useful for content scraping unless specifically needed
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods', 'odp',
                'zip', 'rar', 'gz', 'tar', 'bz2', '7z',
                'mp3', 'mp4', 'avi', 'mov', 'wmv', 'flv', 'wav', 'ogg',
                'xml', 'json', 'atom', 'rss', 'csv',
                'exe', 'dmg', 'iso'
            ]
        )

        # --- Connect to MongoDB ---
        try:
            spider.logger.info(f"Attempting to connect to MongoDB at {spider.mongo_uri}")
            spider.client = MongoClient(spider.mongo_uri, serverSelectionTimeoutMS=5000) # Add timeout
            # The ismaster command is cheap and does not require auth. Forces connection check.
            spider.client.admin.command('ismaster')
            spider.db = spider.client[spider.mongo_db_name]
            spider.collection = spider.db[spider.mongo_collection_name]
            spider.logger.info(f"Successfully connected to MongoDB: DB='{spider.mongo_db_name}', Collection='{spider.mongo_collection_name}'")
        except ConnectionFailure as e:
            spider.logger.error(f"MongoDB connection failed: {e}. Check MONGO_URI and network access.")
            # CloseSpider exception will gracefully stop the spider
            raise CloseSpider(f"MongoDB connection failed: {e}")
        except Exception as e:
            spider.logger.error(f"An unexpected error occurred during MongoDB setup: {e}")
            raise CloseSpider(f"MongoDB setup error: {e}")

        # --- Register signal handler for clean shutdown ---
        # Connect the spider_closed method to the spider_closed signal
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        return spider

    def start_requests(self):
        """
        Generates the initial Requests for the spider to crawl
        based on the start_urls list from settings.
        """
        if not self.start_urls_list:
            self.logger.error("No start URLs available to begin crawling.")
            return # Stop if there are no URLs

        self.logger.info(f"Starting crawl from URLs: {self.start_urls_list}")
        for url in self.start_urls_list:
            # Use dont_filter=True if you might need to re-scrape start URLs
            # if they are encountered again via links, otherwise Scrapy might filter them.
            yield Request(url, callback=self.parse, errback=self.handle_error)

    def parse(self, response):
        """
        This method is called for each successful response downloaded.
        It extracts data using regex, stores it in MongoDB if found,
        and yields further requests for links found on the page.
        """
        self.logger.debug(f"Parsing page: {response.url} (Status: {response.status})")

        try:
            # Use response.text for regex matching on the decoded HTML content.
            # Decoding is handled by Scrapy based on headers/meta tags or defaults.
            content = response.text
        except AttributeError:
            # Handle cases where response.text might not be available (e.g., binary data)
            self.logger.warning(f"Could not get text content for {response.url} (Content-Type: {response.headers.get('Content-Type', b'N/A').decode()}), skipping regex extraction.")
            content = "" # Ensure content is an empty string to avoid errors below

        # --- Extract information using regular expressions ---
        extracted_data = {
            'url': response.url,
            'source_domain': urlparse(response.url).netloc, # Add domain for context
            'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), # Timestamp
            'phone_numbers': [],
            'addresses': [],
            'social_security_numbers': [],
            'national_insurance_numbers': [],
        }
        found_pii = False # Flag to check if any PII was found

        if content: # Only run regex if text content is available
            try:
                # Use set to store unique findings automatically
                extracted_data['phone_numbers'] = list(set(self.PHONE_REGEX.findall(content)))
                # Clean whitespace from address matches
                extracted_data['addresses'] = list(set(addr.strip() for addr in self.ADDRESS_REGEX.findall(content)))
                extracted_data['social_security_numbers'] = list(set(self.SSN_REGEX.findall(content)))
                extracted_data['national_insurance_numbers'] = list(set(self.NI_REGEX.findall(content)))

                # Check if any list is non-empty
                if any(extracted_data[key] for key in ['phone_numbers', 'addresses', 'social_security_numbers', 'national_insurance_numbers']):
                    found_pii = True

            except Exception as e:
                self.logger.error(f"Regex extraction failed unexpectedly for {response.url}: {e}", exc_info=True)
                # Depending on policy, you might want to record the error or stop

        # --- Log and Store extracted information in MongoDB if PII was found ---
        if found_pii:
            self.logger.warning( # Log as WARNING due to sensitive nature
                f"Potential PII found on {response.url}: "
                f"Phones={len(extracted_data['phone_numbers'])}, "
                f"Addresses={len(extracted_data['addresses'])}, "
                f"SSNs={len(extracted_data['social_security_numbers'])}, "
                f"NINs={len(extracted_data['national_insurance_numbers'])}"
            )
            try:
                # Use update_one with upsert=True: If a document with this URL exists,
                # update it; otherwise, insert a new document. This prevents duplicates
                # if a page is visited multiple times but stores the latest findings.
                # The '$set' operator replaces the fields specified.
                # Consider '$addToSet' if you want to accumulate unique values across multiple visits (more complex).
                self.collection.update_one(
                    {'url': response.url}, # Filter document by URL
                    {'$set': extracted_data}, # Data to insert or update
                    upsert=True # Create the document if it doesn't exist
                )
                self.logger.info(f"Successfully saved/updated data for {response.url} in MongoDB.")
            except OperationFailure as e:
                self.logger.error(f"MongoDB operation failed for {response.url}: {e}. Data might not be saved.", exc_info=True)
            except Exception as e:
                 self.logger.error(f"An unexpected error occurred during MongoDB interaction for {response.url}: {e}", exc_info=True)
        else:
            self.logger.debug(f"No specified PII patterns found on {response.url}")

        # --- Yield Requests for next URLs to crawl ---
        self.logger.debug(f"Extracting links from {response.url}")
        try:
            # Use the configured LinkExtractor to find valid links to follow
            links = self.link_extractor.extract_links(response)
            self.logger.info(f"Found {len(links)} links to potentially follow on {response.url}")

            for link in links:
                # response.follow automatically handles relative URLs and respects allowed_domains
                yield response.follow(link, callback=self.parse, errback=self.handle_error)

        except Exception as e:
            self.logger.error(f"Failed to extract or follow links from {response.url}: {e}", exc_info=True)


    def handle_error(self, failure):
        """
        Error handler callback for Requests (e.g., DNS errors, HTTP errors > 300, timeouts).
        Logs the error details.
        """
        self.logger.error(f"Request failed: {failure.request.url} - Error: {failure.value}")
        # You could add more sophisticated error handling here, e.g., retrying requests
        # based on the type of error (using failure.type)


    def spider_closed(self, spider, reason):
        """
        Signal handler called when the spider finishes its crawl (or is closed).
        This is the place to perform cleanup operations like closing database connections.
        """
        self.logger.warning(f"Spider finished crawling. Reason: {reason}. Closing MongoDB connection.")
        if self.client:
            try:
                self.client.close()
                self.logger.info("MongoDB connection closed successfully.")
            except Exception as e:
                self.logger.error(f"Error closing MongoDB connection: {e}", exc_info=True)
        else:
             self.logger.info("No active MongoDB client to close.")

# === Required Imports for Standalone Execution (if needed) ===
# Typically you run this with `scrapy crawl web_crawler`
# But to make the script potentially runnable standalone for simple tests (not recommended for full crawls):
import sys
import os
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings
import datetime # Required for timestamping

if __name__ == '__main__':
    # This block allows running the spider directly using `python your_spider_file.py`
    # BUT it bypasses Scrapy's project structure and settings loading mechanism.
    # It's generally better to use `scrapy crawl web_crawler` within a project.
    # This is primarily for basic testing or demonstration outside a full project.

    print("Running spider directly (for basic testing only - use 'scrapy crawl web_crawler' in a project).")

    # --- Minimal Settings for Direct Execution ---
    # You MUST configure these manually if running standalone
    settings = Settings()
    settings['BOT_NAME'] = 'direct_crawler' # Needs a bot name
    settings['MONGO_URI'] = "mongodb://localhost:27017/" # *** YOUR MONGO URI HERE ***
    settings['MONGO_DATABASE'] = "direct_test_db"
    settings['MONGO_COLLECTION'] = "direct_test_collection"
    settings['START_URLS'] = ["http://example.com"] # *** YOUR START URL HERE ***
    settings['ALLOWED_DOMAINS'] = ["example.com"] # *** YOUR ALLOWED DOMAIN HERE ***
    settings['LOG_LEVEL'] = 'INFO' # Set log level
    settings['ROBOTSTXT_OBEY'] = True # Be polite by default

    # --- Setup and Run ---
    process = CrawlerProcess(settings)
    process.crawl(WebCrawlerSpider)
    process.start() # The script will block here until the crawl is finished
