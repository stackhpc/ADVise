#  Copyright (C) 2013-2015 eNovance SAS <licensing@enovance.com>
#  Author: Erwan Velu  <erwan@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import fnmatch
import math
import os


class Levels:
    INFO = 1 << 0
    WARNING = 1 << 1
    ERROR = 1 << 2
    SUMMARY = 1 << 3
    DETAIL = 1 << 4
    message = {INFO: 'INFO', WARNING: 'WARNING',
               ERROR: 'ERROR', SUMMARY: 'SUMMARY',
               DETAIL: 'DETAIL'}


# Default level is to print everything
PRINTLEVEL = Levels.INFO | Levels.WARNING | Levels.ERROR


def write_gnuplot_file(filename, index, value):
    if not os.path.isfile(filename):
        with open(filename, "a") as myfile:
            if math.isnan(value) is False:
                myfile.write("%d %.2f\n" % (index, value))
    else:
        new_lines = []
        with open(filename, "r") as gnuplotfile:
            lines = (line.rstrip() for line in gnuplotfile)
            found = False
            for line in lines:
                if int(line.split()[0].strip()) == index:
                    found = True
                    new_lines.append("%s %.2f" % (line.strip(), value))
                else:
                    new_lines.append("%s" % (line.strip()))
            if found is False:
                new_lines.append("%d %.2f" % (index, value))
        with open(filename, "w") as gnuplotfile:
            gnuplotfile.write('\n'.join(new_lines) + '\n')


def do_print(mode, level, string, *args):
    global PRINTLEVEL
    if level & int(PRINTLEVEL) != level:
        return
    final_string = "%-34s: %-8s: " + string
    final_args = (mode, Levels.message[int(level)])
    final_args += args
    print(final_string % final_args)


def find_file(path, pattern):
    health_data_file = []
    # For all the local files
    for my_file in os.listdir(path):
        # If the file math the regexp
        if fnmatch.fnmatch(my_file, pattern):
            # Let's consider this file
            health_data_file.append(path + "/" + my_file)

    return health_data_file


def get_item(output, item, item1, item2, item3):
    if item[0] == item1 and item[1] == item2 and item[2] == item3:
        output[item3] = item[3]
        return
    return


def dump_item(output, item, item1, item2, item3):
    if item[0] == item1 and item[1] == item2 and item[2] == item3:
        output.add(item[3])
        return
    return


def get_hosts_list(bench_values, unique_id):
    systems = set()
    for bench in bench_values:
        for line in bench:
            dump_item(systems, line, 'system', 'product', unique_id)

    return systems


# Extract a sub element from the results
def find_sub_element(bench_values, unique_id, element, hosts=set()):
    systems = []
    for bench in bench_values:
        system = {unique_id: ''}
        stuff = []
        for line in bench:
            get_item(system, line, 'system', 'product', unique_id)
            if element in line[0]:
                stuff.append(line)

        if not hosts or system[unique_id] in hosts:
            system[element] = stuff
            systems.append(system)

    return systems
