import os
import sys
import logging
from scrapy.utils.log import configure_logging

BOT_NAME = "quotes"

SPIDER_MODULES = ["quotes.spiders"]
NEWSPIDER_MODULE = "quotes.spiders"

ITEM_PIPELINES = {
    'kscrapy.pipelines.KafkaPublishPipeline': 100
    }

# Scrapy kafka connect settings
KSCRAPY_BOOTSTRAP_SERVERS  = 'localhost:29092'
KSCRAPY_INPUT_TOPIC  = 'ScrapyInput'
KSCRAPY_OUTPUT_TOPIC = 'ScrapyOutput'
KSCRAPY_ERROR_TOPIC = 'ScrapyErrors'
KSCRAPY_STATS_TOPIC = 'ScrapyStats'

KSCRAPY_PRODUCER_KEY = ''
KSCRAPY_PRODUCER_CALLBACKS = False
KSCRAPY_PRODUCER_CONFIG = {
    'queue.buffering.max.ms' : 1,
    'linger.ms' : 5
}

KSCRAPY_CONSUMER_CONFIG = {
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

LOG_LEVEL = 'INFO'  # to only display errors
LOG_FORMAT = '%(asctime)s - %(levelname)8s - %(message)s'
