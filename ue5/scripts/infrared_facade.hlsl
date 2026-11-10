// Facade appearance proxy: material cues, not measured LWIR emissivity.
struct WiseEyeFacadeHeat
{
    float hash(float2 p) {
        // Deterministic world-anchored field: independent of screen UV/time.
        return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);
    }
    float field(float2 p) {
        float2 i=floor(p),f=frac(p);f=f*f*(3.-2.*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),
                    lerp(hash(i+float2(0,1)),hash(i+1.),f.x),f.y);
    }
    float background(float base, float category, float3 normal, float3 albedo,
                     float roughness, float detail, float day, float3 worldPosition)
    {
        // Use geometry/material-space detail, never a screen-space window grid.
        float vertical=1.-smoothstep(.35,.75,abs(normal.z));
        float masonry=1.-step(.5,abs(category-2.));
        float glass=1.-step(.5,abs(category-3.));
        float unknown=1.-step(.5,category);
        float facade=saturate(masonry+glass+unknown);
        float grain=sqrt(saturate(dot(albedo,float3(.2126,.7152,.0722))));
        float smoothSurface=1.-smoothstep(.18,.65,roughness);
        // Bounded roughness/albedo cues reveal opaque window/stone boundaries.
        // A low-roughness surface is NOT a measured or semantic glass label.
        float surfaceVariation=.085*(grain-.45)+.065*(roughness-.65)
                              -.032*smoothSurface;
        float orientation=.045*dot(normal,normalize(float3(.3,.4,.2)));
        float wallBase=lerp(.255,.280,day);
        // Roofs are slightly brighter than walls, without lifting whole facades.
        float building=wallBase+.060*(1.-vertical)+detail*(surfaceVariation+orientation);
        building=lerp(building,base+detail*surfaceVariation,glass);
        float result=lerp(base,building,facade);
        float road=1.-step(.5,abs(category-1.));
        // Paved roads previously returned a single palette value, losing all
        // albedo/roughness and thermal structure. These are appearance proxies,
        // not a solved heat equation or copied visible-light shadow map.
        float2 metres=worldPosition.xy*.01;
        float slow=field(metres/11.7),patch=field(metres/2.9);
        float pavement=.080*(slow-.5)+.036*(patch-.5)
                      +.050*(grain-.45)+.022*(roughness-.65);
        float roadSignal=base-lerp(.010,.035,day)
                         +detail*lerp(.65,1.,day)*pavement;
        result=lerp(result,roadSignal,road);
        // Unknown horizontal surfaces receive a small stable surface response;
        // this does not relabel every roof as asphalt.
        result+=unknown*(1.-vertical)*detail*(.014*(slow-.5)+.008*(patch-.5));
        return result;
    }
};
