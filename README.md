📡 pii_crawler: A Legally-Conscious Web Crawler for PII Discovery
pii_crawler is a modular, ethics-first Scrapy framework designed to identify potentially sensitive personal information (PII) in web content — within legal boundaries and defined scopes.

Built for security engineers, compliance teams and privacy-aware developers.

🔍 What It Does
Crawls only explicitly allowed domains

Honors robots.txt and enforces strict domain constraints

Searches for emails, phone numbers, NI numbers, SSNs and other PII using precompiled regexes

Integrates cleanly with MongoDB for structured, timestamped, deduplicated storage

💡 Why Use This?
✅ Skip massive prebuilt wordlists or unstructured scrapes

✅ Inject target-specific intelligence with scoped crawl configs

✅ Pipe directly into security workflows or audits

✅ Respect bandwidth and rate limits with built-in throttling and AutoDelay

⚙️ Installation
bash
Copy
Edit
git clone https://github.com/your-repo/pii_crawler.git
cd pii_crawler
pip install -r requirements.txt
🚀 Usage
1. Configure the target domain
Edit allowed_domains and start_urls in spiders/pii_spider.py.

2. Crawl and discover
bash
Copy
Edit
scrapy crawl pii_spider
3. Review Results
Data will be stored in your configured MongoDB instance, including:

Match type

Match content

Source URL

Timestamp

🧠 Regex Coverage (Default)
Emails

UK NI numbers

US SSNs

Phone numbers

Credit card patterns (with false-positive filtering)

You can extend these in regex_patterns.py.

🔐 Legal & Ethical Disclaimer
This tool is built for internal audits, red-team simulations, and research within authorized domains only.

❗ Does not bypass robots.txt

❗ Will not crawl or scrape without explicit config

❗ Built-in compliance warnings flag dangerous usage

⚠️ You are responsible for ensuring all use complies with local laws and ethical standards.

🤝 Contribute
Open to forks, pull requests, regex improvements and feedback from the community.

If you're a privacy engineer, infosec researcher or curious builder — this one’s for you.

