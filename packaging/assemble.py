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
parser.add_argument('--content', choices=['Base', 'City', 'All'], required=True)
parser.add_argument('--configuration', choices=['Development', 'Shipping'], required=True)
args = parser.parse_args()
staged = root / 'builds/staged' / f'{args.content}-{args.configuration}' / 'Windows'
desktop = root / 'builds/desktop/WISEYE'
if not staged.is_dir() or not (desktop / 'WISEYE.exe').is_file():
    raise SystemExit('Build Cook and Desktop stages first')
release = root / 'releases' / datetime.now().strftime(f'%Y%m%d-%H%M%S-{args.content}-{args.configuration}')
shutil.copytree(desktop, release)
shutil.copytree(staged, release / 'Simulation', ignore=shutil.ignore_patterns('*.pdb'))
resources = release / 'Resources'
scenes = {'Base': ['original', 'test_range'], 'City': ['city'], 'All': ['original', 'test_range', 'city']}[args.content]
def resource_ignore(directory, names):
    ignored = [name for name in names if name in ('CitySample', '__pycache__')]
    if Path(directory) == root / 'ue5/WISEYE/Config/WISEYE/Scenes':
        ignored.extend(name for name in names if name.endswith('.json') and Path(name).stem not in scenes)
    return ignored
for path in ['configs', 'ue5/WISEYE/Config/WISEYE', 'integrations/ProjectAirSim/config']:
    shutil.copytree(root / path, resources / path, ignore=resource_ignore)
(resources / 'docs').mkdir()
for name in ['USER_GUIDE.md', 'DESKTOP.md', 'SCENES.md', 'PROTOCOL.md', 'GIMBAL_INTERFACE.md', 'RTSP.md', 'RUNTIME_OPTIMIZATION.md', 'SENSOR_LATENCY_REPORT.md', 'INTERFACE_SETTINGS.md', 'INFRARED_REALISM_PLAN.md', 'INFRARED_EXPERIMENT.md', 'ENVIRONMENT_AND_PERFORMANCE.md', 'CLEANUP_REPORT.md']:
    if (root / 'docs' / name).is_file():
        shutil.copy2(root / 'docs' / name, resources / 'docs' / name)
shutil.copy2(root / 'LOGO.jpg', resources / 'LOGO.jpg')
(resources / 'integrations/rtsp').mkdir(parents=True)
shutil.copy2(root / 'integrations/rtsp/mediamtx.yml', resources / 'integrations/rtsp/mediamtx.yml')
tools = release / 'Tools'
tools.mkdir()
ffmpeg = shutil.which('ffmpeg')
if not ffmpeg:
    raise SystemExit('ffmpeg not found on build machine')
shutil.copy2(ffmpeg, tools / 'ffmpeg.exe')
shutil.copy2(Path(ffmpeg).parent.parent / 'LICENSE', tools / 'FFmpeg-LICENSE')
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
(release / 'README.txt').write_text('WISEYE 独立运行测试版\n\n1. 完整解压到本机 SSD 的一个文件夹，不要直接在 ZIP 内运行，也不要单独移动 EXE。\n2. 首次使用若提示缺少 VC++ 运行库，运行 Simulation\\Engine\\Extras\\Redist\\en-us\\vc_redist.x64.exe 安装一次。\n3. 双击 WISEYE.exe，选择已安装场景，点击右上角“启动仿真”，等待场景和飞控就绪后再起飞。\n4. 退出前降落全部无人机。用户配置、航线和日志默认在 %LOCALAPPDATA%\\WISEYE。\n\n不需要安装 UE 编辑器、VS、Python 或 Anaconda；需要支持相应图形功能的 Windows x64、显卡和驱动。\n安装源可以来自移动硬盘或完整下载，解压完成后不依赖原移动硬盘。\n这是独立运行内测包，尚未完成干净电脑及长时间稳定验收；在线更新尚未实现。\n', encoding='utf-8')
files = {}
for file in release.rglob('*'):
    if file.is_file():
        with file.open('rb') as stream:
            files[file.relative_to(release).as_posix()] = {'bytes': file.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
(release / 'checksums.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
print(json.dumps({'release': str(release), 'bytes': sum(v['bytes'] for v in files.values()) + (release / 'checksums.json').stat().st_size, 'files': len(files) + 1, 'manifest_files': len(files)}, indent=2))
