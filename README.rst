=============
ADVise
=============

.. image:: https://travis-ci.com/stackhpc/ADVise.svg?branch=master
    :target: https://travis-ci.com/stackhpc/ADVise

Dependencies
============

.. Requires the python `hardware <https://pypi.org/project/hardware/>`_
.. package to be installed.

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

  advise -I ipmi -p 'extra-hardware/*.eval' -o '/results'


Note
====

ADVise revives the pacakge ``cardiff`` from https://github.com/redhat-cip/hardware/. 

* Author: Erwan Velu <erwan@enovance.com>

ADVise integrates the package ``mungetout`` from https://github.com/stackhpc/mungetout.

* Author: Will Szumski <will@stackhpc.com>

This project has been set up using PyScaffold 2.5.11. For details and usage
information on PyScaffold see http://pyscaffold.readthedocs.org/.
