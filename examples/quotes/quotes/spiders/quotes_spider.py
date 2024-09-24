import os
import sys
import json
import logging
import scrapy

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, os.path.abspath(f'{SCRIPT_DIRECTORY}/../../../../'))

from kscrapy.spiders import KafkaSpider

class TestKafkaSpider(KafkaSpider):
    name = "quotes"

    # Override process_kafka_message to suit your serializer type or use default method which can parse JSON / string serialized messages
    # Method needs to return a URL to crawl / scrape
    # def process_kafka_message(self, message):
    #     logging.info('Custom process kafka message - received message')
    #     json_obj = json.loads(message.value())
    #     url = json_obj['url']
    #     return url


    async def parse(self, response):
        logging.info(f'Received a response ...{response}')
        page = response.meta["playwright_page"]
        await page.wait_for_selector("div.quote")
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        for i in range (2,11):
            pos = i * 10
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await page.wait_for_selector(f"div.quote:nth-child({pos})")

        html = await page.content()
        await page.close()
        selector = scrapy.Selector(text=html)
        for quote in selector.css('.quote'):
            yield {
                    'text' : quote.css('.text ::text').extract_first(),
                    'author' : quote.css('.author ::text').extract_first(),
                    'tags' : quote.css('.tag ::text').extract()
                }
