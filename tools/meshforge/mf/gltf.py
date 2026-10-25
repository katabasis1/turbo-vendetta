"""Запись и чтение .glb (glTF 2.0, бинарный). Без внешних библиотек; вывод детерминирован (одни входы → одни байты).

Что пишется: сцена из узлов-мешей (имя узла = имя меша), у меша — примитив на материал;
атрибуты POSITION (с min/max), NORMAL, TEXCOORD_0; индексы uint16/uint32; материалы без PBR-металла
(metallic 0, roughness 1). Текстура — внешний файл атласа по относительному URI (в .glb не встраивается:
иначе импорт Godot извлёк бы копию PNG рядом с моделью). В игре материалы заменяются нашими ShaderMaterial
(cel_lit / cel_emissive) в сцене модели, материалы .glb нужны для превью в редакторе.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

GLB_MAGIC, GLB_VERSION = 0x46546C67, 2
CHUNK_JSON, CHUNK_BIN = 0x4E4F534A, 0x004E4942
FLOAT, USHORT, UINT = 5126, 5123, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963
LINEAR, LINEAR_MIPMAP_LINEAR, CLAMP = 9729, 9987, 33071

MATERIALS = {
    # имя материала в .glb → как выглядит в превью редактора
    "atlas": {"name": "mf_atlas", "emissive": False},
    "emissive": {"name": "mf_emissive", "emissive": True},
}


def _pad4(b: bytes, fill: bytes = b"\x00") -> bytes:
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path: Path, nodes: list[tuple[str, dict]], image_uri: str, generator: str) -> bytes:
    """nodes: [(имя, surfaces)] — surfaces из Mesh.surfaces(). Возвращает байты файла."""
    js: dict = {
        "asset": {"version": "2.0", "generator": generator},
        "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": [], "meshes": [], "accessors": [], "bufferViews": [], "buffers": [],
        "materials": [], "textures": [{"sampler": 0, "source": 0}],
        "images": [{"uri": image_uri}],
        "samplers": [{"magFilter": LINEAR, "minFilter": LINEAR_MIPMAP_LINEAR, "wrapS": CLAMP, "wrapT": CLAMP}],
    }
    used = sorted({m for _n, s in nodes for m in s})
    mat_index = {}
    for m in used:
        d = MATERIALS[m]
        mj = {"name": d["name"], "pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                                           "metallicFactor": 0.0, "roughnessFactor": 1.0}}
        if d["emissive"]:
            mj["emissiveTexture"] = {"index": 0}
            mj["emissiveFactor"] = [1.0, 1.0, 1.0]
        mat_index[m] = len(js["materials"])
        js["materials"].append(mj)
    blob = bytearray()

    def view(data: bytes, target: int) -> int:
        nonlocal blob
        while len(blob) % 4:
            blob += b"\x00"
        js["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob += data
        return len(js["bufferViews"]) - 1

    def accessor(arr: np.ndarray, ctype: int, typ: str, target: int, minmax: bool = False) -> int:
        bv = view(arr.tobytes(), target)
        a = {"bufferView": bv, "componentType": ctype, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            a["min"] = [float(x) for x in arr.min(axis=0)]
            a["max"] = [float(x) for x in arr.max(axis=0)]
        js["accessors"].append(a)
        return len(js["accessors"]) - 1

    for name, surfaces in nodes:
        prims = []
        for m in sorted(surfaces):
            s = surfaces[m]
            pos = np.ascontiguousarray(s["positions"], dtype="<f4")
            nrm = np.ascontiguousarray(s["normals"], dtype="<f4")
            uv = np.ascontiguousarray(s["uvs"], dtype="<f4")
            idx = s["indices"]
            ia = (np.ascontiguousarray(idx, dtype="<u2"), USHORT) if len(pos) < 65535 else (np.ascontiguousarray(idx, dtype="<u4"), UINT)
            attrs = {"POSITION": accessor(pos, FLOAT, "VEC3", ARRAY_BUFFER, True),
                     "NORMAL": accessor(nrm, FLOAT, "VEC3", ARRAY_BUFFER),
                     "TEXCOORD_0": accessor(uv, FLOAT, "VEC2", ARRAY_BUFFER)}
            ind = accessor(ia[0].reshape(-1, 1), ia[1], "SCALAR", ELEMENT_ARRAY_BUFFER)
            prims.append({"attributes": attrs, "indices": ind, "material": mat_index[m], "mode": 4})
        js["meshes"].append({"name": name, "primitives": prims})
        js["nodes"].append({"name": name, "mesh": len(js["meshes"]) - 1})
    blob_b = _pad4(bytes(blob))
    js["buffers"].append({"byteLength": len(blob_b)})
    jb = _pad4(json.dumps(js, ensure_ascii=False, separators=(",", ":"), sort_keys=False).encode("utf-8"), b" ")
    total = 12 + 8 + len(jb) + 8 + len(blob_b)
    out = struct.pack("<III", GLB_MAGIC, GLB_VERSION, total) + struct.pack("<II", len(jb), CHUNK_JSON) + jb \
        + struct.pack("<II", len(blob_b), CHUNK_BIN) + blob_b
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    return out


_NP = {FLOAT: "<f4", USHORT: "<u2", UINT: "<u4", 5121: "<u1"}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path: Path) -> tuple[dict, dict]:
    """Разбор и проверка .glb по спецификации (то, что важно импорту Godot). → (json, {узел: [примитивы]}).
    Примитив: dict(material, positions, normals, uvs, indices). Ошибка формата — AssertionError с текстом."""
    b = Path(path).read_bytes()
    magic, ver, total = struct.unpack_from("<III", b, 0)
    assert magic == GLB_MAGIC and ver == 2, "не GLB 2.0"
    assert total == len(b), f"длина в заголовке {total} ≠ размер файла {len(b)}"
    jl, jt = struct.unpack_from("<II", b, 12)
    assert jt == CHUNK_JSON and jl % 4 == 0, "первый блок не JSON или не выровнен"
    js = json.loads(b[20:20 + jl].decode("utf-8"))
    bl, bt = struct.unpack_from("<II", b, 20 + jl)
    assert bt == CHUNK_BIN and bl % 4 == 0, "второй блок не BIN или не выровнен"
    binb = b[28 + jl:28 + jl + bl]
    assert js["asset"]["version"] == "2.0"
    assert js["buffers"][0]["byteLength"] <= len(binb)

    def acc(i):
        a = js["accessors"][i]
        v = js["bufferViews"][a["bufferView"]]
        assert v["byteOffset"] % 4 == 0, "bufferView не выровнен по 4"
        n = _NC[a["type"]]
        arr = np.frombuffer(binb, dtype=_NP[a["componentType"]], count=a["count"] * n, offset=v["byteOffset"])
        assert v["byteLength"] >= arr.nbytes
        return arr.reshape(a["count"], n) if n > 1 else arr, a

    out = {}
    for node in js["nodes"]:
        prims = []
        for p in js["meshes"][node["mesh"]]["primitives"]:
            pos, apos = acc(p["attributes"]["POSITION"])
            assert "min" in apos and "max" in apos, "POSITION без min/max (обязательно по спецификации)"
            assert np.allclose(pos.min(axis=0), apos["min"], atol=1e-6) and np.allclose(pos.max(axis=0), apos["max"], atol=1e-6)
            nrm, _ = acc(p["attributes"]["NORMAL"])
            ln = np.linalg.norm(nrm, axis=1)
            assert np.all(np.abs(ln - 1) < 1e-3), "нормали не единичные"
            uv, _ = acc(p["attributes"]["TEXCOORD_0"])
            assert np.all((uv >= 0) & (uv <= 1)), "UV вне [0;1]"
            idx, _ = acc(p["indices"])
            assert len(idx) % 3 == 0 and idx.max() < len(pos), "индексы вне массива вершин"
            prims.append({"material": js["materials"][p["material"]]["name"], "positions": pos, "normals": nrm,
                          "uvs": uv, "indices": idx.astype(np.int64)})
        out[node["name"]] = prims
    return js, out
