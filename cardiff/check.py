#!/usr/bin/env python
#
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

import re
import sys

from dash import Dash, html, dcc
import plotly.express as px

import numpy
from pandas import DataFrame
from pandas import Series

from cardiff import compare_sets, visualise
from cardiff import perf_cpu_tables
from cardiff import utils


def search_item(system_list, unique_id, item, regexp, exclude_list=[],
                include_list=[], override_list=[]):
    sets = {}
    for system in system_list:
        sets[system[unique_id]] = set()
        current_set = sets[system[unique_id]]
        for stuff in system[item]:
            match = re.match(regexp, stuff[1])
            if match:
                shall_be_added = False

                # If we have an include_list, only those shall be used
                # So everything is exclude by default
                if include_list:
                    shall_be_excluded = True
                else:
                    shall_be_excluded = False

                for include in include_list:
                    if include in stuff[2]:
                        # If something is part of the include list
                        # It is no more excluded
                        shall_be_excluded = False

                for exclude in exclude_list:
                    if exclude in stuff[2]:
                        shall_be_excluded = True

                for override in override_list:
                    if override in stuff[2]:
                        shall_be_added = True

                if (shall_be_excluded is False) or (shall_be_added is True):
                    current_set.add(tuple(stuff))
    return sets


def physical_hpa_disks(system_list, unique_id):
    sets = search_item(system_list, unique_id, "disk", r"(\d+)I:(\d+):(\d+)",
                       ['current_temperature_(c)',
                        'maximum_temperature_(c)',
                        'serial_number'])
    return compare_sets.compare(sets)


def physical_megaraid_disks(system_list, unique_id):
    sets = search_item(system_list, unique_id, "pdisk", r"disk(\d+)",
                       ['Wwn', 'SasAddress', 'DriveTemperature',
                        'InquiryData[2]', 'DeviceId'])
    return compare_sets.compare(sets)


def logical_disks(system_list, unique_id):
    sets = search_item(system_list, unique_id, "disk", r"[a-z]d(\S+)",
                       ['simultaneous', 'standalone', 'id', 'serial_number',
                        'SMART/'], [],
                       ['when_failed', 'vendor', 'product', 'health'])
    return compare_sets.compare(sets)


def ahci(system_list, unique_id):
    sets = search_item(system_list, unique_id, "ahci", r".*")
    return compare_sets.compare(sets)


def ipmi(system_list, unique_id):
    sets = search_item(system_list, unique_id, "ipmi",
                       "(?!(.*Temp$|.*RPM$)).*",
                       ['mac-address', 'ip-address'])
    return compare_sets.compare(sets)


def compute_deviance_percentage(item, df):
    # If we have a single item
    # checking the variance is useless
    if df[item].count() == 1:
        return 0
    return df[item].std() / df[item].mean() * 100


def print_detail(detail_options, details, df, matched_category):
    if (utils.PRINTLEVEL & utils.Levels.DETAIL) != utils.Levels.DETAIL:
        return
    if df.loc[details]:
        print()
        print("%-34s: %-8s: %s" % (matched_category[0],
                                   utils.Levels.message[utils.PRINTLEVEL],
                                   detail_options['item']))
        print(df.loc[details])


def prepare_detail(detail_options, group_number, category, item, details,
                   matched_category_to_save):
    if (utils.PRINTLEVEL & utils.Levels.DETAIL) != utils.Levels.DETAIL:
        return

    matched_group = ''
    matched_category = ''
    matched_item = ''

    if detail_options['group'] == str(group_number):
        matched_group = str(group_number)
    elif re.search(detail_options['group'], str(group_number)) is not None:
        matched_group = re.search(detail_options['group'],
                                  str(group_number)).group()

    if detail_options['category'] in category:
        matched_category = category
    elif re.search(detail_options['category'], category) is not None:
        matched_category = re.search(detail_options['category'],
                                     category).group()

    if detail_options['item'] in item:
        matched_item = item
    elif re.search(detail_options['item'], item) is not None:
        matched_item = re.search(detail_options['item'], item).group()

    if matched_group and matched_category and matched_item:
        details.append(matched_item)
        if matched_category not in matched_category_to_save:
            matched_category_to_save.append(matched_category)
        return matched_category

    return ""


def network_perf(system_list, unique_id, group_number, detail_options,
                 global_params, names_dict, vis, rampup_value=0, current_dir=""):
    have_net_data = False
    modes = ['bandwidth', 'requests_per_sec']
    sets = search_item(system_list, unique_id, "network", r"(.*)", [], modes)
    for mode in sorted(modes):
        results = {}
        for system in sets:
            # ignore empty sets, e.g sets = {'CZ3222KDMF': set([])}
            if not sets[system]:
                continue
            net = []
            series = []
            global_perf = 0.0
            for perf in sets[system]:
                if perf[1] == mode:
                    if not perf[1] in net:
                        net.append(perf[1])
                    global_perf = global_perf + float(perf[3])

            series.append(global_perf)
            results[system] = Series(series, dtype='float64', index=net)

        # No need to continue if no network drive data in this benchmark
        if not results:
            continue

        df = DataFrame(results)
        details = []
        matched_category = []
        for net in df.transpose().columns:
            if have_net_data is False:
                print()
                print("Group %d : Checking network disks perf" % group_number)
                with open("%s/_perf_summary" % global_params["output_dir"], "a") as f:
                    print(file=f)
                    print("Group %d : Checking network disks perf" %
                          group_number, file=f)
                have_net_data = True
            consistent = []
            curious = []
            unstable = []
            # How much the variance could be far from the average (in %)
            tolerance_max = 15
            tolerance_min = 2

            print_perf(tolerance_min, tolerance_max, df.transpose()[net], df,
                       mode, net, global_params, names_dict, vis, group_number, consistent,
                       curious, unstable, "", rampup_value, current_dir)
            if mode == 'bandwidth':
                unit = "MB/sec"
            else:
                unit = "RRQ/sec"
            prepare_detail(detail_options, group_number, mode, net, details,
                           matched_category)
            print_summary("%-30s %s" % (mode, net), consistent, "consistent",
                          unit, df)
            print_summary("%-30s %s" % (mode, net), curious, "curious", unit,
                          df)
            print_summary("%-30s %s" % (mode, net), unstable, "unstable",
                          unit, df)

        print_detail(detail_options, details, df, matched_category)


def logical_disks_perf(system_list, unique_id, group_number, detail_options,
                       global_params, names_dict, vis, perf_unit, rampup_value=0,
                       current_dir=""):
    have_disk_data = False
    sets = search_item(system_list, unique_id, "disk", r"[a-z]d(\S+)", [],
                       ['simultaneous', 'standalone'])
    modes = []

    # Searching for modes ran in this benchmark
    for system in sets:
        for perf in sets[system]:
            if perf[2] not in modes and perf_unit in perf[2]:
                modes.append(perf[2])

    for mode in sorted(modes):
        results = {}
        for system in sets:
            disks = []
            series = []
            for perf in sets[system]:
                if perf[2] == mode:
                    if not perf[1] in disks:
                        disks.append(perf[1])
                    series.append(int(round(float(perf[3]))))
            results[system] = Series(series, dtype='float64', index=disks)

        df = DataFrame(results)
        details = []
        matched_category = []
        for disk in df.transpose().columns:
            if have_disk_data is False:
                print()
                print("Group %d : Checking logical disks perf" % group_number)
                with open("%s/_perf_summary" % global_params["output_dir"], "a") as f:
                    print(file=f)
                    print("Group %d : Checking logical disks perf" %
                          group_number, file=f)
                have_disk_data = True
            consistent = []
            curious = []
            unstable = []
            # How much the variance could be far from the average (in %)
            tolerance_max = 10
            tolerance_min = 2
            # In random mode, the variance could be higher as
            # we cannot insure the distribution pattern was similar
            if "rand" in mode:
                tolerance_min = 5
                tolerance_max = 15

            print_perf(tolerance_min, tolerance_max, df.transpose()[disk], df,
                       mode, disk, global_params, names_dict, vis, group_number, consistent,
                       curious, unstable, "-%s" % perf_unit, rampup_value,
                       current_dir)

            prepare_detail(detail_options, group_number, mode, disk, details,
                           matched_category)
            print_summary("%-30s %s" % (mode, disk), consistent, "consistent",
                          perf_unit, df)
            print_summary("%-30s %s" % (mode, disk), curious, "curious",
                          perf_unit, df)
            print_summary("%-30s %s" % (mode, disk), unstable, "unstable",
                          perf_unit, df)

        print_detail(detail_options, details, df, matched_category)


def hpa(system_list, unique_id):
    sets = search_item(system_list, unique_id, "hpa", "(.*)",
                       ['cache_serial_number', 'serial_number'])
    return compare_sets.compare(sets)


def megaraid(system_list, unique_id):
    sets = search_item(system_list, unique_id, "megaraid", "(.*)",
                       ['SerialNo', 'SasAddress', 'ControllerTemperature',
                        'VendorSpecific', 'RocTemperature'])
    return compare_sets.compare(sets)


def systems(system_list, unique_id):
    sets = search_item(system_list, unique_id, "system", "(.*)",
                       ['serial', 'uuid'])
    return compare_sets.compare(sets)


def firmware(system_list, unique_id):
    sets = search_item(system_list, unique_id, "firmware", "(.*)")
    return compare_sets.compare(sets)


def memory_timing(system_list, unique_id):
    sets = search_item(system_list, unique_id, "memory", "DDR(.*)")
    return compare_sets.compare(sets)


def memory_banks(system_list, unique_id):
    sets = search_item(system_list, unique_id, "memory", "bank(.*)",
                       ['serial'])
    return compare_sets.compare(sets)


def network_interfaces(system_list, unique_id):
    sets = search_item(system_list, unique_id, "network", "(.*)",
                       ['serial', 'ipv4'])
    return compare_sets.compare(sets)


def cpu(system_list, unique_id):
    sets = search_item(system_list, unique_id, "cpu", "(.*)",
                       ['bogomips', 'loops_per_sec', 'bandwidth',
                        'cache_size', '/temperature'])
    return compare_sets.compare(sets)


def print_perf(tolerance_min, tolerance_max, item, df, mode, title,
               global_params, names_dict, vis, group_number, consistent=None, curious=None,
               unstable=None, sub_graph="", rampup_value=0, current_dir=""):
    # Tolerance_min represents the min where variance
    # shall be considered (in %)
    # Tolerance_max represents the maximum that variance
    # represent regarding the average (in %)

    variance_group = item.std()
    mean_group = item.mean()
    sum_group = item.sum()
    min_group = mean_group - 2 * variance_group
    max_group = mean_group + 2 * variance_group

    utils.do_print(mode, utils.Levels.INFO,
                   "%-12s : Group performance : min=%8.2f, mean=%8.2f, "
                   "max=%8.2f, stddev=%8.2f", title, item.min(),
                   mean_group, item.max(), variance_group)

    variance_tolerance = compute_deviance_percentage(title, df.transpose())

    if (rampup_value > 0) and (current_dir):
        utils.write_gnuplot_file(current_dir + "/deviance.plot",
                                 rampup_value, variance_group)
        utils.write_gnuplot_file(current_dir + "/deviance_percentage.plot",
                                 rampup_value, variance_tolerance)
        utils.write_gnuplot_file(current_dir + "/mean%s.plot" % sub_graph,
                                 rampup_value, mean_group)
        utils.write_gnuplot_file(current_dir + "/sum%s.plot" % sub_graph,
                                 rampup_value, sum_group)

    if variance_tolerance > tolerance_max:
        utils.do_print(mode, utils.Levels.ERROR,
                       "%-12s : Group's variance is too important : %7.2f%% "
                       "of %7.2f whereas limit is set to %3.2f%%", title,
                       variance_tolerance, mean_group, tolerance_max)
        utils.do_print(mode, utils.Levels.ERROR,
                       "%-12s : Group performance : UNSTABLE", title)
        with open("%s/_perf_summary" % global_params["output_dir"], "a") as f:
            orig_stdout = sys.stdout
            sys.stdout = f
            utils.do_print(mode, utils.Levels.ERROR,
                           "%-12s : Group's variance is too important : "
                           "%7.2f%% of %7.2f whereas limit is set to %3.2f%%",
                           title, variance_tolerance, mean_group,
                           tolerance_max)
            utils.do_print(mode, utils.Levels.ERROR,
                           "%-12s : Group performance : UNSTABLE", title)
            sys.stdout = orig_stdout
        for host in df.columns:
            if host not in curious:
                unstable.append(host)

        if vis:
            vis.add_item_varperf(item, group_number, mode, title)
    else:
        curious_performance = False
        for host in df.columns:
            if (("loops_per_sec") in mode) or ("bogomips" in mode):
                mean_host = df[host][title].mean()
            else:
                mean_host = df[host].mean()
            # If the variance is very low, don't try to find the black sheep
            if variance_tolerance > tolerance_min:
                if mean_host > max_group:
                    if vis:
                        vis.add_item_overperf(item, group_number, mode, title,
                                              names_dict[host], mean_host)
                    curious_performance = True
                    percent_above = 100 * (mean_host - max_group) / max_group
                    utils.do_print(
                        mode, utils.Levels.WARNING,
                        "%-12s : %s : Curious overperformance  %7.2f : "
                        "min_allow_group = %.2f, mean_group = %.2f "
                        "max_allow_group = %.2f, "
                        "%3.2f%% above max", title, names_dict[host],
                        mean_host, min_group, mean_group, max_group,
                        percent_above)
                    with open("%s/_perf_summary" % global_params["output_dir"],
                              "a") as f:
                        orig_stdout = sys.stdout
                        sys.stdout = f
                        utils.do_print(
                            mode, utils.Levels.WARNING,
                            "%-12s : %s : Curious overperformance  %7.2f : "
                            "min_allow_group = %.2f, mean_group = %.2f "
                            "max_allow_group = %.2f, "
                            "%3.2f%% above max", title, names_dict[host],
                            mean_host, min_group, mean_group, max_group,
                            percent_above)
                        sys.stdout = orig_stdout
                    if host not in curious:
                        curious.append(host)
                        if host in consistent:
                            consistent.remove(host)
                elif mean_host < min_group:
                    if vis:
                        vis.add_item_underperf(item, group_number, mode, title,
                                               names_dict[host], mean_host)
                    curious_performance = True
                    percent_below = 100 * (min_group - mean_host) / min_group
                    utils.do_print(
                        mode, utils.Levels.WARNING,
                        "%-12s : %s : Curious underperformance %7.2f : "
                        "min_allow_group = %.2f, mean_group = %.2f "
                        "max_allow_group = %.2f, "
                        "%3.2f%% below min", title, names_dict[host],
                        mean_host, min_group, mean_group, max_group,
                        percent_below)
                    with open("%s/_perf_summary" % global_params["output_dir"],
                              "a") as f:
                        orig_stdout = sys.stdout
                        sys.stdout = f
                        utils.do_print(
                            mode, utils.Levels.WARNING,
                            "%-12s : %s : Curious underperformance %7.2f : "
                            "min_allow_group = %.2f, mean_group = %.2f "
                            "max_allow_group = %.2f, "
                            "%3.2f%% below min", title, names_dict[host],
                            mean_host, min_group, mean_group, max_group,
                            percent_below)
                        sys.stdout = orig_stdout
                    if host not in curious:
                        curious.append(host)
                        if host in consistent:
                            consistent.remove(host)
                else:
                    if (host not in consistent) and (host not in curious):
                        consistent.append(host)
            else:
                if (host not in consistent) and (host not in curious):
                    consistent.append(host)

        unit = " "
        if "Effi." in title:
            unit = "%"
        if curious_performance is False:
            utils.do_print(
                mode, utils.Levels.INFO,
                "%-12s : Group performance = %7.2f %s : CONSISTENT",
                title, mean_group, unit)
        else:
            utils.do_print(mode, utils.Levels.WARNING,
                           "%-12s : Group performance = %7.2f %s : SUSPICIOUS",
                           title, mean_group, unit)


def print_summary(mode, array, array_name, unit, df, item_value=None):
    if (utils.PRINTLEVEL & utils.Levels.SUMMARY) and array:
        result = []
        before = ""
        after = ""
        RED = "\033[1;31m"
        ORANGE = "\033[1;33m"
        WHITE = "\033[1;m"
        GREEN = "\033[1;32m"

        for host in array:
            result.append(df[host].sum())
        if "unstable" in array_name:
            before = RED
            after = WHITE
        if "curious" in array_name:
            before = ORANGE
            after = WHITE

        mean = numpy.mean(result)
        perf_status = ""
        if array_name == "consistent":
            if item_value is not None:
                if mode in ("loops_per_sec", "bogomips"):
                    min_cpu_perf = perf_cpu_tables.get_cpu_min_perf(mode,
                                                                    item_value)
                    if min_cpu_perf == 0:
                        perf_status = (": %(orange)sNO PERF ENTRY IN DB"
                                       "%(white)s for %(item_value)s" %
                                       {'orange': ORANGE,
                                        'white': WHITE,
                                        'item_value': item_value})
                    elif mean >= min_cpu_perf:
                        perf_status = (": %(green)sPERF OK%(white)s" %
                                       {'green': GREEN,
                                        'white': WHITE})
                    else:
                        perf_status = (": %(red)sPERF FAIL%(white)s as min "
                                       "perf should have been : "
                                       "%(min_cpu_perf)s" %
                                       {'red': RED,
                                        'white': WHITE,
                                        'min_cpu_perf': str(min_cpu_perf)})

        msg = ("%(array_length)3d %(before)s%(array_name)-10s%(after)s hosts "
               "with %(mean)8.2f %(unit)-4s as average value and "
               "%(result)8.2f standard deviation %(perf_status)s" %
               {'array_length': len(array),
                'before': before,
                'array_name': array_name,
                'after': after,
                'mean': mean,
                'unit': unit,
                'result': numpy.std(result),
                'perf_status': perf_status})

        utils.do_print(mode, utils.Levels.SUMMARY, msg)


def cpu_perf(system_list, unique_id, group_number, detail_options,
             global_params, names_dict, vis, rampup_value=0, current_dir=""):
    have_cpu_data = False
    host_cpu_list = search_item(system_list, unique_id, "cpu", "(.*)", [],
                                ['product'])
    host_cpu_number = search_item(system_list, unique_id, "cpu",
                                  "(.*logical.*)", [], ['number'])
    core_counts = 1
    for host in host_cpu_number:
        for item in host_cpu_number[host]:
            core_counts = item[3]
            break

    cpu_type = ''
    for host in host_cpu_list:
        for item in host_cpu_list[host]:
            cpu_type = item[3]
            break

    modes = ['bogomips', 'loops_per_sec']
    sets = search_item(system_list, unique_id, "cpu", "(.*)", [], modes)
    global_perf = dict()
    for mode in sorted(modes):
        results = {}
        for system in sets:
            cpu = []
            series = []
            found_data = False
            for perf in sets[system]:
                if perf[2] == mode:
                    # We shall split individual cpu benchmarking from
                    # the global one
                    if "_" in perf[1]:
                        if not perf[1] in cpu:
                            cpu.append(perf[1])
                        series.append(float(perf[3]))
                        found_data = True
                    elif "loops_per_sec" in mode:
                        global_perf[system] = float(perf[3])
                        found_data = True

            if found_data is True:
                # If no series are populated, it means that a single
                # "All CPU" run was done
                # If so, let's create a single run value
                if not series:
                    series.append(global_perf[system])
                    cpu.append("logical")

                results[system] = Series(series, dtype='float64', index=cpu)

        # No need to continue if no CPU data in this benchmark
        if not results:
            continue

        df = DataFrame(results)
        consistent = []
        curious = []
        unstable = []
        details = []
        matched_category = []

        for cpu in df.transpose().columns:
            if have_cpu_data is False:
                print()
                print("Group %d : Checking CPU perf" % group_number)
                with open("%s/_perf_summary" % global_params["output_dir"],
                          "a") as f:
                    print(file=f)
                    print("Group %d : Checking CPU perf" %
                          group_number, file=f)
                have_cpu_data = True
            print_perf(2, 7, df.transpose()[cpu], df, mode, cpu, global_params,
                       names_dict, vis, group_number, consistent, curious,
                       unstable, "", rampup_value, current_dir)
            prepare_detail(detail_options, group_number, mode, cpu, details,
                           matched_category)

        print_detail(detail_options, details, df, matched_category)

        print_summary(mode, consistent, "consistent", "", df, cpu_type)
        print_summary(mode, curious, "curious", "", df)
        print_summary(mode, unstable, "unstable", "", df)

        if mode == "loops_per_sec":
            efficiency = {}
            mode_text = 'CPU Effi.'
            consistent = []
            curious = []
            unstable = []
            details = []
            matched_category = []

            for system in sets:
                host_efficiency_full_load = []
                host_perf = (df[system].sum() *
                             (int(core_counts) / df[system].count()))
                host_efficiency_full_load.append(
                    global_perf[system] / host_perf * 100)
                efficiency[system] = Series(host_efficiency_full_load,
                                            dtype='float64', index=[mode_text])

            cpu_eff = DataFrame(efficiency)
            print_perf(1, 2, cpu_eff.transpose()[mode_text], cpu_eff, mode,
                       mode_text, global_params, names_dict, vis, group_number,
                       consistent, curious, unstable)
            prepare_detail(detail_options, group_number, mode, mode_text,
                           details, matched_category)

            print_detail(detail_options, details, cpu_eff, matched_category)
            print_summary("CPU Efficiency", consistent, "consistent", '%',
                          cpu_eff)
            print_summary("CPU Efficiency", curious, "curious", '%', cpu_eff)
            print_summary("CPU Efficiency", unstable, "unstable", '%', cpu_eff)


def memory_perf(system_list, unique_id, group_number, detail_options,
                global_params, names_dict, vis, rampup_value=0,
                current_dir=""):
    have_memory_data = False
    modes = ['1K', '4K', '1M', '16M', '128M', '256M', '1G', '2G']
    sets = search_item(system_list, unique_id, "cpu", "(.*)", [], modes)
    for mode in sorted(modes):
        real_mode = "Memory benchmark %s" % mode
        results = {}
        threaded_perf = dict()
        forked_perf = dict()
        for system in sets:
            memory = []
            series = []
            found_data = ""
            threaded_perf[system] = 0
            forked_perf[system] = 0
            for perf in sets[system]:
                if mode in perf[2]:
                    # We shall split individual cpu benchmarking from
                    # the global one
                    if ("logical_" in perf[1] and
                            ("bandwidth_%s" % mode) in perf[2]):
                        if not perf[1] in memory:
                            memory.append(perf[1])
                        series.append(float(perf[3]))
                    elif "threaded_bandwidth_%s" % mode in perf[2]:
                        threaded_perf[system] = float(perf[3])
                        found_data = float(perf[3])
                    elif "forked_bandwidth_%s" % mode in perf[2]:
                        forked_perf[system] = float(perf[3])
                        found_data = float(perf[3])

            if found_data:
                # If no series are populated, it means that a single "All CPU"
                # run was done
                # If so, let's create a single run value
                if not series:
                    series.append(found_data)
                    memory.append("logical")

            results[system] = Series(series, dtype='float64', index=memory)

        # No need to continue if no Memory data in this benchmark
        if not results:
            continue

        consistent = []
        curious = []
        unstable = []
        details = []
        matched_category = ''

        df = DataFrame(results)
        for memory in df.transpose().columns:
            if have_memory_data is False:
                print()
                print("Group %d : Checking Memory perf" % group_number)
                with open("%s/_perf_summary" % global_params["output_dir"],
                          "a") as f:
                    print(file=f)
                    print("Group %d : Checking Memory perf" %
                          group_number, file=f)
                have_memory_data = True

            print_perf(1, 7, df.transpose()[memory], df, real_mode, memory,
                       global_params, names_dict, vis, group_number,
                       consistent, curious, unstable, "", rampup_value,
                       current_dir)
            matched_category = []
            prepare_detail(detail_options, group_number, mode, memory,
                           details, matched_category)

        print_detail(detail_options, details, df, matched_category)
        print_summary(mode, consistent, "consistent", "MB/s", df)
        print_summary(mode, curious, "curious", "MB/s", df)
        print_summary(mode, unstable, "unstable", "MB/s", df)

        for bench_type in ["threaded", "forked"]:
            efficiency = {}
            have_forked_or_threaded = False
            if "threaded" in bench_type:
                mode_text = "Thread effi."
            else:
                mode_text = "Forked Effi."
            for system in sets:
                host_efficiency_full_load = []
                host_perf = df[system].sum()
                if (host_perf > 0 and threaded_perf[system] > 0 and
                        forked_perf[system] > 0):
                    have_forked_or_threaded = True
                    if "threaded" in bench_type:
                        host_efficiency_full_load.append(
                            threaded_perf[system] / host_perf * 100)
                    else:
                        host_efficiency_full_load.append(
                            forked_perf[system] / host_perf * 100)

                    efficiency[system] = Series(host_efficiency_full_load,
                                                dtype='float64',
                                                index=[mode_text])

            details = []
            memory_eff = DataFrame(efficiency)
            if have_forked_or_threaded is True:
                consistent = []
                curious = []
                unstable = []

                for memory in memory_eff.transpose().columns:
                    print_perf(2, 10, memory_eff.transpose()[memory],
                               memory_eff, real_mode, memory, global_params,
                               names_dict, vis, group_number, consistent,
                               curious, unstable)
                    matched_category = []
                    prepare_detail(detail_options, group_number, mode,
                                   memory, details, matched_category)

                # Let's pad if its a thread or forked effi in addition
                # of the block size
                if matched_category:
                    matched_category[0] += " " + mode_text

                print_detail(detail_options, details, memory_eff,
                             matched_category)
                print_summary(mode + " " + mode_text, consistent,
                              "consistent", "%", memory_eff)
                print_summary(mode + " " + mode_text, curious,
                              "curious", "%", memory_eff)
                print_summary(mode + " " + mode_text, unstable,
                              "unstable", "%", memory_eff)
            else:
                utils.do_print(real_mode, utils.Levels.WARNING,
                               "%-12s : Benchmark not run on this group",
                               mode_text)
