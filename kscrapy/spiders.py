import json
import logging
import sys
from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Request
from scrapy import signals
from scrapy.spiders import Spider, CrawlSpider
from urllib.parse import urlparse


class KafkaSpiderMixin:
    """
    Mixin class to implement reading URLs from a Kafka queue.
    """

    def setup_kafka_producer(self, settings):
        self.key = settings.get('KSCRAPY_PRODUCER_KEY', '')
        kafka_config = settings.get('KSCRAPY_PRODUCER_CONFIG', {})
        if 'bootstrap.servers' not in kafka_config:
            kafka_config['bootstrap.servers'] = 'localhost:9092'
        self.producer = Producer(kafka_config)
        self.error_topic = settings.get('KSCRAPY_ERROR_TOPIC', 'kscrapy_error')


    def process_kafka_message(self, message, meta={}):
        """
        Extracts URLs from a Kafka message.
        :param message: A Kafka message object
        :type message: Any
        :return: URL extracted from the message, or None if extraction fails
        :rtype: str or None
        """
        # Process message
        try:
            if message is None:
                return None
            if message.error():
                # Handle Kafka errors
                if message.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition
                    return None
                else:
                    raise KafkaException(message.error())
            else:
                try:
                    # Attempt to decode message as JSON
                    json_obj = json.loads(message.value())
                    # If decoding succeeds, it's a JSON object
                    if isinstance(json_obj, dict) and 'url' in json_obj:
                        url = json_obj['url']
                        meta = json_obj.get('meta')
                        if self.is_valid_url(url):
                            logging.debug(f"Received valid URL => {url}")
                            return url, {} if meta is None else meta
                        else:
                            logging.warning(f"Invalid URL => {url}")
                            return None
                    else:
                        logging.warning(f"Invalid JSON format => {json_obj}")
                        return None
                except  json.decoder.JSONDecodeError:
                    message = message.value().decode()
                    # If decoding as JSON fails, check if it's a valid URL string
                    if self.is_valid_url(message):
                        logging.debug(f"Received valid URL => {message}")
                        return message, meta
                    else:
                        logging.warning(f"Message is not a valid URL => {message}")
                        return None
        except ValueError as e:
            logging.warning(f"Error processing message: {e}")
            return None


    def is_valid_url(self, url):
        """
        Checks if a URL is valid.
        :param url: URL to be validated
        :type url: str
        :return: True if the URL is valid, False otherwise
        :rtype: bool
        """
        parsed_url = urlparse(url)
        return parsed_url.scheme in ['http', 'https'] and bool(parsed_url.netloc)


    def setup_kafka_consumer(self, settings):
        """
        Sets up the Kafka consumer.
        :param settings: The current Scrapy settings being used
        :type settings: scrapy.settings.Settings
        """
        kafka_config = settings.get('KSCRAPY_CONSUMER_CONFIG', {})
        if 'bootstrap.servers' not in kafka_config:
            kafka_config['bootstrap.servers'] = 'localhost:9092'
        if 'group.id' not in kafka_config:
            kafka_config['group.id'] = 'kafka-scrapy'
        topic = settings.get('KSCRAPY_INPUT_TOPIC', 'kscrapy_input')
        try:
            self.consumer = Consumer(kafka_config)
            self.consumer.subscribe([topic])
            logging.info(f'Instantiated a kafka consumer subscribed to topic: {topic}.')
        except KafkaException as e:
            logging.error(f"Failed to connect to Kafka: {e}")
            sys.exit(1)
        self.use_playwright = settings.get('KSCRAPY_USE_PLAYWRIGHT', False)
        self.dont_filter = settings.get('KSCRAPY_DONT_FILTER', False)
        # Call idle signal when there are no requests left
        self.crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)
        self.crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        logging.info(f'Connected with the following config: {kafka_config}')
        logging.info(f"Listening to Kafka topic {settings.get('KSCRAPY_INPUT_TOPIC')} for incoming messages.")


    def fetch_next_request(self):
        """
        Fetches the next request to be scheduled
        Consumes messages from Kafka.
        :rtype: scrapy.Request or None
        """
        messages = self.consumer.consume(timeout=1.0)
        if not messages or len(messages) == 0:
            logging.debug('No messages to process')
            return None
        logging.debug(f"Received batch with {len(messages)} messages.")
        for message in messages:
            result = self.process_kafka_message(message)
            if result is not None:
                url, meta = result
                logging.debug(f'Crawling {url}')
                if self.use_playwright:
                    meta['playwright'] = True
                    meta['playwright_include_page'] = True

                yield Request(url=url, meta=meta, dont_filter=self.dont_filter, errback=self.network_error_cb)


    def network_error_cb(self, failure):
        error = f'Network request failure: {repr(failure)}'
        url = failure.request.url
        logging.warning(f'{error}')
        payload = {'url': url, 'error': error}
        self.publish_failures(payload)


    def publish_failures(self, payload):
        logging.debug(f'Publishing failure to {self.error_topic}')
        self.producer.produce(self.error_topic, key=self.key, value=json.dumps(payload))
        self.producer.poll()


    def schedule_next_request(self):
        """Schedules the next request if available."""
        for request in self.fetch_next_request():
            self.crawler.engine.crawl(request)
            logging.debug("Scheduled next request.")


    def spider_idle(self):
        """Schedules a request if available, otherwise waits."""
        self.schedule_next_request()
        logging.debug("Spider is idle.")
        raise DontCloseSpider


    def item_scraped(self, *args, **kwargs):
        """Schedules the next request after an item has been scraped."""
        self.schedule_next_request()


    def close_spider(self, spider):
        """
        Flushes the queue when the spider is closed.
        """
        logging.info("Flushing Kafka publish queue...")
        self.producer.flush()
        logging.info("Kafka publish queue flushed.")
        self.producer.close()


class KafkaSpider(KafkaSpiderMixin, Spider):
    """
    Spider that listens to a Kafka topic for incoming messages and initiates crawling.
    """

    def _set_crawler(self, crawler):
        """
        Sets up the crawler.
        :type crawler: scrapy.crawler.Crawler
        """
        super(KafkaSpider, self)._set_crawler(crawler)
        self.setup_kafka_consumer(crawler.settings)
        self.setup_kafka_producer(crawler.settings)


class KafkaCrawlSpider(KafkaSpiderMixin, CrawlSpider):
    """
    Spider that listens to a Kafka topic for incoming messages and initiates crawling.
    """

    def _set_crawler(self, crawler):
        """
        Sets up the crawler.
        :type crawler: scrapy.crawler.Crawler
        """
        super(KafkaCrawlSpider, self)._set_crawler(crawler)
        self.setup_kafka_consumer(crawler.settings)
        self.setup_kafka_producer(crawler.settings)
