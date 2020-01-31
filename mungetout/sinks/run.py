import json
from jinja2 import Template
import sys
from subprocess import Popen
import os
import logging

_logger = logging.getLogger(__name__)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


if "M2_LOG_LEVEL" in os.environ:
    setup_logging(os.environ["M2_LOG_LEVEL"])


class CmdSink(object):

    def __init__(self, cmd):
        self.cmd = cmd

    def process(self, json):
        if isinstance(json, list):
            self._process_list(json)
        else:
            self._process_item(json)

    def _process_list(self, data):
        for item in data:
            self._process_item(item)

    def _process_item(self, item):
        rendered = []
        for part in self.cmd:
            tmpl = Template(part)
            render = tmpl.render(item=item)
            rendered.append(render)
        _logger.info("Running: {}".format(rendered))
        with Popen(rendered, stdout=sys.stdout, stderr=sys.stderr) as process:
            process.communicate()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception as e:
        data = []
        for line in sys.stdin:
            print(line)
            data.append(json.loads(line))

    sink = CmdSink(sys.argv[1:])
    sink.process(data)


if __name__ == "__main__":
    main()
