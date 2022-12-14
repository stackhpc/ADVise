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

import collections
import pprint


class Machine:

    def __init__(self, name, value):
        self.name = name
        self.value = value


def compare(sets):
    machines = []
    for current_set in sets:
        my_string = repr(sets[current_set])
        machines.append(Machine(current_set, my_string))

    to_be_sorted = collections.defaultdict(list)
    for machine in machines:
        key = machine.value
        value = machine.name
        to_be_sorted[key].append(value)

    return dict(to_be_sorted)


def get_hosts_list_from_result(result):
    systems_list = []
    for element in result:
        current_set = set()
        for system in result[element]:
            current_set.add(system)
        systems_list.append(current_set)
    return systems_list


def print_systems_groups(systems_groups, global_params, vis):
    total_hosts = 0
    for system in systems_groups:
        total_hosts += len(system)
    print("The %d systems can be grouped in %d groups of "
          "identical hardware" % (total_hosts, len(systems_groups)))
    for system in systems_groups:
        print("Group %d (%d Systems)" % (
            systems_groups.index(system), len(system)))
        print("-> " + ', '.join(system))
        print()

    if "output_dir" in global_params.keys():
        with open("%s/results/_summary" % global_params["output_dir"],
                  "a") as f:
            print("The %d systems can be grouped in %d groups of "
                  "identical hardware" % (total_hosts, len(systems_groups)),
                  file=f)
            for system in systems_groups:
                print("Group %d (%d Systems)" % (
                    systems_groups.index(system), len(system)), file=f)
                print("-> " + ', '.join(system), file=f)
                vis.add_group(systems_groups.index(system),
                              "Group %s" % systems_groups.index(system),
                              list(system))


def print_groups(global_params, result, title):
    print("##### %s #####" % title)
    if "output_dir" in global_params.keys():
        with open("%s/results/_summary" % global_params["output_dir"],
                  "a") as f:
            print("##### %s #####" % title, file=f)
    groups_name = ""

    for element in result:
        group = result[element]
        group_name = title.strip().replace(" ", "_")

        if "output_dir" in global_params.keys():
            group_name = "%s/results/%s" % (global_params["output_dir"],
                                            group_name)

        for host in group:
            group_name = "%s_%s" % (group_name, host.strip())

        group_name = group_name[:100]

        groups_name = "%s '%s.def'" % (groups_name, group_name)
        print("%d identical systems :" % (len(group)))
        print(group)

        if "output_dir" in global_params.keys():
            with open("%s/results/_summary" % global_params["output_dir"],
                      "a") as f:
                print("%d identical systems :" % (len(group)), file=f)
                print(group, file=f)

        pprint.pprint(sorted(eval(element)))

        # But always save it to a file for diffing
        # if "output_dir" in global_params.keys():
        #     with open("%s.def" % group_name, "w") as fout:
        #         pprint.pprint(sorted(eval(element)), fout)
        # print()

    # if "output_dir" in global_params.keys():
    #     if len(result) > 1:
    #         output_file = "%s/%s.diff" % (global_params["output_dir"],
    #                                       title.strip().replace(" ", "_"))
    #         os.system("diff -ub --from-file %s > '%s'" %
    #                   (groups_name, output_file))
    #     else:
            # If no difference exists, we can kill the def files
            # for filename in glob.glob("%s/%s*.def" %
            #                           (global_params["output_dir"],
            #                            title.strip().replace(" ", "_"))):
            #     os.remove(filename)

    print("######" * 2 + "#" * len(title))
    if "output_dir" in global_params.keys():
        with open("%s/results/_summary" % global_params["output_dir"],
                  "a") as f:
            print("######" * 2 + "#" * len(title), file=f)


def compute_similar_hosts_list(systems_groups, new_groups):
    for group in new_groups:
        for systems_group in systems_groups:
            intersection = set.intersection(systems_group, group)
            if intersection:
                if len(intersection) < len(systems_group):
                    # We do have a partial match meaning we shall break
                    # the existing group in pieces
                    difference = set.difference(systems_group, group)
                    # The group we worked on doesn't exist anymore
                    # So let's delete it
                    systems_groups.remove(systems_group)

                    # Let's add the two sub groups generated by this split
                    systems_groups.append(intersection)
                    systems_groups.append(difference)
