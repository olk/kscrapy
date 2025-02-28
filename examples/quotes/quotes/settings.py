import os
import sys
import logging
from scrapy.utils.log import configure_logging

# scrapy settings
BOT_NAME = "quotes"

SPIDER_MODULES = ["quotes.spiders"]
NEWSPIDER_MODULE = "quotes.spiders"

ITEM_PIPELINES = {
    'kscrapy.pipelines.KafkaPublishPipeline': 100
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"


# playwright settings
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 20 * 1000,  # 20 seconds
}


# Scrapy kafka connect settings
KSCRAPY_INPUT_TOPIC  = 'ScrapyInput'
KSCRAPY_OUTPUT_TOPIC = 'ScrapyOutput'
KSCRAPY_ERROR_TOPIC = 'ScrapyErrors'
KSCRAPY_STATS_TOPIC = 'ScrapyStats'

KSCRAPY_USE_PLAYWRIGHT = True

KSCRAPY_PRODUCER_KEY = ''
KSCRAPY_PRODUCER_CALLBACKS = False
KSCRAPY_PRODUCER_CONFIG = {
    'bootstrap.servers': '192.168.1.25:29092',
    'queue.buffering.max.ms' : 1,
    'linger.ms' : 5
}

KSCRAPY_CONSUMER_CONFIG = {
    'bootstrap.servers': '192.168.1.25:29092',
    'group.id':'example-crawler',
    'fetch.wait.max.ms': 10,
    'max.poll.interval.ms': 600000,
    'auto.offset.reset': 'earliest'
}

# LOGSTATS_INTERVAL = 60.0
# LOGSTATS_SUMMARY_INTERVAL = "DAILY"

EXTENSIONS = {
   'scrapy.extensions.logstats.LogStats': None,
   'kscrapy.extensions.KafkaLogStats': 500
}

LOG_LEVEL = 'DEBUG'  # to only display errors
LOG_FORMAT = '%(asctime)s - %(levelname)8s - %(message)s'
