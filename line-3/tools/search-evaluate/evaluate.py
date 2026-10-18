#!/usr/bin/env python3
"""Evaluate bounded offline retrieval against caller-labelled source ranges."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('search_batch', TOOLS / 'search-batch' / 'batch.py')
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)
engine = batch.engine
FORMAT = 'evidence-search-evaluation/v1'
PLAN_FORMAT = 'evidence-search-judgments/v1'
MAX_BYTES = 65536
MAX_TARGETS = 128


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {'format', 'queries'} or plan['format'] != PLAN_FORMAT:
        raise engine.SearchError('invalid judgments envelope')
    if not isinstance(plan['queries'], list):
        raise engine.SearchError('queries must be a list')
    search_rows = []
    total = 0
    for row in plan['queries']:
        if not isinstance(row, dict) or set(row) != {'id', 'query', 'limit', 'require_all', 'targets'}:
            raise engine.SearchError('invalid judgment entry')
        search_rows.append({key: row[key] for key in ('id', 'query', 'limit', 'require_all')})
        targets = row['targets']
        if not isinstance(targets, list) or not targets:
            raise engine.SearchError('each query requires at least one labelled target')
        seen = set()
        total += len(targets)
        if total > MAX_TARGETS:
            raise engine.SearchError('at most 128 targets per plan')
        for target in targets:
            if not isinstance(target, dict) or set(target) != {'path', 'line_start', 'line_end'}:
                raise engine.SearchError('invalid target')
            path, start, end = (target[key] for key in ('path', 'line_start', 'line_end'))
            if not engine.valid_relative(path):
                raise engine.SearchError('invalid target source path')
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= 1000000:
                raise engine.SearchError('invalid target line range')
            identity = (path, start, end)
            if identity in seen:
                raise engine.SearchError('duplicate target in query')
            seen.add(identity)
    search_plan = {'format': batch.PLAN_FORMAT, 'queries': search_rows}
    batch.validate_plan(search_plan)
    return search_plan


def load_plan(path):
    raw = engine.read_bytes(engine.workspace_path(path), MAX_BYTES)
    try:
        plan = json.loads(raw.decode('utf-8'), object_pairs_hook=engine.reject_duplicates,
                          parse_constant=batch.reject_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise engine.SearchError('invalid UTF-8 judgments JSON: ' + str(error)) from None
    validate(plan)
    return plan


def score(plan, results):
    """A target is found only if a hit contains its entire labelled line range."""
    rows = []
    for judgment, result in zip(plan['queries'], results['queries']):
        hits = result['result']['hits']
        found, missed, relevant_ranks = [], [], set()
        for target in judgment['targets']:
            ranks = [rank for rank, hit in enumerate(hits, 1)
                     if hit['path'] == target['path']
                     and hit['line_start'] <= target['line_start']
                     and hit['line_end'] >= target['line_end']]
            if ranks:
                found.append({**target, 'ranks': ranks})
                relevant_ranks.update(ranks)
            else:
                missed.append(dict(target))
        rows.append({'id': judgment['id'], 'query': judgment['query'],
                     'limit': judgment['limit'], 'require_all': judgment['require_all'],
                     'hits': hits, 'found': found, 'missed': missed,
                     'target_recall': len(found) / len(judgment['targets']),
                     'labelled_hit_precision': len(relevant_ranks) / len(hits) if hits else 0.0,
                     'reciprocal_rank': 1 / min(relevant_ranks) if relevant_ranks else 0.0})
    n = len(rows)
    return {'format': FORMAT, 'corpus_sha256': results['corpus_sha256'],
            'indexed_documents': results['indexed_documents'], 'queries': rows,
            'macro': {key: sum(row[key] for row in rows) / n
                      for key in ('target_recall', 'labelled_hit_precision', 'reciprocal_rank')},
            'all_targets_found': all(not row['missed'] for row in rows)}


def run(root, plan):
    search_plan = validate(plan)
    # Validate labels and rank the same in-memory source snapshot. A final
    # full-corpus reread rejects observed changes before metrics are returned.
    index = engine.build_index(root)
    docs = {doc['path']: doc for doc in index['documents']}
    for row in plan['queries']:
        for target in row['targets']:
            doc = docs.get(target['path'])
            if doc is None or target['line_end'] > len(engine.source_lines(doc['text'])):
                raise engine.SearchError('target source or line range does not exist')
    results = {'corpus_sha256': batch.corpus_id(index),
               'indexed_documents': len(docs), 'queries': []}
    for row in search_plan['queries']:
        result = engine.search(index, row['query'], root, row['limit'], row['require_all'])
        results['queries'].append({'id': row['id'], 'result': result})
    if not batch.freshness.audit(index, root)['fresh']:
        raise engine.SearchError('corpus changed during evaluation; retry with static files')
    return score(plan, results)


def demo_plan():
    return {'format': PLAN_FORMAT, 'queries': [
        {'id': 'decimals', 'query': 'ZTO token decimals', 'limit': 2, 'require_all': True,
         'targets': [{'path': 'zto.md', 'line_start': 6, 'line_end': 6}]},
        {'id': 'pool', 'query': 'ZTO pool tick spacing', 'limit': 2, 'require_all': True,
         'targets': [{'path': 'pool.md', 'line_start': 6, 'line_end': 6}]},
        {'id': 'missed', 'query': 'glacial orchid', 'limit': 2, 'require_all': True,
         'targets': [{'path': 'imd.md', 'line_start': 6, 'line_end': 6}]}]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    command = commands.add_parser('run')
    command.add_argument('root')
    command.add_argument('judgments')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            root, plan = TOOLS / 'evidence-search' / 'examples' / 'docs', demo_plan()
        else:
            root, plan = args.root, load_plan(args.judgments)
        print(json.dumps(run(root, plan), ensure_ascii=False, indent=2))
        return 0
    except (engine.SearchError, OSError, ValueError, RecursionError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
