"""Fine-tune from separately collected training and validation sessions."""
import argparse
import hashlib
import json
from pathlib import Path


def collect(root,sensor=None):
    root = Path(root).resolve()
    images, sessions, hashes = [], set(), set()
    modalities=set()
    for annotation in sorted(root.rglob('*.json')):
        if annotation.parent.name!='annotations' or '.pending' in annotation.relative_to(root).parts:continue
        item = json.loads(annotation.read_text(encoding='utf8'))
        modality=item.get('sensor_id','').split('/')[-1]
        if sensor and modality!=sensor:continue
        if item.get('annotation_status') != 'complete' or not item.get('training_eligible'):
            continue
        sample_root=annotation.parent.parent
        image = sample_root/'images'/(annotation.stem+'.jpg')
        label = sample_root/'labels'/(annotation.stem+'.txt')
        if not label.is_file() or not image.is_file():
            raise ValueError(f'Incomplete saved sample: {annotation}')
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        if digest != item.get('image_sha256'):
            raise ValueError(f'Image checksum mismatch: {image}')
        if item.get('dataset_schema') in (2,3) and item.get('pair_id'):
            partner=item.get('counterpart_image','')
            if not partner or Path(partner).name!=partner or Path(partner).suffix!='.jpg':raise ValueError('Invalid paired image name')
            partner_root=sample_root
            if item.get('dataset_schema')==3:
                directory=item.get('counterpart_directory')
                if directory not in ('visible','IR'):raise ValueError('Invalid paired modality directory')
                partner_root=sample_root.parent/directory
            partner_image=partner_root/'images'/partner
            partner_label=partner_root/'labels'/(Path(partner).stem+'.txt')
            partner_annotation=partner_root/'annotations'/(Path(partner).stem+'.json')
            if not all(p.is_file() for p in (partner_image,partner_label,partner_annotation)):raise ValueError(f'Incomplete paired group: {sample_root}')
            peer=json.loads(partner_annotation.read_text(encoding='utf8'))
            if peer.get('pair_id')!=item['pair_id'] or peer.get('sample_group_id')!=item.get('sample_group_id') or peer.get('run_id')!=item['run_id'] or peer.get('simulation_time_s')!=item['simulation_time_s']:
                raise ValueError('Paired annotation identity mismatch')
            if peer.get('counterpart_image')!=image.name or not peer.get('training_eligible') or peer.get('annotation_status')!='complete':raise ValueError('Paired annotation is not a valid reciprocal sample')
            if hashlib.sha256(partner_image.read_bytes()).hexdigest()!=peer.get('image_sha256'):raise ValueError('Paired image checksum mismatch')
        images.append(str(image)); sessions.add(item['run_id']); hashes.add(digest)
        modalities.add(modality)
    if not images:
        raise ValueError(f'No committed training samples: {root}')
    if sensor is None and len(modalities)>1:raise ValueError('Dataset contains VIS and IR; choose --sensor visible or infrared')
    return images, sessions, hashes


def prepare(train_root, val_root, output,sensor=None):
    train, train_sessions, train_hashes = collect(train_root,sensor)
    val, val_sessions, val_hashes = collect(val_root,sensor)
    if train_sessions & val_sessions or train_hashes & val_hashes:
        raise ValueError('Training and validation must use separate simulator sessions and different images')
    output = Path(output).resolve(); output.mkdir(parents=True, exist_ok=True)
    for name, paths in [('train', train), ('val', val)]:
        (output/f'{name}.txt').write_text('\n'.join(paths)+'\n', encoding='utf8')
    # JSON is also valid YAML; no additional dependency for dataset preparation.
    spec = dict(path=str(output), train=str(output/'train.txt'), val=str(output/'val.txt'), names={0:'drone'})
    target = output/'dataset.yaml'
    target.write_text(json.dumps(spec, indent=2), encoding='utf8')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train-data', type=Path, required=True)
    parser.add_argument('--val-data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--weights', type=Path, help='Local pretrained or previous checkpoint; required for training')
    parser.add_argument('--epochs', type=int, default=5)
    parser.add_argument('--batch', type=int, default=4)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--sensor',choices=['visible','infrared'],default='infrared',help='Modality to train from paired directories')
    args = parser.parse_args()
    spec = prepare(args.train_data, args.val_data, args.output,args.sensor)
    print(f'Dataset prepared: {spec}', flush=True)
    if args.prepare_only:
        return
    if args.weights is None or not args.weights.is_file():
        raise ValueError('Provide an existing local weights file')
    from ultralytics import YOLO
    model = YOLO(str(args.weights))
    model.train(data=str(spec), epochs=args.epochs, batch=args.batch, imgsz=640,
                device=args.device, project=str(args.output/'runs'), name='finetune', resume=False)


if __name__ == '__main__':
    main()
