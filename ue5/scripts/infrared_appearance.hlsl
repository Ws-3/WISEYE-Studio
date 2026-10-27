// Appearance-only thermal camera prototype, not a calibrated radiance model.
// Sample normalized heat BEFORE optical blur and palette inversion.
struct ThermalAppearance
{
    float hash(float2 p)
    {
        float3 q=frac(float3(p.xyx)*.1031);
        q+=dot(q,q.yzx+33.33);
        return frac((q.x+q.y)*q.z);
    }
    float heat(float2 uv,float ground,float skyHeat,float detail)
    {
        uv=clamp(uv,float2(.5/640.,.5/512.),float2(1.-.5/640.,1.-.5/512.));
        float d=SceneTextureLookup(ViewportUVToSceneTextureUV(uv,PPI_SceneDepth),PPI_SceneDepth,false).r;
        float cd=SceneTextureLookup(ViewportUVToSceneTextureUV(uv,PPI_CustomDepth),PPI_CustomDepth,false).r;
        float s=SceneTextureLookup(ViewportUVToSceneTextureUV(uv,PPI_CustomStencil),PPI_CustomStencil,false).r;
        float3 n=SceneTextureLookup(ViewportUVToSceneTextureUV(uv,PPI_WorldNormal),PPI_WorldNormal,false).rgb;
        float3 rgb=SceneTextureLookup(ViewportUVToSceneTextureUV(uv,PPI_PostProcessInput0),PPI_PostProcessInput0,true).rgb;
        float sky=step(10000000.,d);
        // Broad surface cues only. Visible brightness is a small texture proxy,
        // not a temperature measurement or material classification.
        float textureProxy=sqrt(saturate(dot(rgb,float3(.2126,.7152,.0722))))-.5;
        float structure=dot(n,normalize(float3(.3,.4,1.)));
        float background=ground+detail*(.075*structure+.04*textureProxy);
        background=lerp(background,ground,1.-exp(-max(d,0.)/180000.));
        background=lerp(background,skyHeat,sky);
        float visible=step(.5,s)*step(cd,d+1.);
        float target=.32+.45*(s/255.-.27);
        float transmission=exp(-max(d,0.)/350000.);
        return lerp(background,lerp(background,target,transmission),visible);
    }
};
ThermalAppearance model;
float2 pixel=floor(UV*float2(640.,512.));
if (Enhanced<.5)
{
    // Preserve the original sensor formula for a direct same-pose comparison.
    float visible=step(.5,Stencil.r)*step(CustomDepth.r,Depth.r+1.);
    float sky=step(10000000.,Depth.r);
    float structure=.025*dot(Normal.rgb,normalize(float3(.3,.4,1.)));
    float heat=lerp(lerp(BackgroundHeat+structure,SkyHeat,sky),saturate(Stencil.r/255.),visible);
    float noise=frac(sin(dot(pixel,float2(12.9898,78.233)))*43758.5453)-.5;
    float value=lerp(saturate(heat+noise*NoiseStrength),1.-saturate(heat+noise*NoiseStrength),BlackHot);
    return value.xxx;
}
float heat=model.heat(UV,BackgroundHeat,SkyHeat,BackgroundDetail);
if (BlurPixels>.001)
{
    float2 stepUV=BlurPixels/float2(640.,512.);
    heat=.5*heat+.125*(
        model.heat(UV+float2(stepUV.x,0),BackgroundHeat,SkyHeat,BackgroundDetail)+
        model.heat(UV-float2(stepUV.x,0),BackgroundHeat,SkyHeat,BackgroundDetail)+
        model.heat(UV+float2(0,stepUV.y),BackgroundHeat,SkyHeat,BackgroundDetail)+
        model.heat(UV-float2(0,stepUV.y),BackgroundHeat,SkyHeat,BackgroundDetail));
}
// Sensor-fixed pattern and frame-varying noise are separate terms. Frame index
// is per sensor and advances only when an IR frame is actually captured.
float fixedNoise=model.hash(pixel+float2(17,31))-.5;
float temporalNoise=model.hash(pixel+float2(NoiseFrame*1.37,NoiseFrame*2.91))-.5;
float value=saturate((heat-.3)*Contrast+.4+NoiseStrength*(1.6*temporalNoise+.35*fixedNoise));
value=lerp(value,1.-value,BlackHot);
return value.xxx;
