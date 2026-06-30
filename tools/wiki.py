#!/usr/bin/env python3
"""wiki — 个人 LLM Wiki 的极简 CLI。

只保留 4 个命令：stats / log / search / lint。
更细的操作（建页、找断链、找孤立页…）一律由 LLM 直接读写文件完成。

用法：python tools/wiki.py <stats|log|search|lint> [args]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ----------------------------------------------------------------------------
# 仓库定位（向上找含 AGENTS.md 的目录）
# ----------------------------------------------------------------------------

def find_root(start: Path) -> Path:
    for p in [start.resolve(), *start.resolve().parents]:
        if (p / "AGENTS.md").is_file():
            return p
    sys.exit("ERROR: 未找到 AGENTS.md，请在知识库目录内运行。")

ROOT = find_root(Path.cwd())
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
CLIPPINGS = ROOT / "clippings"
LINT_DIR = ROOT / "lint"

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|[^\]]+)?\]\]")


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def parse_fm(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


def iter_wiki_pages():
    if WIKI.is_dir():
        yield from WIKI.rglob("*.md")


def resolve_link(target: str) -> Path | None:
    target = target.strip().removesuffix(".md").replace("\\", "/").strip("/")
    if not target:
        return None
    leaf = target.rsplit("/", 1)[-1]
    best = None
    for p in iter_wiki_pages():
        rel = p.relative_to(WIKI).as_posix()[:-3]
        if rel == target:
            return p
        if p.stem == leaf:
            best = best or p
    return best


# ----------------------------------------------------------------------------
# 命令
# ----------------------------------------------------------------------------

def cmd_stats(_args):
    pages = list(iter_wiki_pages())
    by_type = Counter()
    by_status = Counter()
    for p in pages:
        fm = parse_fm(read_text(p))
        by_type[fm.get("type", "?")] += 1
        by_status[fm.get("status", "?")] += 1
    raw_n = sum(1 for _ in RAW.rglob("*.md")) if RAW.exists() else 0
    clip_n = sum(1 for _ in CLIPPINGS.rglob("*.md")) if CLIPPINGS.exists() else 0
    print(f"仓库根: {ROOT}")
    print(f"wiki 页面: {len(pages)}   raw: {raw_n}   clippings: {clip_n}")
    print("type:   " + "  ".join(f"{k}={v}" for k, v in sorted(by_type.items())))
    print("status: " + "  ".join(f"{k}={v}" for k, v in sorted(by_status.items())))


def cmd_log(args):
    log = WIKI / "log.md"
    if not log.is_file():
        print("(wiki/log.md 不存在)")
        return
    entries = re.findall(r"^## \[.*", read_text(log), re.MULTILINE)
    for line in entries[: args.n]:
        print(line)
    if not entries:
        print("(log 为空)")


def cmd_search(args):
    pat = re.compile(args.pattern, re.IGNORECASE)
    bases = {"wiki": WIKI, "raw": RAW, "clippings": CLIPPINGS, "all": ROOT}
    base = bases[args.scope]
    total = 0
    for p in base.rglob("*.md"):
        if any(s.startswith(".") for s in p.parts):
            continue
        text = read_text(p)
        hits = [(i + 1, l) for i, l in enumerate(text.splitlines()) if pat.search(l)]
        if hits:
            print(f"\n=== {p.relative_to(ROOT).as_posix()}  ({len(hits)} hit) ===")
            for ln, l in hits[:5]:
                print(f"  {ln:>5}: {l.strip()[:200]}")
            total += len(hits)
    print(f"\n共 {total} 处命中。" if total else "(无匹配)")


def cmd_lint(_args):
    LINT_DIR.mkdir(parents=True, exist_ok=True)
    out = LINT_DIR / f"{dt.date.today().isoformat()}.md"

    pages = list(iter_wiki_pages())
    incoming: dict[Path, set[Path]] = defaultdict(set)
    broken: list[tuple[Path, str]] = []
    stubs: list[Path] = []
    for p in pages:
        text = read_text(p)
        if parse_fm(text).get("status") == "stub":
            stubs.append(p)
        for t in WIKILINK_RE.findall(text):
            r = resolve_link(t)
            if r:
                incoming[r].add(p)
            else:
                broken.append((p, t))

    skip = {WIKI / "index.md", WIKI / "log.md"}
    orphans = [p for p in pages if p not in skip and not incoming.get(p)]

    index_text = read_text(WIKI / "index.md") if (WIKI / "index.md").exists() else ""
    not_indexed = [
        p for p in pages
        if p not in skip
        and p.stem not in index_text
        and p.relative_to(WIKI).as_posix()[:-3] not in index_text
    ]

    def section(title, items, fmt):
        out_lines = [f"## {title} — {len(items)}", ""]
        out_lines += [fmt(x) for x in items] if items else ["- 无"]
        out_lines.append("")
        return out_lines

    lines = [f"# Lint Report — {dt.date.today().isoformat()}", "",
             f"扫描了 **{len(pages)}** 个 wiki 页面。", ""]
    lines += section("孤立页（无 inbound link）", orphans,
                     lambda p: f"- [[{p.relative_to(WIKI).as_posix()[:-3]}]]")
    lines += section("断链", broken,
                     lambda x: f"- `{x[0].relative_to(WIKI).as_posix()}` → `[[{x[1]}]]`")
    lines += section("Stub 页", stubs,
                     lambda p: f"- [[{p.relative_to(WIKI).as_posix()[:-3]}]]")
    lines += section("未在 index.md 出现", not_indexed,
                     lambda p: f"- [[{p.relative_to(WIKI).as_posix()[:-3]}]]")
    lines += ["---", "", "_本报告由 `wiki lint` 自动生成；修不修、怎么修，由人决定。_"]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"已生成 {out.relative_to(ROOT).as_posix()}")
    print(f"  孤立 {len(orphans)} · 断链 {len(broken)} · stub {len(stubs)} · 未入 index {len(not_indexed)}")


# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(prog="wiki", description="个人 LLM Wiki CLI（极简版）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("stats", help="仓库概览").set_defaults(func=cmd_stats)

    s = sub.add_parser("log", help="log.md 最近 N 条")
    s.add_argument("-n", type=int, default=10); s.set_defaults(func=cmd_log)

    s = sub.add_parser("search", help="全文搜索（正则）")
    s.add_argument("pattern")
    s.add_argument("--scope", choices=["wiki", "raw", "clippings", "all"], default="wiki")
    s.set_defaults(func=cmd_search)

    sub.add_parser("lint", help="生成体检报告到 lint/").set_defaults(func=cmd_lint)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
