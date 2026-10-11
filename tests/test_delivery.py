import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from media_toolkit import collection, online, cli
from media_toolkit.runtime import Runner, ToolkitError


class DeliveryTests(unittest.TestCase):
    def test_two_queries_share_budget_fairly_and_resume_next_query(self):
        calls=[]
        def page(r,q,start,size,js_runtime=None):
            calls.append((q,start))
            return [{'id':'abcdefghijk' if q=='one' else 'bcdefghijkl'}]
        with tempfile.TemporaryDirectory() as td,patch.object(collection,'search_page',side_effect=page):
            collection.collect(Runner(),['one','two'],td,page_size=1,max_pages=1)
            collection.collect(Runner(),['one','two'],td,page_size=1,max_pages=1)
        self.assertEqual(calls,[('one',1),('two',1)])

    def test_date_search_and_sort_change_refused(self):
        class Fake:
            def run(self,name,args):
                self.args=args
                return '{"entries":[]}'
        r=Fake()
        self.assertIn('sort',collection.search_page.__code__.co_varnames)
        collection.search_page(r,'topic',1,5,sort='date')
        self.assertIn('ytsearchdateall:topic',r.args)
        with tempfile.TemporaryDirectory() as td:
            collection.collect(r,['topic'],td,sort='date')
            with self.assertRaises(ToolkitError): collection.collect(r,['topic'],td,sort='relevance')

    def test_failed_download_retains_parts_and_resumes_without_overwrite(self):
        class Fake:
            events=[]
            fail=True
            def tool(self,name): return sys.executable
            def run(self,name,args):
                directory=Path(args[args.index('-o')+1]).parent
                if self.fail:
                    (directory/'download.f401.mp4.part').write_bytes(b'partial')
                    raise ToolkitError('timeout','timeout')
                assert (directory/'download.f401.mp4.part').read_bytes()==b'partial'
                (directory/'download.mp4').write_bytes(b'complete')
                return ''
            def validate_media(self,path,**kwargs):
                return {'format':{'duration':'1'},'streams':[{'codec_type':'video','codec_name':'av1','width':3840,'height':2160},{'codec_type':'audio','codec_name':'opus'}]}
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'video.mp4';r=Fake()
            with self.assertRaises(ToolkitError): online.download(r,'https://youtu.be/abcdefghijk',target)
            self.assertTrue((Path(str(target)+'.download')/'download.f401.mp4.part').exists())
            with self.assertRaises(ToolkitError): online.download(r,'https://youtu.be/bcdefghijkl',target)
            r.fail=False
            result=online.download(r,'https://youtu.be/abcdefghijk',target)
            self.assertTrue(result['ok'])
            self.assertEqual(target.read_bytes(),b'complete')

    def test_progress_is_available_while_process_runs(self):
        self.assertIn('progress_dir',Runner.__init__.__code__.co_varnames)
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'tools.json';cfg.write_text(json.dumps({'test-python':sys.executable}))
            r=Runner(tool_config=cfg,progress_dir=Path(td)/'progress')
            errors=[]
            def run():
                try:r.run('test-python',['-u','-c','import time; print(\'MTK_PROGRESS:{"downloaded_bytes":128,"url":"secret"}\',flush=True); time.sleep(0.6)'])
                except BaseException as exc:errors.append(exc)
            worker=threading.Thread(target=run);worker.start()
            snapshot=Path(td)/'progress/current.json';deadline=time.monotonic()+1
            live=None
            while time.monotonic()<deadline and worker.is_alive():
                if snapshot.exists():
                    data=json.loads(snapshot.read_text())
                    if 'progress' in data:live=data;break
                time.sleep(.01)
            self.assertIsNotNone(live)
            self.assertTrue(worker.is_alive())
            worker.join();self.assertEqual(errors,[])
            self.assertNotIn('secret',(Path(td)/'progress/events.jsonl').read_text())
            events=[json.loads(line) for line in (Path(td)/'progress/events.jsonl').read_text().splitlines()]
            self.assertEqual(events[0]['status'],'running')
            self.assertEqual(events[-1]['status'],'success')

    def test_download_default_budget_exceeds_observed_success(self):
        self.assertTrue(callable(getattr(cli,'default_timeout',None)))
        self.assertGreaterEqual(cli.default_timeout('download'),1800)

    def test_project_module_exists(self):
        self.assertTrue((Path(__file__).resolve().parents[1]/'scripts/media_toolkit/project.py').exists())

    def test_project_cannot_complete_without_report_or_drop_selected_downloads(self):
        self.assertTrue((Path(__file__).resolve().parents[1]/'scripts/media_toolkit/project.py').exists())
        from media_toolkit import project
        from media_toolkit.runtime import Artifact
        def publish(r,url,target,**kwargs):
            with Artifact(target) as a:
                a.path.write_text(json.dumps({'source':url,'cues':[{'start':0,'end':1,'text':'128 GB'}]}))
                return a.publish({'source':url,'command':'fetch-subs' if str(target).endswith('.json') else 'download'})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'job'; req=Path(td)/'request.json'
            req.write_text(json.dumps({'request':'report and videos','queries':['topic'],'seed_videos':[{'id':'abcdefghijk'},{'id':'bcdefghijkl'}]}))
            project.init(req,root)
            project.select(root,['abcdefghijk','bcdefghijkl'],['abcdefghijk','bcdefghijkl'],'test sources')
            with patch.object(collection,'collect',return_value={'ok':True}),patch.object(online,'fetch_subs',side_effect=publish),patch.object(online,'download',side_effect=publish):
                first=project.run(Runner(),root)
            self.assertEqual(first['status'],'awaiting_report')
            self.assertFalse(first['ok'])
            self.assertTrue((root/'videos/abcdefghijk.mp4').exists())
            self.assertTrue((root/'videos/bcdefghijkl.mp4').exists())
            claims=Path(td)/'claims.json'
            claims.write_text(json.dumps({'title':'report','claims':[{'transcript':str(root/'transcripts'/f'{i}.json'),'cue':0,'quote':'128 GB','statement':'128 GB','kind':'speaker'} for i in ['abcdefghijk','bcdefghijkl']]}))
            done=project.publish_report(Runner(),root,claims)
            self.assertTrue(done['ok'])
            self.assertEqual(done['status'],'success')
            # Simulate a crash after report publication before checkpoint save.
            state=project.read(root);state['report']=None;project.save(root,state)
            self.assertTrue(project.publish_report(Runner(),root,claims)['complete'])
            with patch.object(online,'fetch_subs') as subs,patch.object(online,'download') as video:
                self.assertTrue(project.run(Runner(),root)['complete'])
                subs.assert_not_called();video.assert_not_called()
            (root/'videos/abcdefghijk.mp4').write_bytes(b'tampered')
            self.assertFalse(project.status(root)['ok'])
            self.assertEqual(project.status(root)['status'],'partial')

    def test_project_subtitle_failure_falls_back_and_asr_error_is_not_success(self):
        self.assertTrue((Path(__file__).resolve().parents[1]/'scripts/media_toolkit/project.py').exists())
        from media_toolkit import project,transcription
        from media_toolkit.runtime import Artifact
        def audio(r,url,target,**kwargs):
            with Artifact(target) as a:
                a.path.write_bytes(b'audio');return a.publish({'source':url,'command':'download-audio'})
        def asr(r,source,target,**kwargs):
            with Artifact(target) as a:
                a.path.write_text(json.dumps({'source':str(source),'cues':[{'start':0,'end':1,'text':'128 GB'}]}));return a.publish({'source':str(source),'command':'transcribe'})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'job';req=Path(td)/'r.json'
            req.write_text(json.dumps({'request':'report','queries':['topic'],'seed_videos':[{'id':'abcdefghijk'}],'asr':{'enabled':True}}))
            project.init(req,root);project.select(root,['abcdefghijk'],[],'test')
            with patch.object(collection,'collect',return_value={'ok':True}),patch.object(online,'fetch_subs',side_effect=ToolkitError('429','rate_limit')),patch.object(online,'download_audio',side_effect=audio),patch.object(transcription,'transcribe',side_effect=asr):
                result=project.run(Runner(),root)
            self.assertEqual(result['status'],'awaiting_report')
            doc=json.loads((root/'transcripts/abcdefghijk.json').read_text())
            self.assertEqual(doc['source'],'https://www.youtube.com/watch?v=abcdefghijk')
            self.assertEqual(doc['cues'][0]['text'],'128 GB')

    def test_failed_transcript_does_not_skip_requested_video_on_resume(self):
        from media_toolkit import project
        from media_toolkit.runtime import Artifact
        calls=[]
        def download(r,url,target,**kwargs):
            calls.append(url)
            with Artifact(target) as a:
                a.path.write_bytes(b'video');return a.publish({'source':url,'command':'download'})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'job';req=Path(td)/'request.json'
            req.write_text(json.dumps({'request':'report+video','queries':['topic'],'seed_videos':[{'id':'abcdefghijk'}],'asr':{'enabled':False}}))
            project.init(req,root);project.select(root,['abcdefghijk'],['abcdefghijk'],'selected')
            state=project.read(root);state['search']={'ok':True};state['selected']['abcdefghijk']['stages']['transcript']={'status':'failed'};project.save(root,state)
            with patch.object(online,'download',side_effect=download):result=project.run(Runner(),root)
            self.assertEqual(len(calls),1)
            self.assertEqual(result['status'],'partial')

    def test_timeout_and_cancel_are_distinct_progress_states(self):
        with tempfile.TemporaryDirectory() as td:
            cfg=Path(td)/'tools.json';cfg.write_text(json.dumps({'test-python':sys.executable}))
            runner=Runner(timeout=.15,tool_config=cfg,progress_dir=Path(td)/'progress')
            with self.assertRaises(ToolkitError) as error:
                runner.run('test-python',['-c','import time; time.sleep(10)'])
            self.assertEqual(error.exception.code,'timeout')
            self.assertEqual(json.loads((Path(td)/'progress/current.json').read_text())['status'],'timeout')
            with patch('media_toolkit.runtime.subprocess.Popen',side_effect=KeyboardInterrupt):
                with self.assertRaises(ToolkitError) as error:runner.run('test-python',[])
            self.assertEqual(error.exception.code,'cancelled')
            self.assertEqual(json.loads((Path(td)/'progress/current.json').read_text())['status'],'cancelled')

    def test_asr_failure_stays_partial_and_explicit_retry_is_required(self):
        from media_toolkit import project,transcription
        from media_toolkit.runtime import Artifact
        def audio(r,url,target,**kwargs):
            with Artifact(target) as a:
                a.path.write_bytes(b'audio');return a.publish({'source':url,'command':'download-audio'})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'job';req=Path(td)/'r.json'
            req.write_text(json.dumps({'request':'report','queries':['topic'],'seed_videos':[{'id':'abcdefghijk'}]}))
            project.init(req,root);project.select(root,['abcdefghijk'],[],'test')
            with patch.object(collection,'collect',return_value={'ok':True}),patch.object(online,'fetch_subs',side_effect=ToolkitError('429','rate_limit')),patch.object(online,'download_audio',side_effect=audio),patch.object(transcription,'transcribe',side_effect=ToolkitError('model missing','model_missing')) as speech:
                first=project.run(Runner(),root)
                second=project.run(Runner(),root)
            self.assertEqual(first['status'],'partial');self.assertFalse(second['complete'])
            self.assertEqual(speech.call_count,1)
            self.assertEqual(project.read(root)['selected']['abcdefghijk']['stages']['transcript']['error']['code'],'model_missing')

    def test_relative_profile_resolves_after_move(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);tools=root/'tools';tools.mkdir()
            import shutil
            shutil.copy2(sys.executable,tools/'python.exe')
            config=root/'profile.json';config.write_text(json.dumps({'python':'tools/python.exe'}))
            self.assertEqual(Path(Runner(tool_config=config).tool('python')),tools/'python.exe')

    def test_concurrent_transfer_is_refused_before_running_tools(self):
        class Fake:
            def tool(self,name):return sys.executable
            def run(self,*args):raise AssertionError('Locked transfer must not execute')
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'video.mp4'
            with collection.job(Path(str(target)+'.download')):
                with self.assertRaises(ToolkitError) as error:online.download(Fake(),'https://youtu.be/abcdefghijk',target)
            self.assertEqual(error.exception.code,'job_locked')

    def test_invalid_request_types_and_unselected_report_are_rejected(self):
        from media_toolkit import project
        with tempfile.TemporaryDirectory() as td:
            req=Path(td)/'r.json';root=Path(td)/'job'
            req.write_text(json.dumps({'request':'report','queries':['topic'],'asr':{'enabled':'false'}}))
            with self.assertRaises(ToolkitError) as error:project.init(req,root)
            self.assertEqual(error.exception.code,'invalid_argument')
            req.write_text(json.dumps({'request':'report','queries':['topic'],'seed_videos':[{'id':'abcdefghijk'}]}))
            project.init(req,root);project.select(root,['abcdefghijk'],[],'test')
            claims=Path(td)/'c.json';claims.write_text(json.dumps({'claims':[{'transcript':'unselected.json'}]}))
            with self.assertRaises(ToolkitError) as error:project.publish_report(Runner(),root,claims)
            self.assertEqual(error.exception.code,'evidence_invalid')
            self.assertFalse((root/'report.md').exists())

if __name__=='__main__':unittest.main()
