"""Dataset inspection and explicit manual annotations for raw aerial images."""
import hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
CLASSES={0:'drone',1:'person',2:'vehicle'}

def inspect_annotation(path,verify=True):
    path=Path(path);item=json.loads(path.read_text(encoding='utf-8'))
    if path.parent.name!='annotations':raise ValueError('Not a WISEYE annotation')
    image=path.parent.parent/'images'/(path.stem+'.jpg')
    labels=path.parent.parent/'labels'/(path.stem+'.txt')
    if not image.is_file():raise ValueError('Missing image')
    if verify and hashlib.sha256(image.read_bytes()).hexdigest()!=item.get('image_sha256'):raise ValueError('Image checksum mismatch')
    if item.get('training_eligible') and item.get('annotation_status')=='complete':
        if not labels.is_file():raise ValueError('Missing YOLO label')
        expected=[]
        for obj in item['objects']:
            x1,y1,x2,y2=obj['bbox_xyxy'];w,h=item['width'],item['height']
            if type(obj['class_id']) is not int or obj['class_id'] not in CLASSES or any(not math.isfinite(v) for v in (x1,y1,x2,y2)) or not (0<=x1<x2<=w and 0<=y1<y2<=h):raise ValueError('Invalid annotation box/class')
            if obj.get('class_name',CLASSES[obj['class_id']])!=CLASSES[obj['class_id']]:raise ValueError('Class ID/name mismatch')
            expected.append((obj['class_id'],(x1+x2)/2/w,(y1+y2)/2/h,(x2-x1)/w,(y2-y1)/h))
        if item.get('negative_sample') is not (not item['objects']) or item.get('ignored_objects'):raise ValueError('Invalid training eligibility')
        lines=labels.read_text(encoding='utf-8').splitlines()
        if len(lines)!=len(expected):raise ValueError('Label count mismatch')
        for line,row in zip(lines,expected):
            values=[float(x) for x in line.split()]
            if len(values)!=5 or any(not math.isfinite(x) for x in values) or any(abs(a-b)>1e-6 for a,b in zip(values,row)):raise ValueError('Label content mismatch')
    return item,image,labels

def scan(root,stop=None,limit=20000):
    root=Path(root).resolve();rows=[];truncated=False
    if not root.is_dir():return dict(rows=[],truncated=False)
    for path in root.rglob('*.json'):
        if stop and stop():break
        if path.parent.name!='annotations' or '.pending' in path.relative_to(root).parts:continue
        if not path.resolve().is_relative_to(root):continue
        if len(rows)>=limit:truncated=True;break
        try:
            item,image,_=inspect_annotation(path)
            state='可训练' if item.get('annotation_status')=='complete' and item.get('training_eligible') else '待标注' if item.get('annotation_status')=='pending_manual' else '已忽略'
            row=dict(path=str(path),image=str(image),name=path.stem,state=state,modality=item.get('sensor_id',''),run=item.get('run_id',''),count=len(item.get('objects',[])),error='')
        except (ValueError,KeyError,OSError,TypeError,AttributeError,IndexError) as exc:row=dict(path=str(path),name=path.stem,state='损坏',modality='',run='',count=0,error=str(exc))
        rows.append(row)
    return dict(rows=rows,truncated=truncated)

def annotate(path,boxes,confirmed_empty=False):
    path=Path(path);item,image,labels=inspect_annotation(path)
    if item.get('dataset_schema')!=4:raise ValueError('Existing paired automatic GT is read-only in this editor')
    w,h=item['width'],item['height'];objects=[]
    for i,(ident,box) in enumerate(boxes):
        if type(ident) is not int or ident not in CLASSES or len(box)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in box):raise ValueError('Invalid class or bounding box')
        x1,y1,x2,y2=box
        if not 0<=x1<x2<=w or not 0<=y1<y2<=h:raise ValueError('Box outside image')
        objects.append(dict(target_id=f'manual-{i+1}',class_id=ident,class_name=CLASSES[ident],bbox_xyxy=list(box),visible_fraction_in_frame=1.,partially_occluded=False,partially_outside=False,annotation_source='manual'))
    if not objects and not confirmed_empty:raise ValueError('Explicitly confirm empty image before marking a negative')
    def publish(target,data):
        target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_suffix(target.suffix+'.tmp');temp.write_bytes(data);temp.replace(target)
    # Invalidate the commit before replacing labels; readers never train on a half edit.
    item.update(annotation_status='pending_manual',training_eligible=False)
    publish(path,json.dumps(item,ensure_ascii=False,indent=2).encode('utf-8'))
    text=''.join(f"{o['class_id']} {(o['bbox_xyxy'][0]+o['bbox_xyxy'][2])/2/w:.8f} {(o['bbox_xyxy'][1]+o['bbox_xyxy'][3])/2/h:.8f} {(o['bbox_xyxy'][2]-o['bbox_xyxy'][0])/w:.8f} {(o['bbox_xyxy'][3]-o['bbox_xyxy'][1])/h:.8f}\n" for o in objects)
    publish(labels,text.encode('utf-8'))
    item.update(objects=objects,ignored_objects=[],annotation_status='complete',training_eligible=True,negative_sample=not objects,annotation_source='manual',reviewed_at=datetime.now(timezone.utc).isoformat())
    item.pop('annotation_error',None)
    publish(path,json.dumps(item,ensure_ascii=False,indent=2).encode('utf-8'))
    return item
