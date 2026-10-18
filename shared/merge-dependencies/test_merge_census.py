"""Integration checks for reviewed merge and component census."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import merge_census as tool


def body(packages, roots):
    return json.dumps({'packages': packages, 'roots': roots}, indent=2, sort_keys=True) + '\n'


class MergeCensusTests(unittest.TestCase):
    def test_historical_catalog_and_input_immutability(self):
        folder = Path(__file__).resolve().parent / 'examples'
        raw = [(folder / ('plan-' + label + '.json')).read_text()
               for label in ('base', 'ours', 'theirs')]
        result = tool.assess(*raw)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(result['review']['clean'])
        self.assertEqual([result['census'][label]['compatible_selections']
                          for label in ('base', 'ours', 'theirs', 'merged')], [12, 12, 8, 8])
        self.assertEqual(result['count_changes'], {'base': -4, 'ours': -4, 'theirs': 0})
        self.assertTrue(result['merged_compatible'])
        self.assertEqual(raw, [(folder / ('plan-' + label + '.json')).read_text()
                               for label in ('base', 'ours', 'theirs')])

    def test_independent_components_are_counted_without_cross_product(self):
        packages = {'a': {'1': {}, '2': {}}, 'b': {'1': {}, '2': {}}}
        text = body(packages, {'a': '*', 'b': '*'})
        result = tool.assess(text, text, text)
        self.assertEqual(result['status'], 'complete')
        row = result['census']['merged']
        self.assertEqual(row['compatible_selections'], 4)
        self.assertEqual(len(row['components']), 2)
        self.assertEqual(row['checked_assignments'], 4)
        self.assertEqual(row['unsplit_candidate_assignments'], 4)
        self.assertEqual(row['count_kind'], 'exact')

    def test_partial_zero_is_unknown_and_exact_zero_is_incompatible(self):
        packages = {'a': {'1': {'missing': '*'}, '2': {'missing': '*'}},
                    'b': {'1': {}, '2': {}}}
        text = body(packages, {'a': '*', 'b': '*'})
        partial = tool.assess(text, text, text, max_assignments=1)
        self.assertEqual(partial['status'], 'inconclusive')
        self.assertIsNone(partial['merged_compatible'])
        exact = tool.assess(text, text, text, max_assignments=3)
        self.assertEqual(exact['status'], 'complete')
        self.assertFalse(exact['merged_compatible'])
        self.assertEqual(exact['census']['merged']['compatible_selections'], 0)

    def test_text_conflict_skips_census(self):
        base = body({'a': {'1': {}}}, {'a': '*'})
        ours = base.replace('"*"', '">=1"')
        theirs = base.replace('"*"', '"<2"')
        result = tool.assess(base, ours, theirs)
        self.assertEqual(result['status'], 'text_conflict')
        self.assertIsNone(result['census'])

    def test_invalid_catalog_and_budget(self):
        base = body({'a': {'1': {}}}, {'a': '*'})
        result = tool.assess('{bad', '{bad', '{bad')
        self.assertEqual(result['status'], 'invalid_catalog')
        with self.assertRaises(ValueError):
            tool.assess(base, base, base, max_assignments=0)

    def test_cli_demo(self):
        script = Path(__file__).resolve().parent / 'merge_census.py'
        proc = subprocess.run([sys.executable, '-B', str(script), 'demo'],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
