import unittest
from app.util import netbox_value_to_default, parse_filter_string


class TestUtil(unittest.TestCase):
    def test_parse_filter_string_valid_filters(self):
        cases = [
            ("name__ic=target", {"name__ic": "target"}),
            ("name__ic=target,tag=hello", {"name__ic": "target", "tag": "hello"}),
            (" name__ic = target ", {"name__ic": "target"}),
            ("a=1 , b = 2", {"a": "1", "b": "2"}),
            ("", {}),
            (None, {}),
        ]
        for filter_str, expected in cases:
            with self.subTest(filter_str=filter_str):
                self.assertEqual(parse_filter_string(filter_str), expected)

    def test_parse_filter_string_invalid_filters(self):
        cases = [
            "name__ic",
            "name__ic=target=extra",
            "foo=bar,baz",
        ]
        for filter_str in cases:
            with self.subTest(filter_str=filter_str):
                with self.assertRaises(ValueError) as ctx:
                    parse_filter_string(filter_str)
                self.assertIn("cannot be parsed correctly", str(ctx.exception))

    def test_netbox_value_to_default(self):
        cases = [
            ("abc", ""),
            ([1, 2], []),
            ({"k": "v"}, None),
            (123, None),
            (3.14, None),
        ]

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(netbox_value_to_default(value), expected)
