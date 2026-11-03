#include "../../ue5/WISEYE/Source/test/WiseEyeEventMath.h"
#include <cassert>
#include <limits>
#include <iostream>
using namespace WiseEyeEvents;
int main() {
    Model m;float v=1;
    assert(m.Process(&v,1,1,0).empty());
    assert(m.Process(&v,1,1,.01).empty());
    v=std::exp(.1f);assert(m.Process(&v,1,1,.02).empty());
    v=std::exp(.45f);auto e=m.Process(&v,1,1,.03);assert(e.size()==2);
    assert(e[0].P==1 && e[0].T>=20000 && e[1].T<=30000 && e[0].T<e[1].T);
    v=std::exp(-.05f);e=m.Process(&v,1,1,.04);assert(e.size()==2 && e[0].P==-1);
    v=std::numeric_limits<float>::quiet_NaN();assert(m.Process(&v,1,1,.05).empty());
    assert(m.Process(&v,1,1,.04).empty());
    m.Reset();m.Refractory=1000000;v=1;m.Process(&v,1,1,0);
    v=std::exp(.85f);e=m.Process(&v,1,1,.01);assert(e.size()==1);
    m.Reset();m.Refractory=0;v=1;m.Process(&v,1,1,0);
    v=std::exp(3.f);e=m.Process(&v,1,1,.1,2);assert(e.size()==2 && m.Truncated>=12);
    m.Reset();assert(m.Previous.empty() && m.Last.empty() && m.PreviousTime<0);
    std::vector<float> field(100,1);m.Process(field.data(),100,1,0);
    field.assign(100,std::exp(.45f));e=m.Process(field.data(),100,1,.1,50);
    assert(e.size()==50 && m.Truncated==150);
    assert(std::any_of(e.begin(),e.end(),[](const Event& v){return v.X>75;}));
    std::cout<<"event threshold, accumulation, polarity, timestamps, refractory, caps, invalid signal PASS\n";
}
