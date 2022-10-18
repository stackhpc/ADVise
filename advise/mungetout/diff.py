import argparse
import logging
import sys
import json
from pprint import pprint

from deepdiff import DeepDiff

from advise.mungetout import convert
from advise.mungetout import __version__

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Basic json diff")
    parser.add_argument(
        '--version',
        action='version',
        version='mungetout {ver}'.format(ver=__version__))
    parser.add_argument(
        'file',
        metavar='FILE',
        nargs=2,
        help='File to diff'
    )
    parser.add_argument(
        '--filter-unique-fields',
        dest="unique",
        help="EXPERIMENTAL: Only compare fields that appear in both",
        action='store_true',
        default=False)
    parser.add_argument(
        '-v',
        '--verbose',
        dest="loglevel",
        help="set loglevel to INFO",
        action='store_const',
        const=logging.INFO)
    parser.add_argument(
        '-vv',
        '--very-verbose',
        dest="loglevel",
        help="set loglevel to DEBUG",
        action='store_const',
        const=logging.DEBUG)
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    with open(args.file[0]) as f1, open(args.file[1]) as f2:
        c1 = convert.clean(json.load(f1), filter_benchmarks=True,
                           filter_serials=True)
        c2 = convert.clean(json.load(f2), filter_benchmarks=True,
                           filter_serials=True)
        if args.unique:
            # x[1] element can be a disk or cpu id, x[3] is the value, so
            # only compare x[0] and x[2]. That way a difference in the
            # number of cpus or disks will still be shown.
            c1_keys = {(x[0], x[2]) for x in c1}
            c2_keys = {(x[0], x[2]) for x in c2}
            common_keys = c1_keys.intersection(c2_keys)
            c1 = [x for x in c1 if (x[0], x[2]) in common_keys]
            c2 = [x for x in c2 if (x[0], x[2]) in common_keys]
        ddiff = DeepDiff(c1, c2, ignore_order=True)
        pprint(ddiff, indent=2)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])
