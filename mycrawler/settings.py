# Scrapy settings for mycrawler project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'mycrawler' # <<< Should match the directory name

SPIDER_MODULES = ['mycrawler.spiders']
NEWSPIDER_MODULE = 'mycrawler.spiders'


# --- USER AGENT ---
# Crawl responsibly by identifying yourself (and your website) on the user-agent
# Be polite: identify your bot. Replace with your project info.
USER_AGENT = 'MyWebCrawler (+http://www.mywebsite.com/botinfo)' # *** CHANGE THIS ***

# --- ROBOTS.TXT ---
# Obey robots.txt rules
# Set to False ONLY if you have explicit permission AND understand the risks.
ROBOTSTXT_OBEY = True

# --- MONGODB CONFIGURATION ---
# *** REPLACE with your actual MongoDB connection string ***
MONGO_URI = "mongodb://localhost:27017/" # Example: "mongodb+srv://user:pass@cluster..."
MONGO_DATABASE = "web_crawler_db"        # Choose a database name
MONGO_COLLECTION = "personal_info_collection" # Choose a collection name

# --- CRAWL SCOPE CONFIGURATION ---
# These are often overridden by spider attributes or command-line args,
# but can serve as defaults. The spider code provided uses these settings.
# *** REPLACE with the actual URL(s) you want to start crawling from ***
START_URLS = ["http://example.com"] # Must be a list
# *** REPLACE with the domain(s) you are legally permitted to crawl ***
ALLOWED_DOMAINS = ["example.com"]   # Must be a list


# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# --- DELAY AND THROTTLING (Highly Recommended) ---
# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 1 # Start with 1 second
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16 # Default is 8
#CONCURRENT_REQUESTS_PER_IP = 16 # Default is 0 (disabled)

#
