#!/usr/bin/env python3
"""Label the 93-case human overlap with a local model via Ollama.

Mirrors the frozen Opus 4.8 protocol: same codebook, same five claim labels plus the
framework field, three independent passes, per-field majority vote. Writes results
incrementally so the run is resumable.

  python3 scripts/run_local_llm.py --model qwen3:14b --passes 3
"""
import argparse, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "local_llm")
LABELS = ["disparate_treatment", "disparate_impact", "refusal_rent_sell",
          "reasonable_accommodation", "zoning_exclusionary"]
FRAMEWORKS = ["mcdonnell", "hud", "both", "none"]

SCHEMA = {
    "type": "object",
    "properties": {**{k: {"type": "integer", "enum": [0, 1]} for k in LABELS},
                   "framework": {"type": "string", "enum": FRAMEWORKS}},
    "required": LABELS + ["framework"],
}


def codebook():
    with open(os.path.join(ROOT, "data", "validation", "CODEBOOK.md")) as f:
        return f.read()


def corpus():
    d = {}
    with open(os.path.join(ROOT, "data", "processed", "paper_corpus.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            d[str(r["cluster_id"])] = r
    return d


def gold_ids():
    with open(os.path.join(ROOT, "data", "validation", "gold_human_codings.json")) as f:
        g = json.load(f)
    return [str(x["case_id"]) for x in g["primary"]]


def truncate(text, budget):
    """Head-and-tail truncation, matching the frozen Opus protocol's intent."""
    if len(text) <= budget:
        return text
    head = int(budget * 0.6)
    tail = budget - head
    return text[:head] + "\n\n[... omitted ...]\n\n" + text[-tail:]


def call(model, prompt, seed, host, num_ctx=10240, timeout=1800):
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0.0, "seed": seed, "num_ctx": num_ctx},
    }).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(json.load(r)["response"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:14b")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--chars", type=int, default=20000,
                    help="head-and-tail truncation budget; 0 sends the full opinion")
    ap.add_argument("--num-ctx", type=int, default=10240,
                    help="model context window; must fit the largest prompt sent")
    ap.add_argument("--tag", default="",
                    help="suffix for the output filenames, so runs don't overwrite")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="idle seconds between calls; lets the GPU cool")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    stem = a.model.replace(":", "-") + a.tag
    raw_path = os.path.join(OUT, f"raw_{stem}.jsonl")

    done = set()
    if os.path.exists(raw_path):
        with open(raw_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add((str(r["cluster_id"]), r["pass"]))
                except Exception:
                    pass

    cb = codebook()
    C = corpus()
    ids = [i for i in gold_ids() if i in C]
    if a.limit:
        ids = ids[:a.limit]

    todo = [(i, p) for i in ids for p in range(1, a.passes + 1)
            if (i, p) not in done]
    print(f"model={a.model} cases={len(ids)} passes={a.passes} "
          f"already_done={len(done)} todo={len(todo)}", flush=True)

    t0 = time.time()
    ok = err = 0
    with open(raw_path, "a") as out:
        for n, (cid, p) in enumerate(todo, 1):
            rec = C[cid]
            full = rec.get("text", "")
            text = full if a.chars <= 0 else truncate(full, a.chars)
            prompt = (f"{cb}\n\n---\nOPINION (cluster {cid}):\n{text}\n---\n"
                      "Return only the structured object.")
            row = {"cluster_id": int(cid), "model": a.model, "pass": p,
                   "chars_sent": len(text), "chars_full": len(full),
                   "num_ctx": a.num_ctx}
            try:
                t1 = time.time()
                lab = call(a.model, prompt, seed=1000 + p, host=a.host,
                           num_ctx=a.num_ctx)
                row.update({"ok": True, "latency_s": round(time.time() - t1, 1),
                            **{k: int(lab.get(k, 0)) for k in LABELS},
                            "framework": lab.get("framework", "none")})
                ok += 1
            except Exception as e:
                row.update({"ok": False, "error": f"{type(e).__name__}: {e}"[:200]})
                err += 1
            out.write(json.dumps(row) + "\n")
            out.flush()
            if a.sleep:
                time.sleep(a.sleep)
            if n % 10 == 0 or n == len(todo):
                el = time.time() - t0
                print(f"  {n}/{len(todo)}  ok={ok} err={err}  "
                      f"{el/60:.1f}min  eta {(el/n)*(len(todo)-n)/60:.0f}min", flush=True)

    # majority vote per field
    rows = [json.loads(l) for l in open(raw_path)]
    by = {}
    for r in rows:
        if r.get("ok"):
            by.setdefault(str(r["cluster_id"]), []).append(r)
    vote = {}
    for cid, rs in by.items():
        v = {}
        for k in LABELS:
            v[k] = int(sum(r[k] for r in rs) * 2 > len(rs))
        fs = [r["framework"] for r in rs]
        v["framework"] = max(set(fs), key=fs.count)
        v["n"] = len(rs)
        vote[cid] = v
    vpath = os.path.join(OUT, f"majority_{stem}.json")
    with open(vpath, "w") as f:
        json.dump(vote, f, indent=1)
    print(f"\nok={ok} err={err}  cases voted={len(vote)}\nwrote {raw_path}\nwrote {vpath}")


if __name__ == "__main__":
    main()
