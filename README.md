How to Use This Spider
Set up a Scrapy Project: If you haven't already, create a Scrapy project:

scrapy startproject mycrawler
cd mycrawler

Save the Spider: Save the Python code above into the spiders directory within your project (e.g., mycrawler/spiders/pii_crawler.py). Make sure the name attribute (web_crawler) is unique within your project's spiders.

Install Dependencies:

pip install scrapy pymongo dnspython # dnspython is often needed for mongodb+srv URIs

Configure settings.py: This is the most important step. Open the settings.py file located in your Scrapy project's root directory (mycrawler/settings.py) and add or modify the following settings:

# settings.py

BOT_NAME = 'mycrawler' # Or your project name
SPIDER_MODULES = ['mycrawler.spiders']
NEWSPIDER_MODULE = 'mycrawler.spiders'

# --- USER AGENT ---
# Be polite: identify your bot. Replace with your project info.
USER_AGENT = 'MyWebCrawler (+http://www.mywebsite.com/botinfo)' # CHANGE THIS

# --- ROBOTS.TXT ---
# Set to False ONLY if you have explicit permission AND understand the risks.
ROBOTSTXT_OBEY = True

# --- MONGODB CONFIGURATION ---
# *** REPLACE with your actual MongoDB connection string ***
# Example for local: "mongodb://localhost:27017/"
# Example for Atlas: "mongodb+srv://<username>:<password>@<cluster-url>/<dbname>?retryWrites=true&w=majority"
MONGO_URI = "mongodb://localhost:27017/"
MONGO_DATABASE = "web_crawler_db"        # Choose a database name
MONGO_COLLECTION = "personal_info_collection" # Choose a collection name

# --- CRAWL SCOPE CONFIGURATION ---
# *** REPLACE with the actual URL(s) you want to start crawling from ***
START_URLS = ["http://example.com"] # Must be a list
# *** REPLACE with the domain(s) you are legally permitted to crawl ***
# The spider will NOT follow links outside these domains.
ALLOWED_DOMAINS = ["example.com"]   # Must be a list

# --- DELAY AND THROTTLING (Highly Recommended) ---
# Be kind to the servers you are crawling. Start with conservative values.
DOWNLOAD_DELAY = 1 # Time in seconds between requests to the same domain
# CONCURRENT_REQUESTS_PER_DOMAIN = 8 # Max concurrent requests to any single domain
# CONCURRENT_REQUESTS = 16 # Max concurrent requests overall

# AutoThrottle adjusts delays based on server load (Recommended)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1 # Initial download delay
AUTOTHROTTLE_MAX_DELAY = 60 # Maximum download delay to be set in case of high latencies
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0 # Aim for this average number of parallel requests; lower is gentler
# AUTOTHROTTLE_DEBUG = False # Set True to see throttling stats

# --- LOGGING ---
LOG_LEVEL = 'INFO' # Options: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
# LOG_FILE = 'scrapy_crawl.log' # Uncomment to log to a file instead of/besides console

# --- Optional: Item Pipelines ---
# For more complex data processing/validation/storage, consider using Item Pipelines.
# ITEM_PIPELINES = {
#    'mycrawler.pipelines.MongoPipeline': 300,
# }

Run the Spider: Open your terminal, navigate to the project's root directory (mycrawler), and run:

scrapy crawl web_crawler

(Replace web_crawler if you changed the name attribute in the spider).

Summary of Changes and Improvements:
Configuration: Moved MongoDB URI, database/collection names, start URLs, and allowed domains to settings.py for easy management.

from_crawler: Used the standard Scrapy method to initialize the spider with settings and connect signals.

MongoDB Handling: Robust connection setup with error handling and timeout. Connection is cleanly closed when the spider stops using signals.spider_closed.

Link Extraction: Switched to LinkExtractor for more reliable and configurable link finding, automatically respecting allowed_domains and ignoring common non-HTML file types.

Error Handling: Added try...except blocks for MongoDB operations, regex extraction, and link following. Implemented errback for handling request errors.

Logging: Integrated standard Scrapy logging (self.logger) with appropriate levels (DEBUG, INFO, WARNING, ERROR). PII findings are logged as WARNING.

Data Storage: Uses update_one with upsert=True to avoid duplicate entries for the same URL, storing the latest findings. Added timestamp and source domain to stored data.

Regex: Pre-compiled regex patterns for efficiency. Added re.IGNORECASE where applicable. Slightly refined NI number regex. (Note: PII regex is inherently complex and imperfect).

Clarity & Warnings: Added extensive comments explaining the code and critical warnings regarding the ethical and legal responsibilities of scraping PII.

Code Structure: Improved organization and adherence to Scrapy conventions.

Timestamping: Added a timestamp for when data was retrieved.

Standalone Runner (for testing): Included an if __name__ == '__main__': block for basic testing outside a full project, though running via scrapy crawl is standard practice.

Again, proceed with extreme caution if you intend to use this for scraping anything resembling personal information. Ensure full legal compliance and ethical justification.