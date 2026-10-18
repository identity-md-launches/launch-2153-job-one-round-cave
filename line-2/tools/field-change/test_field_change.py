"""Real historical integration and explicitly synthetic cryptographic edge tests."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('field_change_test_target', HERE / 'field_change.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
w = t.w


class FieldChangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = t.demo_inputs()

    def check(self, **changes):
        names = ('chain', 'first', 'tip', 'trusted_tip_hash', 'address', 'layout')
        args = dict(zip(names, copy.deepcopy(self.inputs)))
        args['layout_sha256'] = '0x' + t.fingerprint(args['layout'])
        args.update(changes)
        return t.compare(**args)

    def test_real_pool_endpoints(self):
        result = self.check()
        self.assertTrue(result['verified'])
        self.assertEqual(result['ancestry']['parentLinks'], 3)
        self.assertEqual(result['ancestry']['elapsedSeconds'], 36)
        self.assertEqual(result['summary']['changedFields'], [])
        self.assertTrue(result['summary']['storageCommitmentChanged'])
        self.assertFalse(result['summary']['codeHashChanged'])
        self.assertEqual([f['after']['valueDecimal'] for f in result['slots'][0]['fields']],
                         ['20794297345123442418062648917057', '111407', '0', '0', '12500'])

    def test_one_header_identity(self):
        chain, first, _, _, _, _ = self.inputs
        one = {'format': 'header-chain/1', 'headers': [chain['headers'][0]]}
        result = self.check(chain=one, tip=first, trusted_tip_hash=t.d.chain_tool.a.DEMO_HASH)
        self.assertEqual(result['ancestry']['parentLinks'], 0)
        self.assertFalse(result['summary']['requestedWordsChanged'])

    def test_wrong_pin_and_changed_layout(self):
        layout = copy.deepcopy(self.inputs[-1])
        layout['slots'][0]['fields'][0]['name'] = 'somethingElse'
        with self.assertRaises(t.INVALID):
            self.check(layout=layout)
        with self.assertRaises(t.INVALID):
            self.check(layout_sha256='0x' + 'ab' * 32)

    def test_pin_normalizes_order_and_slot_spelling(self):
        layout = copy.deepcopy(self.inputs[-1])
        original = t.fingerprint(layout)
        layout['slots'][0]['fields'].reverse()
        layout['slots'][0]['slot'] = '0x' + layout['slots'][0]['slot'][2:].upper()
        self.assertEqual(t.fingerprint(layout), original)
        self.assertTrue(self.check(layout=layout)['verified'])

    def test_wrong_tip_address_and_requested_slot(self):
        for change in ({'trusted_tip_hash': t.d.chain_tool.a.DEMO_HASH}, {'address': w.ZTO}):
            with self.subTest(change=change), self.assertRaises(t.INVALID):
                self.check(**change)
        layout = copy.deepcopy(self.inputs[-1])
        layout['slots'][0]['slot'] = '0x1'
        with self.assertRaises(t.INVALID):
            self.check(layout=layout, layout_sha256='0x' + t.fingerprint(layout))

    def test_broken_parent_link(self):
        chain = copy.deepcopy(self.inputs[0])
        chain['headers'][1]['parentHash'] = self.inputs[3]
        with self.assertRaises(t.INVALID):
            self.check(chain=chain)

    def test_both_endpoint_proofs_required(self):
        for side in ('first', 'tip'):
            bad = copy.deepcopy(self.inputs[1 if side == 'first' else 2])
            bad['proof']['storageProof'][0]['proof'] = []
            with self.subTest(side=side), self.assertRaises(t.INVALID):
                self.check(**{side: bad})

    def test_labels_never_override_proven_values(self):
        tip = copy.deepcopy(self.inputs[2])
        tip['block'] = {'hash': 'untrusted', 'stateRoot': 'untrusted'}
        tip['address'], tip['slots'] = 'untrusted', []
        self.assertEqual(self.check(tip=tip)['slots'], self.check()['slots'])

    def test_input_immutability(self):
        snapshot = copy.deepcopy(self.inputs)
        t.compare(*self.inputs, '0x' + t.fingerprint(self.inputs[-1]))
        self.assertEqual(self.inputs, snapshot)

    def synthetic(self, before, after, *, absent_account=False, changed_code=False):
        """Build actual valid MPT proofs, but NOT observations of the real pool.

        These hypothetical states exercise signed/unnamed/zero boundaries. No
        synthetic data is saved as a chain example or used by the demo.
        """
        slot = '0x1'
        address = self.inputs[4]
        bundles, headers = [], []
        parent = self.inputs[0]['headers'][0]['parentHash']
        for index, word in enumerate((before, after)):
            def integer(value):
                return value.to_bytes((value.bit_length() + 7) // 8, 'big')
            if word:
                node = w.rlp_encode([b'\x20' + w.keccak256((1).to_bytes(32, 'big')),
                                     w.rlp_encode(integer(word))])
                storage_root, storage_proof = w.keccak256(node), [w.hex0(node)]
            else:
                storage_root, storage_proof = w.EMPTY_TRIE, []
            code_hash = w.keccak256(b'changed' if index and changed_code else b'original')
            account = w.rlp_encode([b'\x01', b'', storage_root, code_hash])
            node = w.rlp_encode([b'\x20' + w.keccak256(w.hex_data(address, 20)), account])
            root, proof = w.keccak256(node), [w.hex0(node)]
            exists = not (absent_account and index == 1)
            if not exists:
                root, proof, storage_root, code_hash = w.EMPTY_TRIE, [], w.EMPTY_TRIE, w.EMPTY_CODE
            bundle = {'format': 'state-witness/1', 'proof': {
                'address': address, 'nonce': '0x1' if exists else '0x0', 'balance': '0x0',
                'storageHash': w.hex0(storage_root), 'codeHash': w.hex0(code_hash),
                'accountProof': proof,
                'storageProof': [{'key': slot, 'value': hex(word) if exists else '0x0',
                                  'proof': storage_proof if exists else []}],
            }}
            header = copy.deepcopy(self.inputs[0]['headers'][index])
            header.pop('hash', None)
            header['stateRoot'], header['parentHash'] = w.hex0(root), parent
            encoded, _ = t.d.chain_tool.a.encode_header(header)
            parent = w.hex0(w.keccak256(encoded))
            headers.append(header)
            bundles.append(bundle)
        layout = {'format': 'storage-fields/1', 'slots': [{
            'slot': slot, 'requireUnusedZero': False, 'fields': [
                {'name': 'signedByte', 'offset': 0, 'bits': 8, 'signed': True},
                {'name': 'unsignedByte', 'offset': 8, 'bits': 8, 'signed': False}]}]}
        return ({'format': 'header-chain/1', 'headers': headers}, *bundles,
                parent, address, layout)

    def synthetic_check(self, before, after, **kwargs):
        args = self.synthetic(before, after, **kwargs)
        return t.compare(*args, '0x' + t.fingerprint(args[-1]))

    def test_signed_boundary_and_unsigned_delta(self):
        result = self.synthetic_check(0x02ff, 0x0301)
        fields = result['slots'][0]['fields']
        self.assertEqual(fields[0]['before']['valueDecimal'], '-1')
        self.assertEqual(fields[0]['after']['valueDecimal'], '1')
        self.assertEqual(fields[0]['deltaDecimal'], '2')
        self.assertEqual(fields[1]['deltaDecimal'], '1')
        self.assertEqual(result['summary']['changedFields'], ['signedByte', 'unsignedByte'])
        reverse = self.synthetic_check(0x0301, 0x02ff)
        self.assertEqual([r['deltaDecimal'] for r in reverse['slots'][0]['fields']], ['-2', '-1'])

    def test_full_width_signed_delta_is_not_modular_arithmetic(self):
        args = list(self.synthetic(1 << 255, (1 << 255) - 1))
        args[-1]['slots'][0]['fields'] = [
            {'name': 'signedWord', 'offset': 0, 'bits': 256, 'signed': True}]
        result = t.compare(*args, '0x' + t.fingerprint(args[-1]))
        self.assertEqual(result['slots'][0]['fields'][0]['deltaDecimal'], str((1 << 256) - 1))

    def test_multiple_real_zto_slots_and_numeric_order(self):
        chain = {'format': 'header-chain/1', 'headers': [self.inputs[0]['headers'][0]]}
        bundle = w.load_bundle(HERE.parent / 'state-witness/examples/zto-mainnet.json')
        layout = {'format': 'storage-fields/1', 'slots': [
            {'slot': slot, 'requireUnusedZero': True, 'fields': [
                {'name': name, 'offset': 0, 'bits': 256, 'signed': False}]}
            for slot, name in [('0x01', 'rawOne'), ('0x00', 'rawZero')]]}
        result = t.compare(chain, bundle, bundle, t.d.chain_tool.a.DEMO_HASH, w.ZTO,
                           layout, '0x' + t.fingerprint(layout))
        self.assertEqual([row['slot'] for row in result['slots']], ['0x0', '0x1'])
        self.assertEqual([row['fields'][0]['name'] for row in result['slots']], ['rawZero', 'rawOne'])
        self.assertFalse(result['summary']['requestedWordsChanged'])

    def test_unnamed_bits_change_without_named_change(self):
        result = self.synthetic_check(0x0301, (1 << 255) | 0x0301)
        self.assertEqual(result['summary']['changedFields'], [])
        self.assertTrue(result['summary']['requestedWordsChanged'])
        self.assertEqual(result['summary']['slotsWithUnnamedBitChanges'], ['0x1'])
        self.assertEqual(result['slots'][0]['unnamedBitsXor'], hex(1 << 255))

    def test_unused_zero_requirement_at_both_ends(self):
        for before, after in ((1 << 255, 1), (1, 1 << 255)):
            args = list(self.synthetic(before, after))
            args[-1]['slots'][0]['requireUnusedZero'] = True
            with self.subTest(before=before), self.assertRaises(t.INVALID):
                t.compare(*args, '0x' + t.fingerprint(args[-1]))

    def test_storage_absence_is_proven_zero(self):
        result = self.synthetic_check(0, 1)
        self.assertFalse(result['slots'][0]['before']['exists'])
        self.assertTrue(result['slots'][0]['after']['exists'])
        self.assertEqual(result['slots'][0]['fields'][0]['deltaDecimal'], '1')

    def test_absent_account_is_rejected(self):
        with self.assertRaises(t.INVALID):
            self.synthetic_check(1, 0, absent_account=True)

    def test_code_change_is_explicit(self):
        result = self.synthetic_check(1, 1, changed_code=True)
        self.assertTrue(result['summary']['codeHashChanged'])
        self.assertFalse(result['summary']['requestedWordsChanged'])
        self.assertIn('BOTH endpoints', result['trust'])

    def test_overlap_and_boolean_width_rejected(self):
        for field in ({'offset': 1}, {'bits': True}, {'signed': 1}):
            layout = copy.deepcopy(self.inputs[-1])
            layout['slots'][0]['fields'][1].update(field)
            with self.subTest(field=field), self.assertRaises(t.INVALID):
                t.fingerprint(layout)

    def cli(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = t.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def compare_args(self, layout=None, tip=None):
        return ['compare', str(HERE.parent / 'header-chain/examples/zto-header-chain.json'),
                str(HERE.parent / 'state-witness/examples/zto-pool-mainnet.json'),
                str(tip or HERE.parent / 'ancestry-diff/examples/pool-tip.json'),
                str(layout or HERE.parent / 'storage-fields/pool-layout.json'),
                '--tip-hash', self.inputs[3], '--address', self.inputs[4],
                '--layout-sha256', '0x' + t.fingerprint(self.inputs[-1])]

    def test_cli_demo_fingerprint_and_compare(self):
        for args in (['demo'], self.compare_args(),
                     ['fingerprint', str(HERE.parent / 'storage-fields/pool-layout.json')]):
            code, stdout, stderr = self.cli(args)
            self.assertEqual((code, stderr), (0, ''))
            result = json.loads(stdout)
            self.assertEqual(result['layoutSha256'], t.fingerprint(self.inputs[-1]))
            self.assertEqual(result['verified'], args[0] != 'fingerprint')

    def test_cli_rejects_corrupt_second_proof_atomically(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir='test/scratch') as temp:
            path = Path(temp) / 'bad.json'
            bad = copy.deepcopy(self.inputs[2])
            bad['proof']['accountProof'] = []
            path.write_text(json.dumps(bad))
            code, stdout, stderr = self.cli(self.compare_args(tip=path))
            self.assertEqual((code, stdout), (1, ''))
            self.assertFalse(json.loads(stderr)['verified'])
            self.assertNotIn('Traceback', stderr)

    def test_strict_bounded_workspace_loading(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir='test/scratch') as temp:
            path = Path(temp) / 'bad.json'
            for raw in ('{"format": 1, "format": 2}', ' ' * 65537):
                path.write_text(raw)
                code, stdout, stderr = self.cli(self.compare_args(layout=path))
                self.assertEqual((code, stdout), (1, ''))
                self.assertFalse(json.loads(stderr)['verified'])
            outside = Path.cwd().parent / 'not-read'
            link = Path(temp) / 'outside.json'
            link.symlink_to(outside)
            for bad_path in (outside, link):
                code, stdout, stderr = self.cli(self.compare_args(layout=bad_path))
                self.assertEqual((code, stdout), (1, ''))
                self.assertIn('workspace', json.loads(stderr)['error'])


if __name__ == '__main__':
    unittest.main()
