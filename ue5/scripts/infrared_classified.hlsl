// Component material categories, not physical emissivity/temperature.
struct WiseEyeRegionalHeat
{
    float spot(float2 uv,float4 p) {
        float2 q=(uv-p.xy)/max(p.z,.0001);q.y*=.8;
        return p.w*exp(-.5*dot(q,q));
    }
};
if (DisplayReadout<.5 && Classified>.5 && Reference>.5)
{
    WiseEyeRegionalHeat regions;
    float d=Depth.r;
    float isSky=step(10000000.,d);
    // Empty custom-depth pixels can carry a far sentinel and nonzero stencil.
    // Never classify the far clear value as a real thermal target.
    float validCustom=step(.001,CustomDepth.r)*(1.-step(1000000.,CustomDepth.r));
    float depthVisible=validCustom*step(CustomDepth.r,d+2.);
    float code=floor(Stencil.r+.5);
    float category=(code>=1. && code<=6. && depthVisible>.5)?code:0.;
#if defined(WISEYE_FACADE)
    // City captures have a finite far sentinel below the old 100 km cutoff.
    // Treat the >=10 km far background as sky. Not a long-range terrain model.
    if (Facade>.5) isSky=max(isSky,step(1000000.,d));
#endif
    float4 palette1=lerp(ClassNight1,ClassDay1,DayWeight);
    float4 palette2=lerp(ClassNight2,ClassDay2,DayWeight);
    float base=lerp(.25,.29,DayWeight); // explicit unknown background
    if (category==1.) base=palette1.x;
    if (category==2.) base=palette1.y;
    if (category==3.) base=palette1.z;
    if (category==4.) base=palette1.w;
    if (category==5.) base=palette2.x;
    if (category==6.) base=palette2.y;
    float structure=dot(Normal.rgb,normalize(float3(.3,.4,1.)));
    // Much less high-frequency RGB/normal detail than the first pilot.
    float textureDetail=dot(SceneColor.rgb,float3(.2126,.7152,.0722))-.5;
    float background=base+BackgroundDetail*(.012*structure+.006*textureDetail);
#if defined(WISEYE_FACADE)
    if (Facade>.5) {
        WiseEyeFacadeHeat facade;
        background=facade.background(base,category,Normal.rgb,BaseColor.rgb,Roughness.r,BackgroundDetail,DayWeight,WorldPosition);
    }
#endif
    background=lerp(background,SkyHeat,isSky);
#if defined(WISEYE_FACADE)
    if (Facade>.5) {
        // Appearance proxy from the actual rendered sky, not fake cloud shapes.
        float lum=saturate(textureDetail+.5);
        float chroma=max(max(SceneColor.r,SceneColor.g),SceneColor.b)-min(min(SceneColor.r,SceneColor.g),SceneColor.b);
        float cloud=saturate((lum-.12)*1.8)*(1.-saturate(chroma/max(lum,.03)));
        background=lerp(background,SkyHeat+BackgroundDetail*(.018*sqrt(lum)+.12*cloud),isSky);
    }
#endif
    float droneVisible=step(32.,code)*depthVisible;
    float car=(1.-step(.5,abs(code-16.)))*depthVisible;
    float person=(1.-step(.5,abs(code-17.)))*depthVisible;
    float population=max(car,person);
    float targetVisible=max(droneVisible,population);
    float selectedBody=(1.-step(.5,abs(code-BodyCode)))*step(abs(CustomDepth.r-TargetDepth),60.);
    float motors=max(max(regions.spot(UV,MotorSpot0),regions.spot(UV,MotorSpot1)),max(regions.spot(UV,MotorSpot2),regions.spot(UV,MotorSpot3)));
    float battery=regions.spot(UV,BatterySpot);
    float target=.30+.55*(code/255.-.32);
#if defined(WISEYE_FACADE)
    if (Facade>.5) {
        // Visible target pixels only: spots never paint through roofs/occluders.
        float selectedSurface=droneVisible*step(abs(CustomDepth.r-TargetDepth),60.);
        target+=selectedSurface*(battery*(.025+.25*BatteryWarmth)+motors*(.025+.45*MotorWarmth));
        // Population stencils are separate from drone temperature codes. A
        // complete car is not a uniform engine-temperature target. Material and
        // normal cues are bounded proxies, not measured glass/engine heat.
        float surface=sqrt(saturate(dot(BaseColor.rgb,float3(.2126,.7152,.0722))));
        float smoothSurface=1.-smoothstep(.18,.65,Roughness.r);
        float vehicleHeat=.285+.045*surface+.018*Roughness.r+.022*abs(Normal.z)-.045*smoothSurface;
        float peopleHeat=.34+.020*surface+.012*Normal.z;
        target=lerp(target,lerp(vehicleHeat,peopleHeat,person),population);
    } else
#endif
    target+=selectedBody*(battery*(.01+.09*BatteryWarmth)+TargetAvata*motors*(.025+.30*MotorWarmth));
    float transmission=exp(-max(d,0.)/500000.);
    float signal=lerp(background,lerp(background,target,transmission),targetVisible);
    float2 pixel=floor(UV*float2(640.,512.));
    float fixedNoise=frac(sin(dot(pixel,float2(12.9898,78.233)))*43758.5453)-.5;
    float temporal=frac(sin(dot(pixel+NoiseFrame*float2(1.37,2.91),float2(39.346,11.135)))*47453.5453)-.5;
    signal=saturate(signal+NoiseStrength*(.8*temporal+.25*fixedNoise));
    // G/B are diagnostic labels before detector PSF; only R feeds the detector.
    float motorRegion=selectedBody*TargetAvata*step(.2,motors);
#if defined(WISEYE_FACADE)
    if (Facade>.5) motorRegion=droneVisible*step(abs(CustomDepth.r-TargetDepth),60.)*step(.2,motors);
#endif
    return float3(signal,category/8.,droneVisible*(.5+.5*motorRegion)+population*.23+(1.-targetVisible)*isSky*.125);
}
