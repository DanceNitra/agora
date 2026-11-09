import unreal, json, time
W, H = 512, 768
raw = open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\ref_512x768.bgra", "rb").read()
t = time.time()
cols = [unreal.Color(raw[i+2], raw[i+1], raw[i], raw[i+3]) for i in range(0, len(raw), 4)]
mhs = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
res = mhs.track_face_landmarks_from_image(cols, W, H)
out = {}
if res:
    for k, tp in res.items():
        if not out: print("ATTRS", [a for a in dir(tp) if not a.startswith("_")])
        pts = None
        for name in ("points", "tracking_points", "point_data", "points2d", "positions"):
            try:
                pts = tp.get_editor_property(name); break
            except Exception:
                pass
        out[str(k)] = [[p.x, p.y] for p in pts] if pts is not None else []
json.dump(out, open(r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\ref_landmarks.json", "w"))
print("curves", len(out), "points", sum(len(v) for v in out.values()), "sec", round(time.time()-t, 1))
print(sorted(out.keys()))
