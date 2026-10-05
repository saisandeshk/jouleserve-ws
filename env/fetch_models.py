"""Download the WS stand-ins for P1's models, pinned to a revision (OPTIONS_PLAN.md S1, D13).

Run on the WS with the legacy serving venv:
    ~/legacy/jouleserve-ws/.venv/bin/python env/fetch_models.py [name ...]
Writes ~/work/logs/fetch_models.done when every requested model is complete. Serve them afterwards with
HF_HUB_OFFLINE=1 so SGLang never fetches a newer revision (AGENTS.md §6b).
"""
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

MODELS = {
    # name: (repo, revision)
    "gemma26b-awq": ("cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit", "180b2d35e35e4e48f6245367f3b41036f7cdabd6"),
    "gemma-e4b": ("google/gemma-4-E4B-it", "ee0ef6023621cff504d758262d4e04895a5af4a2"),
    "granite8b": ("ibm-granite/granite-4.2-8b", "f8de16cdcdbc6c779ca517604e050d82cc119e44"),
    "gemma26b-fp8": ("RedHatAI/gemma-4-26B-A4B-it-FP8-dynamic", "ed35d7abe5d940da41b4ff06eb482feb0be8cb44"),
}
# weights, configs, tokenizer and chat template only (the E4B repo also carries other formats)
ALLOW = ["*.json", "*.safetensors", "*.jinja", "*.model", "*.txt", "tokenizer*"]


def main(names):
    for name in names:
        repo, rev = MODELS[name]
        path = snapshot_download(repo, revision=rev, allow_patterns=ALLOW, max_workers=8)
        print(f"{name}: {repo}@{rev[:7]} -> {path}", flush=True)
    done = Path.home() / "work/logs/fetch_models.done"
    done.write_text("\n".join(names) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:] or ["gemma26b-awq", "gemma-e4b", "granite8b"])
