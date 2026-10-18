import copy
import importlib.util
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('components', Path(__file__).with_name('components.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def oracle(data):
    """Independent full subset enumeration for exact/wildcard test catalogs."""
    packages, roots = data['packages'], data['roots']
    names = sorted(packages)
    solutions = []
    for values in itertools.product(*[[None] + list(packages[p]) for p in names]):
        chosen = {p: v for p, v in zip(names, values) if v is not None}
        todo, reached, valid = list(roots.items()), set(), True
        while todo:
            p, constraint = todo.pop()
            v = chosen.get(p)
            if v is None or (constraint != '*' and constraint != '==' + v):
                valid = False
                break
            if p not in reached:
                reached.add(p)
                todo.extend(packages[p][v].items())
        if valid and set(chosen) == reached:
            solutions.append(chosen)
    return solutions


class ComponentTests(unittest.TestCase):
    def test_large_independent_product(self):
        data = {'roots': {f'p{i}': '*' for i in range(100)},
                'packages': {f'p{i}': {'1': {}, '2': {}} for i in range(100)}}
        r = m.census(data, 200)
        self.assertEqual(r['status'], 'complete')
        self.assertEqual(r['compatible_selections'], 2**100)
        self.assertEqual(r['unsplit_candidate_assignments'], 2**100)
        self.assertEqual(r['split_candidate_assignments'], 200)
        self.assertEqual(r['checked_assignments'], 200)
        self.assertEqual(len(r['components']), 100)
        self.assertEqual(len(r['witness']), 100)

    def test_shared_dependency_joins_roots(self):
        data = {'roots': {'a': '*', 'b': '*'}, 'packages': {
            'a': {'1': {'shared': '==1'}}, 'b': {'1': {'shared': '==2'}},
            'shared': {'1': {}, '2': {}}}}
        r = m.census(data)
        self.assertEqual(len(r['components']), 1)
        self.assertEqual(r['classification'], 'unsatisfiable')
        self.assertEqual(r['empty_component_index'], 0)
        self.assertIsNone(r['witness'])

    def test_all_release_edges_even_excluded_ones(self):
        data = {'roots': {'a': '==1', 'b': '*'}, 'packages': {
            'a': {'1': {}, '2': {'b': '*'}}, 'b': {'1': {}, '2': {}}}}
        r = m.census(data)
        self.assertEqual(len(r['components']), 1)
        self.assertEqual(r['compatible_selections'], 2)

    def test_optional_missing_cycle_and_unreachable(self):
        data = {'roots': {'a': '*', 'x': '*'}, 'packages': {
            'a': {'1': {}, '2': {'b': '*'}, '3': {'missing': '*'}},
            'b': {'1': {'a': '==2'}, '2': {'a': '==1'}},
            'x': {'1': {}, '2': {}},
            'unused': {'1': {'a': '*', 'x': '*'}}}}
        r = m.census(data)
        self.assertEqual(len(r['components']), 2)
        self.assertEqual(r['compatible_selections'], 4)
        self.assertEqual(r['ignored_packages'], ['unused'])
        self.assertIn('missing', r['components'][0]['packages'])
        self.assertIn(r['witness'], oracle(data))

    def test_budget_is_global_and_partial_count_is_sound(self):
        data = {'roots': {'a': '*', 'b': '*'}, 'packages': {
            'a': {'1': {}, '2': {}}, 'b': {'1': {}, '2': {}}}}
        for budget, count, classification in ((1, 0, 'unknown'), (2, 0, 'unknown'),
                                               (3, 2, 'multiple'), (4, 4, 'multiple')):
            r = m.census(data, budget)
            self.assertEqual(r['checked_assignments'], budget)
            self.assertEqual(r['compatible_selections'], count)
            self.assertEqual(r['classification'], classification)
            self.assertEqual(r['status'], 'complete' if budget == 4 else 'inconclusive')
            self.assertEqual(r['count_kind'], 'exact' if budget == 4 else 'lower-bound')
            if r['witness']:
                self.assertIn(r['witness'], oracle(data))

    def test_empty_component_proves_zero_despite_other_cutoff(self):
        data = {'roots': {'a': '*', 'z': '*'}, 'packages': {'a': {'1': {}, '2': {}}}}
        r = m.census(data, 1)
        self.assertEqual(r['classification'], 'unsatisfiable')
        self.assertEqual(r['count_kind'], 'exact')
        self.assertEqual(r['compatible_selections'], 0)
        self.assertFalse(r['all_components_complete'])
        self.assertEqual(r['components'][0]['status'], 'inconclusive')
        self.assertEqual(r['components'][1]['checked_assignments'], 0)
        self.assertEqual(r['empty_component_index'], 1)

    def test_exhausted_nonempty_domains_with_no_solution(self):
        data = {'roots': {'a': '*', 'z': '*'}, 'packages': {
            'a': {'1': {'missing': '*'}}, 'z': {'1': {}, '2': {}}}}
        r = m.census(data, 1)
        self.assertEqual(r['classification'], 'unsatisfiable')
        self.assertFalse(r['all_components_complete'])
        self.assertEqual(r['components'][1]['status'], 'inconclusive')

    def test_seeded_raw_edge_oracle(self):
        rng = random.Random(3704)
        for _ in range(500):
            packages = {p: {v: {q: rng.choice(('*', '==1', '==2'))
                                for q in ('a', 'b', 'c', 'd', 'missing')
                                if rng.random() < .12}
                            for v in ('1', '2') if rng.random() < .85}
                        for p in ('a', 'b', 'c', 'd')}
            roots = {p: rng.choice(('*', '==1', '==2'))
                     for p in rng.sample(('a', 'b', 'c', 'd'), rng.randint(1, 4))}
            data = {'packages': packages, 'roots': roots}
            expected = oracle(data)
            r = m.census(data)
            self.assertEqual(r['status'], 'complete')
            self.assertEqual(r['compatible_selections'], len(expected))
            if expected:
                self.assertIn(r['witness'], expected)
            else:
                self.assertIsNone(r['witness'])
            groups = [set(c['packages']) for c in r['components']]
            self.assertEqual(sum(map(len, groups)), len(set().union(*groups)))
            for budget in (1, 3):
                partial = m.census(data, budget)
                self.assertLessEqual(partial['checked_assignments'], budget)
                self.assertLessEqual(partial['compatible_selections'], len(expected))
                if partial['count_kind'] == 'exact':
                    self.assertEqual(partial['compatible_selections'], len(expected))
                if partial['witness']:
                    self.assertIn(partial['witness'], expected)

    def test_numeric_constraints_normalization_and_immutable_input(self):
        data = {'roots': {'A_B': '>=1,!=2,<4', 'z': '*'},
                'packages': {'a-b': {'1.0': {}, '2': {}, '3': {}, '4': {}},
                             'z': {'1': {}}}}
        saved = copy.deepcopy(data)
        r = m.census(data)
        self.assertEqual(r['compatible_selections'], 2)
        self.assertEqual(r['witness'], {'a-b': '1.0', 'z': '1'})
        self.assertEqual(data, saved)
        data['roots'] = {'z': '*', 'a-b': '>=1,!=2,<4'}
        self.assertEqual(r, m.census(data))
        data['packages']['z']['2'] = {}
        self.assertNotEqual(r['catalog_sha256'], m.census(data)['catalog_sha256'])

    def test_combined_witness_checked(self):
        data = {'roots': {'a': '*'}, 'packages': {'a': {'1': {}}}}
        original = m.checker.assignment
        calls = []
        def reject_final(*args):
            calls.append(args)
            return original(*args) if len(calls) == 1 else None
        with patch.object(m.checker, 'assignment', side_effect=reject_final):
            with self.assertRaises(m.fmt.Invalid):
                m.census(data)

    def test_validation(self):
        data = {'roots': {'a': '*'}, 'packages': {'a': {'1': {}}}}
        for budget in (True, 0, -1, 1000001, 1.5):
            with self.assertRaises(m.fmt.Invalid):
                m.census(data, budget)
        for bad in (dict(data, roots={}), dict(data, roots={'a': '^1'}),
                    dict(data, packages={'a': {'1': {}, '1.0': {}}})):
            with self.assertRaises(m.fmt.Invalid):
                m.census(bad)

    def test_real_catalog_and_demo_cli(self):
        data = m.fmt.load(m.CHECKER.parent.parent / 'offline-resolver/examples/requests.json')
        r = m.census(data)
        self.assertEqual(len(r['components']), 1)
        self.assertEqual(r['compatible_selections'], 8)
        self.assertEqual(r['checked_assignments'], 27)
        script = str(Path(__file__).with_name('components.py'))
        for args, exit_code in ((['demo'], 0), (['demo', '--max-assignments', '1'], 3),
                                (['demo', '--max-assignments', '0'], 2)):
            run = subprocess.run([sys.executable, '-B', script] + args,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, exit_code, run.stdout + run.stderr)
            result = json.loads(run.stdout)
            if args == ['demo']:
                self.assertEqual(result['compatible_selections'], 8)
                self.assertEqual(result['checked_assignments'], 7)
                self.assertEqual(result['unsplit_candidate_assignments'], 8)
                self.assertEqual(len(result['components']), 4)

    def test_cli_loader(self):
        scratch = Path('test/scratch/component-census-37')
        scratch.mkdir(parents=True, exist_ok=True)
        script = str(Path(__file__).with_name('components.py'))
        files = {'conflict.json': '{"roots":{"absent":"*"},"packages":{}}',
                 'duplicate.json': '{"roots":{},"roots":{},"packages":{}}',
                 'oversized.json': ' ' * 1000001}
        for name, content in files.items():
            path = scratch / name
            path.write_text(content)
            run = subprocess.run([sys.executable, '-B', script, str(path)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0 if name == 'conflict.json' else 2)
            self.assertEqual(path.read_text(), content)
        run = subprocess.run([sys.executable, '-B', script, '/outside-component-catalog.json'],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('inside the current workspace', run.stdout)


if __name__ == '__main__':
    unittest.main()
