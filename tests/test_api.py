import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

CLI=Path(__file__).resolve().parents[1]/'scripts/media.py'


class APITests(unittest.TestCase):
    def test_invalid_key_is_not_exposed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); src=p/'speech.wav'; src.write_bytes(b'audio')
            env=os.environ.copy(); env['MEDIA_ASR_API_KEY']='secret-sentinel\ninvalid'
            proc=subprocess.run([sys.executable,str(CLI),'transcribe-api',str(src),'-o',str(p/'out.json'),'--endpoint','http://127.0.0.1:1/audio/transcriptions','--allow-network'],env=env,capture_output=True,text=True)
            self.assertNotIn('secret-sentinel',proc.stdout+proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['error']['code'],'configuration_invalid')

    def test_network_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); src=p/'speech.wav'; src.write_bytes(b'audio')
            proc=subprocess.run([sys.executable,str(CLI),'transcribe-api',str(src),'-o',str(p/'out.json'),'--endpoint','http://127.0.0.1:1/audio/transcriptions'],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertEqual(json.loads(proc.stdout)['error']['code'],'network_not_authorized')

    def test_multipart_and_timed_transcript(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=self.rfile.read(int(self.headers['Content-Length'])); requests.append(body)
                response=json.dumps({'language':'en','segments':[{'start':0,'end':1,'text':'128GB memory'}]}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(response))); self.end_headers(); self.wfile.write(response)
        server=HTTPServer(('127.0.0.1',0),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d); src=p/'speech.wav'; src.write_bytes(b'audio')
                proc=subprocess.run([sys.executable,str(CLI),'transcribe-api',str(src),'-o',str(p/'out.json'),'--endpoint',f'http://127.0.0.1:{server.server_port}/audio/transcriptions','--allow-network'],capture_output=True,text=True)
                self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
                data=json.loads((p/'out.json').read_text(encoding='utf-8'))
                self.assertEqual(data['cues'][0]['text'],'128GB memory')
                self.assertIn(b'name="response_format"',requests[0]); self.assertIn(b'verbose_json',requests[0])
                self.assertFalse(json.loads(proc.stdout)['validated']['accuracy_certified'])
        finally: server.shutdown(); server.server_close(); thread.join()
