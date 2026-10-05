"""Derive the WS stand-in for P1's gemma-4-26B-A4B (OPTIONS_PLAN.md S1, D13) from RedHatAI's FP8-dynamic checkpoint.

SGLang 0.5.20 on the A5000s (Ampere, no native FP8) runs FP8 linear layers through Marlin, which needs a split
input width divisible by 64. With TP=2 (the model does not fit one 24 GB GPU) the dense MLP's down_proj has
2,112 / 2 = 1,056 inputs per GPU, which Marlin rejects. So this script writes a text-only checkpoint where:
- the 30 dense-MLP down_proj weights are dequantized to bf16 (FP8 value x per-row scale); their scales dropped;
- every other tensor is copied unchanged (attention and MoE experts stay FP8-dynamic);
- vision and audio towers are left out (the model is served as Gemma4ForCausalLM, text only);
and a config.json made of the text_config, with SGLang's Gemma-4 head-size renaming (base = full attention,
swa_* = sliding window), and the quantization ignore list renamed to SGLang's module names (model.layers.*),
plus the 30 down_proj layers. Run on the WS:
    ~/legacy/jouleserve-ws/.venv/bin/python env/derive_gemma26b_fp8.py
"""
import glob
import json
import os
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import save_file

SRC = Path(glob.glob(os.path.expanduser(
    "~/.cache/huggingface/hub/models--RedHatAI--gemma-4-26B-A4B-it-FP8-dynamic/snapshots/ed35d7a*"))[0])
DST = Path(os.path.expanduser("~/work/models/gemma26b-fp8-text"))
SKIP = ("vision_tower", "embed_vision", "audio_tower", "embed_audio")


def main():
    DST.mkdir(parents=True, exist_ok=True)
    out, n_deq, n_skip = {}, 0, 0
    with safe_open(str(SRC / "model.safetensors"), framework="pt") as f:
        keys = list(f.keys())
        for k in keys:
            if any(s in k for s in SKIP):
                n_skip += 1
                continue
            if ".mlp.down_proj.weight_scale" in k:
                continue
            t = f.get_tensor(k)
            if ".mlp.down_proj.weight" in k and t.dtype == torch.float8_e4m3fn:
                s = f.get_tensor(k.replace(".weight", ".weight_scale")).to(torch.float32)
                t = (t.to(torch.float32) * s).to(torch.bfloat16)
                n_deq += 1
            out[k] = t
    for p in DST.iterdir():                       # replace the old symlinked layout
        if p.is_symlink() or p.name.startswith("model"):
            p.unlink()
    save_file(out, str(DST / "model.safetensors"), metadata={"format": "pt"})
    for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja", "generation_config.json"):
        if (SRC / name).exists():
            os.symlink(os.path.realpath(SRC / name), DST / name)

    c = json.load(open(SRC / "config.json"))
    t = dict(c["text_config"])
    t["architectures"] = ["Gemma4ForCausalLM"]
    for k in ("torch_dtype", "dtype", "tie_word_embeddings", "transformers_version"):
        if k in c and k not in t:
            t[k] = c[k]
    t["swa_head_dim"] = t["head_dim"]
    t["swa_v_head_dim"] = t["head_dim"]
    t["swa_num_key_value_heads"] = t["num_key_value_heads"]
    t["head_dim"] = t["global_head_dim"]
    t["num_key_value_heads"] = t["num_global_key_value_heads"]
    t["v_head_dim"] = t["head_dim"]
    q = dict(c["quantization_config"])
    ign = [x.replace("model.language_model.", "model.") for x in q.get("ignore", []) if not any(s in x for s in SKIP)]
    ign += [f"model.layers.{i}.mlp.down_proj" for i in range(t["num_hidden_layers"])]
    q["ignore"] = sorted(set(ign))
    t["quantization_config"] = q
    t["_derived_from"] = ("RedHatAI/gemma-4-26B-A4B-it-FP8-dynamic@ed35d7a via env/derive_gemma26b_fp8.py: text only; "
                          "dense-MLP down_proj dequantized to bf16; head dims and ignore names as SGLang expects")
    json.dump(t, open(DST / "config.json", "w"), indent=1)
    print(f"tensors written {len(out)}, dequantized down_proj {n_deq}, skipped vision/audio {n_skip}, "
          f"ignore entries {len(q['ignore'])}")


if __name__ == "__main__":
    main()
