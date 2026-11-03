// Facade appearance proxy: material cues, not measured LWIR emissivity.
struct WiseEyeFacadeHeat
{
    float background(float base, float category, float3 normal, float3 albedo,
                     float roughness, float detail, float day)
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
        return lerp(base,building,facade);
    }
};
