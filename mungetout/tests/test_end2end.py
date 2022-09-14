#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess

# try:
#     import unittest.mock as mock
# except ImportError:
#     import mock as mock


__author__ = "Will Szumski"
__copyright__ = "Will Szumski"
__license__ = "apache"


def test_e2e():
    with open('samples/raw', 'r') as instream:
        output = subprocess.check_output(
            ['m2-convert'], stdin=instream
        )
        assert output != ""
        # cardiff loads this output using eval
        parsed = eval(output)
        assert type(parsed[0] == tuple)
