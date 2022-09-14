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


# This function is trying to find the closest CPU performance for a given model
def get_generic_cpu_perf(cpu_struct, cpu_type):
    # Let's find in the cpu already exist in the list of known CPUs
    for cpu_list in sorted(cpu_struct, reverse=True):
        if cpu_list in cpu_type:
            return cpu_struct[cpu_list]

    # Unless, retry by shortening the string by one word
    if len(cpu_type.split()) > 1:
        shorten_cpu_type = cpu_type.rsplit(' ', 1)[0]
        return get_generic_cpu_perf(cpu_struct, shorten_cpu_type)

    return 0


def get_loops_per_sec_cpu_min_perf(cpu_type):
    cpu_struct = {
        "Intel(R) Xeon(R) CPU": 300,
        "Intel(R) Xeon(R) CPU X5675 @ 3.07GHz": 680,
        "Intel(R) Xeon(R) CPU E5-2650 0 @ 2.00GHz": 450,
        "Intel(R) Xeon(R) CPU E5-2630 0 @ 2.30GHz": 460,
        "Intel(R) Xeon(R) CPU E5-2650": 420,
        "Intel(R) Xeon(R) CPU E5": 400}

    return get_generic_cpu_perf(cpu_struct, cpu_type)


def get_bogomips_cpu_min_perf(cpu_type):
    cpu_struct = {
        "Intel(R) Xeon(R) CPU": 3000,
        "Intel(R) Xeon(R) CPU X5675 @ 3.07GHz": 6130,
        "Intel(R) Xeon(R) CPU E5-2650 0 @ 2.00GHz": 3900,
        "Intel(R) Xeon(R) CPU E5-2630 0 @ 2.30GHz": 4580,
        "Intel(R) Xeon(R) CPU E5-2650": 3900,
        "Intel(R) Xeon(R) CPU E5": 3500}

    return get_generic_cpu_perf(cpu_struct, cpu_type)


def get_cpu_min_perf(test_type, cpu_type):
    if "loops_per_sec" in test_type:
        return get_loops_per_sec_cpu_min_perf(cpu_type)

    if "bogomips" in test_type:
        return get_bogomips_cpu_min_perf(cpu_type)

    return 0
