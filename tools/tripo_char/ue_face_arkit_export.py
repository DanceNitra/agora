"""Runs inside Unreal. Exports Yuki's MetaHuman face mesh in the neutral pose and in each ARKit expression, as the
source for transferring expressions onto the Tripo head (plan section 9, path T).

The expressions come from Epic's mapping animation /MetaHumanCharacter/Face/ARKit/AS_MetaHuman_ARKit_Mapping, which
holds one ARKit expression per frame as RigLogic control curves. The face only evaluates animation in Play-in-Editor,
so every step runs on the play copy and a frame needs one engine tick between "set" and "copy".

ARGS = dict(STEP="probe" | "set" | "copy", FRAME=<int>, OUT=<folder>)
- probe: prints the mapping animation's frame count, curve count and the pose asset's pose names.
- set:   plays the mapping animation on the play copy's Face at FRAME, rate 0, LOD 0.
- copy:  copies the posed Face mesh (bones and morph targets applied) and writes OUT/face_<FRAME>.txt (vertices) and,
         for frame 0, OUT/face_tris.txt (triangles)."""
import os

import unreal

_A = globals().pop("ARGS", {})
STEP, FRAME, OUT = _A.get("STEP", "probe"), int(_A.get("FRAME", 0)), _A.get("OUT", "")
MAP = "/MetaHumanCharacter/Face/ARKit/AS_MetaHuman_ARKit_Mapping"

if STEP == "probe":
    an = unreal.load_asset(MAP)
    print("PROBE anim", an.get_class().get_name(), "frames", an.get_editor_property("number_of_sampled_frames")
          if hasattr(an, "get_editor_property") else None, "length", an.get_play_length())
    names = unreal.AnimationLibrary.get_animation_curve_names(an, unreal.RawCurveTrackTypes.RCT_FLOAT)
    print("PROBE curves", len(names), [str(n) for n in names[:6]])
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for ad in reg.get_assets_by_path("/MetaHumanCharacter/Face/ARKit", recursive=True):
        print("PROBE asset", ad.asset_class_path.asset_name, ad.package_name)
    for ad in reg.get_assets_by_path("/MetaHumanCharacter/Face/ARKit", recursive=True):
        if str(ad.asset_class_path.asset_name) == "PoseAsset":
            pa = unreal.load_asset(str(ad.package_name))
            pn = [str(x) for x in pa.get_pose_names()]
            print("PROBE poses", len(pn), pn)
else:
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    face = None
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        if "MHC_Yuki" in a.get_class().get_name():
            face = next(c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face")
    if face is None:
        raise RuntimeError("no play copy of Yuki: start Play-in-Editor first")
    if STEP == "set":
        an = unreal.load_asset(MAP)
        fps = 24.0           # the mapping animation: 53 keys at 1/24 s (probed 2026-11-14)
        face.set_forced_lod(1)          # 1 = LOD 0 (0 means automatic)
        # The body's idle moves the neck, so every frame would carry a different head position: hold the body still.
        for c in face.get_owner().get_components_by_class(unreal.SkeletalMeshComponent):
            if c.get_name() == "Body":
                c.set_position(0.0, False)
                c.set_play_rate(0.0)
        face.play_animation(an, False)
        face.set_position(FRAME / fps, False)
        face.set_play_rate(0.0)
        print("SET frame", FRAME, "pos", round(face.get_position(), 4))
    elif STEP == "setcopy":
        # song frames, one call per frame: copy the pose set by the previous call (one engine tick has passed), then
        # set the next one. ARGS: ANIM (asset path), T0 (seconds), FPS, FRAME (index to set; FRAME-1 is copied)
        an = unreal.load_asset(_A["ANIM"])
        fps_s, t0 = float(_A.get("FPS", 30.0)), float(_A.get("T0", 0.0))
        if FRAME > 0:
            os.makedirs(OUT, exist_ok=True)
            dm = unreal.DynamicMesh()
            opts = unreal.GeometryScriptCopyMeshFromComponentOptions()
            opts.set_editor_property("want_normals", False)
            opts.set_editor_property("want_tangents", False)
            lod = unreal.GeometryScriptMeshReadLOD()
            lod.set_editor_property("lod_type", unreal.GeometryScriptLODType.RENDER_DATA)
            lod.set_editor_property("lod_index", 0)
            opts.set_editor_property("requested_lod", lod)
            res = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(face, dm, opts, False)
            dm = res[0] if isinstance(res, (list, tuple)) else res
            _, vl, _gap = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
            pts = vl.convert_vector_list_to_array()
            np_ = __import__("array").array("f", [c for p_ in pts for c in (p_.x, p_.y, p_.z)])
            with open(os.path.join(OUT, f"f_{FRAME - 1:05d}.bin"), "wb") as f:
                np_.tofile(f)
        if face.get_animation_mode() != unreal.AnimationMode.ANIMATION_SINGLE_NODE or FRAME == 0:
            face.set_forced_lod(1)
            for c in face.get_owner().get_components_by_class(unreal.SkeletalMeshComponent):
                if c.get_name() == "Body":
                    c.set_position(0.0, False)
                    c.set_play_rate(0.0)
            face.play_animation(an, False)
        face.set_position(t0 + FRAME / fps_s, False)
        face.set_play_rate(0.0)
        print("SETCOPY", FRAME, round(face.get_position(), 4))
    elif STEP == "uvs":
        # UV set 0 per vertex, material id per triangle and the face mesh's material slot names (same vertex order
        # as the "copy" step, which copies the same component the same way)
        os.makedirs(OUT, exist_ok=True)
        dm = unreal.DynamicMesh()
        opts = unreal.GeometryScriptCopyMeshFromComponentOptions()
        opts.set_editor_property("want_normals", False)
        opts.set_editor_property("want_tangents", False)
        lod = unreal.GeometryScriptMeshReadLOD()
        lod.set_editor_property("lod_type", unreal.GeometryScriptLODType.RENDER_DATA)
        lod.set_editor_property("lod_index", 0)
        opts.set_editor_property("requested_lod", lod)
        res = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(face, dm, opts, False)
        dm = res[0] if isinstance(res, (list, tuple)) else res
        # UV set 0 as a mesh in UV space (same triangle ids): per-corner UVs come from its triangles
        uvm = unreal.DynamicMesh()
        r = unreal.GeometryScript_UVs.copy_mesh_uv_layer_to_mesh(dm, 0, uvm)
        uvm = r[1] if isinstance(r, (list, tuple)) else uvm
        _, pl, _g = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(uvm, False)
        upts = pl.convert_vector_list_to_array()
        _, tl2, _g2 = unreal.GeometryScript_MeshQueries.get_all_triangle_indices(uvm, False)
        utris = tl2.convert_triangle_list_to_array()
        with open(os.path.join(OUT, "face_tri_uv0.txt"), "w") as f:
            for t in utris:
                a_, b_, c_ = upts[t.x], upts[t.y], upts[t.z]
                f.write(f"{a_.x:.6f} {a_.y:.6f} {b_.x:.6f} {b_.y:.6f} {c_.x:.6f} {c_.y:.6f}" + chr(10))
        r2 = unreal.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
        mids = r2[1].convert_index_list_to_array() if hasattr(r2[1], "convert_index_list_to_array") else list(r2[1])
        with open(os.path.join(OUT, "face_matid.txt"), "w") as f:
            f.write(chr(10).join(str(int(m)) for m in mids))
        uvs = utris
        names = [str(m.get_name()) if m else "None" for m in face.get_materials()]
        with open(os.path.join(OUT, "face_materials.txt"), "w") as f:
            f.write(chr(10).join(names))
        print("UVS tris", len(utris), "uv verts", len(upts), "matid tris", len(mids), "mats", names)
    elif STEP == "copy":
        os.makedirs(OUT, exist_ok=True)
        dm = unreal.DynamicMesh()
        opts = unreal.GeometryScriptCopyMeshFromComponentOptions()
        opts.set_editor_property("want_normals", False)
        opts.set_editor_property("want_tangents", False)
        lod = unreal.GeometryScriptMeshReadLOD()
        lod.set_editor_property("lod_type", unreal.GeometryScriptLODType.RENDER_DATA)
        lod.set_editor_property("lod_index", 0)
        opts.set_editor_property("requested_lod", lod)
        res = unreal.GeometryScript_SceneUtils.copy_mesh_from_component(face, dm, opts, False)
        dm = res[0] if isinstance(res, (list, tuple)) else res
        _, vl, _gap = unreal.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
        pts = vl.convert_vector_list_to_array()
        with open(os.path.join(OUT, f"face_{FRAME:03d}.txt"), "w") as f:
            for p in pts:
                f.write(f"{p.x:.5f} {p.y:.5f} {p.z:.5f}\n")
        if FRAME == 0:
            _, tl, _tgap = unreal.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
            tris = tl.convert_triangle_list_to_array()
            with open(os.path.join(OUT, "face_tris.txt"), "w") as f:
                for t in tris:
                    f.write(f"{t.x} {t.y} {t.z}\n")
            print("COPY tris", len(tris))
        print("COPY frame", FRAME, "verts", len(pts), "pos", round(face.get_position(), 4))
