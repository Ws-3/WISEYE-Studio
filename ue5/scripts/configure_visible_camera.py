"""Build only the visible camera material; no map or user settings are edited."""
import unreal

folder='/Game/WISEYE/Sensors'
tools=unreal.AssetToolsHelpers.get_asset_tools()
mat=unreal.load_asset(folder+'/M_VisibleCamera')
if not mat:mat=tools.create_asset('M_VisibleCamera',folder,unreal.Material,unreal.MaterialFactoryNew())
mat.modify()
lib=unreal.MaterialEditingLibrary
lib.delete_all_material_expressions(mat)
mat.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
def node(cls,x,y):return lib.create_material_expression(mat,cls,x,y)
custom=node(unreal.MaterialExpressionCustom,300,0)
custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
names=['Scene','BlurPixels','Noise','Contrast','Saturation','LowLight','Clock']
inputs=[]
for name in names:
    i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
custom.set_editor_property('inputs',inputs)
custom.set_editor_property('code',r'''
float2 uv=GetDefaultSceneTextureUV(Parameters,14);
float3 color=Scene.rgb;
if (BlurPixels>0.001) {
    float2 d=View.BufferSizeAndInvSize.zw*BlurPixels;
    color=0;
    [unroll] for(int y=-1;y<=1;y++) {
        [unroll] for(int x=-1;x<=1;x++) {
            float w=(x==0?2:1)*(y==0?2:1)/16.0;
            color+=w*SceneTextureLookup(ClampSceneTextureUV(uv+float2(x,y)*d,14),14,true).rgb;
        }
    }
}
float luma=dot(color,float3(.2126,.7152,.0722));
color=lerp(luma.xxx,color,Saturation);
// Contrast response preserves black. The old affine pivot added a grey floor
// in every dark pixel, washing out night scenes regardless of exposure.
color=saturate(color);
color+=(Contrast-1.)*2.*color*(1.-color)*(2.*color-1.);
float2 pixel=floor(uv*View.BufferSizeAndInvSize.xy);
// Independent zero-mean samples approximate shot/read noise; fixed response
// is weak and scene brightness does not create an artificial fog overlay.
float frame=floor(Clock*30.);
float a=frac(sin(dot(pixel+frame*float2(1.37,2.91),float2(12.9898,78.233)))*43758.5453);
float b=frac(sin(dot(pixel+frame*float2(3.11,1.17),float2(39.346,11.135)))*47453.5453);
float fixedPattern=frac(sin(dot(pixel,float2(93.989,67.345)))*24634.6345)-.5;
float grain=(a+b-1.)+.08*fixedPattern;
float gain=lerp(1.,4.,saturate(LowLight));
color+=grain*Noise*gain*(.45+.55*(1.-sqrt(saturate(luma))));
return saturate(color);
''')
scene=node(unreal.MaterialExpressionSceneTexture,-500,0)
scene.set_editor_property('scene_texture_id',unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
lib.connect_material_expressions(scene,'Color',custom,'Scene')
for j,(name,value) in enumerate([('BlurPixels',.95),('Noise',.006),('Contrast',.96),('Saturation',.88),('LowLight',0)]):
    p=node(unreal.MaterialExpressionScalarParameter,-300,150+j*100)
    p.set_editor_property('parameter_name',name);p.set_editor_property('default_value',value)
    lib.connect_material_expressions(p,'',custom,name)
clock=node(unreal.MaterialExpressionTime,-500,600)
lib.connect_material_expressions(clock,'',custom,'Clock')
lib.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
lib.recompile_material(mat)
assert unreal.EditorAssetLibrary.save_asset(mat.get_path_name(),only_if_is_dirty=False)
print('WISEYE_VISIBLE_CAMERA_MATERIAL_SAVED')
