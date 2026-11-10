"""Dataset review and manual aerial annotation, sharing the training theme."""
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal,QRectF,QPointF
from PySide6.QtGui import QImage,QPainter,QColor,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QLineEdit,QTableWidget,QTableWidgetItem,QFileDialog,QDialog,QCheckBox,QMessageBox)
from .view import Canvas,controls
from .dataset import scan,inspect_annotation,annotate,CLASSES

class ScanWorker(QThread):
    result=Signal(object)
    def __init__(self,root):super().__init__();self.root=root
    def run(self):
        try:self.result.emit(scan(self.root,self.isInterruptionRequested))
        except (OSError,ValueError) as exc:self.result.emit(dict(rows=[],truncated=False,error=str(exc)))

class PrepareWorker(QThread):
    result=Signal(str)
    def __init__(self,train,val,output,sensor):super().__init__();self.arguments=(train,val,output,sensor)
    def run(self):
        from .train import prepare
        try:self.result.emit('已导出：'+str(prepare(*self.arguments,stop=self.isInterruptionRequested)))
        except (ValueError,OSError,KeyError,TypeError) as exc:self.result.emit('导出失败：'+str(exc))

class BoxCanvas(Canvas):
    changed=Signal()
    def __init__(self):
        super().__init__();self.boxes=[];self.class_id=0;self.origin=None;self.end=None;self.editable=False
        self.setToolTip('左键拖动标框 · 中键平移 · 滚轮缩放')
    def pixel(self,point):
        s=self.scale()*self.zoom
        return QPointF(max(0,min(self.image.width(),(point.x()-(self.width()-self.image.width()*s)/2-self.offset.x())/s)),max(0,min(self.image.height(),(point.y()-(self.height()-self.image.height()*s)/2-self.offset.y())/s)))
    def mousePressEvent(self,event):
        if self.editable and event.button()==Qt.MouseButton.LeftButton:
            self.origin=self.end=self.pixel(event.position());event.accept()
        else:super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self.origin is not None:self.end=self.pixel(event.position());self.update()
        else:super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        if self.origin is not None:
            self.end=self.pixel(event.position());r=QRectF(self.origin,self.end).normalized()
            if r.width()>=1 and r.height()>=1:self.boxes.append((self.class_id,[r.left(),r.top(),r.right(),r.bottom()]));self.changed.emit()
            self.origin=None;self.end=None;self.update()
        else:super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.image.isNull():return
        p=QPainter(self);s=self.scale()*self.zoom;p.translate((self.width()-self.image.width()*s)/2+self.offset.x(),(self.height()-self.image.height()*s)/2+self.offset.y());p.scale(s,s)
        p.setPen(QPen(QColor('#50e6b4'),2/max(.01,s)))
        for ident,box in self.boxes:
            x1,y1,x2,y2=box;p.drawRect(QRectF(x1,y1,x2-x1,y2-y1));p.drawText(QPointF(x1,max(12.,y1-3)),CLASSES.get(ident,str(ident)))
        if self.origin is not None:p.drawRect(QRectF(self.origin,self.end).normalized())
        p.end()

class ReviewDialog(QDialog):
    saved=Signal()
    def __init__(self,path,parent=None):
        super().__init__(parent);self.path=Path(path);self.dirty=False;self.setWindowTitle('样本检查与标注');self.resize(1200,800)
        item,image,_=inspect_annotation(self.path)
        layout=QVBoxLayout(self);bar=QHBoxLayout();self.classes=QComboBox()
        for ident,title in [(0,'无人机'),(1,'行人'),(2,'车辆')]:self.classes.addItem(title,ident)
        bar.addWidget(self.classes);self.canvas=BoxCanvas();self.canvas.image=QImage(str(image));self.canvas.editable=item.get('dataset_schema')==4
        if self.canvas.image.isNull() or (self.canvas.image.width(),self.canvas.image.height())!=(item['width'],item['height']):raise ValueError('Image dimensions do not match metadata')
        self.canvas.changed.connect(lambda:setattr(self,'dirty',True))
        self.canvas.boxes=[(o['class_id'],o['bbox_xyxy']) for o in item.get('objects',[])]
        self.classes.currentIndexChanged.connect(lambda _:setattr(self.canvas,'class_id',self.classes.currentData()))
        undo=QPushButton('撤销最后一框');undo.clicked.connect(self.undo);bar.addWidget(undo);undo.setEnabled(self.canvas.editable)
        self.empty=QCheckBox('确认画面没有上述目标（负样本）');bar.addWidget(self.empty);bar.addStretch();layout.addLayout(bar)
        layout.addLayout(controls(self.canvas));layout.addWidget(self.canvas,1)
        self.status=QLabel('原有自动GT只读；航拍原图可手动标框，保存后才可训练。');self.status.setWordWrap(True);layout.addWidget(self.status)
        save=QPushButton('保存标注并设为可训练');save.setEnabled(self.canvas.editable);save.clicked.connect(self.commit);layout.addWidget(save)
        self.classes.setEnabled(self.canvas.editable);self.empty.setEnabled(self.canvas.editable)
    def undo(self):
        if self.canvas.boxes:self.canvas.boxes.pop();self.dirty=True;self.canvas.update()
    def commit(self):
        try:annotate(self.path,self.canvas.boxes,self.empty.isChecked())
        except (ValueError,OSError,KeyError) as exc:self.status.setText(str(exc));return
        self.dirty=False;self.status.setText('标注已保存；图像和原始来源元数据保留。');self.saved.emit()
    def closeEvent(self,event):
        if self.dirty and QMessageBox.question(self,'未保存标注','放弃当前未保存的标框？',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Discard:event.ignore();return
        event.accept()

class DatasetPanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.scanner=None;self.preparer=None;self.rows=[];self.dialogs=[]
        layout=QVBoxLayout(self);bar=QHBoxLayout();self.root=QLineEdit(window.directory.text());bar.addWidget(self.root,1)
        choose=QPushButton('选择数据集');choose.clicked.connect(self.browse);bar.addWidget(choose)
        self.refresh=QPushButton('扫描与校验');self.refresh.clicked.connect(self.start_scan);bar.addWidget(self.refresh)
        self.filter=QComboBox();self.filter.addItems(['全部','可训练','待标注','已忽略','损坏']);self.filter.currentIndexChanged.connect(self.render);bar.addWidget(self.filter);layout.addLayout(bar)
        self.summary=QLabel('扫描图像、标签与标注元数据；双击样本检查，航拍原图可手动标注。');layout.addWidget(self.summary)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels(['样本','模态','状态','目标数','会话']);self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.horizontalHeader().setStretchLastSection(True);self.table.cellDoubleClicked.connect(self.review);layout.addWidget(self.table,1)
        prep=QHBoxLayout();self.train=QLineEdit();self.train.setPlaceholderText('训练集目录（独立仿真会话）');self.val=QLineEdit();self.val.setPlaceholderText('验证集目录（另一次仿真会话）')
        prep.addWidget(self.train);prep.addWidget(self.val);self.sensor=QComboBox();self.sensor.addItem('红外','infrared');self.sensor.addItem('可见光','visible');prep.addWidget(self.sensor)
        prepare=QPushButton('导出训练配置');prepare.clicked.connect(self.prepare);prep.addWidget(prepare);layout.addLayout(prep)
        note=QLabel('仅完整且可训练的样本进入导出；训练与验证必须来自不同仿真会话，并检查图像重复。此处准备数据配置，不自动启动模型训练。');note.setWordWrap(True);layout.addWidget(note)
    def browse(self):
        path=QFileDialog.getExistingDirectory(self,'数据集目录',self.root.text())
        if path:self.root.setText(path);self.start_scan()
    def start_scan(self):
        if self.scanner:return
        self.refresh.setEnabled(False);self.summary.setText('正在校验…');self.scanner=ScanWorker(self.root.text());self.scanner.result.connect(self.loaded);self.scanner.finished.connect(self.finished);self.scanner.start()
    def finished(self):
        self.scanner.deleteLater();self.scanner=None;self.refresh.setEnabled(True)
    def loaded(self,result):
        if result.get('error'):self.summary.setText('扫描失败：'+result['error']);return
        self.rows=result['rows'];counts={s:sum(r['state']==s for r in self.rows) for s in ('可训练','待标注','已忽略','损坏')}
        self.summary.setText(' · '.join(f'{k} {v}' for k,v in counts.items())+(' · 达到20000条扫描上限，请选择更小目录' if result['truncated'] else ''));self.render()
    def render(self):
        wanted=self.filter.currentText();rows=[r for r in self.rows if wanted=='全部' or r['state']==wanted];self.table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,value in enumerate([r['name'],r['modality'],r['state'],r['count'],r['run'][:12]]):
                cell=QTableWidgetItem(str(value));cell.setData(Qt.ItemDataRole.UserRole,r);cell.setToolTip(r.get('error') or r['path']);self.table.setItem(i,j,cell)
        self.table.setColumnWidth(0,460)
    def review(self,row,column):
        record=self.table.item(row,0).data(Qt.ItemDataRole.UserRole)
        try:d=ReviewDialog(record['path'],self)
        except (OSError,ValueError,KeyError) as exc:self.summary.setText(str(exc));return
        self.dialogs.append(d);d.saved.connect(self.start_scan);d.show()
    def prepare(self):
        if self.preparer:return
        if not self.train.text().strip() or not self.val.text().strip():self.summary.setText('请先填写训练集与验证集目录');return
        output=QFileDialog.getExistingDirectory(self,'导出训练配置到')
        if not output:return
        self.summary.setText('正在校验并导出训练配置…');self.preparer=PrepareWorker(self.train.text(),self.val.text(),output,self.sensor.currentData());self.preparer.result.connect(self.summary.setText);self.preparer.finished.connect(self.prepared);self.preparer.start()
    def prepared(self):
        self.preparer.deleteLater();self.preparer=None
    def stop(self):
        for d in self.dialogs:
            if d.isVisible() and not d.close():return None
        if self.preparer:self.preparer.requestInterruption();return False
        if self.scanner:self.scanner.requestInterruption();return False
        return True
