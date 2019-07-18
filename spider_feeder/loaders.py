from urllib.parse import urlparse
import logging
from os import path

from scrapy import signals
from scrapy.exceptions import NotConfigured
from scrapy.utils.misc import load_object

logger = logging.getLogger(__name__)


class StartUrlsLoader:

    FILE_HANDLERS = {
        '': 'spider_feeder.file_handler.local.open',
        'file': 'spider_feeder.file_handler.local.open',
        's3': 'spider_feeder.file_handler.s3.open',
    }

    FILE_PARSERS = {
        'txt': 'spider_feeder.parser.TxtParser',
        'csv': 'spider_feeder.parser.CsvParser',
        'json': 'spider_feeder.parser.JsonParser',
    }

    @classmethod
    def from_crawler(cls, crawler):
        input_file_uri = crawler.settings.get('SPIDERFEEDER_INPUT_FILE', None)
        if not input_file_uri:
            raise NotConfigured('StartUrlsLoader requires SPIDERFEEDER_INPUT_FILE setting.')

        handlers = crawler.settings.getdict('SPIDERFEEDER_FILE_HANDLERS', {})
        handlers = dict(cls.FILE_HANDLERS, **handlers)

        parsers = crawler.settings.getdict('SPIDERFEEDER_FILE_PARSERS', {})
        parsers = dict(cls.FILE_PARSERS, **parsers)

        encoding = crawler.settings.get('SPIDERFEEDER_INPUT_FILE_ENCODING', 'utf-8')

        extension = cls(crawler, input_file_uri, encoding, handlers, parsers)
        crawler.signals.connect(extension.spider_openened, signal=signals.spider_opened)
        return extension

    def __init__(self, crawler, input_file_uri, file_encoding, handlers, parsers):
        self._input_file_uri = input_file_uri
        self._file_handlers = handlers
        self._file_parsers = parsers
        self._file_encoding = file_encoding
        self._crawler = crawler

    def spider_openened(self, spider):
        input_file_uri = self._get_formatted_input_file_uri(spider)
        with self._open(input_file_uri) as f:
            spider.start_urls = self._parse(f, input_file_uri)
            n_urls = len(spider.start_urls)
            logger.info(f'Loaded {n_urls} urls from {input_file_uri}.')
            self._crawler.stats.set_value(f'spider_feeder/{spider.name}/url_count', n_urls)

    def _get_formatted_input_file_uri(self, spider):
        params = {k: getattr(spider, k) for k in dir(spider)}
        return self._input_file_uri % params

    def _open(self, input_file_uri):
        parsed = urlparse(input_file_uri)
        open = load_object(self._file_handlers[parsed.scheme])
        logger.info(f'Opening file {input_file_uri} with scheme {parsed.scheme}.')
        return open(input_file_uri, encoding=self._file_encoding)

    def _parse(self, fd, input_file_uri):
        (_, file_extension) = path.splitext(input_file_uri)
        file_extension = file_extension[1:]
        parser_cls = load_object(self._file_parsers[file_extension])
        print(self._file_parsers[file_extension])
        print(parser_cls)
        parser = parser_cls(self._crawler.settings)
        return parser.parse(fd)