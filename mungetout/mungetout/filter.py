#!/bin/python
from __future__ import print_function
import sys
from ipaddress import ip_address as IP
import json


def main():
    nodes_in = json.load(sys.stdin)
    nodes_out = []
    line = sys.argv[1]
    start_ip, end_ip = line.split('-')
    encoding = sys.stdout.encoding or "UTF-8"
    for node in nodes_in:
        if "ipmi_address" not in node["Driver Info"]:
            print("Skipping node: %s" % node["UUID"], file=sys.stderr)
            continue
        ip = IP(node["Driver Info"]["ipmi_address"].decode(encoding))
        if IP(start_ip.decode(encoding)) <= ip <= IP(end_ip.decode(encoding)):
            nodes_out += [node]
    print(json.dumps(nodes_out))


if __name__ == "__main__":
    main()
