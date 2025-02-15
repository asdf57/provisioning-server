import unittest
from utils.dict_utils import deep_merge

class TestDeepMerge(unittest.TestCase):

    def test_deep_merge_simple(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        result = deep_merge(d1, d2)
        expected = {"a": 1, "b": 3, "c": 4}
        self.assertEqual(result, expected)

    def test_deep_merge_nested(self):
        d1 = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
        d2 = {"b": {"d": {"f": 4}}}
        result = deep_merge(d1, d2)
        expected = {"a": 1, "b": {"c": 2, "d": {"e": 3, "f": 4}}}
        self.assertEqual(result, expected)

    def test_deep_merge_overwrite(self):
        d1 = {"a": 1, "b": {"c": 2}}
        d2 = {"b": {"c": 3}}
        result = deep_merge(d1, d2)
        expected = {"a": 1, "b": {"c": 3}}
        self.assertEqual(result, expected)

    def test_deep_merge_empty_dict(self):
        d1 = {}
        d2 = {"a": 1}
        result = deep_merge(d1, d2)
        expected = {"a": 1}
        self.assertEqual(result, expected)

    def test_deep_merge_both_empty(self):
        d1 = {}
        d2 = {}
        result = deep_merge(d1, d2)
        expected = {}
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()