=============
mungetout
=============

.. image:: https://travis-ci.com/stackhpc/mungetout.svg?branch=master
    :target: https://travis-ci.com/stackhpc/mungetout

Convert from Ironic Inspector introspection format to cardiff format. Now
you can mungetout...


Dependencies
============

Requires the python `hardware <https://pypi.org/project/hardware/>`_
package to be installed.

Usage
=====

Install ``mungetout`` as follows:

.. code-block::

  pip install git+https://github.com/stackhpc/mungetout
  mkdir working-dir && cd working-dir

To Download the introspection data (or use kayobe overcloud introspection data save instead):

.. code-block::

  m2-collect

It can be useful to limit the number of nodes for debugging purposes:

.. code-block::

  m2-collect --limit 4 -vv

To extract the the introspection data and process it ready for cardiff input:

.. code-block::

  m2-extract introspection-data/*.json

This will have created the directores: ``extra-hardware``, ``extra-hardware-json``
and ``extra-hardware-filtered``. The contents of these files is as follows:

- extra-hardware: input for cardiff
- extra-hardware-json: unmodified extra-hardware data
- extra-hardware-filtered: extra-hardware data stripped of all unique IDs. This
  can be used with the ``diff`` tool to look for differences between nodes.
  You can identify a group of similar servers using cardiff. Select one node
  from this group and one outlier and do a ``diff`` between them.
  You will have to grep for the system id in the extra-hardware data. The file
  names are consistent across all of the directories.

Running ``cardiff`` on the output:

.. code-block::

  hardware-cardiff -I ipmi -p 'extra-hardware/*.eval'

Examples
========

Running a script on some Ironic nodes:

.. code-block::

  openstack baremetal node list -f json --long | m2-filter 192.168.0.1-192.168.0.54 | m2-sink-run ./onboard.sh '{{ item.UUID }}'

List node names:

.. code-block::

  openstack baremetal node list -f json --long | m2-filter 192.168.0.1-192.168.0.6 | jq -r '.[] | ."Name"' | sort

Rename nodes:

.. code-block::

  cat asset-map
  "node1","192.168.0.1"
  "node2","192.168.0.2"
  openstack baremetal node list -f json --long | m2-filter 192.168.0.1-192.168.0.2 | m2-sink-ironic-name asset-map

Note
====

This project has been set up using PyScaffold 2.5.11. For details and usage
information on PyScaffold see http://pyscaffold.readthedocs.org/.
