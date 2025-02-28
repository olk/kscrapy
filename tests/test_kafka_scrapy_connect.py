from ast import parse
import os
import sys
import json
import uuid
import unittest
import pytest
import requests
import time
from confluent_kafka import Producer, Consumer, KafkaError
from scrapy.http import HtmlResponse, Response, Request
from scrapy.settings import Settings

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.abspath(f'{SCRIPT_DIRECTORY}/../'))

from kscrapy.spiders import KafkaSpider
#from kscrapy.spiders import KafkaSpiderMixin
from kscrapy.pipelines import KafkaPublishPipeline

class TestSpider(KafkaSpider):
    name = 'test-spider'

    def process_kafka_input_message(self, message):
        msg = json.loads(message.value())
        request_url = msg['url']
        return request_url
    
    def parse(self, response):
        for quote in response.xpath('//div[@class="quote"]'):
            yield {
                'text' : quote.xpath('./span[@class="text"]/text()').extract_first(),
                'author' : quote.xpath('.//small[@class="author"]/text()').extract_first(),
                'tags' : quote.xpath('.//div[@class="tags"]/a[@class="tag"]/text()').extract()
            }

#=============================================================================================#
#===================================== PYTEST FIXTURES =======================================#
#=============================================================================================#
@pytest.fixture
def kafka_producer():
    conf = {'bootstrap.servers': 'localhost:9092')}
    producer = Producer(conf)
    return producer

@pytest.fixture
def kafka_consumer():
    group_id = str(uuid.uuid4())
    kafka_config = {
        'bootstrap.servers' : 'localhost:9092'),
        'group.id' : 'pytest-' + group_id,
        'auto.offset.reset' : 'earliest'
    }
    consumer = Consumer(kafka_config)
    return consumer

@pytest.fixture
def kafka_input_message(kafka_consumer):
    kafka_consumer.subscribe(['ScrapyInput'])
    message = kafka_consumer.poll(timeout=30)
    return message

@pytest.fixture
def kafka_output_message(kafka_consumer):
    kafka_consumer.subscribe(['ScrapyOutput'])
    message = kafka_consumer.poll(timeout=30)
    message = json.loads(message.value())
    return message

@pytest.fixture
def html_response_fixture():
    url = 'https://quotes.toscrape.com'
    response = requests.get(url)
    response.raise_for_status()
    test_directory = os.path.dirname(os.path.abspath(__file__))
    fixture_path = os.path.join(test_directory, 'test_response.html')
    with open(fixture_path, 'wb') as f:
        f.write(response.content)
    yield fixture_path
    os.remove(fixture_path)

@pytest.fixture
def parse_result(html_response_fixture):
    spider = TestSpider()
    with open(html_response_fixture, 'rb') as f:
        html_content = f.read()
    mock_response = create_mock_response(html_content)
    result = list(spider.parse(mock_response))
    yield result

def create_mock_response(html_content, url='https://quotes.toscrape.com',status=200, meta={}):
    meta_dict = meta
    request = Request(url=url, meta=meta_dict)
    return HtmlResponse(url, status=status, request=request, body=html_content,encoding='utf-8')

#=============================================================================================#
#====================================== PYTEST TESTS =========================================#
#=============================================================================================#

def test_publish_valid_message_to_kafka(kafka_producer):
    '''
    Verifies if a message can be successfully published to a Kafka topic. 
    It checks if the message is successfully delivered by setting a flag 
    upon delivery and then checking if the flag is set to true.
    '''
    message_delivered = False
    message_payload = {"url" : "https://quotes.toscrape.com"}
    message_json = json.dumps(message_payload)
    def delivery_callback(err, msg):
        nonlocal message_delivered
        if err is not None:
            raise Exception(f"Failed to deliver message: {err}")
        else:
            message_delivered = True
    kafka_producer.produce('ScrapyInput', value=message_json.encode('utf-8'),callback=delivery_callback)
    kafka_producer.flush()
    assert message_delivered, "Message was not delivered successfully"

def test_consume_valid_message_from_kafka(kafka_input_message):
    '''
    This test checks if a message can be consumed from a Kafka topic. 
    It simply checks if a message object is received from the Kafka topic.
    '''
    assert kafka_input_message is not None, "No message received from Kafka topic"

def test_is_valid_url():
    spider = TestSpider()
    assert spider.is_valid_url('https://quotes.toscrape.com')

def test_is_invalid_url():
    spider = TestSpider()
    assert spider.is_valid_url('im_not_a_url') == False

def test_process_kafka_input_message(kafka_input_message):
    '''
     This test checks if the method process_kafka_input_message of the TestSpider class 
     correctly processes a Kafka message by extracting the URL from the message
    '''
    spider = TestSpider()
    result = spider.process_kafka_input_message(kafka_input_message)
    assert result == 'https://quotes.toscrape.com'

def test_parse(parse_result):
    '''
    This test verifies if the parse method of the TestSpider class correctly extracts data from an HTML response.
    '''
    result = parse_result
    assert result[0]['author'] == 'Albert Einstein'
    assert result[0]['tags'] == ['change','deep-thoughts','thinking','world']
    assert len(result[0]['text']) > 1

def test_pipeline_publish_to_kafka(kafka_producer,parse_result,kafka_consumer):
    '''
    This test checks if the KafkaPublishPipeline's process_item method executes without errors.
    '''
    kafka_publish_pipeline = KafkaPublishPipeline(producer=kafka_producer, topic='ScrapyOutput')
    spider = TestSpider()
    kafka_publish_pipeline.process_item(parse_result[0],spider)
    kafka_producer.flush()
    kafka_consumer.subscribe(['ScrapyOutput'])
    message = kafka_consumer.poll(timeout=30)
    message = json.loads(message.value())
    assert isinstance(message, dict)
    assert message is not None, "No output message received"
