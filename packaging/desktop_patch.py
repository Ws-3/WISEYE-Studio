"""Overlay a rebuilt desktop onto the exact existing Shipping release, keeping UE data."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED


def build(base, desktop, source, output):
    release = json.loads((base/'release.json').read_text(encoding='utf8'))
    if release['release_id'] != '20261023-001704-All-Shipping':
        raise ValueError('This patch only supports the verified 20261023-001704-All-Shipping baseline')
    release['base_release_id'] = release['release_id']
    release['release_id'] += '-desktop20261026'
    release['desktop_version'] = '20261026'
    checksums = json.loads((base/'checksums.json').read_text(encoding='utf8'))
    files = {p.relative_to(desktop).as_posix():p for p in desktop.rglob('*')
             if p.is_file() and p.name not in ('release.json','checksums.json')}
    for name in ['INTERFACE_SETTINGS.md','INFRARED_REALISM_PLAN.md','CLEANUP_REPORT.md','RTSP.md','DESKTOP.md']:
        files['Resources/docs/'+name] = source/'docs'/name
    notes = ('WISEYE 桌面更新 2026-10-26\n'
             '适用完整版本：20261023-001704-All-Shipping。请保留原完整包以便恢复。\n'
             '先降落、关闭WISEYE及其仿真/视频服务。将本ZIP内容全部解压覆盖到原WISEYE.exe所在目录。\n'
             'Simulation、Tools、原用户配置继续使用；本包不能单独运行。不要解压到Simulation子目录。\n'
             '启动后：数据与接口→编辑网络与传感器接口，或数据源操作→编辑接口。\n'
             '配置保存在本机%LOCALAPPDATA%\\WISEYE，不覆盖已有用户参数。\n'
             '支持RTSP主机/端口/流路径及每云台独立路径；保存前退出仿真并断开连接。\n'
             'UE内置控制/飞控仍监听50051/50052。红外画质本轮仅完成改进方案，尚未升级渲染。\n'
             '清理被自动审批拒绝，本轮释放0；候选详见Resources/docs/CLEANUP_REPORT.md。\n')
    generated = {'release.json':json.dumps(release,ensure_ascii=False,indent=2).encode('utf8'),
                 'Desktop-Update-20261026.txt':notes.encode('utf-8-sig')}
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',compression=ZIP_STORED,allowZip64=True) as archive:
        for name,path in sorted(files.items()):
            data=path.read_bytes()
            archive.writestr(name,data)
            checksums[name] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        for name,data in generated.items():
            archive.writestr(name,data)
            checksums[name] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        archive.writestr('checksums.json',json.dumps(checksums,ensure_ascii=False,indent=2).encode('utf8'))
    with ZipFile(output) as archive:
        if archive.testzip(): raise ValueError('Patch ZIP CRC verification failed')
    digest=hashlib.file_digest(output.open('rb'),'sha256').hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    print(json.dumps(dict(path=str(output),bytes=output.stat().st_size,sha256=digest),ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    for arg in ['base','desktop','source','output']: parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args()
    build(args.base,args.desktop,args.source,args.output)
