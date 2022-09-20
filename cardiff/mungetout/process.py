#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converts Openstack Ironic introspection data to a format accepted
by cardiff from python hardware.
"""
from __future__ import division, print_function, absolute_import

import argparse
import logging
import json
import sys
import re

from cardiff.mungetout import __version__

__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"

_logger = logging.getLogger(__name__)


_cardiff_blacklist = [
    # (u'hpa', u'slot_0', u'total_cache_memory_available', u'0.3')
    'total_cache_memory_available',
    # Strip out serial numbers e.g from ssacli for HP servers:
    #  (u'disk', u'1I:1:2', u'wwid', u'1234567'),
    'wwid',
    # ['hpa', 'slot_0', 'serial_number', '1234']
    'serial_number',
    # ['hpa', 'slot_0', 'host_serial_number', '1234']
    'host_serial_number',
    # ["disk", "sda", "wwn-id", "wwn-0xdeadbeef"]
    'wwn-id',
    # ["disk", "sda", "scsi-id", "scsi-1234"]
    'scsi-id',
    # ["system", "product", "uuid", "e21c3ea6-4215-40e6-99db-cf48569f1e59"]
    'uuid',
    # ["ipmi", "lan", "ip-address", "10.64.3.2"]
    'ip-address',
    # ["ipmi", "lan", "mac-address", "80:c1:6e:77:71:8c"]
    'mac-address',
    # ["cpu", "physical_0", "current_Mhz", 2700.224]
    'current_Mhz',
]

_serial_blacklist = [
    # ["system", "product", "serial", "CZHITHERE"]
    'serial',
]

_benchmark_regexps = [
    # Match threaded_bandwidth_2G, bandwidth_2G
    "^.*bandwidth_.*$",
    "^loops_per_sec$",
    "^bogomips$"
]

_benchmark_regex_fmt = "|".join(["(%s)" for _ in _benchmark_regexps])
_benchmark_regex = re.compile(_benchmark_regex_fmt % tuple(_benchmark_regexps))


def _parse_cmdline_param(p):
    # given ipa-collect-lldp=1, produce: ('ipa-collect-lldp', '1')
    # given nofb, produce: ('nofb', None)
    key_values = tuple(p.split("=", 1))
    return key_values if len(key_values) > 1 else (key_values[0], None)


def _cmdline2dict(cmdline):
    # given "ipa-collect-lldp=1", produce: {"ipa-collect-lldp": "1"}
    split_on_ws = cmdline.split()
    mapping = dict([_parse_cmdline_param(p) for p in split_on_ws])
    return mapping


def _dict2cmdline(mappings):
    # given "{"ipa-collect-lldp": "1"}", produce: "ipa-collect-lldp=1"
    # given ('nofb', None), produce nofb
    items = []
    for key, value in mappings.items():
        if value:
            items.append("{key}={value}".format(key=key, value=value))
        else:
            items.append(key)
    return " ".join(items)


def _use_placeholder(cmdline_dict, key):
    if key in cmdline_dict:
        logging.debug("Using placeholder for key: {}".format(key))
        cmdline_dict[key] = "PLACEHOLDER"


def _clean_kernel_cmdline(item):
    # ('system', 'kernel', 'cmdline',
    # 'ipa-inspection-callback-url=http://10.64.0.10:5050/v1/continue systemd.journald.forward_to_console=yes \ # noqa
    # ip=10.64.0.231:10.64.0.10:10.64.0.10:255.255.254.0 BOOTIF=80:c1:6e:7a:73:98 \  # noqa
    # nofb nomodeset vga=normal console=ttyS0 ipa-collect-lldp=1 \
    # ipa-inspection-collectors=default,logs,pci-devices,extra-hardware \
    # ipa-inspection-benchmarks=cpu,disk,mem')
    if len(item) < 4 or item[0] != "system" or item[1] != "kernel" or \
            item[2] != "cmdline":
        return item
    logging.debug("Before _clean_kernel_cmdline: {}".format(item[3]))
    cmdline = _cmdline2dict(item[3])
    # Remove unique values that prevent systems from being grouped
    _use_placeholder(cmdline, "BOOTIF")
    _use_placeholder(cmdline, "ip")
    _use_placeholder(cmdline, "ipa-global-request-id")
    cleaned = _dict2cmdline(cmdline)
    logging.debug("After _clean_kernel_cmdline: {}".format(cleaned))
    return item[0], item[1], item[2], cleaned


def _filter_network(item):
    if len(item) < 4:
        return item
    elif item[0] != "network":
        return item
    # Examples:
    # ["network", "eth0", "ipv4", "10.64.0.207"]
    # Assume common network, otherwise also need to filter ipv4-netmask,
    # ipv4-cidr etc.
    field = item[2]
    if field not in ["ipv4"]:
        return item
    logging.debug("_filter_network removing: {}".format(item))


def _filter_temperatures(item):
    # Strip out temperatures e.g from ssacli for HP servers:
    # (u'disk', u'1I:1:2', u'maximum_temperature_c', u'27'),
    # (u'disk', u'1I:1:2', u'current_temperature_c', u'18'),
    # (u'hpa', u'slot_0', u'capacitor_temperature_c', u'12'),
    if len(item) < 4 or "temperature" not in item[2]:
        return item
    logging.debug("_filter_temperatures, removing: {}".format(item))
    return None


def _clean_boot_volume(item):
    # (u'hpa',
    #  u'slot_0',
    #  u'secondary_boot_volume',
    #  u'logicaldrive 1 (600508B1001C6D568C431707B847FA3A)'),
    if len(item) < 4 or item[2] not in \
            ["primary_boot_volume", "secondary_boot_volume"]:
        return item
    # Only keep "logicaldrive NUM" component
    match = re.search(r"^(logicaldrive [0-9]+) \(.*?\)", item[3])
    if not match:
        return item
    logging.debug("_clean_boot_volume cleaning: {}".format(item))
    return item[0], item[1], item[2], match.group(1)


def _filter_ipmi_sensor_data(item):
    # This removes voltages, fan speeds, temperatures, power consumption e.g:
    # ["ipmi", "Power Meter", "value", "84"]
    if len(item) < 4:
        return item
    elif item[0] != "ipmi":
        return item
    elif item[2] != "value":
        return item
    logging.debug("_filter_ipmi_sensor_data removing: {}".format(item))


def _filter_generic_field(item):
    if len(item) < 4 or item[2] not in _cardiff_blacklist:
        return item
    logging.debug("_filter_generic_field removing: {}".format(item))
    return None


def _filter_serials(item):
    if len(item) < 4 or item[2] not in _serial_blacklist:
        return item
    logging.debug("_filter_serials removing: {}".format(item))
    return None


def _filter_benchmarks(item):
    if len(item) < 4 or not _benchmark_regex.match(item[2]):
        return item
    logging.debug("_filter_benchmarks removing: {}".format(item))
    return None


def _filter_memory(item):
    # If the memory is placed in different memory banks, but the same amount
    # of memory exists for each CPU this can cause grouping to fail.
    # E.g:
    # ["memory", "bank:10", "description",
    #  "DIMM DDR3 Synchronous Registered (Buffered) 1600 MHz (0.6 ns)"]
    # You could probably do some sort of fuzzy match, but for now keep it
    # simple and remove the values
    if len(item) < 4 or item[0] != "memory" or "bank" not in item[1]:
        return item
    logging.debug("_filter_memory removing: {}".format(item))


def _filter_memory_ipmi(item):
    # Needs filtering if memory in different banks, see _filter_memory
    if len(item) < 4 or item[0] != "ipmi" or "dimm" not in item[1].lower():
        return item
    logging.debug("_filter_memory removing: {}".format(item))


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Munges OpenStack Ironic introspection data to "
                    "a format accepted by cardiff")
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
        '--filter-benchmarks',
        dest="filter_benchmarks",
        default=False,
        action='store_true',
        help='Filter benchmarks from extra data')
    parser.add_argument(
        '--filter-serials',
        dest="filter_serials",
        default=False,
        action='store_true',
        help='Filter serial numbers')
    parser.add_argument(
        '--output-format',
        dest="output_format",
        choices=['json', 'eval'],
        nargs="?",
        default="json",
        help='Format to print the data as. eval will print a python evaluable '
             'string')
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stderr,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def clean(extrahw, filter_benchmarks=False, filter_serials=False):
    def _modify(item):
        steps = [
            _clean_kernel_cmdline,
            _filter_temperatures,
            _clean_boot_volume,
            _filter_memory,
            _filter_memory_ipmi,
            _filter_network,
            _filter_ipmi_sensor_data,
            _filter_generic_field,
        ]
        if filter_serials:
            steps.append(_filter_serials)
        if filter_benchmarks:
            steps.append(_filter_benchmarks)
        for step in steps:
            item = step(item)
            # A step may return None to remove the value
            if not item:
                break
        return item
    # modify then strip falsy values, operates on python data structure
    tuples = filter(lambda x: x, [_modify(tuple(xs)) for xs in extrahw])
    return sorted(list(tuples))

def internal_main(filter_benchmarks, filter_serials, output_format, data):
    result = clean(data, filter_benchmarks=filter_benchmarks,
                   filter_serials=filter_serials)
    if output_format == "eval":
        print(result)
    else:
        json.dump(result, sys.stdout, indent=4, separators=(',', ': '))

def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)
    data = json.load(sys.stdin)
    result = clean(data, filter_benchmarks=args.filter_benchmarks,
                   filter_serials=args.filter_serials)
    if args.output_format == "eval":
        print(result)
    else:
        json.dump(result, sys.stdout, indent=4, separators=(',', ': '))


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
