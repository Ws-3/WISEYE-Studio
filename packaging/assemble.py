"""Combine verified build outputs, preserving UE's staged relative layout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import importlib.metadata
import sys
from datetime import datetime

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--content', choices=['City'], required=True)
parser.add_argument('--configuration', choices=['Development', 'Shipping'], required=True)
parser.add_argument('--include-big-city',action='store_true')
args = parser.parse_args()
staged = root / 'builds/staged' / f'{args.content}-{args.configuration}' / 'Windows'
desktop = root / 'builds/desktop/WISEYE'
if not staged.is_dir() or not (desktop / 'WISEYE.exe').is_file():
    raise SystemExit('Build Cook and Desktop stages first')
release = root / 'releases' / datetime.now().strftime(f'%Y%m%d-%H%M%S-{args.content}-{args.configuration}')
shutil.copytree(desktop, release)
shutil.copytree(staged, release / 'Simulation', ignore=shutil.ignore_patterns('*.pdb'))
resources = release / 'Resources'
scenes = ['city','city_large'] if args.include_big_city else ['city']
training = root / 'builds/desktop/WISEYE-Training'
if not (training/'WISEYE-Training.exe').is_file():raise SystemExit('Build the training desktop before assembly')
shutil.copytree(training,release/'Training')
(release/'portable.flag').write_text('Use UserData beside the application.\n',encoding='utf-8')
def resource_ignore(directory, names):
    ignored = [name for name in names if name in ('CitySample', '__pycache__')]
    if Path(directory) == root / 'ue5/WISEYE/Config/WISEYE/Scenes':
        ignored.extend(name for name in names if name.endswith('.json') and Path(name).stem not in scenes)
    return ignored
for path in ['configs', 'ue5/WISEYE/Config/WISEYE', 'integrations/ProjectAirSim/config']:
    incoming = root / 'UserData' / path
    if not incoming.is_dir():incoming=root/path
    shutil.copytree(incoming, resources / path, ignore=resource_ignore)
(resources / 'docs').mkdir()
for name in ['USER_GUIDE.md', 'DESKTOP.md', 'SCENES.md', 'PROTOCOL.md', 'GIMBAL_INTERFACE.md', 'RTSP.md', 'RUNTIME_OPTIMIZATION.md', 'SENSOR_LATENCY_REPORT.md', 'INTERFACE_SETTINGS.md', 'INFRARED_REALISM_PLAN.md', 'INFRARED_EXPERIMENT.md', 'ENVIRONMENT_AND_PERFORMANCE.md', 'CLEANUP_REPORT.md']:
    if (root / 'docs' / name).is_file():
        shutil.copy2(root / 'docs' / name, resources / 'docs' / name)
shutil.copy2(root / 'LOGO.jpg', resources / 'LOGO.jpg')
(resources / 'integrations/rtsp').mkdir(parents=True)
shutil.copy2(root / 'integrations/rtsp/mediamtx.yml', resources / 'integrations/rtsp/mediamtx.yml')
tools = release / 'Tools'
tools.mkdir()
ffmpeg = str(root/'Tools/ffmpeg/ffmpeg.exe') if (root/'Tools/ffmpeg/ffmpeg.exe').is_file() else shutil.which('ffmpeg')
if not ffmpeg:
    raise SystemExit('ffmpeg not found on build machine')
shutil.copy2(ffmpeg, tools / 'ffmpeg.exe')
ffmpeg_license=next((p for p in (Path(ffmpeg).parent/'LICENSE',Path(ffmpeg).parent.parent/'LICENSE') if p.is_file()),None)
if not ffmpeg_license:raise SystemExit('FFmpeg license missing')
shutil.copy2(ffmpeg_license, tools / 'FFmpeg-LICENSE')
shutil.copy2(root / 'third_party/mediamtx/mediamtx.exe', tools / 'mediamtx.exe')
shutil.copy2(root / 'third_party/mediamtx/LICENSE', tools / 'MediaMTX-LICENSE')
licenses = release / 'Licenses'
licenses.mkdir()
for distribution in importlib.metadata.distributions():
    for entry in distribution.files or []:
        if '.dist-info/licenses/' in str(entry).replace('\\', '/'):
            source = Path(distribution.locate_file(entry))
            destination = licenses / Path(str(entry))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
if (Path(sys.base_prefix) / 'LICENSE.txt').is_file():
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', licenses / 'Python-LICENSE.txt')
if (root / 'third_party/notices/ProjectAirSim-LICENSE.txt').is_file():
    shutil.copy2(root / 'third_party/notices/ProjectAirSim-LICENSE.txt', licenses / 'ProjectAirSim-LICENSE.txt')
binaries = [p for p in (release / 'Simulation/test/Binaries/Win64').glob('*.exe') if p.name.startswith('test')]
if len(binaries) != 1:
    raise SystemExit(f'Expected one staged Game executable, found {binaries}')
manifest = {'version': 1, 'release_id': release.name, 'engine': '5.8.4', 'configuration': args.configuration,
            'scenes': scenes, 'simulation_executable': binaries[0].relative_to(release).as_posix(),
            'status': 'local-test-build-not-clean-machine-certified'}
(release / 'release.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
(release/'PORTABLE.txt').write_text('Portable build: UserData beside WISEYE.exe holds configuration, routes and logs. Keep the complete folder together. Training/WISEYE-Training.exe uses the same data root. Windows, GPU drivers and VC++ prerequisites remain host requirements. Online update is not implemented.\n',encoding='utf-8')
(release / 'README.txt').write_text('WISEYE 便携运行包\n\n1. 保留完整目录，双击 WISEYE.exe；启动桌面不会自动启动UE。\n2. 场景编排中选择小城市或大城市（试验），点击启动仿真，等待就绪再起飞。\n3. 训练端可从桌面打开，或运行 Training/WISEYE-Training.exe。算法训练依赖/权重为可选扩展，不代表已内置全部算法。\n4. portable.flag启用便携模式；配置、航线、日志、采集数据及界面设置保存在本目录UserData。\n5. 若提示缺少系统运行库，使用Simulation/Engine/Extras/Redist/en-us中的前置安装程序。仍需兼容的Windows x64、显卡和驱动。\n6. 更换电脑/盘符时保留完整目录，首次运行可能准备图形缓存。退出仿真和写入后安全弹出移动硬盘。\n\n这是当前源码生成的内测包；不需要完整UE编辑器、VS或另装Python。尚未完成干净电脑和长期稳定验收，在线更新尚未实现。\n', encoding='utf-8')
files = {}
for file in release.rglob('*'):
    if file.is_file():
        with file.open('rb') as stream:
            files[file.relative_to(release).as_posix()] = {'bytes': file.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
(release / 'checksums.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
print(json.dumps({'release': str(release), 'bytes': sum(v['bytes'] for v in files.values()) + (release / 'checksums.json').stat().st_size, 'files': len(files) + 1, 'manifest_files': len(files)}, indent=2))
