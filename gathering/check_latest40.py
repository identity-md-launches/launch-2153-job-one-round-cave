"""Try the current line pieces against inherited real data and explicit scratch."""
import json
from pathlib import Path
import subprocess
import sys


def run(command):
    proc = subprocess.run([sys.executable, '-B', *command], capture_output=True,
                          text=True, timeout=90, check=False)
    if proc.returncode:
        raise AssertionError({'command': command, 'exit': proc.returncode,
                              'stderr': proc.stderr[-500:]})
    return json.loads(proc.stdout)


def main():
    root = Path('test/scratch/gathering40-evidence')
    if root.exists() or root.is_symlink():
        raise ValueError('scratch destination must be new')
    bundle = 'line-3/tools/evidence-bundle/examples/zto-bundle.json'
    pin = '4199bcadadc0df319c7e98137bf3ee83e4895373bedf35d929ba3ff5984b48e2'
    receipt = run(['line-1/tools/merge-receipt/merge_receipt.py', *(
        'shared/merge-dependencies/examples/' + p + '.json'
        for p in ('base', 'ours', 'theirs'))])
    fields = run(['line-2/tools/field-change/field_change.py', 'demo'])
    checked = run(['line-3/tools/evidence-bundle/bundle.py', 'check', bundle,
                   '--expected-sha256', pin])
    restored = run(['line-3/tools/evidence-bundle/bundle.py', 'unpack', bundle,
                    '--expected-sha256', pin, '--destination', str(root)])
    census = run(['line-4/tools/component-census/components.py', 'demo'])
    assert all(row['total_changes'] == 1 and not row['truncated']
               for row in receipt['branches'])
    assert fields['verified'] is True
    assert checked['receipt_reproduced'] is False
    assert restored['receipt_reproduced'] is True
    assert census['status'] == 'complete' and census['compatible_selections'] == 8
    output = {
        'line_1': {'tool': 'bounded merge receipt', 'branch_hunks': [
            row['total_changes'] for row in receipt['branches']], 'exit': 0},
        'line_2': {'tool': 'field change', 'verified': fields['verified'], 'exit': 0},
        'line_3': {'tool': 'evidence bundle', 'integrity_check': True,
                   'restored_receipt_reproduced': restored['receipt_reproduced'], 'exit': 0},
        'line_4': {'tool': 'component census', 'status': census['status'],
                   'compatible_selections': census['compatible_selections'], 'exit': 0},
    }
    Path('gathering/latest-checks-40.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
