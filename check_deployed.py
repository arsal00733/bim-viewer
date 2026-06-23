"""Check deployed GLB for baseColorFactor values."""
import json, struct

with open("deployed.glb", "rb") as f:
    f.read(12)  # header
    while True:
        cl = struct.unpack("<I", f.read(4))[0]
        ct = struct.unpack("<I", f.read(4))[0]
        cd = f.read(cl)
        if ct == 0x4E4F534A:
            gltf = json.loads(cd)
            for i, mat in enumerate(gltf["materials"]):
                pbr = mat.get("pbrMetallicRoughness", {})
                bcf = pbr.get("baseColorFactor", "?")
                rough = pbr.get("roughnessFactor", "?")
                print(f"  [{i}] {mat['name']}: bcf={bcf}, rough={rough}")
            break
