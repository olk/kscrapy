[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-3918) [![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31013/) [![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3117/)
## kscrapy 

### Overview

`kscrapy` is a custom Scrapy library that integrates Scrapy with Kafka.

It consists of two main components: spiders and pipelines, which interact with Kafka for message consumption and item publishing.

The library also comes with a custom extension that publishes log stats to a kafka topic at EoD, which allows the user to analyse offline how well the spider is performing!

This project is based on the great work undertaken in: https://github.com/dfdeshom/scrapy-kafka and https://github.com/spicyparrot/kafka_scrapy_connect.

`kscrapy` utilises [Confluent's](https://github.com/confluentinc/confluent-kafka-python) Kafka Python client under the hood, to provide high-level producer and consumer features.

## Features

**Integration with Kafka**
   - Enables communication between Scrapy spiders and Kafka topics for efficient data processing.
   - Through partitions and consumer groups message processing can be parallelised across multiple spiders!
   - Reduces overhead and improves throughput by giving the user the ability to consume messages in batches.

**Customizable Settings**
   - Provides flexibility through customisable configuration for both consumers and producers.

**Error Handling**
   - Automatically handles network errors during crawling and publishes failed URLs to a designated output topic. 

**Serialisation Customisation**
   - Allows users to customize how Kafka messages are deserializsd by overriding the process_kafka_message method.

## Installation

You can install `kscrapy` via pip:
```
pip install kscrapy
```

## Examples

The *only prerequisite for walking through the examples* is the installation of **Docker**.

This is needed because a kafka cluster will be created locally using containers so `kscrapy` can communicate with a broker. 

If all set, follow the below steps

1. Create a virtual environment, clone the repo and install requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
git clone https://github.com/olk/kscrapy.git && cd kscrapy
pip install -r requirements.txt
```
2. Create a local kafka cluster with required topics:

```bash
bash ./examples/kafka/kafka_start.sh --input-topic ScrapyInput,1 --output-topic ScrapyOutput,1 --error-topic ScrapyError,1 --stats-topic ScrapyStats,1
```

### simple spider

1. Initiate the spider:
```bash
cd examples/quotes && scrapy crawl quotes
```
2. Publish a message to the input kafka topic and watch the spider consume and process the mesasge
   1.  This will require some custom producer code to publish messages or go to http://localhost:8080
   2. Navigate in the UI to `Topics` section and click on topic `InputTopic` (the topic the scraper is listening to).
   3. Hit `Produce Message` for topic `InputTopic` and add `https://quotes.toscrape.com/` as `Value` (leave `Key` blank).
   4. After publishing the message the scrape starts to parse `https://quotes.toscrape.com/`.
   5. The quotes scraper produces some messages for the `ScrapyOutput` topic (register `Messages` for `ScrapyOutput` topic in the UI) containing the parsed quotes. 

3. When satisfied with testing, exit the spider and clean up the local kafka cluster:
```bash
bash ./examples/kafka/kafka_stop.sh
```

### crawling spider

1. Initiate the spider:
```bash
cd examples/books && scrapy crawl books
```
2. Publish a message to the input kafka topic and watch the spider consume and process the mesasge
   1.  This will require some custom producer code to publish messages or go to http://localhost:8080
   2. Navigate in the UI to `Topics` section and click on topic `InputTopic` (the topic the scraper is listening to).
   3. Hit `Produce Message` for topic `InputTopic` and add `https://books.toscrape.com/` as `Value` (leave `Key` blank).
   4. After publishing the message the scrape starts crawling and parsing `https://books.toscrape.com/`.
   5. The quotes scraper produces some messages for the `ScrapyOutput` topic (register `Messages` for `ScrapyOutput` topic in the UI) containing the parsed quotes. 

3. When satisfied with testing, exit the spider and clean up the local kafka cluster:
```bash
bash ./examples/kafka/kafka_stop.sh
```

## Usage

### Custom Settings
`kscrapy` supports the following custom settings:

- `KSCRAPY_INPUT_TOPIC`	- Topic from which the spider[s] *consumes* messages from. (Default: `ScrapyInput`)
- `KSCRAPY_OUTPUT_TOPIC` - Topic where scraped items are published. (Default: `ScrapyOutput`)
- `KSCRAPY_ERROR_TOPIC`	- Topic for publishing URLs that failed due to *network errors*. (Default: `ScrapyError`)
- `KSCRAPY_CONSUMER_CONFIG` - Additional configuration options for Kafka consumers (see [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md))
- `KSCRAPY_PRODUCER_CONFIG` - Additional configuration options for Kafka producers (see [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md))
- `KSCRAPY_PRODUCER_KEY` - Key used for partitioning messages in Kafka producer (Default: `""` *Roundrobin*)
- `KSCRAPY_PRODUCER_PARTITION` - Partition messages are send to in Kafka producer (Default: -1 *use internal partitioner*)
- `KSCRAPY_PRODUCER_CALLBACKS` - Enable or disable asynchronous message delivery callbacks. (Default: `False`)

### Customisation

---

**Customising deserialisation**

You can customize how Kafka messages are deserialized by overriding the process_kafka_message method in your spider class. 

This allows for handling custom message formats or data transformations.

```python
class CustomSpider(KafkaSpider):
	def process_kafka_message(self, message, meta={}, headers={}):
		# Custom deserialization logic
		# Return URL, metadata or None if extraction fails
		pass
```

*By default*, if no custom `process_kafka_message` method is provided, the spider method `process_kafka_message` **will expect** a JSON payload or a string containing a valid url. If it's a JSON object, it expects `url` in the K/V pair.

---

**Customising Producer & Consumer settings**

You can customize producer and consumer settings by providing a dictionary of configuration options in your Scrapy settings under `KSCRAPY_PRODUCER_CONFIG` and `KSCRAPY_CONSUMER_CONFIG`.

```python
# Example KSCRAPY_PRODUCER_CONFIG
KSCRAPY_PRODUCER_CONFIG = {
	'bootstrap.servers': '192.168.10.10:9092',
	'compression.type': 'gzip',
	'request.timeout.ms': 5000
}

# Example KSCRAPY_CONSUMER_CONFIG
KSCRAPY_CONSUMER_CONFIG = {
	'bootstrap.servers': '192.168.10.10:9092',
	'fetch.wait.max.ms': 10,
	'max.poll.interval.ms': 600000,
	'auto.offset.reset': 'latest'
}
```
---
**Custom stats extensions**

`kscrapy` comes with a custom Scrapy stats extension that:
1. logs basic scraping statistics every minute (*frequency can be configured by the scrapy setting* `KAFKA_LOGSTATS_INTERVAL`)
2. At **end-of-day**, will publish logging statistics to a Kafka topic (specified by the scrapy setting `KSCRAPY_STATS_TOPIC`).
   1. Each summary message will be published with a key specifying the summary date (`2024-02-27`) for easy identification.
3.	If the spider is shutdown or closed, due to a deployment etc, a summary payload will also be sent to a kafka topic (`KSCRAPY_STATS_TOPIC`)


To enable this custom extension, disable the standard LogStats extension and modify your `settings.py` to include the below:
```
# Kafka topic for capturing stats
KSCRAPY_STATS_TOPIC = 'ScrapyStats'

# Disable standard logging extension (use custom kscrapy extension)
EXTENSIONS = {
  "scrapy.extensions.logstats.LogStats": None,
  "kscrapy.extensions.KafkaLogStats": 500
}
```

An example payload sent to the statistics topic will look like:
```json
{
	"pages_crawled": 3,
	"items_scraped": 30,
	"avg pages/min": 0.4,
	"avg pages/hour": 23.78,
	"avg pages/day": 570.63,
	"avg items/min": 3.96,
	"avg items/hour": 237.76,
	"avg items/day": 5706.3,
	"successful_request_pct": 100.0,
	"http_status_counts": "200: 3",
	"max_memory": 76136448,
	"elapsed_time": 454.23
}
```
