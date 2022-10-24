from pyvis.network import Network
from dash import Dash, html, dcc, dash_table, Input, Output
import plotly.express as px
import pickle
import sys
import os
import argparse
import pandas as pd


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
    output_dir = ""
    shared_fields = {"HPA Controller", "HPA Disks", "Megaraid Controller",
                     "Megaraid Disks", "AHCI Controller", "System", "Firmware",
                     "DDR Timing", "Network Interfaces", "Processors"}
    names_dict = {}
    networks = {}

    overperf_groups = {}
    underperf_groups = {}
    varperf_groups = {}

    table_data = {}

    def save_data(self):
        filepath = "%s/data/vis" % self.output_dir
        if not os.path.exists("%s/data/vis" % self.output_dir):
            os.mkdir("%s/data/vis" % self.output_dir)
        with open("%s/results.pkl" % filepath, "wb") as f:
            pickle.dump(self.results, f)
        with open("%s/performance_stats.pkl" % filepath, "wb") as f:
            pickle.dump(self.performance_stats, f)
        with open("%s/groups.pkl" % filepath, "wb") as f:
            pickle.dump(self.groups, f)
        with open("%s/names_dict.pkl" % filepath, "wb") as f:
            pickle.dump(self.names_dict, f)
        with open("%s/overperf_groups.pkl" % filepath, "wb") as f:
            pickle.dump(self.overperf_groups, f)
        with open("%s/underperf_groups.pkl" % filepath, "wb") as f:
            pickle.dump(self.underperf_groups, f)
        with open("%s/varperf_groups.pkl" % filepath, "wb") as f:
            pickle.dump(self.varperf_groups, f)

    def load_data(self):
        filepath = "%s/data/vis" % self.output_dir
        with open("%s/results.pkl" % filepath, "rb") as f:
            self.results = pickle.load(f)
        with open("%s/performance_stats.pkl" % filepath, "rb") as f:
            self.performance_stats = pickle.load(f)
        with open("%s/groups.pkl" % filepath, "rb") as f:
            self.groups = pickle.load(f)
        with open("%s/names_dict.pkl" % filepath, "rb") as f:
            self.names_dict = pickle.load(f)
        with open("%s/overperf_groups.pkl" % filepath, "rb") as f:
            self.overperf_groups = pickle.load(f)
        with open("%s/underperf_groups.pkl" % filepath, "rb") as f:
            self.underperf_groups = pickle.load(f)
        with open("%s/varperf_groups.pkl" % filepath, "rb") as f:
            self.varperf_groups = pickle.load(f)

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

    def __init__(self, output_dir):
        self.output_dir = output_dir

    def add_result(self, title, result):
        self.results[title] = result

    def add_group(self, id, title, serials):
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

    def record_networks(self):
        with open("%s/results/All_result.html" % self.output_dir, "r") as f:
            self.networks["All"] = f.read()
        for field in self.fields:
            if (eval(list(self.results[field].keys())[0]) != set()
                    and len(self.results[field]) != 1):
                with open("%s/results/%s_result.html" % (self.output_dir,
                          field.replace(" ", "_")), "r") as f:
                    self.networks[field] = f.read()

    def compare_two_groups(self, A, B):
        A_T1s = set()
        A_T2s = set()
        A_T3s = set()
        for item in A:
            A_T1s.add(item[1])
            A_T2s.add((item[1], item[2]))
            A_T3s.add((item[1], item[2], item[3]))

        B_T1s = set()
        B_T2s = set()
        B_T3s = set()
        for item in B:
            B_T1s.add(item[1])
            B_T2s.add((item[1], item[2]))
            B_T3s.add((item[1], item[2], item[3]))

        unique_A_T1s = set()
        for item in A_T1s:
            if item not in B_T1s:
                unique_A_T1s.add(item)

        unique_A_T2s = set()
        for item in A_T2s:
            if item not in B_T2s:
                unique_A_T2s.add(item)

        unique_A_T3s = set()
        for item in A_T3s:
            if item not in B_T3s:
                unique_A_T3s.add(item)

        sub_unique_A_T2s = set()
        for item in A:
            if (item[1], item[2]) in unique_A_T2s and item[1] not in unique_A_T1s:
                sub_unique_A_T2s.add((item[1], item[2]))

        sub_unique_A_T3s = set()
        for item in A:
            if ((item[1], item[2], item[3]) in unique_A_T3s
                and item[1] not in unique_A_T1s
                    and (item[1], item[2]) not in unique_A_T2s):
                sub_unique_A_T3s.add((item[1], item[2], item[3]))

        unique_B_T1s = set()
        for item in B_T1s:
            if item not in A_T1s:
                unique_B_T1s.add(item)

        unique_B_T2s = set()
        for item in B_T2s:
            if item not in A_T2s:
                unique_B_T2s.add(item)

        unique_B_T3s = set()
        for item in B_T3s:
            if item not in A_T3s:
                unique_B_T3s.add(item)

        sub_unique_B_T2s = set()
        for item in B:
            if (item[1], item[2]) in unique_B_T2s and item[1] not in unique_B_T1s:
                sub_unique_B_T2s.add((item[1], item[2]))

        sub_unique_B_T3s = set()
        for item in B:
            if ((item[1], item[2], item[3]) in unique_B_T3s
                and item[1] not in unique_B_T1s
                    and (item[1], item[2]) not in unique_B_T2s):
                sub_unique_B_T3s.add((item[1], item[2], item[3]))

        A_diffs = {"A_T1": [], "A_T2": [], "A_T3": []}
        for item in sorted(unique_A_T1s):
            A_diffs["A_T1"].append(str(item))
            A_diffs["A_T2"].append("")
            A_diffs["A_T3"].append("")
        
        for item in sorted(sub_unique_A_T2s):
            A_diffs["A_T1"].append(str(item[0]))
            A_diffs["A_T2"].append(str(item[1]))
            A_diffs["A_T3"].append("")
        
        for item in sorted(sub_unique_A_T3s):
            A_diffs["A_T1"].append(str(item[0]))
            A_diffs["A_T2"].append(str(item[1]))
            A_diffs["A_T3"].append(str(item[2]))

        B_diffs = {"B_T1": [], "B_T2": [], "B_T3": []}

        for item in sorted(unique_B_T1s):
            B_diffs["B_T1"].append(str(item))
            B_diffs["B_T2"].append("")
            B_diffs["B_T3"].append("")
        
        for item in sorted(sub_unique_B_T2s):
            B_diffs["B_T1"].append(str(item[0]))
            B_diffs["B_T2"].append(str(item[1]))
            B_diffs["B_T3"].append("")
        
        for item in sorted(sub_unique_B_T3s):
            B_diffs["B_T1"].append(str(item[0]))
            B_diffs["B_T2"].append(str(item[1]))
            B_diffs["B_T3"].append(str(item[2]))

        return (pd.DataFrame(data=A_diffs), pd.DataFrame(data=B_diffs))

    def generate_table_data(self):
        for field in self.fields:
            if eval(list(self.results[field].keys())[0]) != set():
                groups = self.results[field]
                self.table_data[field] = {}
                for groupA in groups:
                    group_ids = []
                    for group in self.groups:
                        if group.serials[0] in groups[groupA]:
                            group_ids.append(str(group.id))
                    if len(group_ids) == 1:
                        name_A = group_ids[0]
                    else:
                        name_A = "_".join(group_ids)
                    for groupB in groups:
                        if groups[groupA] != groups[groupB]:
                            group_ids = []
                            for group in self.groups:
                                if group.serials[0] in groups[groupB]:
                                    group_ids.append(str(group.id))
                            if len(group_ids) == 1:
                                name_B = group_ids[0]
                            else:
                                name_B = "_".join(group_ids)
                            if "%s vs %s" % (name_B, name_A) not in self.table_data[field].keys():
                                diffs = self.compare_two_groups(eval(groupA),
                                                                eval(groupB))
                                self.table_data[field]["%s vs %s"
                                                    % (name_A, name_B)] = diffs

    def separate_networks(self):
        for field in self.fields:
            if eval(list(self.results[field].keys())[0]) != set():
                net = Network(directed=True, width="1200px", height="600px")

                self.generate_subgraph(net, field)

                net.toggle_physics(False)
                try:
                    net.show("%s/results/%s_result.html" %
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
            net.show("%s/results/All_result.html" % self.output_dir)
        except Exception as e:
            print(e)

    def visualise_hardware(self):
        self.combined_network()
        self.separate_networks()

    def visualise_performance(self):
        app = Dash(__name__)

        self.record_networks()

        output = [html.H1(children='ADVise Hardware Differences'),
                  html.H2(children='Groups')]

        group_names = []
        for group in self.groups:
            group_names.append(html.B("Group %s: " % group.id))
            names = []
            for serial in group.serials:
                names.append(self.names_dict[serial])
            group_names.append(", ".join(names))
            group_names.append(html.Br())
        output.append(html.P(group_names))

        for field in self.networks:
            output.append(html.H2(field))
            output.append(
                html.Div(html.Iframe(
                    id='network_graph_%s' % field,
                    srcDoc=self.networks[field],
                    style={"height": "650px", "width": "100%"})))
            if field != "All":
                groupings = list(self.table_data[field].keys())
                output.append(dcc.Dropdown(groupings, groupings[0], id="%s-dropdown" % field, style={"width" : "50%"}))
                output.append(html.Div([
                    html.Div([
                        html.P("Group %s has unique values:" % groupings[0].split()[0], id="%s-text-A" % field),
                        dash_table.DataTable(
                            self.table_data[field][groupings[0]][0].to_dict('records'),
                            id='%s-table-A' % field,
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto'
                            },
                            style_cell={'textAlign': 'left'},
                            style_table={'overflowX': 'scroll'},
                            fill_width=False
                        )],
                        style={'width': '50%', 'display': 'inline-block'}
                    ),
                    html.Div([
                        html.P("Group %s has unique values:" % groupings[0].split()[2], id="%s-text-B" % field),
                        dash_table.DataTable(
                            self.table_data[field][groupings[0]][1].to_dict('records'),
                            id='%s-table-B' % field,
                            style_data={
                                'whiteSpace': 'normal',
                                'height': 'auto'
                            },
                            style_cell={'textAlign': 'left'},
                            style_table={'overflowX': 'scroll'},
                            fill_width=False
                        )],
                        style={'width': '50%', 'display': 'inline-block'}
                    )
                ]))

        output.extend([
            html.H1(children='ADVise Performance Results'),

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
        ])

        i = 0
        output.append(html.H2(children='High Variance'))
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
                    group_number, title), orientation='h',
                    hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        output.append(html.H2(children='Curious Overperformance'))
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
                    group_number, title), orientation='h',
                    hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        output.append(html.H2(children='Curious Underperformance'))
        for group_number in self.underperf_groups:
            element = self.underperf_groups[group_number]
            for title in element:
                data = element[title]
                new_index = {}
                for serial in data.index:
                    if serial in self.names_dict:
                        new_index[serial] = self.names_dict[serial]
                data.rename(index=new_index, inplace=True)
                fig = px.box(data.round(2), title="Group %s %s" % (
                    group_number, title), orientation='h',
                    hover_data=[data.index])
                output.append(dcc.Graph(
                    id='example-graph-%s' % i,
                    figure=fig
                ))
                i += 1

        app.layout = html.Div(children=output)

        def make_callback_A(field):
            @app.callback(
                [Output('%s-table-A' % field, 'data'), Output('%s-text-A' % field, 'children')],
                Input('%s-dropdown' % field, 'value')
            )
            def update_output(value):
                if value != None:
                    text = "Group %s has unique values:" % value.split()[0]
                    return self.table_data[field][value][0].to_dict('records'), text
                else:
                    return None, ""
            return update_output
        
        def make_callback_B(field):
            @app.callback(
                [Output('%s-table-B' % field, 'data'), Output('%s-text-B' % field, 'children')],
                Input('%s-dropdown' % field, 'value')
            )
            def update_output(value):
                if value != None:
                    text = "Group %s has unique values:" % value.split()[2]
                    return self.table_data[field][value][1].to_dict('records'), text
                else:
                    return None, ""
            return update_output
        
        for field in self.networks:
            if field != "All":
                make_callback_A(field)
                make_callback_B(field)

        app.run_server(debug=True)

    def visualise(self):
        self.generate_table_data()
        self.visualise_hardware()
        self.visualise_performance()


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="")
    parser.add_argument(
        '--output_dir')
    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    vis = Visualiser(args.output_dir)
    vis.load_data()

    vis.visualise()
