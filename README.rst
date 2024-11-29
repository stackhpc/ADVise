=============
ADVise
=============

Usage
=====

Install ``ADVise`` as follows:

.. code-block::

  pip install git+https://github.com/stackhpc/ADVise
  mkdir working-dir && cd working-dir

Mungetout utility
-----------------

To Download the introspection data (or use kayobe overcloud introspection data save instead):

.. code-block::

  m2-collect

It can be useful to limit the number of nodes for debugging purposes:

.. code-block::

  m2-collect --limit 4 -vv

To extract the introspection data and process it ready for ADVise input:

.. code-block::

  m2-extract introspection-data/*.json

This will have created the directories: ``extra-hardware``, ``extra-hardware-json``
and ``extra-hardware-filtered``. The contents of these files is as follows:

- extra-hardware: input for ADVise
- extra-hardware-json: unmodified extra-hardware data
- extra-hardware-filtered: extra-hardware data stripped of all unique IDs. This
  can be used with the ``diff`` tool to look for differences between nodes.
  You can identify a group of similar servers using ADVise. Select one node
  from this group and one outlier and do a ``diff`` between them.
  You will have to grep for the system id in the extra-hardware data. The file
  names are consistent across all of the directories.

ADVise
------

.. code-block::

  advise-process -I ipmi -p 'path-to-output_dir/data/extra-hardware/*.eval' -o 'path-to-output_dir'

The ADVise tool will output a selection of results found under ``output_dir/results`` these include:

* ``.html`` files to display network visualisations of any hardware differences.

The folder ``Paired_Comparisons`` which contains information on the shared and differing fields found between the systems. This is a reflection of the network visualisation webpage, with more detail as to what the differences are.

* ``_summary``, a listing of how the systems can be grouped into sets of identical hardware.

* ``_performance``, the results of analysing the benchmarking data gathered.

* ``_perf_summary``, a subset of the performance metrics, just showing any potentially anomalous data such as where variance is too high, or individual nodes have been found to over/underperform.

.. code-block::

  advise-visualise -output_dir 'path-to-output_dir' 

The ADVise tool will also launch an interactive `Dash <https://dash.plotly.com/>`_ webpage, which displays the network visualisations, tables with information on the differing hardware attributes, the performance metrics as a range of box-plots, and specifies which individual nodes may be anomalous via box-plot outliers. This can be accessed at ``localhost:8050``.

Note
====

ADVise revives the package ``cardiff`` from https://github.com/redhat-cip/hardware/. 

* Author: `Erwan Velu <https://github.com/ErwanAliasr1>`_

ADVise integrates the package ``mungetout`` from https://github.com/stackhpc/mungetout.

* Author: `Will Szumski <https://github.com/jovial>`_

This project has been set up using PyScaffold 2.5.11. For details and usage
information on PyScaffold see http://pyscaffold.readthedocs.org/.
