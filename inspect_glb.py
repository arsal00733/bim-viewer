"""Inspect GLB vertex colour values."""
import json, struct
import numpy as np

with open("bridge_model_20260623114352.glb", "rb") as f:
    magic = struct.unpack("<I", f.read(4))[0]
    version = struct.unpack("<I", f.read(4))[0]
    length = struct.unpack("<I", f.read(4))[0]

    json_buf = None
    bin_buf = None
    while f.tell() < length:
        chunk_len = struct.unpack("<I", f.read(4))[0]
        chunk_type = struct.unpack("<I", f.read(4))[0]
        chunk_data = f.read(chunk_len)
        if chunk_type == 0x4E4F534A:
            gltf = json.loads(chunk_data.decode("utf-8"))
        elif chunk_type == 0x004E4942:
            bin_buf = chunk_data

    # Show all materials with their baseColorFactor
    print("=== Materials ===")
    for i, mat in enumerate(gltf["materials"]):
        pbr = mat.get("pbrMetallicRoughness", {})
        bcf = pbr.get("baseColorFactor", "N/A")
        rough = pbr.get("roughnessFactor", "N/A")
        metal = pbr.get("metallicFactor", "N/A")
        print(f"  [{i}] {mat['name']}: bcf={bcf}, rough={rough}, metal={metal}")
    print()

    # Check first few meshes
    for mesh_idx in [0, 4, 12, 15, 18, 23]:
        mesh = gltf["meshes"][mesh_idx]
        prim = mesh["primitives"][0]
        col_idx = prim["attributes"]["COLOR_0"]
        acc = gltf["accessors"][col_idx]
        bv = gltf["bufferViews"][acc["bufferView"]]
        comp_type = acc["componentType"]
        nrm = acc.get("normalized", False)
        offset = bv.get("byteOffset", 0)

        dtype = np.uint8 if comp_type == 5121 else np.float32
        ncols = 4 if acc["type"] == "VEC4" else 3
        count = acc["count"]
        arr = np.frombuffer(bin_buf, dtype=dtype, count=count * ncols,
                            offset=offset).reshape(count, ncols)

        mat_name = gltf["materials"][prim["material"]]["name"]
        print(f"[{mesh_idx}] {mat_name}: type={acc['type']}, "
              f"compType={comp_type}, norm={nrm}, count={count}")
        print(f"  min={arr.min(axis=0).tolist()} "
              f"max={arr.max(axis=0).tolist()} "
              f"mean={arr.mean(axis=0).round(1).tolist()}")
        print(f"  first 3 verts: {arr[:3].tolist()}")
        print()
