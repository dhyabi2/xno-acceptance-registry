import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
import probe

ADDRESS = 'nano_1gqjcgoc4hfghdmabpw3i1pcwr8ppcgjkoyhf4txsktdpthqb97apxz9qpyb'
AMOUNT = '186276480000000000000000000000'


def payment_result():
    # Shape observed from an unpaid character-sprites call; no live invoice IDs.
    return {'jsonrpc': '2.0', 'id': 1, 'result': {
        'content': [{'type': 'text', 'text': 'PAYMENT REQUIRED'}],
        'structuredContent': {'x402': {
            'paymentId': 'test-only', 'address': ADDRESS, 'amountRaw': AMOUNT,
            'uri': 'nano:%s?amount=%s' % (ADDRESS, AMOUNT)}}}}


class MCPProbeTests(unittest.TestCase):
    def probe_response(self, obj, sse=False):
        text = json.dumps(obj)
        if sse: text = 'event: message\ndata: ' + text + '\n\n'
        response = io.BytesIO(text.encode())
        response.status = 200
        response.headers = {'Content-Type': 'text/event-stream' if sse else 'application/json'}
        with patch('probe.urllib.request.urlopen', return_value=response) as request:
            result = probe.probe({'id': 'test', 'endpoint': 'https://example.test/mcp'})
        request.assert_called_once()  # No monitor, payment or result follow-up.
        return result

    def test_json_and_sse_quotes_are_paid_mcp(self):
        for sse in (False, True):
            with self.subTest(sse=sse):
                result = self.probe_response(payment_result(), sse)
                self.assertEqual(result['http_status'], 200)
                self.assertEqual(build.state({}, result)[0], 'live_mcp_nano')
                self.assertEqual(build.payto_of(result), [{'address': ADDRESS, 'checksum_valid': True}])
                self.assertEqual(result['mcp_payment_quote']['amountRaw'], AMOUNT)
                self.assertEqual(result['nano_accepts'], [])

    def test_sse_progress_crlf_and_multiline(self):
        obj = payment_result()
        encoded = json.dumps(obj, indent=1)
        data = '\r\n'.join('data: ' + line for line in encoded.splitlines())
        text = ': keepalive\r\n\r\ndata: {"method":"notifications/progress"}\r\n\r\n' + data + '\r\n\r\ndata: [DONE]\r\n\r\n'
        objects = probe.response_objects(text, {'content-type': 'text/event-stream'})
        self.assertEqual(objects[-1], obj)

    def test_incomplete_or_invalid_quotes_are_never_free(self):
        for field, value in [('amountRaw', '0'), ('amountRaw', '000'), ('amountRaw', '1.5'), ('amountRaw', 42),
                             ('address', ADDRESS[:-1] + '1'), ('uri', 'nano:wrong'), ('paymentId', '')]:
            with self.subTest(field=field, value=value):
                obj = payment_result()
                obj['result']['structuredContent']['x402'][field] = value
                result = self.probe_response(obj)
                self.assertNotIn('mcp_payment_quote', result)
                self.assertEqual(build.state({}, result)[0], 'unclear')

    def test_other_mcp_results_are_not_payment_quotes(self):
        for obj in [{'result': payment_result()['result']}, {'jsonrpc': '2.0', 'id': 1, 'result': []},
                    {'jsonrpc': '2.0', 'id': 1, 'error': {'message': ADDRESS}}, []]:
            self.assertIsNone(probe.mcp_nano_quote(obj))
        obj = payment_result()
        obj['result']['isError'] = True
        self.assertIsNone(probe.mcp_nano_quote(obj))

    def test_existing_classifications_unchanged(self):
        cases = [({'http_status': 402, 'mentions_nano': True}, 'live_402_nano'),
                 ({'http_status': 200, 'address_paths': [{'path': '/payTo', 'address': ADDRESS}]}, 'live_free_tier'),
                 ({'http_status': 200, 'expect': 200}, 'live_status_route'),
                 ({'http_status': 404}, 'dead'), ({'door': 'mail'}, 'mail_only')]
        for result, expected in cases: self.assertEqual(build.state({}, result)[0], expected)

    def test_extra_is_one_unpaid_tools_call(self):
        root = Path(__file__).resolve().parents[1]
        extra = next(s for s in json.loads((root / 'extras.json').read_text()) if s['id'] == 'nanoodle-mcp')
        self.assertEqual(extra['probe']['method'], 'POST')
        call = json.loads(extra['probe']['body'])
        self.assertEqual(call['method'], 'tools/call')
        self.assertEqual(call['params'], {'name': 'character-sprites', 'arguments': {}})

    def test_feed_keeps_existing_services_and_marks_mcp_transport(self):
        root = Path(__file__).resolve().parents[1]
        reg = json.loads((root / 'registry.json').read_text())
        reg['entries'] = [e for e in reg['entries'] if e['id'] != 'nanoodle-mcp']
        prior = json.loads((root / 'feeds/nano-sellers.json').read_text())['services']
        prior = [e for e in prior if e['id'] != 'nanoodle-mcp']
        row = copy.deepcopy(reg['entries'][0])
        row.update(id='nanoodle-mcp', state_today='live_mcp_nano', note='Read a fresh MCP quote.',
                   payto=[{'address': ADDRESS, 'checksum_valid': True}], payto_all_checksum_valid=True)
        reg['entries'].append(row)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'registry.json').write_text(json.dumps(reg))
            subprocess.run([sys.executable, str(root / 'feeds.py')], cwd=directory, check=True, capture_output=True)
            feed = json.loads(Path(directory, 'feeds/nano-sellers.json').read_text())
        self.assertEqual(feed['services'][:-1], prior)
        self.assertEqual(feed['services'][-1]['payment_transport'], 'mcp-streamable-http')


if __name__ == '__main__': unittest.main()
