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

    # Check first few meshes for COLOR_0
    print("=== Mesh attributes ===")
    for mesh_idx in range(min(6, len(gltf["meshes"]))):
        mesh = gltf["meshes"][mesh_idx]
        prim = mesh["primitives"][0]
        attrs = prim.get("attributes", {})
        has_color = "COLOR_0" in attrs
        mat_name = gltf["materials"][prim["material"]]["name"]
        print(f"  Mesh[{mesh_idx}] {mat_name}: COLOR_0={has_color}")
