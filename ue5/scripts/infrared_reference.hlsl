// Reference-guided normalized thermal signal. Not calibrated LWIR radiance.
if (DisplayReadout>.5) return DisplayColor.rgb;
if (Reference>.5)
{
    float d=Depth.r;
    float lum=sqrt(saturate(dot(SceneColor.rgb,float3(.2126,.7152,.0722))));
    float structure=dot(Normal.rgb,normalize(float3(.3,.4,1.)));
    float sky=step(10000000.,d);
    // Background cues remain a proxy in this pilot; no city material is edited.
    float background=BackgroundHeat+BackgroundDetail*(.055*structure+.035*(lum-.5));
    background=lerp(background,SkyHeat+BackgroundDetail*.035*lum,sky);
    float visible=step(.5,Stencil.r)*step(CustomDepth.r,d+1.);
    float body=1.-step(.5,abs(Stencil.r-BodyCode));
    float2 offset=(UV-BatterySpot.xy)/max(BatterySpot.z,.0001);
    offset.y*=.8;
    float battery=body*BatterySpot.w*(.015+.07*BatteryWarmth)*exp(-.5*dot(offset,offset));
    float target=saturate(Stencil.r/255.+battery);
    float transmission=exp(-max(d,0.)/500000.);
    float signal=lerp(background,lerp(BackgroundHeat,target,transmission),visible);
    float2 pixel=floor(UV*float2(640.,512.));
    float fixedNoise=frac(sin(dot(pixel,float2(12.9898,78.233)))*43758.5453)-.5;
    float temporal=frac(sin(dot(pixel+NoiseFrame*float2(1.37,2.91),float2(39.346,11.135)))*47453.5453)-.5;
    float row=frac(sin(pixel.y*17.31)*13758.21)-.5;
    signal=saturate(signal+NoiseStrength*(.8*temporal+.25*fixedNoise+.12*row));
    return signal.xxx;
}
