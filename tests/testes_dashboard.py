import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import autoteste
import dashboard


class DashboardDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'estado').mkdir()
        self.execution = {'status': 'ok', 'enabled': True, 'embeddings_enabled': False}
        self.exec_patch = patch.object(dashboard.p, 'estado_execucao', side_effect=lambda: self.execution)
        self.root_patch = patch.object(autoteste, 'REAL_SYSTEM', self.root)
        self.fp_patch = patch.object(autoteste, 'fingerprint', return_value='current')
        for item in (self.exec_patch, self.root_patch, self.fp_patch):
            item.start()
            self.addCleanup(item.stop)

    def write_report(self, **changes):
        report = {'status': 'passed', 'fingerprint': 'current', 'checked_at': 'today',
                  'suites': [{'status': 'passed'}, {'status': 'failed'}]}
        report.update(changes)
        (self.root / 'estado' / 'autoteste.json').write_text(json.dumps(report), encoding='utf8')

    def test_absent_report_is_not_approval(self):
        result = dashboard.dashboard_diagnostic()
        self.assertEqual(result['tests']['status'], 'not_run')
        self.assertFalse(result['embeddings_enabled'])

    def test_report_and_matching_fingerprint_are_reported(self):
        self.write_report(status='failed')
        self.execution['embeddings_enabled'] = True
        result = dashboard.dashboard_diagnostic()
        self.assertEqual((result['tests']['status'], result['tests']['passed'], result['tests']['suites']), ('failed', 1, 2))
        self.assertTrue(result['embeddings_enabled'])

    def test_old_fingerprint_is_stale(self):
        self.write_report(fingerprint='old')
        self.assertEqual(dashboard.dashboard_diagnostic()['tests']['status'], 'stale')

    def test_broken_report_is_unknown(self):
        (self.root / 'estado' / 'autoteste.json').write_text('{', encoding='utf8')
        self.assertEqual(dashboard.dashboard_diagnostic()['tests']['status'], 'unknown')

    def test_disabled_runtime_does_not_claim_vector_search(self):
        self.execution.update(enabled=False, embeddings_enabled=True)
        self.assertFalse(dashboard.dashboard_diagnostic()['embeddings_enabled'])

    def test_access_error_propagates_without_exposing_results(self):
        self.execution = {'status': 'blocked', 'error': 'access disabled'}
        self.assertEqual(dashboard.dashboard_diagnostic(), self.execution)

    def test_page_does_not_hardcode_success_or_hide_search_errors(self):
        self.assertNotIn('100% OK', dashboard.HTML_PAGE)
        self.assertNotIn('ONNX Local E5 Ativo', dashboard.HTML_PAGE)
        self.assertNotIn("fluxo.records || '257'", dashboard.HTML_PAGE)
        self.assertIn("Busca indisponível:", dashboard.HTML_PAGE)
        self.assertIn('Epistemic Memory Core', dashboard.HTML_PAGE)


if __name__ == '__main__':
    unittest.main()
