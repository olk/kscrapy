import json
import logging
from confluent_kafka import Producer
from scrapy.exporters import BaseItemExporter

class KafkaPublishPipeline:
    """
    Publishes a serialized item into a Kafka topic.
    """

    def __init__(self, producer, topic, key='', partition=-1, drcb=False):
        """
        Initializes the Kafka item publisher.

        Args:
            producer (Producer): The Kafka producer.
            topic (str): The Kafka topic being used.
        """
        self.producer = producer
        self.topic = topic
        self.key = key
        self.partition = partition
        self.drcb = drcb

    def process_item(self, item, spider):
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
            self.producer.produce(self.topic, key=self.key, partition=self.partition, value=json.dumps(payload), callback=self.delivery_callback)
        else:
            logging.debug(f'Publishing results to {self.topic}')
            self.producer.produce(self.topic, key=self.key, partition=self.partition, value=json.dumps(payload))
        self.producer.poll(0)
        return item

    def delivery_callback(self, err, msg):
        if err is not None:
            logging.error(f'Failed to deliver message {msg}')
        else:
            logging.info(f'Produced to {msg.topic()} [{msg.partition()}] @ {msg.offset()}')

    @classmethod
    def from_settings(cls, settings):
        """
        Initializes the Kafka item publisher from Scrapy settings.

        Args:
            settings: The current Scrapy settings.

        Returns:
            KafkaItemPublisher: An instance of KafkaItemPublisher.
        """
        topic = settings.get('KSCRAPY_OUTPUT_TOPIC', 'kscrapy_output')
        key = settings.get('KSCRAPY_PRODUCER_KEY', '')
        partition = settings.get('KSCRAPY_PRODUCER_PARTITION', -1)
        drcb = settings.get('KSCRAPY_PRODUCER_CALLBACKS', False)
        kafka_config = settings.get('KSCRAPY_PRODUCER_CONFIG', {})
        kafka_producer = Producer(kafka_config)
        logging.info(f'Instantiated a kafka producer for topic: {topic} with the following configuration: {kafka_config}')
        return cls(kafka_producer, topic, key, partition, drcb)

    def close_spider(self, spider):
        """
        Flushes the queue when the spider is closed.
        """
        logging.info("Flushing Kafka publish queue...")
        self.producer.flush()
        logging.info("Kafka publish queue flushed.")
