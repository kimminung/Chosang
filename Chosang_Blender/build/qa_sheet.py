"""QA 시트: 셰이프 1.0 스냅샷을 격자로(눈·눈썹 시트, 입·턱 시트). _QA_Shapes 컬렉션(내보내기 대상 아님)."""
import bpy, json, numpy as np, math
UP = ["Basis", "eyeBlinkLeft", "eyeBlinkRight", "eyeWideLeft", "eyeWideRight", "eyeSquintLeft", "eyeSquintRight", "eyeLookUpLeft", "eyeLookUpRight",
      "eyeLookDownLeft", "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight", "browDownLeft", "browDownRight",
      "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight", "cheekPuff"]
LO = ["Basis", "jawOpen", "jawForward", "jawLeft", "jawRight", "mouthClose", "mouthFunnel", "mouthPucker", "mouthLeft", "mouthRight",
      "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight", "mouthDimpleLeft", "mouthDimpleRight", "mouthStretchLeft",
      "mouthStretchRight", "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthPressLeft", "mouthPressRight",
      "mouthLowerDownLeft", "mouthLowerDownRight", "mouthUpperUpLeft", "mouthUpperUpRight", "tongueOut"]
def run():
    coll = bpy.data.collections.get("_QA_Shapes")
    if coll:
        for o in list(coll.objects):
            d = o.data; bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and d.users == 0:
                (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.curves).remove(d)
    else:
        coll = bpy.data.collections.new("_QA_Shapes"); bpy.context.scene.collection.children.link(coll)
    bust = bpy.data.objects["Bust"]; me = bust.data; kb = me.shape_keys.key_blocks; n = len(me.vertices)
    def co_of(block, nv):
        a = np.empty(nv * 3); block.data.foreach_get("co", a); return a.reshape(-1, 3)
    B = co_of(kb["Basis"], n)
    meta = json.loads(bust["chosang_patch"]); band = set(meta["lid_inner"] + meta["lip_inner"])
    polys = [tuple(p.vertices) for p in me.polygons if p.index < 1152 or any(v in band for v in p.vertices)]
    fz = np.array([B[list(f)][:, 2].mean() for f in polys])
    mio = bpy.data.objects["Mouth_Inner"]; mik = mio.data.shape_keys.key_blocks; mn = len(mio.data.vertices)
    MI_B = co_of(mik["Basis"], mn); mi_faces = [tuple(p.vertices) for p in mio.data.polygons]
    mi_mats = list(mio.data.materials); mi_mi = [p.material_index for p in mio.data.polygons]
    skin = bpy.data.materials["Skin"]
    def mk(name, P, faces, off, mats, midx=None):
        used = sorted(set(v for f in faces for v in f)); rm = {v: i for i, v in enumerate(used)}
        m = bpy.data.meshes.new(name); m.from_pydata((P[used] + off).tolist(), [], [[rm[v] for v in f] for f in faces]); m.update()
        for p in m.polygons: p.use_smooth = True
        for mt in mats: m.materials.append(mt)
        if midx is not None:
            for p, k in zip(m.polygons, midx): p.material_index = k
        o = bpy.data.objects.new(name, m); coll.objects.link(o); return o
    def label(txt, loc):
        cu = bpy.data.curves.new("L_" + txt, 'FONT'); cu.body = txt; cu.size = 0.011; cu.align_x = 'CENTER'
        o = bpy.data.objects.new("L_" + txt, cu); o.location = loc; o.rotation_euler = (math.radians(90), 0, 0); coll.objects.link(o)
    eyes = [bpy.data.objects["Eye_L"], bpy.data.objects["Eye_R"]]
    def sheet(names, region, origin, cols, dx, dz):
        sel = [f for f, zz in zip(polys, fz) if (zz > 0.405 if region == "upper" else zz < 0.428)]
        for i, nm in enumerate(names):
            r, c = divmod(i, cols); off = np.array([origin[0] + c * dx, 0.0, origin[2] - r * dz])
            mk("QA_" + nm + "_" + region, B if nm == "Basis" else co_of(kb[nm], n), sel, off, [skin])
            if region == "upper":
                for e in eyes:
                    o = bpy.data.objects.new("QA_eye_%s_%s" % (nm, e.name), e.data); o.location = tuple(off); coll.objects.link(o)
            else:
                mk("QA_mi_" + nm, co_of(mik[nm], mn) if nm in mik else MI_B, mi_faces, off, mi_mats, mi_mi)
            label(nm, (off[0], -0.13, (0.395 if region == "upper" else 0.318) + off[2]))
    sheet(UP, "upper", (3.0, 0, 0.0), 5, 0.16, 0.135)
    sheet(LO, "lower", (4.2, 0, 0.0), 6, 0.16, 0.13)
    return len(coll.objects)
