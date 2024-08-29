import json
import logging
from confluent_kafka import Producer
from scrapy.exceptions import DropItem
from scrapy.exporters import BaseItemExporter
from .exceptions import KafkaReportError

class KafkaPublishPipeline:
    """
    Publishes a serialized item into a Kafka topic.
    """

    def __init__(self, producer, output_topic, error_topic, key='', partition=-1, drcb=False):
        """
        Initializes the Kafka item publisher.

        Args:
            producer (Producer): The Kafka producer.
            output_topic (str): The Kafka topic being used for ouput.
            errortopic (str): The Kafka topic being used for errors.
        """
        self.producer = producer
        self.output_topic = output_topic
        self.error_topic = error_topic
        self.key = key
        self.partition = partition
        self.drcb = drcb

    def on_process_item(self, item, spider):
        return item

    def process_item(self, item, spider):
        try:
            item = self.on_process_item(item, spider)
        except KafkaReportError as ex:
            logging.info(f'Report error to {self.error_topic}')
            self.producer.produce(self.error_topic, key=self.key, value=json.dumps(str(ex)))
            raise DropItem("item dropped due Kafka error reporting")

        """
        Processes the item and publishes it to Kafka.

        Args:
            item: Item being processed.
            spider: The current spider being used.
        """
        payload = dict(item)
        if self.drcb:
            # Produce is asynchronous, all it does is enqueue the message to an internal queue
            # Adding flush after every produce effectively makes it synchronous
            self.producer.produce(self.output_topic, key=self.key, partition=self.partition, value=json.dumps(payload), callback=self.delivery_callback)
        else:
            logging.debug(f'Publishing results to {self.output_topic}')
            self.producer.produce(self.output_topic, key=self.key, partition=self.partition, value=json.dumps(payload))
        self.producer.poll(0)
        return item

    def delivery_callback(self, err, msg):
        if err is not None:
            logging.error(f'Failed to deliver message {msg}')
        else:
            logging.info(f'Produced to {msg.output_topic()} [{msg.partition()}] @ {msg.offset()}')

    @classmethod
    def from_settings(cls, settings):
        """
        Initializes the Kafka item publisher from Scrapy settings.

        Args:
            settings: The current Scrapy settings.

        Returns:
            KafkaItemPublisher: An instance of KafkaItemPublisher.
        """
        output_topic = settings.get('KSCRAPY_OUTPUT_TOPIC', 'kscrapy_output')
        error_topic = settings.get('KSCRAPY_ERROR_TOPIC', 'kscrapy_error')
        key = settings.get('KSCRAPY_PRODUCER_KEY', '')
        partition = settings.get('KSCRAPY_PRODUCER_PARTITION', -1)
        drcb = settings.get('KSCRAPY_PRODUCER_CALLBACKS', False)
        kafka_config = settings.get('KSCRAPY_PRODUCER_CONFIG', {})
        kafka_producer = Producer(kafka_config)
        logging.info(f'Instantiated a kafka producer for topics: [{output_topic}, {error_topic}] with the following configuration: {kafka_config}')
        return cls(kafka_producer, output_topic, error_topic, key, partition, drcb)
    
    def on_close_spider(self, spider):
        pass

    def close_spider(self, spider):
        try:
            self.on_close_spider(spider)
        except KafkaReportError as ex:
            logging.info(f'Report error to {self.error_topic}')
            self.producer.produce(self.error_topic, key=self.key, value=json.dumps(str(ex)))

        """
        Flushes the queue when the spider is closed.
        """
        logging.info("Flushing Kafka publish queue...")
        self.producer.flush()
        logging.info("Kafka publish queue flushed.")
