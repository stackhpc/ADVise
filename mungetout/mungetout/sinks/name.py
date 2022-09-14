import sys
import json
import subprocess
import shlex
import csv


def main():
    nodes_in = json.load(sys.stdin)
    mappings = {}

    prefix = None

    if len(sys.argv) >= 3:
        prefix = sys.argv[2]

    # e.g asset map
    # "node1","10.64.3.246"
    # "node2","10.64.3.247"

    with open(sys.argv[1]) as f:
        rows = csv.reader(f, delimiter=',', quotechar='"')
        for row in rows:
            if not row:
                continue
            mappings[row[1]] = row[0]
    for node in nodes_in:
        addr = node["Driver Info"]["ipmi_address"]
        if addr not in mappings:
            print("WARNING: skipping %s" % addr)
            continue
        name = "%s" % mappings[addr]
        if prefix:
            name = prefix + name
        cmd = "openstack baremetal node set --name %s %s" % \
              (name, node["UUID"])
        print(cmd)
        subprocess.check_output(shlex.split(cmd))


if __name__ == "__main__":
    main()
