# settings.py

BOT_NAME = 'mycrawler'
SPIDER_MODULES = ['mycrawler.spiders']
NEWSPIDER_MODULE = 'mycrawler.spiders'

# --- CRITICAL: Obey robots.txt rules ---
ROBOTSTXT_OBEY = True # Set to False ONLY if you have explicit permission

# --- Configure user agent ---
# USER_AGENT = 'Your Project Name (+http://www.yourwebsite.com)' # Be polite

# --- Configure MongoDB Connection ---
MONGO_URI = "mongodb://localhost:27017/"  # Replace with your MongoDB connection string
                                         # e.g., "mongodb+srv://user:password@cluster.mongodb.net/?retryWrites=true&w=majority"
MONGO_DATABASE = "web_crawler_db"        # Choose a database name
MONGO_COLLECTION = "personal_info_collection" # Choose a collection name

# --- Configure Starting Point & Scope ---
START_URLS = ["http://example.com"] # !!! REPLACE with your actual target start URL(s) !!!
ALLOWED_DOMAINS = ["example.com"]   # !!! REPLACE with the domain(s) you are allowed to crawl !!!

# --- Crawl Control Settings (Optional but Recommended) ---
# Configure maximum crawl depth (0 means no limit)
# DEPTH_LIMIT = 3

# Configure request delay to be polite to servers
# DOWNLOAD_DELAY = 1 # 1 second delay between requests
# CONCURRENT_REQUESTS_PER_DOMAIN = 8 # Adjust as needed, be mindful of server load

# Enable and configure the AutoThrottle extension (recommended)
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 1
# AUTOTHROTTLE_MAX_DELAY = 60
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0 # Adjust based on server response times
# AUTOTHROTTLE_DEBUG = False # Set to True to see throttling stats

# --- Configure Logging ---
# LOG_LEVEL = 'INFO' # Options: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
# LOG_FILE = 'scrapy_crawl.log' # Optional: Log to a file

# --- Optional: Item Pipelines (A more robust way to handle data storage) ---
# ITEM_PIPELINES = {
#    'mycrawler.pipelines.MongoPipeline': 300, # Example pipeline
# }