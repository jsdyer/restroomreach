import copy,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import normalize,valid_config,query_for,check_drop,run,ROOT
class RefreshTests(unittest.TestCase):
 def setUp(self):
  self.cfg=json.loads((ROOT/'web/config.json').read_text())
  self.cfg['regions']=self.cfg['regions'][:2]
  self.source={'osm3s':{'timestamp_osm_base':'2026-07-15T00:00:00Z'},'elements':[{'type':'node','id':1,'lat':49.2,'lon':-123,'tags':{'amenity':'toilets','wheelchair':'yes','name':'One'},'timestamp':'2025-01-01T00:00:00Z'},{'type':'way','id':2,'center':{'lat':44.6,'lon':-63.6},'tags':{'amenity':'toilets'},'timestamp':'2025-01-01T00:00:00Z'}]}
 def test_actual_source_edition_is_distinct_from_capture(self):
  d=normalize(self.source,self.cfg,'2026-11-23T00:00:00Z');self.assertEqual(len(d['records']),2);self.assertNotEqual(d['capturedAt'],d['sourceUpdatedAt']);self.assertNotIn('wheelchair',d['records'][1]['tags'])
 def test_can_add_region_beyond_starter_list(self):
  self.cfg['regions'].append({'id':'new-area','name':'New area','bbox':[40,-80,41,-79],'center':[40.5,-79.5]});self.source['elements'].append({'type':'node','id':3,'lat':40.5,'lon':-79.5,'tags':{'amenity':'toilets'}})
  d=normalize(self.source,self.cfg,'2026-11-23T00:00:00Z');self.assertEqual(d['records'][-1]['regions'],['halifax']);self.assertIn('new-area',next(x for x in d['records'] if x['id']=='node/3')['regions']);self.assertIn('(40,-80,41,-79)',query_for(valid_config(self.cfg)))
 def test_source_error_and_missing_region_rejected(self):
  for source in [dict(self.source,remark='timeout'),dict(self.source,elements=self.source['elements'][:1]),dict(self.source,osm3s={})]:
   with self.assertRaises(ValueError):normalize(source,self.cfg,'2026-11-23T00:00:00Z')
 def test_bad_bounds_and_duplicate_regions_rejected(self):
  self.cfg['regions'][0]['bbox']=[-90,-180,90,180]
  with self.assertRaises(ValueError):valid_config(self.cfg)
 def test_duplicate_id_rejected(self):
  self.source['elements'].append(self.source['elements'][0])
  with self.assertRaises(ValueError):normalize(self.source,self.cfg,'2026-11-23T00:00:00Z')
 def test_unrelated_personal_contributor_metadata_excluded(self):
  self.source['elements'][0]['user']='someone';self.source['elements'][0]['uid']=10;self.source['elements'][0]['tags']['phone']='555-0100'
  d=normalize(self.source,self.cfg,'2026-11-23T00:00:00Z');self.assertNotIn('user',d['records'][0]);self.assertNotIn('phone',d['records'][0]['tags'])
 def test_record_drop_checks_only_comparable_coverage(self):
  d=normalize(self.source,self.cfg,'2026-11-23T00:00:00Z');old=copy.deepcopy(d);old['records']*=4
  with self.assertRaises(ValueError):check_drop(old,d,self.cfg)
  d['scope']='different'
  with self.assertRaises(ValueError):check_drop(old,d,self.cfg)
  for r in d['regions']:r['bbox'][0]+=0.01
  check_drop(old,d,self.cfg)
 def test_failed_refresh_leaves_index_unchanged(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);(root/'web/data').mkdir(parents=True);(root/'web/config.json').write_text(json.dumps(self.cfg));(root/'web/data/index.json').write_text('{"captures":[]}');p=root/'source.json';p.write_text('{"remark":"timeout"}')
   before=(root/'web/data/index.json').read_bytes()
   with self.assertRaises(ValueError):run(root,p)
   self.assertEqual(before,(root/'web/data/index.json').read_bytes())
if __name__=='__main__':unittest.main()
