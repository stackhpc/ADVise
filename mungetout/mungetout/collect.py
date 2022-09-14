#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collects Ironic introspection data
"""
from __future__ import division, print_function, absolute_import

import argparse
import logging
import json
import subprocess
import sys
import os
import re
import random
import shlex

from mungetout import __version__

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
                    "suitable for cardiff ingest from OpenStack "
                    "Ironic inspector")
    parser.add_argument(
        '--version',
        action='version',
        version='mungetout {ver}'.format(ver=__version__))
    parser.add_argument(
        '--inspector-cloud',
        dest='inspector_cloud',
        metavar="CLOUD",
        nargs='?',
        default="",
        help="Cloud to use for introspection data")
    parser.add_argument(
        '--regex',
        dest='regex',
        metavar="REGEX",
        nargs='?',
        default="",
        help="Select nodes using a regex")
    parser.add_argument(
        '--limit',
        dest='limit',
        metavar="MAX",
        nargs='?',
        type=int,
        help="Limit the number of nodes processed",
        default=None)
    parser.add_argument(
        '--seed',
        dest='seed',
        metavar="SEED",
        nargs='?',
        type=int,
        help="Seed for the random number generator",
        default=None)
    parser.add_argument(
        '--shuffle',
        dest="shuffle",
        help="Randomize nodes. Useful for sampling with limit.",
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


class DownloadException(Exception):
    pass


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def _get_nodes():
    if nodes:
        return nodes
    cmd = "openstack baremetal node list -f json -c UUID -c Name"
    output = subprocess.check_output(shlex.split(cmd))
    return json.loads(output)


def _get_introspection_data(uuid, cloud=None):
    env = dict(os.environ)
    if cloud:
        env = dict(os.environ, OS_CLOUD=cloud)
    cmd = "openstack baremetal introspection data save {}".format(uuid)
    output = subprocess.check_output(shlex.split(cmd), env=env)
    return json.loads(output)


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)

    # Use stdin for the node list if available
    if not sys.stdin.isatty():
        global nodes
        nodes = json.load(sys.stdin)

    if args.limit:
        _logger.info("Using limit: {}".format(args.limit))
    skipped = 0
    i = 0
    nodes = _get_nodes()
    if args.seed:
        _logger.info("Using seed: {}".format(args.seed))
        random.seed(args.seed)
    if args.shuffle:
        random.shuffle(nodes)

    os.mkdir("introspection-data")

    for i, node in enumerate(nodes):
        if args.limit and i - skipped >= args.limit:
            skipped += len(nodes) - i
            break
        node_name = node["Name"]
        node_uuid = node["UUID"]

        if not node_name:
            _logger.warning("Node with uuid: {}, has no name. Skipping..."
                            .format(node_uuid))
            skipped += 1
            continue

        if args.regex and not re.search(args.regex, node_name):
            _logger.debug("Node with name: {} doesn't match regex"
                          .format(node_name))
            skipped += 1
            continue

        introspection_data = _get_introspection_data(
            node_uuid, cloud=args.inspector_cloud)
        introspection_path = os.path.join(
            "introspection-data", '%s.json' % node_name)
        with open(introspection_path, 'w') as f:
            json.dump(introspection_data, f, indent=4, sort_keys=True)

    _logger.info("Processed {} nodes".format(i))
    _logger.info("Skipped {} nodes".format(skipped))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])
