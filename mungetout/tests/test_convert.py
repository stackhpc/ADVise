import unittest

from mungetout.process import _clean_boot_volume # noqa
from mungetout.process import _filter_benchmarks # noqa
from mungetout.process import _filter_generic_field # noqa


class FilterTests(unittest.TestCase):
    def test_clean_boot_volume(self):
        item = (u'hpa',
                u'slot_0',
                u'secondary_boot_volume',
                u'logicaldrive 1 (600508B1001C6D568C431707B847FA3A)')
        expected = (u'hpa',
                    u'slot_0',
                    u'secondary_boot_volume',
                    u'logicaldrive 1')
        result = _clean_boot_volume(item)
        self.assertEqual(result, expected)

    def test_clean_benchmarks_bogomips(self):
        item = ["cpu", "logical_0", "bogomips", "5399.97"]
        result = _filter_benchmarks(item)
        self.assertEqual(None, result)

    def test_clean_benchmarks_bandwidth(self):
        item = ["cpu", "logical_0", "bandwidth_4K", "9934"]
        result = _filter_benchmarks(item)
        self.assertEqual(None, result)

    def test_clean_benchmarks_threaded_bandwith(self):
        item = ["cpu", "logical", "threaded_bandwidth_16M", "91774"]
        result = _filter_benchmarks(item)
        self.assertEqual(None, result)

    def test_clean_benchmarks_negative(self):
        # Items not matching benchmark should be passed through
        item = ["cpu", "logical_0", "should not match", "0"]
        expected = ['cpu', 'logical_0', 'should not match', '0']
        result = _filter_benchmarks(item)
        self.assertEqual(expected, result)

    def test_clean_generic_serial_number(self):
        item = ["hpa", "slot_0", "serial_number", "1234"]
        result = _filter_generic_field(item)
        self.assertEqual(result, None)


if __name__ == '__main__':
    unittest.main()
