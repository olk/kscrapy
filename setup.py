import os
from setuptools import setup, find_packages

MY_DIR = os.path.dirname(__file__)
README_MD = open(os.path.join(MY_DIR, 'README.md')).read()

setup(
    name='kscrapy',
    version='0.1.0',
    description='Integrating Scrapy with kafka using the confluent-kafka python client',
    long_description=README_MD,
    long_description_content_type="text/markdown",
    packages=['kscrapy'],
    install_requires=[
        'scrapy >= 2.11.1',
        'confluent-kafka >= 2.2.0'
    ],
    url='https://github.com/olk/kscrapy',
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11"
    ],
    keywords="kafka, scrapy, crawling, scraping",
)
