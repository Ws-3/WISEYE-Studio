"""Build only design deliverables; no simulator launch or configuration writes."""
import base64
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATA=ROOT/'docs/evidence/gt-rate-20261029/final/dataset'
key='0d04727c8952373bb854b64b'
assets={}
for name,folder in [('vis','visible'),('ir','IR')]:
    image=next((DATA/folder/'images').glob('*'+key+'.jpg'))
    meta=json.loads((DATA/folder/'annotations'/(image.stem+'.json')).read_text(encoding='utf-8'))
    assets[name]=dict(uri='data:image/jpeg;base64,'+base64.b64encode(image.read_bytes()).decode(),
                     width=meta['width'],height=meta['height'],box=meta['objects'][0]['bbox_xyxy'])
image=ROOT/'docs/evidence/dual-camera-rooftop-20261028/hover_overview.jpg'
assets['obs']=dict(uri='data:image/jpeg;base64,'+base64.b64encode(image.read_bytes()).decode(),width=960,height=540)
template=HERE/'preview-fragment.html'
fragment=template.read_text(encoding='utf-8')
if '__WISEYE_ASSETS__' in fragment:
    fragment=fragment.replace('__WISEYE_ASSETS__',json.dumps(assets,ensure_ascii=False))
    template.write_text(fragment,encoding='utf-8')
assert len(fragment.encode('utf-8'))<1_000_000
destination=Path(r'C:\Users\Administrator\.codex\visualizations\2026\10\14\01a13980-0f2d-70f3-912c-0fae99d3f630\wiseye-ui-v4-proposal.html')
destination.write_text(fragment,encoding='utf-8')
# Local QA wrapper: the inline deliverable remains the fragment above.
wrapper='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>WISEYE UI V4 — 待审批设计稿</title><style>body{margin:0;padding:16px;background:#101216;color:#e9eef5}</style></head><body>'''+fragment+'''</body></html>'''
(HERE/'review.html').write_text(wrapper,encoding='utf-8')
print('fragment_bytes',len(fragment.encode('utf-8')))
print(destination)
