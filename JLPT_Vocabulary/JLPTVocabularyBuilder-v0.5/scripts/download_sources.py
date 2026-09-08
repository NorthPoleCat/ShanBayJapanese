#!/usr/bin/env python3
from pathlib import Path
from urllib.request import Request, urlopen
import argparse, shutil

ROOT = Path(__file__).resolve().parents[1]
OPENJLPT_BASE = "https://raw.githubusercontent.com/evanclan/OpenJLPT/main/data/json/vocab"
JMDICT_URL = "https://www.edrdg.org/pub/Nihongo/JMdict_e.gz"

def download(url: str, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}")
    req = Request(url, headers={"User-Agent": "JLPTVocabularyBuilder/0.1"})
    with urlopen(req, timeout=120) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f)
    print(f" -> {dst} ({dst.stat().st_size:,} bytes)")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--skip-openjlpt", action="store_true")
    p.add_argument("--skip-jmdict", action="store_true")
    args = p.parse_args()

    if not args.skip_openjlpt:
        for n in range(1, 6):
            download(f"{OPENJLPT_BASE}/n{n}.json", ROOT / f"data/raw/openjlpt/n{n}.json")

    if not args.skip_jmdict:
        download(JMDICT_URL, ROOT / "data/raw/jmdict/JMdict_e.gz")

if __name__ == "__main__":
    main()
