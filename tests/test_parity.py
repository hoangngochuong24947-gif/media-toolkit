"""Capability gaps: real audio/image processing and evidence rejection."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/'scripts/media.py'
sys.path.insert(0, str(ROOT/'scripts'))
from media_toolkit.runtime import Runner


class EntrypointTests(unittest.TestCase):
    def test_isolated_interpreter_can_load_skill(self):
        proc=subprocess.run([sys.executable,'-I',str(CLI),'--help'],capture_output=True,text=True,errors='replace')
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertIn('transcribe-api',proc.stdout)


class ReportTests(unittest.TestCase):
    def test_numbers_outside_quote_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); t=p/'t.json'; c=p/'c.json'; out=p/'report.md'
            t.write_text(json.dumps({'cues':[{'start':0,'end':1,'text':'128GB memory'}]}))
            c.write_text(json.dumps({'title':'Bad','claims':[{'statement':'999GB memory','transcript':str(t),'cue':0,'quote':'128GB memory'}]}))
            proc=subprocess.run([sys.executable,str(CLI),'report',str(c),'-o',str(out)],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertEqual(json.loads(proc.stdout)['error']['code'],'evidence_invalid')
            self.assertFalse(out.exists())

    def test_exact_evidence_and_timestamp(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); transcript=p/'transcript.json'; claims=p/'claims.json'; out=p/'report.md'
            transcript.write_text(json.dumps({'source':'https://www.youtube.com/watch?v=abcdefghijk','cues':[{'start':12,'end':14,'text':'It has 128GB memory.'}]}))
            claims.write_text(json.dumps({'title':'Report','claims':[{'statement':'Speaker reports 128GB memory.','transcript':str(transcript),'cue':0,'quote':'128GB memory','kind':'speaker'}]}))
            proc=subprocess.run([sys.executable,str(CLI),'report',str(claims),'-o',str(out)],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
            self.assertIn('t=12',out.read_text(encoding='utf-8'))
            self.assertIn('128GB memory',out.read_text(encoding='utf-8'))

    def test_invented_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); t=p/'t.json'; c=p/'c.json'; out=p/'report.md'
            t.write_text(json.dumps({'cues':[{'start':0,'end':1,'text':'128GB'}]}))
            c.write_text(json.dumps({'title':'Bad','claims':[{'statement':'999GB','transcript':str(t),'cue':0,'quote':'999GB','kind':'speaker'}]}))
            proc=subprocess.run([sys.executable,str(CLI),'report',str(c),'-o',str(out)],capture_output=True,text=True)
            self.assertNotEqual(proc.returncode,0)
            self.assertEqual(json.loads(proc.stdout)['error']['code'],'evidence_invalid')
            self.assertFalse(out.exists())


@unittest.skipUnless(os.environ.get('MEDIA_INTEGRATION')=='1','Real tools required')
class MediaParityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='parity-'); self.p=Path(self.temp.name); self.r=Runner(60)
        self.source=self.p/'source.mp4'
        self.r.ffmpeg(['-f','lavfi','-i','testsrc2=size=128x96:rate=10','-f','lavfi','-i','sine=sample_rate=48000','-t','1','-c:v','libx264','-c:a','aac',self.source])

    def tearDown(self): self.temp.cleanup()

    def cli(self,*args):
        proc=subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        return proc, json.loads(proc.stdout)

    def test_m4a_packet_preserving_copy(self):
        proc,result=self.cli('audio',self.source,'-o',self.p/'copy.m4a','--format','m4a','--copy')
        self.assertEqual(proc.returncode,0,result)
        self.assertTrue(result['validated']['packet_identity'])
        self.assertFalse(result['actual']['reencoded'])

    def test_m4a_encoding(self):
        proc,result=self.cli('audio',self.source,'-o',self.p/'encoded.m4a','--format','m4a')
        self.assertEqual(proc.returncode,0,result)
        self.assertIn('aac',result['actual']['codecs'])

    def test_copy_incompatible_pcm_rejected(self):
        wav=self.p/'source.wav'; self.r.ffmpeg(['-i',self.source,'-vn','-c:a','pcm_s16le',wav])
        proc,result=self.cli('audio',wav,'-o',self.p/'copy.m4a','--format','m4a','--copy')
        self.assertNotEqual(proc.returncode,0)
        self.assertEqual(result['error']['code'],'lossless_unavailable')

    def test_image_batch_resume_and_tamper(self):
        src=self.p/'图片 原始'; src.mkdir()
        for name in ['a.png','b.jpg']: self.r.run('magick',['-size','64x32','xc:red',src/name])
        dest=self.p/'转换 结果'
        proc,result=self.cli('images',src,'-o',dest)
        self.assertEqual(proc.returncode,0,result); self.assertEqual(result['processed'],2)
        proc,result=self.cli('images',src,'-o',dest)
        self.assertEqual(result['processed'],0); self.assertEqual(result['skipped'],2)
        (dest/'a.webp').write_bytes(b'damaged')
        proc,result=self.cli('images',src,'-o',dest)
        self.assertNotEqual(proc.returncode,0); self.assertEqual(result['status'],'partial')
        self.assertEqual((dest/'a.webp').read_bytes(),b'damaged')

    def test_batch_colliding_stems_rejected(self):
        src=self.p/'images'; src.mkdir()
        for name in ['a.png','a.jpg']: self.r.run('magick',['-size','16x16','xc:red',src/name])
        proc,result=self.cli('images',src,'-o',self.p/'out')
        self.assertNotEqual(proc.returncode,0); self.assertEqual(result['error']['code'],'output_collision')

    def test_batch_source_overlap_rejected(self):
        src=self.p/'images'; src.mkdir(); self.r.run('magick',['-size','16x16','xc:red',src/'a.png'])
        proc,result=self.cli('images',src,'-o',src/'outputs','--recursive')
        self.assertNotEqual(proc.returncode,0); self.assertEqual(result['error']['code'],'source_protection')

    def test_batch_corrupt_image_retains_successful_items(self):
        src=self.p/'images'; src.mkdir(); self.r.run('magick',['-size','16x16','xc:red',src/'a.png'])
        (src/'bad.png').write_bytes(b'not an image')
        proc,result=self.cli('images',src,'-o',self.p/'out')
        self.assertNotEqual(proc.returncode,0); self.assertEqual(result['processed'],1)
        self.assertEqual(result['failed'],1); self.assertTrue((self.p/'out/a.webp').exists())

    def test_h265_cpu(self):
        proc,result=self.cli('compress',self.source,'-o',self.p/'h265.mp4','--codec','h265')
        self.assertEqual(proc.returncode,0,result); self.assertIn('hevc',result['actual']['codecs'])

    def test_auto_reports_actual_encoder(self):
        proc,result=self.cli('compress',self.source,'-o',self.p/'auto.mp4','--encoder','auto')
        self.assertEqual(proc.returncode,0,result); self.assertIn('encoder',result['actual'])

    def test_unavailable_videotoolbox_falls_back(self):
        if sys.platform=='darwin': return
        proc,result=self.cli('compress',self.source,'-o',self.p/'fallback.mp4','--encoder','videotoolbox')
        self.assertEqual(proc.returncode,0,result); self.assertEqual(result['actual']['encoder'],'libx264')
        self.assertTrue(result['actual']['fallback'])
