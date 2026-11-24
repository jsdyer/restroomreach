import copy,io,json,sys,unittest
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh import collect_regions,fetch_region,ROOT,normalize
class Downloads(unittest.TestCase):
 def setUp(self):self.cfg=json.loads((ROOT/'web/config.json').read_text())
 def source(self,i):
  region=self.cfg['regions'][i];lat,lon=region['center']
  return {'osm3s':{'timestamp_osm_base':f'2026-11-2{3+i}T00:00:00Z'},'elements':[{'type':'node','id':i+1,'lat':lat,'lon':lon,'tags':{'amenity':'toilets'}}]}
 def test_regions_are_sequential_bounded_and_keep_oldest_edition(self):
  calls=[]
  def opener(req,timeout):
   i=len(calls);calls.append(req.data.decode());self.assertEqual(timeout,120)
   return io.BytesIO(json.dumps(self.source(i)).encode())
  result=collect_regions(self.cfg,opener,lambda _:None)
  self.assertEqual(len(calls),2);self.assertTrue(all(x.count('nwr')==1 for x in calls))
  self.assertEqual(result['osm3s']['timestamp_osm_base'],'2026-11-23T00:00:00Z')
  self.assertEqual(len(normalize(result,self.cfg,'2026-11-24T00:00:00Z')['records']),2)
 def test_timeout_retries_once_but_rejections_do_not(self):
  for error,wanted in [(TimeoutError('timeout'),2),(HTTPError('https://example.test',429,'rate limit',{},None),1),(HTTPError('https://example.test',403,'blocked',{},None),1)]:
   calls=[]
   def opener(*args,**kwargs):calls.append(1);raise error
   with self.assertRaises(type(error)):fetch_region(self.cfg['sourceUrl'],self.cfg['regions'][0],opener,lambda _:None)
   self.assertEqual(len(calls),wanted)
 def test_second_region_error_cannot_produce_partial_capture(self):
  calls=[]
  def opener(*args,**kwargs):
   calls.append(1)
   return io.BytesIO(json.dumps(self.source(0) if len(calls)==1 else {'remark':'query timed out','elements':[]}).encode())
  with self.assertRaisesRegex(ValueError,'incomplete'):collect_regions(self.cfg,opener,lambda _:None)
 def test_overlap_deduplicates_identical_osm_records(self):
  calls=[]
  def opener(*args,**kwargs):calls.append(1);return io.BytesIO(json.dumps(self.source(0)).encode())
  self.assertEqual(len(collect_regions(self.cfg,opener,lambda _:None)['elements']),1)
