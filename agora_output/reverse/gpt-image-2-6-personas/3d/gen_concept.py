"""Generate one GPT Image 2.6 concept from the ```text block of a prompt file.

Usage: python gen_concept.py <prompt.md> <out_stem> [model] [quality]
Skips when <out_stem>.png exists. Writes <out_stem>.json with usage and cost.
"""
import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from openai import OpenAI

ENV = Path(r"C:\Users\Danculus\agora\server\.env")
PRICE = {"text_in": 5.0, "image_in": 8.0, "image_out": 30.0}


def key():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("OPENAI_API_KEY missing")


def main():
    src, stem = Path(sys.argv[1]), Path(sys.argv[2])
    model = sys.argv[3] if len(sys.argv) > 3 else "gpt-image-2.6-sunburst"
    quality = sys.argv[4] if len(sys.argv) > 4 else "medium"
    png = stem.with_suffix(".png")
    if png.exists():
        print("exists", png)
        return
    prompt = re.search(r"```text\n(.*?)```", src.read_text(encoding="utf-8"), re.S).group(1).strip()
    ref = sys.argv[5] if len(sys.argv) > 5 else None
    t = time.time()
    client = OpenAI(api_key=key())
    if ref:
        with open(ref, "rb") as fh:
            r = client.images.edit(model=model, image=[fh], prompt=prompt, size="1024x1536",
                                   quality=quality, n=1)
    else:
        r = client.images.generate(model=model, prompt=prompt, size="1024x1536",
                                   quality=quality, n=1)
    raw = base64.b64decode(r.data[0].b64_json)
    png.parent.mkdir(parents=True, exist_ok=True)
    png.write_bytes(raw)
    u = r.usage.model_dump() if r.usage else {}
    d = u.get("input_tokens_details") or {}
    usd = (d.get("text_tokens", 0) * PRICE["text_in"] + d.get("image_tokens", 0) * PRICE["image_in"]
           + u.get("output_tokens", 0) * PRICE["image_out"]) / 1e6
    stem.with_suffix(".json").write_text(json.dumps({
        "model": model, "quality": quality, "prompt_file": str(src), "usage": u, "usd": usd,
        "seconds": round(time.time() - t, 1), "sha256": hashlib.sha256(raw).hexdigest(),
    }, indent=2), encoding="utf-8")
    print(f"ok {png} {time.time() - t:.0f}s usd={usd:.4f}")


if __name__ == "__main__":
    main()
