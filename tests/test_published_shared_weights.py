import hashlib
import json

import pytest
import torch
from safetensors.torch import save_file

from scripts.ascend910c import published_shared_weights as loader

PREFIX = "layers.30.ffn.shared_experts."
INDEX = "quant_model_weights.safetensors.index.json"
DESC = "quant_model_description.json"


def fixture_files(root, mutate=None):
    tensors = {}
    for i, (w, shape) in enumerate((("w1", (2, 3)), ("w2", (3, 2)), ("w3", (2, 3)))):
        tensors[PREFIX + w + ".weight"] = (torch.arange(6).reshape(shape) - 128 + 100 * i).to(torch.int8)
        tensors[PREFIX + w + ".weight_scale"] = torch.arange(1, shape[0] + 1, dtype=torch.float32).reshape(-1, 1)
        tensors[PREFIX + w + ".weight_offset"] = torch.zeros(shape[0], 1)
    if mutate:
        mutate(tensors)
    mapping = {}
    for w in ("w1", "w2", "w3"):
        subset = {n: t for n, t in tensors.items() if n.startswith(PREFIX + w + ".")}
        save_file(subset, root / (w + ".safetensors"))
        mapping.update({n: w + ".safetensors" for n in subset})
    (root / INDEX).write_text(json.dumps({"weight_map": mapping}))
    (root / DESC).write_text(json.dumps({n: "W8A8_DYNAMIC" for n in tensors}))
    return tensors


def test_exact_codes_order_hash_and_selective_read(tmp_path, monkeypatch):
    tensors = fixture_files(tmp_path)
    real_open = loader.safe_open
    read = []

    class Tracked:
        def __init__(self, *args, **kwargs):
            assert kwargs == {"framework": "pt", "device": "cpu"}
            self.context = real_open(*args, **kwargs)
        def __enter__(self):
            self.handle = self.context.__enter__()
            return self
        def __exit__(self, *args):
            return self.context.__exit__(*args)
        def keys(self):
            return self.handle.keys()
        def get_slice(self, name):
            return self.handle.get_slice(name)
        def get_tensor(self, name):
            read.append(name)
            return self.handle.get_tensor(name)
    monkeypatch.setattr(loader, "safe_open", Tracked)
    result = loader.load_published_shared(tmp_path, 30)
    assert set(read) == set(tensors) and len(read) == 9
    assert torch.equal(result["up_codes"], torch.cat([tensors[PREFIX + w + ".weight"] for w in ("w1", "w3")]))
    assert torch.equal(result["up_scale"], torch.cat([tensors[PREFIX + w + ".weight_scale"].flatten() for w in ("w1", "w3")]))
    assert torch.equal(result["down_codes"], tensors[PREFIX + "w2.weight"])
    assert torch.equal(result["down_scale"], tensors[PREFIX + "w2.weight_scale"].flatten())
    for key in ("up_codes", "down_codes"):
        assert result[key].dtype == torch.int8 and result[key].is_contiguous()
    for entry in result["manifest"]:
        tensor = tensors[entry["name"]]
        assert entry["shape"] == list(tensor.shape)
        assert entry["dtype"] == ("I8" if tensor.dtype == torch.int8 else "F32")
        assert entry["shard"] == entry["name"].split(".")[-2] + ".safetensors"
        assert entry["sha256"] == hashlib.sha256(tensor.numpy().tobytes()).hexdigest()


@pytest.mark.parametrize("case", ["missing", "label", "offset", "nan", "inf", "zero", "negative", "geometry", "dtype", "escape", "absolute", "symlink", "index_symlink", "description_symlink"])
def test_reject_contract(tmp_path, case):
    def mutate(t):
        key = PREFIX + "w1."
        if case in ("offset", "nan", "inf", "zero", "negative"):
            field = "weight_offset" if case == "offset" else "weight_scale"
            t[key + field][0, 0] = {"offset": 1, "nan": float("nan"), "inf": float("inf"), "zero": 0, "negative": -1}[case]
        if case == "geometry":
            t[key + "weight"] = torch.ones(3, 3, dtype=torch.int8)
        if case == "dtype":
            t[key + "weight"] = t[key + "weight"].float()
    fixture_files(tmp_path, mutate)
    if case in ("missing", "escape", "absolute", "symlink"):
        data = json.loads((tmp_path / INDEX).read_text())
        key = PREFIX + "w1.weight"
        if case == "missing":
            del data["weight_map"][key]
        else:
            outside = tmp_path.parent / (tmp_path.name + "-outside")
            outside.write_bytes((tmp_path / "w1.safetensors").read_bytes())
            if case == "symlink":
                (tmp_path / "link").symlink_to(outside)
            data["weight_map"][key] = {"escape": "../" + outside.name, "absolute": str(outside), "symlink": "link"}[case]
        (tmp_path / INDEX).write_text(json.dumps(data))
    if case == "label":
        data = json.loads((tmp_path / DESC).read_text())
        data[PREFIX + "w1.weight_scale"] = "W4A8"
        (tmp_path / DESC).write_text(json.dumps(data))
    if case in ("index_symlink", "description_symlink"):
        path = tmp_path / (INDEX if case == "index_symlink" else DESC)
        outside = tmp_path.parent / (tmp_path.name + "-metadata")
        outside.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(outside)
    with pytest.raises(ValueError):
        loader.load_published_shared(tmp_path, 30)


@pytest.mark.parametrize("layer", [-1, True, 1.0, "30"])
def test_layer(tmp_path, layer):
    with pytest.raises(ValueError):
        loader.load_published_shared(tmp_path, layer)


def test_budget_before_any_tensor_read(tmp_path, monkeypatch):
    fixture_files(tmp_path)
    class Huge:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def keys(self):
            return [PREFIX + "w1.weight"]
        def get_slice(self, name):
            return self
        def get_shape(self):
            return [100_000_001, 1]
        def get_dtype(self):
            return "I8"
        def get_tensor(self, name):
            pytest.fail("tensor read before budget validation")
    monkeypatch.setattr(loader, "safe_open", lambda *a, **k: Huge())
    with pytest.raises(ValueError, match="budget"):
        loader.load_published_shared(tmp_path, 30)
