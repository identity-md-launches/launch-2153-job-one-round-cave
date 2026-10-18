#!/usr/bin/env python3
"""Count compatible selections by independent finite dependency components."""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

CHECKER = Path(__file__).resolve().parent.parent / 'exhaustive-audit/audit.py'
if not CHECKER.is_relative_to(Path.cwd().resolve()):
    raise RuntimeError('run from the workspace containing the tools')
spec = importlib.util.spec_from_file_location('component_checker', CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
fmt = checker.fmt


def partition(packages, roots):
    """Conservative undirected components of all root-reachable release edges."""
    graph, todo = {}, list(roots)
    expanded = set()
    while todo:
        p = todo.pop()
        graph.setdefault(p, set())
        if p in expanded:
            continue
        expanded.add(p)
        for deps in packages.get(p, {}).values():
            for q in deps:
                graph[p].add(q)
                graph.setdefault(q, set()).add(p)
                if q not in expanded:
                    todo.append(q)
    groups, seen = [], set()
    for start in sorted(graph):
        if start in seen:
            continue
        group, todo = set(), [start]
        while todo:
            p = todo.pop()
            if p in group:
                continue
            group.add(p)
            todo.extend(graph[p] - group)
        seen.update(group)
        groups.append(sorted(group))
    return groups


def census(data, max_assignments=10000):
    if type(max_assignments) is not int or not 1 <= max_assignments <= 1000000:
        raise fmt.Invalid('max_assignments must be an integer from 1 to 1000000')
    packages, roots = fmt.validate(data)
    groups = partition(packages, roots)
    checked, components = 0, []
    flat_total, split_total, count = 1, 0, 1
    first = {}
    for names in groups:
        local_roots = {p: roots[p] for p in names if p in roots}
        domains, total = [], 1
        for p in names:
            versions = sorted(packages.get(p, {}), key=fmt.version)
            domain = ([v for v in versions if checker.matches(v, roots[p])]
                      if p in roots else [None] + versions)
            domains.append(domain)
            total *= len(domain)
        flat_total *= total
        split_total += total
        local_checked, solutions, witness = 0, 0, None
        for values in itertools.product(*domains):
            if checked == max_assignments:
                break
            checked += 1
            local_checked += 1
            selected = {p: v for p, v in zip(names, values) if v is not None}
            reached = checker.assignment(packages, local_roots, selected)
            # Reject extraneous choices rather than counting one root closure
            # multiple times through optional/unreachable package versions.
            if reached is None or reached != selected:
                continue
            solutions += 1
            if witness is None:
                witness = reached
        complete = local_checked == total
        row = {'packages': names, 'roots': local_roots,
               'status': 'complete' if complete else 'inconclusive',
               'count_kind': 'exact' if complete else 'lower-bound',
               'compatible_selections': solutions,
               'candidate_assignments': total,
               'checked_assignments': local_checked, 'witness': witness}
        components.append(row)
        count *= solutions
        if witness is not None:
            first.update(witness)
    all_complete = all(c['status'] == 'complete' for c in components)
    # An exhausted empty component makes the entire product zero, even if
    # another component ran out of budget. A partial zero proves nothing.
    empty = next((i for i, c in enumerate(components)
                  if c['status'] == 'complete' and c['compatible_selections'] == 0), None)
    exact = all_complete or empty is not None
    classification = ('unsatisfiable' if count == 0 else
                      'unique' if count == 1 else 'multiple') if exact else (
                      'multiple' if count >= 2 else 'unknown')
    witness = None
    if all(c['witness'] is not None for c in components):
        witness = dict(sorted(first.items()))
        if checker.assignment(packages, roots, witness) != witness:
            raise fmt.Invalid('combined component witness failed validation')
    payload = {'packages': packages, 'roots': roots}
    return {'method': 'independent-component-census-v1',
            'status': 'complete' if exact else 'inconclusive',
            'classification': classification, 'all_components_complete': all_complete,
            'count_kind': 'exact' if exact else 'lower-bound',
            'compatible_selections': count,
            'empty_component_index': empty,
            'catalog_sha256': hashlib.sha256(json.dumps(payload, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest(),
            'checked_assignments': checked, 'max_assignments': max_assignments,
            'unsplit_candidate_assignments': flat_total,
            'split_candidate_assignments': split_total,
            'components': components, 'witness': witness,
            'ignored_packages': sorted(set(packages) - set().union(*map(set, groups)))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', help='workspace-local JSON or demo')
    parser.add_argument('--max-assignments', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        path = (CHECKER.parent.parent / 'offline-resolver/examples/requests.json'
                if args.catalog == 'demo' else args.catalog)
        data = fmt.load(path)
        if args.catalog == 'demo':
            # Explicit standalone roots over real stored release metadata;
            # this is not a claim about an observed installed environment.
            data = dict(data, roots={'certifi': '*', 'charset-normalizer': '*',
                                     'idna': '*', 'urllib3': '<2'})
        result = census(data, args.max_assignments)
        if args.catalog == 'demo':
            result['demonstration_roots'] = data['roots']
        code = 0 if result['status'] == 'complete' else 3
    except (fmt.Invalid, OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        result, code = {'status': 'invalid', 'error': str(exc)}, 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
