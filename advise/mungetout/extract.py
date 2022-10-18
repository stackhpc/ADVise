#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generates a directory tree containing extra hardware data suitable
for ingest by ADVise
"""
from __future__ import division, print_function, absolute_import

import argparse
import logging
import json
import sys
import os
import shlex
from subprocess import Popen, PIPE

from advise.mungetout import process as m2convert
from advise.mungetout import __version__

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)

nodes = []

def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Generates extra hardware data in format "
                    "suitable for ADVise ingest from OpenStack "
                    "Ironic inspector")
    parser.add_argument(
        '--output_dir')
    parser.add_argument(
        '--version',
        action='version',
        version='mungetout {ver}'.format(ver=__version__))
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
    parser.add_argument(
        'files',
        metavar='files',
        nargs='+',
        help='files to process')
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

    output_dir = args.output_dir

    if not os.path.exists(output_dir): os.mkdir(output_dir)

    if not os.path.exists("%s/extra-hardware" % output_dir): os.mkdir("%s/extra-hardware" % output_dir)
    if not os.path.exists("%s/extra-hardware-filtered" % output_dir): os.mkdir("%s/extra-hardware-filtered" % output_dir)
    if not os.path.exists("%s/extra-hardware-json" % output_dir): os.mkdir("%s/extra-hardware-json" % output_dir)

    for path in args.files:

        # assume <node_name>.json
        node_name = os.path.basename(path)[:-5]

        with open(path, 'r') as f:
            introspection_data = json.load(f)

        extra_data = introspection_data["data"]

        extra_path = os.path.join('%s/extra-hardware' % output_dir, '%s.eval' % node_name)
        filtered_path = os.path.join(
            '%s/extra-hardware-filtered' % output_dir, '%s.json' % node_name)
        json_path = os.path.join('%s/extra-hardware-json' % output_dir, '%s.json' % node_name)

        with open(extra_path, 'w') as f:
            orig_stdout = sys.stdout
            sys.stdout = f
            m2convert.internal_main(data=extra_data, filter_benchmarks=False, filter_serials=False, output_format="eval")
            sys.stdout = orig_stdout
            # cmd = 'm2-convert --output-format eval'
            # process = Popen(shlex.split(cmd), stdout=f, stdin=PIPE,
            #                 stderr=PIPE)
            # stdout, stderr = process.communicate(
            #     input=json.dumps(extra_data).encode("UTF-8"))
            # rc = process.returncode
            # if rc != 0:
            #     print((stdout, stderr))

        with open(json_path, 'w') as f:
            json.dump(extra_data, f)

        with open(filtered_path, 'w') as f:
            orig_stdout = sys.stdout
            sys.stdout = f
            m2convert.internal_main(data=extra_data, filter_benchmarks=True, filter_serials=True, output_format=None)
            sys.stdout = orig_stdout
            # cmd = 'm2-convert --filter-benchmarks --filter-serials'
            # process = Popen(shlex.split(cmd), stdout=f, stdin=PIPE,
            #                 stderr=PIPE)
            # stdout, stderr = process.communicate(
            #     input=json.dumps(extra_data).encode("UTF-8"))
            # rc = process.returncode
            # if rc != 0:
            #     print((stdout, stderr))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])
