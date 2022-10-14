from tokenize import group
from pyvis.network import Network
from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd
import numpy as np


class Visualiser():
    fields = {
        "HPA Controller": ('#be1313', 0.1, 'curvedCW'),
        "HPA Disks": ("#f17474", 0.2, 'curvedCW'),
        "Megaraid Controller": ("#b59412", 0.3, 'curvedCW'),
        "Megaraid Disks": ("#f8f254", 0.4, 'curvedCW'),
        "AHCI Controller": ("#e67c0a", 0.5, 'curvedCW'),
        "System": ("#08c908", 0.1, 'curvedCCW'),
        "Firmware": ("#08b2c9", 0.2, 'curvedCCW'),
        "DDR Timing": ("#083fc9", 0.3, 'curvedCCW'),
        "Network Interfaces": ("#9208c9", 0.4, 'curvedCCW'),
        "Processors": ("#f74abe", 0.5, 'curvedCCW')
    }

    class Group():
        id = 0
        title = ""
        serials = []
        connections = {}

        def __init__(self, id, title, serials):
            self.id = id
            self.title = title
            self.serials = serials
            self.connections = {}

        def add_connection(self, label, target):
            if label not in self.connections:
                self.connections[label] = set()
                self.connections[label].add(target)
            else:
                self.connections[label].add(target)

    results = {}
    performance_stats = {}
    groups = []
    label_groups = {}
    output_dir = ""
    shared_fields = {"HPA Controller", "HPA Disks", "Megaraid Controller",
                     "Megaraid Disks", "AHCI Controller", "System", "Firmware",
                     "DDR Timing", "Network Interfaces", "Processors"}
    names_dict = {}

    overperf_groups = {}
    underperf_groups = {}
    varperf_groups = {}

    def add_item_varperf(self, item, group_number, mode, title):
        index = "%s %s" % (mode, title)
        if group_number not in self.varperf_groups:
            self.varperf_groups[group_number] = {index: item}
        else:
            self.varperf_groups[group_number][index] = item

    def add_item_overperf(self, item, group_number, mode, title):
        index = "%s %s" % (mode, title)
        if group_number not in self.overperf_groups:
            self.overperf_groups[group_number] = {index: item}
        else:
            self.overperf_groups[group_number][index] = item

    def add_item_underperf(self, item, group_number, mode, title):
        index = "%s %s" % (mode, title)
        if group_number not in self.underperf_groups:
            self.underperf_groups[group_number] = {index: item}
        else:
            self.underperf_groups[group_number][index] = item

    def __init__(self, output_dir, names_dict):
        self.output_dir = output_dir
        self.names_dict = names_dict

    def add_result(self, title, result):
        self.results[title] = result

    def print_results(self, file):
        for item in self.results:
            print(item, self.results[item], file=file)

    def add_group(self, id, title, serials):
        group = Visualiser.Group(id, title, serials)
        self.groups.append(group)

    def add_label_group(self, id, title, serials):
        group = Visualiser.Group(id, title, serials)
        self.groups.append(group)

    def compare_serials(self, group, other_group, systems, label):
        if (group.id != other_group.id
                and other_group.serials[0] not in systems):
            if label in self.shared_fields:
                self.shared_fields.remove(label)
            if label not in other_group.connections:
                if group.id < other_group.id:
                    group.add_connection(
                        label, other_group.id)
                else:
                    other_group.add_connection(
                        label, group.id)
            elif group.id not in other_group.connections[label]:
                if group.id < other_group.id:
                    group.add_connection(
                        label, other_group.id)
                else:
                    other_group.add_connection(
                        label, group.id)

    def extract_connections(self):
        for item in self.results:
            label = item
            for group in self.groups:
                for element in self.results[item]:
                    if eval(element) == set():
                        if label in self.shared_fields:
                            self.shared_fields.remove(label)
                    systems = self.results[item][element]
                    if group.serials[0] in systems:
                        for other_group in self.groups:
                            self.compare_serials(group, other_group, systems,
                                                 label)

    def print_connections(self, file):
        for group in self.groups:
            print(group.title, group.connections, file=file)

    def generate_subgraph(self, net, item):
        node_count = 0
        for element in self.results[item]:
            if eval(element) == set():
                return
            systems = self.results[item][element]
            title = ""
            group_ids = []
            for group in self.groups:
                if group.serials[0] in systems:
                    group_ids.append(str(group.id))
            if len(group_ids) == 1:
                label = "Group %s" % group_ids[0]
            else:
                label = "Groups %s" % ", ".join(group_ids)
            if len(systems) > 1:
                label += "\n%s systems" % len(systems)
            else:
                label += "\n1 system"

            for system in systems:
                title += "%s\n" % self.names_dict[system]
            net.add_node(
                n_id=node_count,
                label=label,
                title=title,
                shape='circle',
                font_size=10,
                color='grey',
                value=len(systems))
            node_count += 1

        for i in range(node_count):
            for j in range(node_count):
                if i < j:
                    net.add_edge(
                        source=i,
                        to=j,
                        width=3,
                        length=10,
                        label=item,
                        physics=False,
                        color=self.fields[item][0],
                        smooth={
                            'type': self.fields[item][2],
                            'roundness': self.fields[item][1]},
                        font={'size': 9, 'align': 'middle'},
                        arrows={'to': {'enabled': False}},
                        hoverWidth=0.05)

    def print_button_to_eof(self, field, file):
        print("<button onclick=\"location.href = '%s/%s_result.html';"
              "\" class=\"float-left submit-button\" >%s</button>" %
              (self.output_dir, field.replace(" ", "_"), field), file=file)

    def add_buttons(self):
        for field in self.fields:
            if (eval(list(self.results[field].keys())[0]) != set()
                    and len(self.results[field]) != 1):
                with open("%s/%s_result.html" % (self.output_dir,
                          field.replace(" ", "_")), "a") as f:
                    for other_field in self.fields:
                        if (eval(list(self.results[other_field].keys())[0]) !=
                                set() and len(self.results[other_field]) != 1):
                            self.print_button_to_eof(other_field, f)
                    self.print_button_to_eof("All", f)
        with open("%s/All_result.html" % self.output_dir, "a") as f:
            for field in self.fields:
                if (eval(list(self.results[field].keys())[0]) != set()
                        and len(self.results[field]) != 1):
                    self.print_button_to_eof(field, f)
            self.print_button_to_eof("All", f)

    def separate_networks(self):
        for field in self.fields:
            if eval(list(self.results[field].keys())[0]) != set():
                net = Network(directed=True, width="1200px", height="600px")

                self.generate_subgraph(net, field)

                net.toggle_physics(False)
                try:
                    net.show("%s/%s_result.html" %
                             (self.output_dir, field.replace(" ", "_")))
                except Exception as e:
                    print(e)

    def combined_network(self):
        net = Network(directed=True, width="1200px", height="600px")

        self.extract_connections()

        for group in self.groups:
            names = []
            for serial in group.serials:
                names.append("%s - %s" % (self.names_dict[serial], serial))
            label = group.title
            if len(group.serials) > 1:
                label += "\n%s systems" % len(group.serials)
            else:
                label += "\n1 system"
            net.add_node(
                n_id=group.id,
                label=label,
                shape='circle',
                title="\n".join(names),
                font_size=10,
                color='grey',
                value=len(group.serials))

        for group in self.groups:
            for connection in group.connections:
                info = group.connections[connection]
                count = 0
                width = 1.5
                font_size = 9
                for target in info:
                    net.add_edge(
                        source=group.id,
                        to=target,
                        width=width,
                        label=connection,
                        color=self.fields[connection][0],
                        smooth={
                            'type': self.fields[connection][2],
                            'roundness': self.fields[connection][1]},
                        font={'size': font_size, 'align': 'middle'},
                        arrows={'to': {'enabled': False}},
                        hoverWidth=0.05)
                    count += 1

        net.toggle_physics(False)
        try:
            net.show("%s/All_result.html" % self.output_dir)
        except Exception as e:
            print(e)

    def visualise_hardware(self):
        self.combined_network()
        self.separate_networks()
        self.add_buttons()

    def visualise_performance(self):
        app = Dash(__name__)

        output = [
            html.H1(children='Cardiff Performance Results'),

            html.Div(html.P([
                'This page is split into three sections:',
                html.Br(),
                '''1. High Variance - the group results where performance has
                 varied greatly.''',
                html.Br(),
                '''2. Curious Overperformance - results where individual nodes
                 have overperformed compared to the rest of the group.''',
                html.Br(),
                '''3. Curious Underperformance - results where individual nodes
                 have underperformed compared to the rest of the group.'''
            ])),
        ]

        i = 0
        output.append(html.H1(children='High Variance'))
        for group_number in self.varperf_groups:
            element = self.varperf_groups[group_number]
            for title in element:
                data = element[title]
                new_index = {}
                for serial in data.index:
                    if serial in self.names_dict:
                        new_index[serial] = self.names_dict[serial]
                data.rename(index=new_index, inplace=True)
                fig = px.box(data.round(2), title="Group %s %s" % (
                    group_number, title), orientation='h', hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        output.append(html.H1(children='Curious Overperformance'))
        for group_number in self.overperf_groups:
            element = self.overperf_groups[group_number]
            for title in element:
                data = element[title]
                new_index = {}
                for serial in data.index:
                    if serial in self.names_dict:
                        new_index[serial] = self.names_dict[serial]
                data.rename(index=new_index, inplace=True)
                fig = px.box(data.round(2), title="Group %s %s" % (
                    group_number, title), orientation='h', hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        output.append(html.H1(children='Curious Underperformance'))
        for group_number in self.underperf_groups:
            element = self.underperf_groups[group_number]
            for title in element:
                new_index = {}
                for serial in data.index:
                    if serial in self.names_dict:
                        new_index[serial] = self.names_dict[serial]
                data.rename(index=new_index, inplace=True)
                fig = px.box(data.round(2), title="Group %s %s" % (
                    group_number, title), orientation='h', hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        app.layout = html.Div(children=output)

        app.run_server(debug=True)

    def visualise(self):
        self.visualise_hardware()
        self.visualise_performance()
