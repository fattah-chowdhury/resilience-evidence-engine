"""Operational checks use unittest so recovery checks need no test-framework download.
All constructed records are synthetic. The earlier pytest suite remains unchanged except
for its explicit software-version provenance tolerance assertion.
"""
import csv
import importlib.util
import io
import json
import socket
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from ree.cache import CatalogCache
from ree.cli import main, reference_config
from ree.config import ProjectConfig, load_config
from ree.exporters import file_hashes, write_json
from ree.ingestion import ingest_file
from ree.integrity import validate_run
from ree.models import Record, digest
from ree.operations import compare_runs, resume_run
from ree.pipeline import RunFailure, dataset_digest, process_records, processing_assets, run
from ree.review import apply_event_links, apply_review
from ree.sources import USGSAdapter, asset, collect_adapter, discover, fetch_catalog

REPO = Path(__file__).resolve().parents[1]
URL = 'https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def live_config():
    return ProjectConfig(project={'name': 'synthetic-live'}, mode='live', topics=['earthquake'],
                         collection={'public_sources': True}, time={'start': '2024-01-01', 'end': '2024-01-02'})


def record(index=1, **overrides):
    return Record.model_validate({'source_record_id': str(index), 'source_id': 'usgs_pages',
        'text': 'Synthetic flood in Japan on 2024-01-01.', 'country': 'Japan',
        'category': 'flood', 'sensitive': False, **overrides})


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def process(self, records, config=None, registry=None):
        config = config or reference_config()
        return process_records(records, registry or asset('source_registry.json'), config,
                               processing_assets(config, self.root))

    def local(self, names=('a.json',)):
        return ProjectConfig(project={'name': 'local'}, mode='local', inputs=[{'path': n} for n in names])

    def file(self, name='a.json', text='Synthetic flood on 2024-01-01'):
        write_json(self.root/name, [{'text': text, 'location_text': 'Japan'}])

    def demo(self):
        return run(reference_config(), output=self.root)

    def test_frozen_values_and_only_declared_version_tolerance(self):
        with patch.object(socket, 'getaddrinfo', side_effect=AssertionError('network used')):
            root, manifest = self.demo()
        self.assertFalse(validate_run(root)[1])
        self.assertEqual(manifest['record_counts'], asset('expected.json')['record_counts'])
        tables, *_ = self.process([Record.model_validate(r) for r in asset('frozen.json')])
        expected = asset('expected.json')
        self.assertEqual(dataset_digest(tables, expected['ree_version']), expected['dataset_hash'])
        self.assertNotEqual(dataset_digest(tables), expected['dataset_hash'])
        tables['claim'][0]['statement'] += ' drift'
        self.assertNotEqual(dataset_digest(tables, expected['ree_version']), expected['dataset_hash'])

    def test_discovery_contains_actionable_metadata(self):
        rows = discover(live_config())
        for row in rows:
            self.assertTrue({'provider','source_type','access_method','license','geographic_coverage',
                'temporal_coverage','authentication_required','scope','reasons'} <= row.keys())
        self.assertTrue(next(r for r in rows if r['id']=='usgs_catalog')['live_eligible'])
        self.assertFalse(next(r for r in rows if r['id']=='reliefweb')['live_eligible'])

    def test_cache_reuses_original_provenance(self):
        calls=[]
        cache=CatalogCache(self.root,fetcher=lambda *_: calls.append(1) or {'type':'FeatureCollection','features':[]})
        cache(URL,live_config()); provenance=cache.access.copy()
        cache(URL,live_config())
        self.assertEqual(calls,[1]); self.assertEqual(cache.access['status'],'cache_hit')
        self.assertEqual(cache.access['fetched_at'],provenance['fetched_at'])
        self.assertEqual(cache.access['body_hash'],provenance['body_hash'])
        self.assertTrue(cache.status()['entries'][0]['valid'])

    def test_cache_only_and_expired_never_call_transport(self):
        cache=CatalogCache(self.root,mode='only',fetcher=lambda *_: self.fail('network'))
        with self.assertRaisesRegex(ValueError,'fresh cached'): cache(URL,live_config())
        cache.mode='reuse'; cache.fetcher=lambda *_: {'type':'FeatureCollection','features':[]}
        cache(URL,live_config()); cache.ttl=0; cache.mode='only'
        with self.assertRaises(ValueError): cache(URL,live_config())

    def test_cache_refresh_and_clear_preserve_unrelated_files(self):
        calls=[]
        cache=CatalogCache(self.root,fetcher=lambda *_: calls.append(1) or {'type':'FeatureCollection','features':[]})
        cache(URL,live_config()); cache.mode='refresh'; cache(URL,live_config())
        self.assertEqual(len(calls),2)
        unrelated=cache.root/'notes.json'; unrelated.write_text('{}')
        self.assertEqual(cache.clear(),{'removed_entries':1}); self.assertTrue(unrelated.exists())

    def test_cache_corruption_is_not_silently_replaced(self):
        for key,value in [('body_hash','bad'),('fetched_at','3000-01-01T00:00:00+00:00'),
                          ('request_url','https://127.0.0.1/secret'),('body',{'error':'bad'})]:
            with self.subTest(key=key):
                cache=CatalogCache(self.root/key,fetcher=lambda *_: {'type':'FeatureCollection','features':[]})
                cache(URL,live_config()); path=cache.entries()[0]; data=read(path); data[key]=value; write_json(path,data)
                with self.assertRaisesRegex(ValueError,'Corrupt cache'): cache(URL,live_config())
                self.assertFalse(cache.status()['entries'][0]['valid'])

    def test_cache_refuses_symlinks_and_unapproved_body(self):
        cache=CatalogCache(self.root); cache.root.mkdir()
        outside=self.root/'outside.json'; outside.write_text('{}')
        (cache.root/(digest(URL)+'.json')).symlink_to(outside)
        with self.assertRaises(ValueError): cache(URL,live_config())
        with self.assertRaises(ValueError): cache.clear()
        self.assertTrue(outside.exists())
        cache=CatalogCache(self.root/'bad',fetcher=lambda *_: {'error':'synthetic error'})
        with self.assertRaises(ValueError): cache(URL,live_config())
        self.assertFalse(cache.entries())

    def test_resume_keeps_finished_inputs_and_original_config_base(self):
        self.file()
        with self.assertRaises(RunFailure) as failed: run(self.local(('a.json','b.json')),base=self.root)
        parent=failed.exception.output; before=file_hashes(parent)
        (self.root/'a.json').unlink(); self.file('b.json','Synthetic cyclone test')
        child,manifest=resume_run(parent,output=self.root/'resumed')
        self.assertEqual(manifest['record_counts']['documents'],2)
        self.assertEqual(manifest['parent_run'],parent.name)
        self.assertEqual(before,file_hashes(parent)); self.assertFalse(validate_run(child)[1])

    def test_resume_downstream_failure_needs_no_original_input(self):
        self.file()
        with (
            patch('ree.pipeline.export_all', side_effect=OSError('synthetic disk failure')),
            self.assertRaises(RunFailure) as failed,
        ):
            run(self.local(), base=self.root)
        (self.root/'a.json').unlink()
        child,manifest=resume_run(failed.exception.output,output=self.root/'resumed')
        self.assertEqual(manifest['status'],'succeeded'); self.assertFalse(validate_run(child)[1])

    def test_live_timeout_and_explicit_resume(self):
        with (
            patch.object(USGSAdapter, 'collect', side_effect=TimeoutError('synthetic timeout')),
            self.assertRaises(RunFailure) as failed,
        ):
            run(live_config(), output=self.root, live=True)
        parent=failed.exception.output
        with self.assertRaisesRegex(ValueError,'--live'): resume_run(parent)
        with patch.object(USGSAdapter,'collect',return_value=([],[])):
            child,manifest=resume_run(parent,output=self.root,live=True)
        self.assertEqual(manifest['record_counts']['documents'],0); self.assertFalse(validate_run(child)[1])

    def test_corrupt_checkpoint_refused(self):
        with self.assertRaises(RunFailure) as failed: run(self.local(),base=self.root)
        (failed.exception.output/'provenance/acquisition_checkpoint.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Changed output'): resume_run(failed.exception.output)

    def test_partial_replay_preserves_failures(self):
        write_json(self.root/'a.json',[{'text':'Synthetic flood'},{'text':''}])
        parent,before=run(self.local(),base=self.root)
        child,after=resume_run(parent,output=self.root/'resumed')
        self.assertEqual(before['status'], 'partial'); self.assertEqual(after['status'],'partial')
        self.assertEqual(before['failed_records'],after['failed_records']); self.assertFalse(validate_run(child)[1])

    def test_public_checkpoint_and_exports_suppress_private_canary(self):
        canary='SYNTHETIC_PRIVATE_CANARY_8491'; self.file(text=canary)
        config=ProjectConfig(project={'name':'privacy'},mode='hybrid',inputs=[{'path':'a.json'}],
                             topics=['earthquake'],export_policy='public',collection={'public_sources':True})
        with (
            patch.object(USGSAdapter, 'collect', side_effect=OSError('synthetic unavailable')),
            self.assertRaises(RunFailure) as failed,
        ):
            run(config, base=self.root, live=True)
        for path in failed.exception.output.rglob('*'):
            if path.is_file(): self.assertNotIn(canary.encode(),path.read_bytes())

    def test_integrity_inventory_counts_and_config(self):
        for mutation in ['inventory','extra','nested_manifest','counts','digest','config']:
            with self.subTest(mutation=mutation):
                root,manifest=self.demo()
                if mutation=='inventory': manifest['export_files'].pop('data/claims.csv')
                elif mutation=='extra': (root/'untracked.txt').write_text('unexpected')
                elif mutation=='nested_manifest': (root/'data/run_manifest.json').write_text('{}')
                elif mutation=='counts': manifest['record_counts']['claims']=99
                elif mutation=='digest': manifest['dataset_hash']='bad'
                else: manifest['config_hash']='bad'
                write_json(root/'provenance/run_manifest.json',manifest)
                self.assertTrue(validate_run(root)[1])
        root,_=self.demo()
        write_json(root/'provenance/run_manifest.json',[])
        with self.assertRaisesRegex(ValueError,'JSON object'): validate_run(root)
        with self.assertRaisesRegex(ValueError,'JSON object'): resume_run(root)

    def test_event_geometry_and_link_corruption_detected(self):
        root,manifest=self.demo()
        with sqlite3.connect(root/'data/evidence.sqlite') as db:
            eid,raw=db.execute('SELECT event_id,metadata_json FROM event LIMIT 1').fetchone()
            data=json.loads(raw); data['geometry']={'type':'Point','coordinates':[999,999]}
            db.execute('UPDATE event SET metadata_json=? WHERE event_id=?',(json.dumps(data),eid))
        manifest['export_files']=file_hashes(root); write_json(root/'provenance/run_manifest.json',manifest)
        self.assertTrue(any('geometry' in p for p in validate_run(root)[1]))

    def test_review_context_preserves_location_time_uncertainty(self):
        root,_=self.demo(); rows=read(root/'review/context.json')
        row=next(r for r in rows if r['original_location']=='Sylhet')
        self.assertTrue(row['original_text']); self.assertTrue(row['url'].startswith('https://'))
        self.assertEqual(len(row['candidates']),2); self.assertIsNone(row['time_interpretation']['start'])
        self.assertTrue(all(c['confidence'] is None and c['parent_geography'] for c in row['candidates']))

    def test_provider_updates_keep_distinct_location_versions(self):
        a=record(provider_event_id='synthetic-one',geometry={'type':'Point','coordinates':[90,24]},geometry_role='source_point')
        b=a.model_copy(update={'geometry':{'type':'Point','coordinates':[91,24]}})
        tables,events,*_=self.process([a,b])
        self.assertEqual(len(tables['location']),2)
        self.assertEqual(len({r['location_id'] for r in tables['claim_location']}),2)
        self.assertEqual(len(events),1); self.assertTrue(events[0]['geometry_conflict']); self.assertIsNone(events[0]['geometry'])

    def test_copy_detection_and_event_identity_are_separate(self):
        records=[record(i,location_text='Japan',date_text='2024-01-01') for i in [1,2]]
        tables,events,proposals,*_=self.process(records)
        self.assertEqual(len(events),2); self.assertEqual(len(proposals),1)
        self.assertEqual(len(tables['document_duplicate']),1)

    def test_syndicated_reports_do_not_inflate_corroboration(self):
        a=record(1,provider_event_id='shared'); b=record(2,provider_event_id='shared')
        _,events,*_=self.process([a,b]); self.assertEqual(events[0]['independent_source_groups'],1)

    def test_duplicate_provenance_references_only_its_document_pair(self):
        tables, *_ = self.process([record(i) for i in range(3)])
        transforms = [json.loads(r['transformation_json']) for r in tables['provenance']
                      if r['entity'] == 'document_duplicate']
        self.assertTrue(transforms)
        self.assertTrue(all(len(r['input_hashes']) == 2 for r in transforms))

    def test_unsupported_language_and_bad_gazetteer_are_explicit(self):
        config=ProjectConfig(project={'name':'french'},languages=['fr'],topics=['flood'])
        result=self.process([record(language='fr')],config)
        self.assertIn('unsupported_language',result[4][0]['reason'])
        path=self.root/'bad.json'; write_json(path,[{'id':'missing-fields'}])
        config=ProjectConfig(project={'name':'bad'},processing={'gazetteer':str(path)})
        with self.assertRaises(ValueError): processing_assets(config,self.root)

    def test_configuration_examples_without_code_changes(self):
        for name,claims in [('configs/examples/bangladesh_excerpt.yml',1),('examples/custom_csv/project.yml',3),
                            ('examples/cyclone_monitoring/project.yml',1),('examples/custom_csv/kenya.yml',1)]:
            with self.subTest(name=name):
                path=REPO/name; root,manifest=run(load_config(path),base=path.parent,output=self.root)
                self.assertEqual(manifest['record_counts']['claims'],claims); self.assertFalse(validate_run(root)[1])

    def test_external_adapter_documented_contract(self):
        spec=importlib.util.spec_from_file_location('external_fixture',REPO/'examples/external_adapter/adapter.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        config=live_config().model_copy(update={'collection':live_config().collection.model_copy(update={'sources':[module.SOURCE['id']]})})
        root,manifest=run(config,output=self.root,live=True,adapters={module.SOURCE['id']:module.FixtureAdapter},source_registry=[module.SOURCE])
        self.assertEqual(manifest['record_counts']['claims'],1); self.assertFalse(validate_run(root)[1])
        self.assertFalse(manifest['collections'][0]['network_used'])
        with self.assertRaises(TypeError): collect_adapter(object(),config,module.SOURCE)
        adapter=module.FixtureAdapter(); adapter.collect=lambda _: ([record()],[])
        with self.assertRaisesRegex(ValueError,'source_id'): collect_adapter(adapter,config,module.SOURCE)

    def test_transport_rate_limit_then_success_and_malformed_response(self):
        class Response(io.BytesIO): status=200
        attempts=[]; delays=[]
        class Opener:
            def open(self,request,timeout):
                attempts.append(1)
                if len(attempts)==1: raise HTTPError(URL,429,'',{'Retry-After':'2'},None)
                return Response(b'{"type":"FeatureCollection","features":[]}')
        resolver=lambda *a,**k:[(None,None,None,None,('8.8.8.8',443))]
        self.assertEqual(fetch_catalog(URL,live_config(),opener=Opener(),resolver=resolver,pause=delays.append)['features'],[])
        self.assertEqual(delays,[2])
        adapter=USGSAdapter(fetcher=lambda *_:{'malformed':True})
        with self.assertRaises(ValueError): adapter.collect(live_config())

    def test_utf8_csv_and_geojson_geometry_roundtrip(self):
        root,_=self.demo()
        with (root/'data/claims.csv').open(encoding='utf-8',newline='') as f: self.assertEqual(len(list(csv.DictReader(f))),5)
        geo=read(root/'gis/events.geojson'); self.assertEqual(len(geo['features']),4)
        self.assertEqual(sum(f['geometry'] is not None for f in geo['features']),2)
        self.assertEqual(sum(bool(f['properties']['representational']) for f in geo['features']),1)

    def test_claim_and_event_link_review_are_immutable(self):
        root,_=self.demo(); before=file_hashes(root)
        rows=read(root/'review/context.json'); row=next(r for r in rows if r['original_location']=='Sylhet')
        path=self.root/'decisions.csv'
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['review_id','decision','reviewer','note','location_id']); w.writeheader()
            w.writerow({'review_id':row['review_id'],'decision':'accepted','reviewer':'Synthetic reviewer',
                        'note':'Synthetic workflow test','location_id':row['candidates'][0]['id']})
        child,_=apply_review(root,path,self.root/'reviews'); self.assertEqual(file_hashes(root),before)
        self.assertFalse(validate_run(child)[1])
        write_json(self.root/'a.json',[{'source_record_id':str(i),'text':'Synthetic flood in Japan on 2024-01-01',
                    'location_text':'Japan','date_text':'2024-01-01'} for i in [1,2]])
        root,_=run(self.local(),base=self.root)
        contexts=read(root/'review/event_link_context.json'); self.assertEqual(len(contexts),1)
        self.assertTrue(contexts[0]['left']['claims'] and contexts[0]['right']['claims'])
        path=self.root/'links.csv'
        with (root/'review/possible_event_links.csv').open(newline='') as f: proposals=list(csv.DictReader(f))
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(proposals[0])); w.writeheader()
            w.writerow({**proposals[0],'decision':'accepted','reviewer':'Synthetic reviewer','note':'Synthetic merge test'})
        child,manifest=apply_event_links(root,path,self.root/'linked')
        self.assertEqual(manifest['record_counts']['events'],1); self.assertFalse(validate_run(child)[1])

    def test_cli_comparison_cache_and_resume(self):
        a,_=self.demo(); b,_=self.demo(); result=compare_runs(a,b)
        self.assertTrue(result['same_dataset']); self.assertEqual(set(result['count_delta_right_minus_left'].values()),{0})
        with redirect_stdout(io.StringIO()):
            for argv in [['compare',str(a),str(b)],['cache','status','--cache-dir',str(self.root/'cache')],
                         ['cache','clear','--cache-dir',str(self.root/'cache')],
                         ['run','--resume',str(a),'--output',str(self.root/'resume')]]:
                self.assertEqual(main(argv),0)

    def test_streaming_jsonl_and_csv_budget(self):
        (self.root/'a.jsonl').write_text('{"text":"Synthetic flood"}\nBAD\n{"text":"Synthetic cyclone"}\n')
        spec=self.local(('a.jsonl',)).inputs[0]
        records,_,_,errors=ingest_file(spec,self.root,3,10000)
        self.assertEqual(len(records),2); self.assertEqual(len(errors),1)
        (self.root/'a.csv').write_text('text\nSynthetic flood\nSynthetic cyclone\n')
        records,_,_,errors=ingest_file(self.local(('a.csv',)).inputs[0],self.root,1,10000)
        self.assertEqual(len(records),1); self.assertIn('budget',errors[0]['reason'])


if __name__ == '__main__': unittest.main()
