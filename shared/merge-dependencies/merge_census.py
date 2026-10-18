#!/usr/bin/env python3
"""Count finite catalog selections on each side of a reviewed text merge."""
import argparse
import json
import sys

import check_merge as merge
import components


def assess(base, ours, theirs, max_assignments=10000):
    if type(max_assignments) is not int or not 1 <= max_assignments <= 1000000:
        raise ValueError('assignment budget must be an integer from 1 to 1000000')
    packet = merge.review.packet(base, ours, theirs)
    report = {
        'format': 'merge-component-census/v1',
        'status': 'text_conflict',
        'review': packet,
        'census': None,
        'count_changes': None,
        'merged_compatible': None,
        'limits': [
            'Counts concern only complete reachable selections in the finite numeric catalog.',
            'Equal counts do not mean equal selection sets; review the merge separately.',
            'Each catalog gets a separate assignment budget; a partial zero is not unsatisfiable.',
            'Catalog bytes, publisher identity, artifacts, platforms and installation are not authenticated.',
        ],
    }
    if not packet['clean']:
        return report
    # Validate all four catalogs before expensive work. A clean text merge can
    # still yield invalid JSON or invalid dependency metadata.
    parsed = {}
    try:
        for label, body in (('base', base), ('ours', ours), ('theirs', theirs),
                            ('merged', packet['merged'])):
            value = merge.parse(body)
            components.fmt.validate(value)
            parsed[label] = value
    except (ValueError, TypeError, RecursionError):
        report['status'] = 'invalid_catalog'
        report['error'] = 'An input or the clean merge is not a supported dependency catalog.'
        return report
    report['census'] = {
        label: components.census(parsed[label], max_assignments)
        for label in ('base', 'ours', 'theirs', 'merged')
    }
    merged = report['census']['merged']
    report['merged_compatible'] = (False if merged['status'] == 'complete' and
                                   merged['compatible_selections'] == 0 else
                                   True if merged['compatible_selections'] > 0 else None)
    if all(row['status'] == 'complete' for row in report['census'].values()):
        report['status'] = 'complete'
        report['count_changes'] = {
            label: merged['compatible_selections'] - report['census'][label]['compatible_selections']
            for label in ('base', 'ours', 'theirs')
        }
    else:
        report['status'] = 'inconclusive'
    return report


def demo(max_assignments=10000):
    folder = merge.HERE / 'examples'
    texts = [merge.review.engine.read_text(folder / ('plan-' + label + '.json'))
             for label in ('base', 'ours', 'theirs')]
    return assess(*texts, max_assignments)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    run = sub.add_parser('check')
    for label in ('base', 'ours', 'theirs'):
        run.add_argument(label)
    run.add_argument('--max-assignments', type=int, default=10000)
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            result = demo()
        else:
            texts = [merge.review.engine.read_text(p)
                     for p in (args.base, args.ours, args.theirs)]
            result = assess(*texts, args.max_assignments)
        code = {'complete': 0, 'text_conflict': 1,
                'invalid_catalog': 2, 'inconclusive': 3}[result['status']]
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return code
    except (ValueError, OSError, TypeError, RecursionError):
        print(json.dumps({'status': 'invalid', 'error': 'Invalid workspace inputs or budget.'}),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
