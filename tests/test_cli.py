"""Black-box contracts; integration is opt-in with MEDIA_INTEGRATION=1."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/'scripts/media.py'
sys.path.insert(0, str(ROOT/'scripts'))
from media_toolkit.runtime import Artifact, Runner, ToolkitError


class RuntimeTests(unittest.TestCase):
    def test_failure_discards_staged_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'failed.mp4'
            try:
                with Artifact(output) as artifact:
                    artifact.path.write_bytes(b'broken')
                    raise ToolkitError('encode failed')
            except ToolkitError:
                pass
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_publication_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'existing'
            output.write_bytes(b'original')
            with self.assertRaises(ToolkitError):
                Artifact(output)
            self.assertEqual(output.read_bytes(), b'original')

    def test_race_created_destination_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            with Artifact(output) as artifact:
                artifact.path.write_bytes(b'new')
                output.write_bytes(b'concurrent writer')
                with self.assertRaises(ToolkitError):
                    artifact.publish({'command':'test'})
            self.assertEqual(output.read_bytes(), b'concurrent writer')

    def test_atomic_output_has_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'output'
            with Artifact(output) as artifact:
                artifact.path.write_bytes(b'valid')
                receipt = artifact.publish({'command':'test'})
            self.assertEqual(receipt['bytes'], 5)
            self.assertEqual(json.loads(Path(str(output)+'.result.json').read_text()), receipt)

    def test_missing_dependency_is_explicit(self):
        with patch.dict(os.environ, {'MEDIA_FFMPEG':'missing-command-no-such-tool'}):
            with self.assertRaises(ToolkitError) as ctx:
                Runner().tool('ffmpeg')
            self.assertEqual(ctx.exception.code, 'dependency_missing')

    def test_subprocess_timeout_is_bounded(self):
        with patch.dict(os.environ, {'MEDIA_TEST_PYTHON':sys.executable}):
            with self.assertRaises(ToolkitError) as ctx:
                Runner(0.1).run('test-python', ['-c','import time; time.sleep(2)'])
            self.assertEqual(ctx.exception.code, 'timeout')


class CLITests(unittest.TestCase):
    def invoke(self, *args, success=True):
        process = subprocess.run([sys.executable, str(CLI), *map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        self.assertEqual(process.returncode == 0, success, process.stderr+process.stdout)
        return json.loads(process.stdout)

    def test_help(self):
        process = subprocess.run([sys.executable, str(CLI), '--help'],capture_output=True,text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('subtitles', process.stdout)

    def test_subtitle_cli_retains_numeric_text_and_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.vtt'; output=Path(directory)/'notes.json'
            source.write_text('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n128GB <c>memory</c>\n',encoding='utf-8')
            result=self.invoke('subtitles', source, '-o',output)
            document=json.loads(output.read_text())
            self.assertEqual(document['text'], '128GB memory\n')
            self.assertEqual(document['cues'][0]['start'], 1)
            self.assertTrue(result['ok'])

    def test_missing_input_is_json_failure(self):
        result=self.invoke('subtitles', 'missing-no-such.vtt', '-o','ignored.json',success=False)
        self.assertEqual(result['error']['code'], 'input_missing')

    def test_rejects_negative_timeout(self):
        result=self.invoke('--timeout','-1','doctor',success=False)
        self.assertEqual(result['error']['code'], 'invalid_argument')

    def test_bad_arguments_are_json_failure(self):
        result=self.invoke('trim','file.mp4','-o','output.mp4',success=False)
        self.assertEqual(result['error']['code'],'invalid_argument')


@unittest.skipUnless(os.environ.get('MEDIA_INTEGRATION')=='1', 'Set MEDIA_INTEGRATION=1 for real external tools')
class IntegrationTests(CLITests):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='media-integration-')
        cls.directory=Path(cls.temp.name); cls.source=cls.directory/'fixture.mkv'
        cls.runner=Runner(60)
        cls.runner.ffmpeg(['-f','lavfi','-i','testsrc2=size=320x180:rate=25','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','4','-c:v','ffv1','-c:a','pcm_s16le',cls.source])

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def output(self, name): return self.directory/(self._testMethodName+'-'+name)

    def test_target_budget(self):
        output=self.output('compressed.mp4')
        result=self.invoke('compress',self.source,'-o',output,'--target-mb','0.2')
        self.assertLessEqual(output.stat().st_size, 200_000)
        self.assertEqual(result['requested']['max_bytes'], 200_000)
        self.assertTrue(result['validated']['decodable'])

    def test_impossible_budget_no_artifact(self):
        output=self.output('impossible.mp4')
        result=self.invoke('compress',self.source,'-o',output,'--target-mb','0.001',success=False)
        self.assertEqual(result['error']['code'], 'budget_unreachable')
        self.assertFalse(output.exists())

    def test_gif_budget_retry(self):
        output=self.output('demo.gif')
        result=self.invoke('gif',self.source,'-o',output,'--width','640','--fps','15','--max-mb','0.25')
        self.assertLessEqual(output.stat().st_size, 250_000)
        self.assertGreater(result['actual']['attempts'],1)

    def test_gif_impossible_no_artifact(self):
        output=self.output('impossible.gif')
        self.invoke('gif',self.source,'-o',output,'--max-mb','0.000001',success=False)
        self.assertFalse(output.exists())

    def test_accurate_and_fast_trim(self):
        encoded=self.output('longgop.mp4')
        self.runner.ffmpeg(['-i',self.source,'-c:v','libx264','-g','100','-c:a','aac',encoded])
        exact=self.invoke('trim',encoded,'-o',self.output('exact.mp4'),'--start','0.7','--end','2.2','--mode','accurate')
        self.assertLessEqual(abs(exact['actual']['duration']-1.5),exact['requested']['tolerance_seconds'])
        fast=self.invoke('trim',encoded,'-o',self.output('fast.mp4'),'--start','0.7','--end','2.2','--mode','fast')
        self.assertFalse(fast['requested']['exact_boundaries'])

    def test_audio_and_inspect(self):
        output=self.output('audio.mp3')
        self.invoke('audio',self.source,'-o',output)
        info=self.invoke('inspect',output)
        self.assertEqual(info['media']['streams'][0]['codec_type'],'audio')

    def test_nvenc_failure_cpu_fallback(self):
        # Runtime failure is injected; CPU retry performs a real encode.
        from media_toolkit.operations import compress
        runner=Runner(60); original=runner.ffmpeg
        def fail_gpu(args):
            if 'h264_nvenc' in args:
                raise ToolkitError('No capable NVENC device', 'process_failed')
            return original(args)
        output=self.output('fallback.mp4')
        with patch.object(runner, 'ffmpeg', side_effect=fail_gpu):
            result=compress(runner,self.source,output,encoder='nvenc')
        self.assertEqual(result['actual']['encoder'],'libx264')
        self.assertTrue(result['actual']['fallback'])

    def test_images_privacy_and_dimensions(self):
        from PIL import Image, TiffImagePlugin
        source=self.output('gps.jpg'); exif=Image.Exif()
        exif[271]='PRIVATE_MAKE'; exif[272]='PRIVATE_MODEL'
        exif[34853]={1:'N',2:tuple(TiffImagePlugin.IFDRational(x,1) for x in [31,12,0])}
        Image.new('RGB',(2400,1600),'red').save(source,exif=exif)
        output=self.output('image.webp')
        result=self.invoke('image',source,'-o',output,'--max-side','1920')
        with Image.open(output) as converted:
            self.assertEqual(converted.size,(1920,1280))
        self.assertTrue(result['validated']['privacy_scrubbed'])

    def test_lossless_rejects_sixteen_bit_source(self):
        source=self.output('16bit.png')
        self.runner.run('magick',['-size','100x100','gradient:red-blue','-depth','16',source])
        result=self.invoke('image',source,'-o',self.output('lossless.webp'),'--lossless',success=False)
        self.assertEqual(result['error']['code'],'lossless_unavailable')

    def test_source_protection(self):
        before=self.source.read_bytes()
        self.invoke('compress',self.source,'-o',self.source,success=False)
        self.assertEqual(self.source.read_bytes(),before)

    def test_doctor_has_versions(self):
        result=self.invoke('doctor')
        self.assertTrue(result['local_ready'])
        self.assertIn('version',result['tools']['ffmpeg'])

    def test_invalid_media_does_not_publish(self):
        source=self.output('broken.mp4'); source.write_bytes(b'not media')
        output=self.output('bad-output.mp4')
        result=self.invoke('compress',source,'-o',output,success=False)
        self.assertFalse(result['ok'])
        self.assertFalse(output.exists())

    def test_lossless_eight_bit_pixels(self):
        from PIL import Image,ImageChops
        source=self.output('8bit.png'); Image.new('RGB',(100,80),(5,42,100)).save(source)
        output=self.output('same.webp')
        result=self.invoke('image',source,'-o',output,'--lossless')
        with Image.open(source) as original, Image.open(output) as converted:
            self.assertIsNone(ImageChops.difference(original,converted.convert('RGB')).getbbox())
        self.assertTrue(result['validated']['pixel_identity'])

    def test_http_download_is_verified(self):
        from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
        from functools import partial
        import threading
        source=self.output('served.mp4')
        self.runner.ffmpeg(['-i',self.source,'-c:v','libx264','-c:a','aac',source])
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(self.directory)))
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            result=self.invoke('download',f'http://127.0.0.1:{server.server_port}/{source.name}','-o',self.output('download.mp4'))
            self.assertTrue(result['validated']['decodable'])
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
