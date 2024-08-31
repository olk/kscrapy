import os
import sys
import json
import logging

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, os.path.abspath(f'{SCRIPT_DIRECTORY}/../../../../'))

from kscrapy.spiders import KafkaCrawlSpider
from scrapy.spiders import Rule
from scrapy.linkextractors import LinkExtractor


class TestKafkaCrawlSpider(KafkaCrawlSpider):
    name = "books"

    # Override process_kafka_message to suit your serializer type or use default method which can parse JSON / string serialized messages
    # Method needs to return a URL to crawl / scrape
    # def process_kafka_message(self, message):
    #     logging.info('Custom process kafka message - received message')
    #     json_obj = json.loads(message.value())
    #     url = json_obj['url']
    #     return url

    rules = (
            Rule(LinkExtractor(allow='index.html',
                               deny=[
                                   'catalogue/page',
                                   'catalogue/category/books',
                                   'https://books.toscrape.com/index.html']
                               ), callback='parse', follow=True),
            Rule(LinkExtractor(allow='catalogue/page'), follow=True)
    )

    def parse(self, response):
        item = {
                'title': response.xpath('//h1/text()').get(),
                'price': response.xpath('//div[contains(@class, "product_main")]/p[@class="price_color"]/text()').get(),
                'url': response.url
        }
        logging.info(f'parsed item ...{item}')
        yield item
