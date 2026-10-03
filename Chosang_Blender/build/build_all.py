"""초상 템플릿 처음부터 다시 만들기 (결정적, 난수 없음):
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P build_all.py -- <출력.blend>
입력: source/ARFaceGeometry.obj. 각 단계는 build/*.py. 작업 파일(Chosang_Template.blend)은 건드리지 않는다."""
import bpy, os, sys, math, json
ROOT = os.path.expanduser("~/Desktop/Chosang_Blender"); BD = os.path.join(ROOT, "build")
def load(name):
    ns = {}; p = os.path.join(BD, name); exec(compile(open(p, encoding="utf-8").read(), p, "exec"), ns); return ns
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else os.path.join(ROOT, "Chosang_Template_rebuild.blend")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.name = "Chosang"
sc.unit_settings.system = 'METRIC'; sc.unit_settings.length_unit = 'METERS'
sc.render.fps = 30; sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = 'Standard'
def coll(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    (parent or sc.collection).children.link(c); return c
tpl = coll("Chosang_Template"); lib = coll("Library")
for n in ("Library_Hair", "Library_Glasses", "Library_Beard", "Library_Shoulders"): coll(n, lib)
prev = coll("Previz")
from mathutils import Vector
aim = bpy.data.objects.new("Previz_Aim", None); prev.objects.link(aim); aim.location = (0.0, -0.09, 0.41)
cd = bpy.data.cameras.new("Previz_Camera"); cd.lens = 50; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_start = 0.05
cam = bpy.data.objects.new("Previz_Camera", cd); prev.objects.link(cam); cam.location = (0.0, -1.29, 0.41); cam.rotation_euler = (math.radians(90), 0, 0)
cam["chosang_aim"] = [0.0, -0.09, 0.41]; cam["chosang_distance_m"] = 1.2; cam["chosang_hfov_deg"] = math.degrees(2 * math.atan(18 / 50))
sc.camera = cam
for nm, off, pw, sz, col in (("Light_Key", (-0.65, -0.85, 0.45), 55.0, 0.8, (1, .97, .93)), ("Light_Fill", (0.8, -0.75, 0.1), 18.0, 1.0, (.93, .96, 1)), ("Light_Rim", (0.35, 0.9, 0.55), 45.0, 0.6, (1, 1, 1))):
    ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = pw; ld.size = sz; ld.color = col; ld.shape = 'DISK'
    o = bpy.data.objects.new(nm, ld); prev.objects.link(o); o.location = aim.location + Vector(off)
    c = o.constraints.new('TRACK_TO'); c.target = aim; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
w = bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.18, 0.18, 0.19, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
g = load("gen_hair_textures.py"); g["build_atlas"](); g["build_buzz"]()
load("bust_build.py")["build_bust"]()
bust = bpy.data.objects["Bust"]
load("eye_fix.py")["fix"](bust)
load("ears.py")["add_ears"](bust)
meta = json.loads(bust["chosang_patch"])
arm = bpy.data.objects.new("Armature", bpy.data.armatures.new("Armature")); tpl.objects.link(arm); arm.show_in_front = True
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
def bone(n, h, t, par=None):
    b = eb.new(n); b.head = h; b.tail = t; b.roll = 0.0
    if par: b.parent = eb[par]
cL, cR = meta["eyeball_center_left"], meta["eyeball_center_right"]
bone("Root", (0, 0.024, 0.0), (0, 0.024, 0.12)); bone("Spine", (0, 0.024, 0.12), (0, 0.024, 0.30), "Root")
bone("Neck", (0, 0.024, 0.30), (0, 0.012, 0.36), "Spine"); bone("Head", (0, 0.012, 0.36), (0, 0.012, 0.54), "Neck")
bone("Eye_L", tuple(cL), (cL[0], cL[1] - 0.02, cL[2]), "Head"); bone("Eye_R", tuple(cR), (cR[0], cR[1] - 0.02, cR[2]), "Head")
bpy.ops.object.mode_set(mode='OBJECT')
load("uv_eyes_mouth.py")["run"]()
for m in bpy.data.materials:
    if m.use_nodes and m.node_tree.nodes.get("Principled BSDF"):
        c = m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value; m.diffuse_color = (c[0], c[1], c[2], 1)
s = load("shapes.py"); V, D, mags, info = s["bust_shapes"](); s["mouth_inner_shapes"](info)
bust.data.shape_keys.name = "Key_Bust"; bpy.data.objects["Mouth_Inner"].data.shape_keys.name = "Key_MouthInner"
bust.data.polygons.foreach_set("use_smooth", [True] * len(bust.data.polygons))
load("author_clips.py")["author"]()
load("hair.py")["run"](); load("library_misc.py")["run"]()
bpy.ops.wm.save_as_mainfile(filepath=out)
print("BUILD_ALL_DONE", out, len(bust.data.vertices), flush=True)
