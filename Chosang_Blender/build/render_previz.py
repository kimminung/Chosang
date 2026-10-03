"""프리비즈 렌더(백그라운드): blender -b Chosang_Template.blend -P render_previz.py -- <outdir> [clip ...]
각 clip_<name> 액션을 Armature(OB 슬롯)·Bust 셰이프키(KE 슬롯)에 할당하고 Previz_Camera 로 1920x1080 30fps H.264 mp4.
라이브러리·QA·참조 컬렉션은 제외(맨 흉상 기준)."""
import bpy, sys, os, glob
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
outdir = argv[0] if argv else os.path.expanduser("~/Desktop/Chosang_Blender/Template/previz")
only = set(argv[1:])
os.makedirs(outdir, exist_ok=True)
sc = bpy.context.scene; vl = bpy.context.view_layer
def find(lc, name):
    if lc.collection.name == name: return lc
    for ch in lc.children:
        r = find(ch, name)
        if r: return r
for name in ("Library", "_QA_Shapes", "_QA_Hair", "_Ref_Soban"):
    lc = find(vl.layer_collection, name)
    if lc: lc.exclude = True
for o in sc.objects: o.hide_render = False
sc.camera = bpy.data.objects["Previz_Camera"]
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
sc.render.fps = 30; sc.render.fps_base = 1.0
try: sc.eevee.taa_render_samples = 32
except Exception: pass
im = sc.render.image_settings
try: im.media_type = 'VIDEO'
except Exception: pass
im.file_format = 'FFMPEG'
ff = sc.render.ffmpeg; ff.format = 'MPEG4'; ff.codec = 'H264'; ff.constant_rate_factor = 'HIGH'; ff.ffmpeg_preset = 'GOOD'; ff.audio_codec = 'NONE'
arm = bpy.data.objects["Armature"]; key = bpy.data.objects["Bust"].data.shape_keys
for act in sorted([a for a in bpy.data.actions if a.name.startswith("clip_")], key=lambda a: a.name):
    name = act.name[5:]
    if only and name not in only: continue
    ad = arm.animation_data_create(); ad.action = act
    ad.action_slot = [s for s in act.slots if s.target_id_type == 'OBJECT'][0]
    kad = key.animation_data_create(); kad.action = act
    ks = [s for s in act.slots if s.target_id_type == 'KEY']
    if ks: kad.action_slot = ks[0]
    sc.frame_start = int(act.frame_range[0]); sc.frame_end = int(act.frame_range[1])
    base = os.path.join(outdir, name + "_")
    for f in glob.glob(base + "*.mp4"): os.remove(f)
    sc.render.filepath = base
    bpy.ops.render.render(animation=True)
    made = sorted(glob.glob(base + "*.mp4"), key=os.path.getmtime)
    if made: os.replace(made[-1], os.path.join(outdir, name + ".mp4"))
    print("PREVIZ_DONE", name, flush=True)
print("PREVIZ_ALL_DONE", flush=True)
