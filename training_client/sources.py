"""Read-only discovery of simulator devices through the existing data gateway."""
from PySide6.QtCore import QThread,Signal
from .client import Client
class SourceDiscovery(QThread):
    result=Signal(object)
    failed=Signal(str)
    def __init__(self,host,port):super().__init__();self.host=host;self.port=port
    def run(self):
        try:
            client=Client(self.host,self.port,None);client.connect_timeout=1;client.response_timeout=2
            state=client.rpc('sim.get_state')
            self.result.emit([dict(id=d['id'],kind=d['kind'],name=d.get('name',d['id'])) for d in state.get('devices',[]) if d.get('kind') in ('gimbal','drone')])
        except (OSError,ValueError,RuntimeError,KeyError) as error:self.failed.emit(str(error))
