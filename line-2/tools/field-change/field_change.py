#!/usr/bin/env python3
"""Compare packed fields in two proven Ethereum states under one trusted tip.

Offline Python standard library only; read bounded workspace inputs, print JSON.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def sibling(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


d = sibling('ancestry_diff_for_field_change', 'ancestry-diff/ancestry_diff.py')
f = sibling('storage_fields_for_field_change', 'storage-fields/storage_fields.py')
w = d.w
INVALID = d.INVALID + (f.w.Invalid,)


def fingerprint(layout):
    """Same normalized-layout commitment as Storage Fields; names are included."""
    normalized = f.validate_layout(layout)
    canonical = json.dumps(normalized, sort_keys=True, separators=(',', ':')).encode('ascii')
    return hashlib.sha256(canonical).hexdigest()


def compare(chain, first, tip, trusted_tip_hash, address, layout, layout_sha256):
    """Verify all evidence before interpreting fields or returning any result.

    layout_sha256 is a separate caller trust input, not a field in the evidence.
    Parent links bind both endpoint roots to the supplied tip; layout semantics
    and checkpoint authentication remain the caller's responsibility.
    """
    layout = f.validate_layout(layout)
    digest = fingerprint(layout)
    w.require(w.hex_data(layout_sha256, 32, 'layout SHA-256') == bytes.fromhex(digest),
              'layout differs from separately reviewed fingerprint')
    verified = d.compare(chain, first, tip, trusted_tip_hash, address,
                         [row['slot'] for row in layout['slots']])
    difference = verified['difference']
    accounts = {row['field']: row for row in difference['account']}
    existence = accounts['accountExists']
    w.require(existence['before'] and existence['after'],
              'field interpretation requires an existing account at both endpoints')
    by_slot = {row['slot']: row for row in difference['storage']}
    slots, changed_fields, unnamed_slots = [], [], []
    for row in layout['slots']:
        proven = by_slot[row['slot']]
        before = f.decode_word(int(proven['before']['value'], 16), row)
        after = f.decode_word(int(proven['after']['value'], 16), row)
        fields = []
        for old, new in zip(before['fields'], after['fields']):
            changed = old['rawBits'] != new['rawBits']
            fields.append({k: old[k] for k in ('name', 'offset', 'bits', 'signed')})
            fields[-1].update({
                'before': {'rawBits': old['rawBits'], 'valueDecimal': old['valueDecimal']},
                'after': {'rawBits': new['rawBits'], 'valueDecimal': new['valueDecimal']},
                'changed': changed,
                'deltaDecimal': str(int(new['valueDecimal']) - int(old['valueDecimal'])),
            })
            if changed:
                changed_fields.append(old['name'])
        unused_before, unused_after = int(before['unusedBits'], 16), int(after['unusedBits'], 16)
        unnamed = unused_before != unused_after
        if unnamed:
            unnamed_slots.append(row['slot'])
        slots.append({
            'slot': row['slot'], 'before': {**proven['before'], 'unusedBits': before['unusedBits']},
            'after': {**proven['after'], 'unusedBits': after['unusedBits']},
            'wordChanged': proven['changed'], 'fields': fields,
            'unnamedBitsChanged': unnamed, 'unnamedBitsXor': hex(unused_before ^ unused_after),
        })
    code_changed = accounts['codeHash']['changed']
    return {
        'format': 'field-change/1', 'verified': True, 'address': difference['address'],
        'layoutSha256': digest, 'ancestry': verified['ancestry'],
        'before': difference['before'], 'after': difference['after'],
        'account': difference['account'], 'slots': slots,
        'summary': {
            'changedFields': changed_fields, 'namedFieldsChanged': bool(changed_fields),
            'slotsWithUnnamedBitChanges': unnamed_slots,
            'requestedWordsChanged': difference['summary']['requestedSlotsChanged'],
            'storageCommitmentChanged': difference['summary']['storageCommitmentChanged'],
            'codeHashChanged': code_changed,
        },
        'trust': ('Authenticate the tip hash and chain, consensus/execution validity, canonicality '
                  'and finality independently. Review the layout at BOTH endpoints, including '
                  'proxy implementation changes; even an unchanged account code hash does not '
                  'prove stable layout or semantics. Fingerprinting binds assumptions, not truth. '
                  'Signed deltas are endpoint arithmetic, not events, transfers, profit, balances '
                  'or swap quotes. Equal endpoints can hide intermediate changes. Unnamed bits '
                  'are reported without interpretation; unrequested slots are not enumerated.'),
    }


def demo_inputs():
    return (d.chain_tool.load_chain(HERE.parent / 'header-chain/examples/zto-header-chain.json'),
            w.load_bundle(HERE.parent / 'state-witness/examples/zto-pool-mainnet.json'),
            w.load_bundle(HERE.parent / 'ancestry-diff/examples/pool-tip.json'),
            d.chain_tool.DEMO_TIP, w.POOL_MANAGER,
            f.load_layout(HERE.parent / 'storage-fields/pool-layout.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='offline real historical ZTO/IMD pool field comparison')
    pin = sub.add_parser('fingerprint', help='fingerprint a separately reviewed storage-fields/1 layout')
    pin.add_argument('layout')
    check = sub.add_parser('compare', help='verify linked endpoint proofs, then compare packed fields')
    for arg in ('chain', 'first_witness', 'tip_witness', 'layout'):
        check.add_argument(arg)
    check.add_argument('--tip-hash', required=True)
    check.add_argument('--address', required=True)
    check.add_argument('--layout-sha256', required=True, help='separately retained 32-byte 0x-prefixed digest')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fingerprint':
            result = {'format': 'field-change-layout/1', 'verified': False,
                      'layoutSha256': fingerprint(f.load_layout(args.layout))}
        elif args.command == 'demo':
            inputs = demo_inputs()
            result = compare(*inputs, '0x' + fingerprint(inputs[-1]))
            result['demo'] = ('Real historical ZTO/IMD pool observations at blocks 26212390 and '
                              '26212393; stored checkpoint is an RPC observation, not independent '
                              'consensus authentication. No live RPC or present-state claim.')
        else:
            result = compare(d.chain_tool.load_chain(args.chain),
                             w.load_bundle(args.first_witness), w.load_bundle(args.tip_witness),
                             args.tip_hash, args.address, f.load_layout(args.layout), args.layout_sha256)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except INVALID as error:
        print(json.dumps({'verified': False, 'error': str(error)}), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({'verified': False, 'error': 'Unreadable or malformed input.'}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
