"""Packaged RTSP custom route and owned frozen training launcher acceptance."""
import argparse,json,os,subprocess,time
from dataclasses import replace
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    os.environ['WISEYE_RELEASE_ROOT']=str(args.release.resolve());os.environ['WISEYE_DATA_DIR']=str(args.output/'Data')
    os.environ['PATH']=os.environ['SystemRoot']+'\\System32;'+os.environ['SystemRoot']
    import apps.desktop_app.main
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage
    from core.config import AppConfig
    from apps.desktop_app.main_window import MainWindow
    from apps.desktop_app.training_launcher import launch_training
    app=QApplication([]);config=replace(AppConfig.load(),rtsp_port=19554,rtsp_paths={'ptz-01/infrared':'portable/thermal'});config.save()
    window=MainWindow(config);window.show();report=dict(passed=False)
    def pump(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:app.processEvents();time.sleep(.02)
    def wait(predicate,seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            pump(.05)
            if predicate():return
        raise TimeoutError('Portable tools acceptance timeout')
    try:
        for i in range(window.scenes.count()):
            if window.scenes.itemData(i)['id']=='city':window.scenes.setCurrentIndex(i);break
        window.launch_ue();wait(lambda:window.client.ready and window.air_client.ready,300);pump(2)
        output=args.output/'custom-rtsp.png';url=config.stream_url('ptz-01','infrared')
        with (args.output/'decode.log').open('w',encoding='utf-8') as log:
            decoder=subprocess.Popen([str(args.release/'Tools/ffmpeg.exe'),'-nostdin','-y','-rtsp_transport','tcp','-i',url,'-frames:v','1',str(output)],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:wait(lambda:decoder.poll() is not None,45)
            finally:
                if decoder.poll() is None:decoder.kill();decoder.wait()
        assert decoder.returncode==0 and output.is_file()
        image=QImage(str(output));assert (image.width(),image.height())==(640,512)
        report['rtsp']=dict(url=url,size=[image.width(),image.height()])
        launch_training(window);pump(3)
        training=getattr(window,'_training_process',None);assert training is not None and training.poll() is None
        report['frozen_training_launched']=True;report['training_pid']=training.pid
        report['passed']=True
    finally:
        window.close();wait(lambda:not window.runtime_manager.running,90)
        training=getattr(window,'_training_process',None)
        if training is not None:wait(lambda:training.poll() is not None,20)
        report['owned_processes_stopped']=True
        (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');app.quit()
    print('PORTABLE_RTSP_AND_TRAINING_LAUNCH_PASS',flush=True)

if __name__=='__main__':main()
