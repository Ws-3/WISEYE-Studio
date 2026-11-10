"""Independent display/save deadlines; source requests follow the faster rate."""
import math
import threading


class Rates:
    def __init__(self,display_fps=1,save_fps=1,recording=False,max_display=10):
        self.lock=threading.Lock();self.next_display=0;self.next_save=0
        self.max_display=max_display
        self.configure(display_fps,save_fps,recording)

    def configure(self,display_fps,save_fps,recording):
        if any(type(v) not in (int,float) or not math.isfinite(v) or not .1<=v<=limit for v,limit in ((display_fps,self.max_display),(save_fps,10))):
            raise ValueError(f'Display must be 0.1..{self.max_display}, saving 0.1..10 FPS')
        with self.lock:
            if getattr(self,'display',None)!=display_fps:self.next_display=0
            if getattr(self,'save',None)!=save_fps or getattr(self,'recording',None)!=recording:self.next_save=0
            self.display,self.save,self.recording=display_fps,save_fps,bool(recording)

    def period(self):
        with self.lock:return 1/max(self.display,self.save if self.recording else .1)

    def due(self,now,source_driven=False):
        with self.lock:
            display=now>=self.next_display-1e-6
            # The receiver already paces source requests at the faster limit.
            # When preview drives that limit, show every fresh arrival instead
            # of dropping alternating frames due to readback/network jitter.
            source=max(self.display,self.save if self.recording else .1)
            if source_driven and self.display>=source and now!=getattr(self,'last_display',None):display=True
            save=self.recording and now>=self.next_save-1e-6
            if display:self.next_display=now+1/self.display;self.last_display=now
            if save:self.next_save=now+1/self.save
            return display,save
