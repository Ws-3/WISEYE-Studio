"""Exercise the actual native JSBSim DLL, independent of UE/render latency."""
import ctypes as c
import math
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DLL=ROOT/'ue5/WISEYE/ThirdParty/JSBSim/bin/WiseEyeJSBSim.dll'
class State(c.Structure):
    _fields_=[(k,c.c_double) for k in 'dx dy dz speed yaw pitch roll throttle alpha beta p q r load_factor'.split()]

@unittest.skipUnless(DLL.is_file(),'Build JSBSim native runtime first')
class JSBSimTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=c.CDLL(str(DLL))
        cls.lib.WiseEyeFDMCreate.argtypes=[c.c_char_p,c.c_char_p,c.c_int];cls.lib.WiseEyeFDMCreate.restype=c.c_void_p
        cls.lib.WiseEyeFDMReset.argtypes=[c.c_void_p,c.c_double,c.c_double,c.c_char_p,c.c_int]
        cls.lib.WiseEyeFDMStep.argtypes=[c.c_void_p,c.c_double,c.c_double,c.c_double,c.c_double,c.POINTER(State),c.c_char_p,c.c_int]
        cls.lib.WiseEyeFDMDestroy.argtypes=[c.c_void_p]
    def setUp(self):
        self.error=c.create_string_buffer(2048)
        self.handle=self.lib.WiseEyeFDMCreate(str(DLL.parents[1]/'Resources').encode(),self.error,len(self.error))
        self.assertTrue(self.handle,self.error.value)
        self.assertTrue(self.lib.WiseEyeFDMReset(self.handle,0,12,self.error,len(self.error)))
    def tearDown(self):self.lib.WiseEyeFDMDestroy(self.handle)
    def step(self,dt=1/120,speed=12,bank=0,gamma=0):
        s=State();ok=self.lib.WiseEyeFDMStep(self.handle,dt,speed,bank,gamma,c.byref(s),self.error,len(self.error))
        self.assertTrue(ok,self.error.value)
        self.assertTrue(all(math.isfinite(getattr(s,k)) for k,_ in s._fields_))
        return s
    def run_for(self,seconds,**kw):
        for _ in range(round(seconds*120)):s=self.step(**kw)
        return s
    def test_stable_reference_cruise(self):
        s=self.run_for(30)
        self.assertAlmostEqual(s.speed,12,delta=.5);self.assertLess(abs(s.roll),.1)
        self.assertLess(abs(s.beta),.1);self.assertLess(abs(s.pitch),8)
    def test_bank_is_continuous_and_turns_then_levels(self):
        first=self.step(dt=1/30,bank=25);self.assertLess(abs(first.roll),2)
        s=self.run_for(2,bank=25);self.assertGreater(s.yaw,15);self.assertAlmostEqual(s.roll,25,delta=3)
        s=self.run_for(2);self.assertLess(abs(s.roll),2)
    def test_speed_has_inertia(self):
        s=self.step(dt=1/30,speed=15);self.assertLess(abs(s.speed-12),.15)
        s=self.run_for(12,speed=15);self.assertAlmostEqual(s.speed,15,delta=.5)
    def test_climb_is_driven_by_pitch(self):
        self.run_for(2,gamma=8)
        s=self.step(gamma=8);self.assertGreater(s.dz,0);self.assertGreater(s.pitch,5)
    def test_fixed_step_independent_of_render_rate(self):
        def displacement(dt,count):
            self.lib.WiseEyeFDMReset(self.handle,35,12,self.error,len(self.error))
            xyz=[0.,0.,0.]
            for _ in range(count):
                s=self.step(dt=dt,bank=15)
                for i,k in enumerate(('dx','dy','dz')):xyz[i]+=getattr(s,k)
            return xyz
        a=displacement(1/30,150);b=displacement(1/60,300)
        self.assertLess(math.dist(a,b),.001)
    def test_nonfinite_command_is_rejected(self):
        s=State()
        self.assertFalse(self.lib.WiseEyeFDMStep(self.handle,.03,float('nan'),0,0,c.byref(s),self.error,len(self.error)))
        self.assertIn(b'Invalid',self.error.value)
        self.step()
    def test_missing_aircraft_fails_without_kinematic_fallback(self):
        h=self.lib.WiseEyeFDMCreate(str(ROOT/'builds/not-a-jsbsim-model').encode(),self.error,len(self.error))
        if h:self.lib.WiseEyeFDMDestroy(h)
        self.assertFalse(h)
