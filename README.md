[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-3918) [![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31013/) [![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3117/)
## kscrapy
**kscrapy** is a specialized extension of the Scrapy framework designed to integrate seamlessly with Apache Kafka, enabling robust, scalable, and efficient
web scraping with real-time data streaming capabilities. This integration leverages Kafka’s distributed streaming platform to enhance the data processing
workflow, making it ideal for high-throughput, distributed web crawling tasks.

### Overview
**kscrapy** extends the core functionalities of Scrapy by introducing Kafka-based spiders and pipelines, which allow direct communication with Kafka topics.
This integration facilitates a seamless flow of data between your Scrapy spiders and Kafka, enabling scalable and resilient data pipelines. Additionally,
a custom extension is provided to publish log statistics to a Kafka topic at the end of each day, allowing for detailed offline analysis of your spider's
performance.

This project builds upon the foundational work of [scrapy-kafka](https://github.com/dfdeshom/scrapy-kafka) and
[kafka_scrapy_connect](https://github.com/spicyparrot/kafka_scrapy_connect), incorporating Confluent’s Kafka Python client to provide advanced producer
and consumer features.

## Features
**Kafka Integration**
   - **Seamless Communication:** Integrates Scrapy spiders with Kafka topics, enabling the efficient flow of data from crawled web pages to your Kafka-based data pipeline.
   - **Parallel Processing:** Leverages Kafka’s partitioning and consumer group features to parallelize message processing across multiple spiders, improving throughput and reducing latency.
   - **Batch Processing:** Allows the consumption of messages in batches, enhancing performance and reducing overhead by minimizing the number of individual operations.

**Customizable Settings**
   - **Flexible Configuration**: kscrapy provides extensive customization options for Kafka consumers and producers. Users can configure various settings to tailor the behavior of spiders and pipelines to their specific needs.

**Error Handling**
   - **Resilient Crawling:** Automatically manages network errors encountered during crawling by publishing the URLs that failed to a designated error topic. This ensures that no data is lost and that failed attempts can be retried or analyzed later.

**Serialisation Customisation**
   - **Custom Message Handling:** Users can override the process_kafka_message method in their spider classes to define custom deserialization logic. This feature allows for handling complex message formats or applying specific data transformations before processing.

**Custom Stats Extension**
   - **Performance Monitoring:** Includes a custom Scrapy extension that logs basic scraping statistics at regular intervals and publishes detailed end-of-day summaries to a specified Kafka topic. This feature is invaluable for monitoring and optimizing spider performance.
	
**Playwright Integration**
   - **Rendering dynamic webpages:** kscrapy integrates with Playwright to enable the automatic rendering of dynamic webpages.

## Installation
You can install `kscrapy` via pip:
```
pip install kscrapy
```

## Getting Started
### Prerequisites
   - **Docker:** Docker is required to set up a local Kafka cluster. This cluster is necessary for running the kscrapy examples and for enabling communication between kscrapy spiders and Kafka brokers.

### Setup Instructions
1. **Create a Virtual Environment:**
   - Set up a virtual environment to isolate your Python dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. **Clone the kscrapy repository and install the required dependencies:**
```bash
git clone https://github.com/olk/kscrapy.git && cd kscrapy
pip install -r requirements.txt
```

3. **Launch a Local Kafka Cluster:**
   - Use the provided script to start a Kafka cluster with the required topics:
```bash
bash ./examples/kafka/kafka_start.sh --input-topic ScrapyInput,1 --output-topic ScrapyOutput,1 --error-topic ScrapyError,1 --stats-topic ScrapyStats,1
```

### Example: Simple Spider
This example demonstrates how to use a basic kscrapy spider to consume URLs from a Kafka topic and scrape data from the corresponding web pages.

1. **Run the Spider:**
   - Navigate to the quotes example directory and start the spider:
```bash
cd examples/quotes && scrapy crawl quotes
```

2. **Publish a Message to Kafka:**
   - You can publish a URL to the Kafka input topic using custom producer code or by using the Kafka UI at http://localhost:8080:
   - Navigate to the Topics section in the Kafka-UI, select InputTopic, and publish a message with the URL http://quotes.toscrape.com/scroll.
   - The spider will consume the message, start crawling the provided URL, and publish the scraped data to the ScrapyOutput topic.

3. **Cleanup:**
   - After completing the test, stop the spider and clean up the local Kafka cluster:
```bash
bash ./examples/kafka/kafka_stop.sh
```

### Example: Crawling Spider
This example demonstrates how to use a crawling spider that not only scrapes data from a single page but also follows links to scrape additional pages.

1. **Run the Crawling Spider:**
   - Navigate to the books example directory and start the spider:
```bash
cd examples/books && scrapy crawl books
```

2. **Publish a Message to Kafka:**
   - Publish a message with the URL https://books.toscrape.com/ to the Kafka InputTopic.
   - The spider will crawl the site, follow links, and scrape data, publishing the results to the ScrapyOutput topic.

3. **Cleanup:**
   - After completing the test, stop the spider and clean up the local Kafka cluster:
```bash
bash ./examples/kafka/kafka_stop.sh
```

## Usage
### Implementing a Listening Spider
To create a spider that listens for messages from a Kafka topic, inherit from **KafkaSpider** and implement the parse method:

```python
class TestKafkaSpider(KafkaSpider):
    name = "quotes"

    def parse(self, response):
        logging.info(f'Received a response ...{response}')
        for quote in response.xpath('//div[@class="quote"]'):
            yield {
                'text' : quote.xpath('./span[@class="text"]/text()').extract_first(),
                'author' : quote.xpath('.//small[@class="author"]/text()').extract_first(),
                'tags' : quote.xpath('.//div[@class="tags"]/a[@class="tag"]/text()').extract()
            }
```

### Implementing a Listening Crawling Spider
For more complex use cases, you can create a crawling spider by inheriting from **KafkaCrawlSpider**. This allows the spider to follow links and scrape data from multiple pages:

```python
class TestKafkaCrawlSpider(KafkaCrawlSpider):
    name = "books"
    
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
```

### Implementing a Pipeline that Publishes to Kafka
To publish the results or errors of your scraping tasks to Kafka topics, inherit from **KafkaPublishPipeline**:

```python
class TestKafkaPipeline(KafkaPublishPipeline):
    seen = False

    def on_process_item(self, item, spider):
	# Custom processing logic
        if item["author"] is None:
	    # Filter out item
            raise DropItem("property author not found")

        self.seen = True

    def on_close_spider(self, spider):
        if False == self.seen:
            # report error to Kafka error topic
            raise KafkaReportError("no quotes")
```

The method **on_process_item** can be customized in order to filter out items from the pipeline while **on_close_spider** is used to report errors on closing the pipeline.

## Customisation
### Custom Settings
**kscrapy** supports various custom settings to fine-tune the Kafka integration:

- `KSCRAPY_INPUT_TOPIC`	- The Kafka topic from which the spider consumes messages. Default: `ScrapyInput`.
- `KSCRAPY_OUTPUT_TOPIC` - The Kafka topic where the scraped items are published. Default: `ScrapyOutput`.
- `KSCRAPY_ERROR_TOPIC`	- The Kafka topic where URLs that failed due to network errors are published. Default: `ScrapyError`.
- `KSCRAPY_CONSUMER_CONFIG` - Additional Kafka consumer configuration options (see [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md)).
- `KSCRAPY_PRODUCER_CONFIG` - Additional Kafka producer configuration options (see [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md)).
- `KSCRAPY_PRODUCER_KEY` - The key used for partitioning messages in the Kafka producer. Default: `""` (Round-robin).
- `KSCRAPY_PRODUCER_PARTITION` - The Kafka partition where messages are sent. Default: `-1` (use internal partitioner).
- `KSCRAPY_PRODUCER_CALLBACKS` -  Enable or disable asynchronous message delivery callbacks. Default: `False`.
- `KSCRAPY_PRODUCER_CALLBACKS` -  Enable or disable asynchronous message delivery callbacks. Default: `False`.
- `KSCRAPY_USE_PLAYWRIGHT` -  Enable or disable the use of Playwright. Default: `False`.
- `KSCRAPY_DONT_FILTER` -  Enable or disable filtering requests by scrapy framework. Default: `False`.
  
### Customising deserialisation
You can override the **process_kafka_message** method to customize how Kafka messages are deserialized. This is useful for handling custom message formats or performing specific data transformations:

```python
class TestKafkaSpider(KafkaSpider):
	def process_kafka_message(self, message, meta={}, headers={}):
		# Custom deserialization logic
		# Return URL, metadata or None if extraction fails
		pass
```

By default, if no custom **process_kafka_message** method is provided, the spider expects a JSON payload or a string containing a valid URL. If a JSON object is provided, iT EXPECTS URL IN THE k/v PAIR.

### Customising Producer & Consumer settings
Provide a dictionary of options in Scrapy settings:

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

### Custom stats extensions
**kscrapy** provides a custom Scrapy stats extension to log and publish statistics to a Kafka topic:

1. logs basic scraping statistics every minute (*frequency can be configured by the scrapy setting* `KAFKA_LOGSTATS_INTERVAL`)
2. At **end-of-day**, will publish logging statistics to a Kafka topic (specified by the scrapy setting `KSCRAPY_STATS_TOPIC`).
   1. Each summary message will be published with a key specifying the summary date (`2024-02-27`) for easy identification.
   2. If the spider is shutdown or closed, due to a deployment etc, a summary payload will also be sent to a kafka topic (`KSCRAPY_STATS_TOPIC`)

```
# Kafka topic for capturing stats
KSCRAPY_STATS_TOPIC = 'ScrapyStats'

# Disable standard logging extension (use custom kscrapy extension)
EXTENSIONS = {
  "scrapy.extensions.logstats.LogStats": None,
  "kscrapy.extensions.KafkaLogStats": 500
}
```

An example payload sent to the stats topic might look like:
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

### Playwright Integration
** kscrapy** integrates with Playwright to enable the automatic rendering of dynamic webpages:

1. Install `playwright` via `pip`.
2. Run `playwright install chromium --with-deps`.
3. Install `scrapy-playwright` via `pip`.
4. Set `KSCRAPY_USE_PLAYWRIGHT` to `True` in Scrapy settings file `settings.py`.
5. Add Playwright configuration options (headless, timeout etc.) in Scrapy settings file `settings.py`.


```
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
KSCRAPY_USE_PLAYWRIGHT = True
...
```

```python
class TestKafkaSpider(KafkaSpider):
    name = "quotes"

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
```
