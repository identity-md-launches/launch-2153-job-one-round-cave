"""Focused offline checks; generated fixtures live only in test/scratch."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('merge_receipt', Path(__file__).with_name('merge_receipt.py'))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.cwd() / 'test' / 'scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.paths = [self.root / name for name in ('base', 'ours', 'theirs')]
        self.contents = [b'one\ntwo\nthree\n', b'one\nours\nthree\n', b'one\ntwo\ntheirs\n']
        for p, data in zip(self.paths, self.contents):
            p.write_bytes(data)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = m.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_real_receipt_and_immutability(self):
        result = m.receipt(self.paths)
        self.assertEqual(result['base']['sha256'], hashlib.sha256(self.contents[0]).hexdigest())
        self.assertEqual([p.read_bytes() for p in self.paths], self.contents)
        for branch in result['branches']:
            self.assertEqual(branch['total_changes'], 1)
            self.assertEqual(branch['total_added_lines'], 1)
            self.assertEqual(branch['total_removed_lines'], 1)
            self.assertFalse(branch['truncated'])
            self.assertEqual(branch['shown_changes'], 1)
        self.assertNotIn('lines_data', json.dumps(result))

    def test_preview_reports_all_totals(self):
        base = [f'anchor{i}\n' for i in range(40)]
        branch = [line if i % 2 else f'changed{i}\n' for i, line in enumerate(base)]
        items = [m.snapshot_data(''.join(lines).encode(), name)
                 for lines, name in ((base, 'base'), (branch, 'ours'), (base, 'theirs'))]
        row = m.from_snapshots(items)['branches'][0]
        self.assertEqual((row['total_changes'], row['shown_changes']), (20, 12))
        self.assertTrue(row['truncated'])
        self.assertEqual((row['total_added_lines'], row['total_removed_lines']), (20, 20))
        self.assertEqual(len(row['changes']), 12)

    def test_exact_preview_boundary(self):
        with patch.object(m, 'PREVIEW', 1):
            self.assertFalse(m.receipt(self.paths)['branches'][0]['truncated'])

    def test_unchanged_empty(self):
        for p in self.paths:
            p.write_bytes(b'')
        result = m.receipt(self.paths)
        self.assertEqual(result['base']['lines'], 0)
        self.assertEqual(result['branches'][0]['total_changes'], 0)

    def test_endings_are_changes(self):
        self.paths[0].write_bytes(b'x\n')
        self.paths[1].write_bytes(b'x\r\n')
        self.paths[2].write_bytes(b'x')
        result = m.receipt(self.paths)
        self.assertEqual([b['total_changes'] for b in result['branches']], [1, 1])

    def test_outside_workspace_rejected_before_io(self):
        root = Path.cwd()
        original = Path.stat
        def guarded(path, *args, **kwargs):
            if path != root and not path.is_relative_to(root):
                raise AssertionError('must not inspect outside')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', guarded):
            with self.assertRaises(ValueError):
                m.snapshot(root.parent / 'outside')

    def test_parent_traversal(self):
        with self.assertRaises(ValueError):
            m.snapshot(self.root / '..' / self.root.name / 'base')

    def test_file_symlink(self):
        link = self.root / 'link'
        link.symlink_to(self.paths[0])
        with self.assertRaises(ValueError):
            m.snapshot(link)

    def test_ancestor_symlink(self):
        link = self.root / 'dirlink'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.snapshot(link / 'base')

    def test_directory_and_missing(self):
        with self.assertRaises(ValueError):
            m.snapshot(self.root)
        with self.assertRaises(OSError):
            m.snapshot(self.root / 'missing')

    def test_special_file(self):
        fifo = self.root / 'fifo'
        m.os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            m.snapshot(fifo)

    def test_cli_argument_errors(self):
        for args in ([], [str(self.paths[0])], ['--demo', str(self.paths[0])]):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    m.main(args)
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('error:', err.getvalue())

    def test_byte_limits(self):
        self.paths[0].write_bytes(b'x' * m.LIMIT)
        self.assertEqual(m.snapshot(self.paths[0])['bytes'], m.LIMIT)
        self.paths[0].write_bytes(b'x' * (m.LIMIT + 1))
        with self.assertRaises(ValueError):
            m.snapshot(self.paths[0])
        with self.assertRaises(ValueError):
            m.snapshot_data(b'x' * (m.LIMIT + 1), 'over')

    def test_bounded_read_even_if_stat_is_stale(self):
        self.paths[0].write_bytes(b'x' * 31)
        # Pre-read fstat sees an acceptable size, but the bounded read must still
        # detect the extra byte. Exercise that path by substituting fstat only.
        real_fstat = m.os.fstat
        def stale(fd):
            info = list(real_fstat(fd))
            info[6] = 1
            return m.os.stat_result(info)
        with patch.object(m, 'LIMIT', 30), patch.object(m.os, 'fstat', stale):
            with self.assertRaises(ValueError):
                m.snapshot(self.paths[0])

    def test_line_limits_encoding_and_nul(self):
        self.assertEqual(m.snapshot_data(b'x\n' * m.MAX_LINES, 'ok')['lines'], m.MAX_LINES)
        for data in (b'x\n' * (m.MAX_LINES + 1), b'\xff', b'x\0y'):
            with self.assertRaises(ValueError):
                m.snapshot_data(data, 'bad')
        self.assertEqual(m.snapshot_data('蛙\n'.encode(), 'unicode')['lines'], 1)

    def test_cli_success_failure(self):
        code, out, err = self.invoke([str(p) for p in self.paths])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), m.receipt(self.paths))
        self.assertEqual(err, '')
        code, out, err = self.invoke([str(p) for p in self.paths[:2]] + [str(self.root / 'absent')])
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertIn('merge-receipt', err)

    def test_arity(self):
        for paths in ([], self.paths[:2], self.paths * 2):
            with self.assertRaises(ValueError):
                m.receipt(paths)

    def test_demo_never_reads_or_writes(self):
        with patch.object(Path, 'open', side_effect=AssertionError('no disk IO')):
            code, out, err = self.invoke(['--demo'])
        self.assertEqual(code, 0)
        self.assertEqual(err, '')
        result = json.loads(out)
        self.assertEqual(result['base']['path'], 'demo:base')
        self.assertEqual(result['branches'][0]['total_changes'], 1)


if __name__ == '__main__':
    unittest.main()
