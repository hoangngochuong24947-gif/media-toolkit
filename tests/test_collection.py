import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from media_toolkit import subtitles, online
from media_toolkit.runtime import Runner, ToolkitError


class SubtitleRegressionTests(unittest.TestCase):
    def test_touching_rolling_captions(self):
        cues = subtitles.parse_subtitles('WEBVTT\n\n00:00.000 --> 00:01.000\nfirst\nshared\n\n00:01.000 --> 00:01.010\nshared\n\n00:01.010 --> 00:02.000\nshared\nlast\n')
        self.assertEqual(subtitles.clean_text(cues), 'first\nshared\nlast\n')

    def test_touching_actual_repetition_preserved(self):
        cues = subtitles.parse_subtitles('WEBVTT\n\n00:00.000 --> 00:01.000\nYes\n\n00:01.000 --> 00:02.000\nYes\n')
        self.assertEqual(subtitles.clean_text(cues), 'Yes\nYes\n')

    def test_source_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'talk.en.vtt'
            p.write_text('WEBVTT\n\n00:00.000 --> 00:01.000\n128 GB\n',encoding='utf-8')
            result=online.caption_document(p, {'automatic_captions':{'en':[]}, 'duration':2})
            self.assertEqual(result['kind'], 'automatic')
            self.assertEqual(result['language'], 'en')
            self.assertEqual(result['quality']['timeline_fraction'], 0.5)
            self.assertEqual(result['raw'], p.read_text(encoding='utf-8'))
            self.assertFalse(result['quality']['coverage_is_accuracy'])


class CaptureTests(unittest.TestCase):
    def test_persisted_tool_profile_without_global_environment(self):
        with tempfile.TemporaryDirectory() as td:
            config=Path(td)/'tools.json'
            config.write_text(json.dumps({'test-python':sys.executable}))
            runner=Runner(tool_config=config)
            self.assertEqual(runner.run('test-python',['-c','print(128)']).strip(),'128')

    def test_large_structured_output_not_truncated(self):
        with patch.dict('os.environ', {'MEDIA_TEST_PYTHON': sys.executable}):
            output = Runner().run('test-python', ['-c', "print('x'*100000)"])
        self.assertEqual(len(output.strip()), 100000)

    def test_huge_output_is_explicit_failure_not_invalid_json(self):
        with patch.dict('os.environ', {'MEDIA_TEST_PYTHON':sys.executable}):
            with self.assertRaises(ToolkitError) as caught:
                Runner().run('test-python',['-c',"print('x'*(17*1024*1024))"])
            self.assertEqual(caught.exception.code,'output_too_large')


class CollectionTests(unittest.TestCase):
    def test_collection_available(self):
        from media_toolkit import collection
        self.assertTrue(callable(collection.collect))

    def test_pagination_dedup_resume_and_exhaustion(self):
        from media_toolkit import collection
        calls = []
        def page(runner, query, start, size, js_runtime=None):
            calls.append(start)
            return [{'id': i, 'title': '<script>bad</script>'} for i in {1:['abcdefghijk','bcdefghijkl'],3:['bcdefghijkl','cdefghijklm'],5:[]}[start]]
        with tempfile.TemporaryDirectory() as td, patch.object(collection, 'search_page', side_effect=page):
            first = collection.collect(Runner(), ['topic'], td, page_size=2, max_pages=1)
            self.assertEqual(first['status'], 'partial')
            self.assertFalse(first['coverage']['all_platform_videos'])
            second = collection.collect(Runner(), ['topic'], td, page_size=2, max_pages=5)
            self.assertEqual(second['status'], 'source_exhausted')
            self.assertEqual(second['counts']['videos'], 3)
            self.assertEqual(calls, [1,3,5])
            self.assertNotIn('<script>bad', (Path(td)/'index.html').read_text(encoding='utf-8'))
            collection.collect(Runner(), ['topic'], td, page_size=2)
            self.assertEqual(calls, [1,3,5])
            with self.assertRaises(ToolkitError):
                collection.collect(Runner(), ['other'], td)

    def test_resource_limit_keeps_cursor(self):
        from media_toolkit import collection
        page = [{'id': i} for i in ['abcdefghijk','bcdefghijkl']]
        with tempfile.TemporaryDirectory() as td, patch.object(collection, 'search_page', return_value=page):
            result = collection.collect(Runner(), ['topic'], td, page_size=2, max_videos=1)
            self.assertEqual(result['status'], 'partial')
            state = json.loads((Path(td)/'state.json').read_text())
            self.assertEqual(state['queries'][0]['next_start'], 1)

    def test_rate_limit_checkpoint(self):
        from media_toolkit import collection
        with tempfile.TemporaryDirectory() as td, patch.object(collection, 'search_page', side_effect=ToolkitError('429','rate_limit')):
            result = collection.collect(Runner(), ['topic'], td)
            self.assertFalse(result['ok'])
            self.assertEqual(result['stop_reason'], 'rate_limit')
            self.assertTrue((Path(td)/'index.html').exists())

    def test_lock_refuses_concurrent_writer(self):
        from media_toolkit import collection
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/'.job.lock').write_text('other')
            with self.assertRaises(ToolkitError):
                collection.collect(Runner(), ['topic'], td)

    def test_receipt_requires_hash_and_status(self):
        from media_toolkit import collection
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'caption.json'; p.write_text('{}')
            self.assertFalse(collection.verified_artifact(p))
            Path(str(p)+'.result.json').write_text(json.dumps({'ok':True,'sha256':'wrong','bytes':2}))
            self.assertFalse(collection.verified_artifact(p))


class BatchTests(unittest.TestCase):
    def test_audio_acquisition_available(self):
        self.assertTrue(callable(getattr(online, 'download_audio', None)))

    def test_resume_recovers_published_receipt_without_redownload(self):
        from media_toolkit import collection
        from media_toolkit.runtime import Artifact
        with tempfile.TemporaryDirectory() as td, patch.object(collection, 'search_page', return_value=[{'id':'abcdefghijk'}]):
            collection.collect(Runner(), ['topic'], td)
            target=Path(td)/'subtitles/abcdefghijk.json'
            with Artifact(target) as artifact:
                artifact.path.write_text('{}')
                artifact.publish({'command':'fetch-subs','source':'https://www.youtube.com/watch?v=abcdefghijk'})
            with patch.object(online,'fetch_subs',side_effect=AssertionError('must not download again')):
                result=collection.batch(Runner(),td)
            self.assertEqual(result['counts']['success'],1)
            self.assertEqual(result['processed'],0)

    def test_failure_and_explicit_retry(self):
        from media_toolkit import collection
        with tempfile.TemporaryDirectory() as td, patch.object(collection, 'search_page', return_value=[{'id':'abcdefghijk'}]):
            collection.collect(Runner(), ['topic'], td)
            with patch.object(online,'fetch_subs',side_effect=ToolkitError('No captions','subtitles_unavailable')) as fetch:
                result=collection.batch(Runner(),td)
                self.assertEqual(result['counts']['failed'],1)
                collection.batch(Runner(),td)
                self.assertEqual(fetch.call_count,1)
                collection.batch(Runner(),td,retry_failed=True)
                self.assertEqual(fetch.call_count,2)

    def test_download_requires_channel_allowlist(self):
        from media_toolkit import collection
        with self.assertRaises(ToolkitError):
            collection.batch(Runner(),'unused',stage='download')

    def test_asr_capability_exists(self):
        from media_toolkit import transcription
        self.assertTrue(callable(transcription.transcribe))

    def test_tampered_success_becomes_failure_without_overwrite(self):
        from media_toolkit import collection
        from media_toolkit.runtime import Artifact
        with tempfile.TemporaryDirectory() as td, patch.object(collection,'search_page',return_value=[{'id':'abcdefghijk'}]):
            collection.collect(Runner(),['topic'],td)
            target=Path(td)/'subtitles/abcdefghijk.json'
            with Artifact(target) as artifact:
                artifact.path.write_text('{}')
                artifact.publish({'command':'fetch-subs','source':'https://www.youtube.com/watch?v=abcdefghijk'})
            target.write_text('tampered')
            result=collection.batch(Runner(),td)
            self.assertEqual(result['counts']['failed'],1)
            self.assertEqual(target.read_text(),'tampered')

    def test_access_denial_stops_batch_before_next_video(self):
        from media_toolkit import collection
        entries=[{'id':'abcdefghijk'},{'id':'bcdefghijkl'}]
        with tempfile.TemporaryDirectory() as td, patch.object(collection,'search_page',return_value=entries):
            collection.collect(Runner(),['topic'],td)
            with patch.object(online,'fetch_subs',side_effect=ToolkitError('403','access_denied')) as fetch:
                result=collection.batch(Runner(),td)
            self.assertEqual(fetch.call_count,1)
            self.assertEqual(result['stop_reason'],'access_denied')
            self.assertEqual(result['counts']['pending'],1)

    def test_download_excludes_wrong_channel_before_media_acquisition(self):
        from media_toolkit import collection
        with tempfile.TemporaryDirectory() as td, patch.object(collection,'search_page',return_value=[{'id':'abcdefghijk'}]):
            collection.collect(Runner(),['topic'],td)
            runner=Runner()
            with patch.object(runner,'run',return_value=json.dumps({'channel_id':'UC_OTHER'})), patch.object(online,'download') as download:
                result=collection.batch(runner,td,stage='download',channel_ids=['UC_ALLOWED'])
            download.assert_not_called()
            self.assertEqual(result['counts']['excluded'],1)


class ASRTests(unittest.TestCase):
    def test_download_is_opt_in_and_source_hash_preserved(self):
        from media_toolkit import transcription
        class FakeRunner:
            events=[]
            def run(self,name,args):
                config=json.loads(Path(args[1]).read_text(encoding='utf-8'))
                assert config['allow_model_download'] is False
                Path(config['output']).write_text(json.dumps({'language':'en','cues':[{'start':0,'end':1,'text':'128 GB'}]}))
                return '{"ok":true}'
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'audio.wav'; source.write_bytes(b'fixture')
            output=Path(td)/'asr.json'
            receipt=transcription.transcribe(FakeRunner(),source,output,cache_dir=Path(td)/'models')
            result=json.loads(output.read_text())
            self.assertEqual(result['source_sha256'],__import__('hashlib').sha256(b'fixture').hexdigest())
            self.assertFalse(receipt['validated']['accuracy_certified'])

    def test_no_speech_does_not_publish(self):
        from media_toolkit import transcription
        runner=Runner()
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'source'; source.write_bytes(b'fixture')
            output=Path(td)/'result.json'
            def worker(name,args):
                config=json.loads(Path(args[1]).read_text())
                Path(config['output']).write_text('{"cues":[],"language":"en"}')
                return '{"ok":true}'
            with patch.object(runner,'run',side_effect=worker), self.assertRaises(ToolkitError) as caught:
                transcription.transcribe(runner,source,output,cache_dir=Path(td)/'models')
            self.assertEqual(caught.exception.code,'asr_empty')
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
