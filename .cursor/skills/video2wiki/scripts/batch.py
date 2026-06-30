#!/usr/bin/env python3
"""batch.py — 批量把 clippings/ 里的视频剪藏跑完"下载 + 转写"。

只做机械的、耗时的前两步（fetch + transcribe），产出逐字稿到 raw/transcripts/，
并把每条的元信息写进 manifest.json，供 LLM 后续逐篇撰写成品笔记 + ingest。

特性：
- 断点续跑：已有同 source_url 逐字稿的剪藏自动跳过。
- 容错：单条失败（非视频/下载失败/转写失败）记录状态后继续下一条。
- 省空间：每条转写成功后删除临时 mp4（逐字稿已留底）。

用法（在仓库根目录运行）：
    python .cursor/skills/video2wiki/scripts/batch.py --model small
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def find_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "AGENTS.md").is_file():
            return p
    sys.exit("ERROR: 未找到 AGENTS.md")


ROOT = find_root(Path.cwd())

# Windows 控制台默认 GBK；yt-dlp 日志也常是系统编码，subprocess 需与之对齐
_SUBPROC_ENC = "gbk" if sys.platform == "win32" else "utf-8"


def log(msg: str) -> None:
    ts = dt.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        print(line.encode(enc, errors="replace").decode(enc, errors="replace"), flush=True)


def rel_path(p: Path | str) -> str:
    """相对仓库根的路径（POSIX），避免 Windows subprocess 传中文绝对路径乱码。"""
    pp = Path(p).resolve()
    root = ROOT.resolve()
    try:
        return pp.relative_to(root).as_posix()
    except ValueError:
        ps, rs = pp.as_posix(), root.as_posix()
        if ps.lower().startswith(rs.lower() + "/"):
            return ps[len(rs) + 1 :]
        return pp.as_posix()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def fm_field(text: str, key: str) -> str | None:
    m = re.search(rf'^{key}:\s*["\']?(\S.*?)["\']?\s*$', text, re.MULTILINE)
    return m.group(1).strip() if m else None


def extract_source(text: str) -> str | None:
    s = fm_field(text, "source")
    if s and s.startswith("http"):
        return s
    m = re.search(r"https?://[^\s\"')]+", text)
    return m.group(0) if m else None


def slugify(name: str) -> str:
    name = re.sub(r"[\s！!？?～~，,。、:：·\|/\\<>\"'*]+", "", name)
    return name[:40] or "untitled"


def slug_from_clip(clip: Path, src: str, created: str) -> str:
    """工作目录 / 逐字稿 slug：优先用 URL 里的笔记 ID（纯 ASCII），避免 Windows subprocess 中文路径乱码。"""
    m = re.search(r"/explore/([0-9a-f]+)", src, re.I)
    if m:
        return f"{created}-xhs-{m.group(1)}"
    return f"{created}-{slugify(clip.stem)}"


def existing_source_urls(transcripts_dir: Path) -> set[str]:
    urls = set()
    if transcripts_dir.is_dir():
        for p in transcripts_dir.glob("*.md"):
            u = fm_field(read(p), "source_url")
            if u:
                # 去掉 query 串后比对，避免 xsec_token 变化导致重复
                urls.add(u.split("?")[0])
    return urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clippings-dir", default=str(ROOT / "clippings"))
    ap.add_argument("--transcripts-dir", default=str(ROOT / "raw" / "transcripts"))
    ap.add_argument("--work-dir", default=str(ROOT / "output" / ".video_work"))
    ap.add_argument("--manifest", default=str(ROOT / "output" / ".video_work" / "manifest.json"))
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--limit", type=int, default=0, help="最多处理几条（0=全部）")
    args = ap.parse_args()

    clip_dir = Path(args.clippings_dir)
    trans_dir = Path(args.transcripts_dir)
    work_dir = Path(args.work_dir)
    trans_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)

    manifest = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(read(manifest_path))
        except Exception:  # noqa: BLE001
            manifest = {}

    done_urls = existing_source_urls(trans_dir)
    clippings = sorted(clip_dir.glob("*.md"))
    log(f"共 {len(clippings)} 篇剪藏，已有逐字稿 {len(done_urls)} 篇")

    processed = 0
    for clip in clippings:
        text = read(clip)
        src = extract_source(text)
        if not src:
            log(f"跳过（无 source）：{clip.name}")
            continue
        src_key = src.split("?")[0]
        if src_key in done_urls:
            log(f"跳过（已转写）：{clip.name}")
            continue

        if args.limit and processed >= args.limit:
            log(f"达到 limit={args.limit}，停止")
            break

        title = fm_field(text, "title") or clip.stem
        created = fm_field(text, "created") or dt.date.today().isoformat()
        slug = slug_from_clip(clip, src, created)
        work = work_dir / slug
        transcript = trans_dir / f"{slug}.md"

        log(f"处理：{clip.name}")
        entry = {"clipping": clip.name, "title": title, "source_url": src,
                 "slug": slug, "status": "", "transcript": "", "error": ""}

        # 1. fetch
        try:
            r = subprocess.run(
                [sys.executable, rel_path(SCRIPT_DIR / "fetch.py"),
                 "--clipping", rel_path(clip), "--out", rel_path(work)],
                cwd=str(ROOT),
                capture_output=True, text=True,
                encoding=_SUBPROC_ENC, errors="replace", timeout=900,
            )
        except subprocess.TimeoutExpired:
            entry["status"] = "fetch_timeout"
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log("  下载超时，跳过")
            continue

        if r.returncode == 2:
            entry["status"] = "not_video"
            entry["error"] = (r.stderr or "").strip()[:300]
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log("  非视频（图文），跳过，留待文本 ingest")
            continue
        if r.returncode != 0:
            entry["status"] = "fetch_failed"
            entry["error"] = (r.stderr or "").strip()[:300]
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"  下载失败：{entry['error'][:120]}")
            continue

        try:
            # stdout 末行应为 JSON；stderr 可能混入 progress，取最后一条以 { 开头的行
            out_lines = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
            json_line = next((ln for ln in reversed(out_lines) if ln.startswith("{")), "")
            meta = json.loads(json_line)
        except Exception as e:  # noqa: BLE001
            entry["status"] = "fetch_badjson"
            entry["error"] = str(e)
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log("  下载输出解析失败")
            continue

        dur = meta.get("duration_s", 0)
        log(f"  已下载 {meta.get('size_bytes',0)//1024//1024}MB, 时长 {dur//60}:{dur%60:02d}，开始转写……")

        # 音频路径：优先从 work 目录取实际文件，避免 fetch JSON 里绝对路径在 Windows 上解析失败
        audio_candidates = [p for p in work.iterdir() if p.is_file() and p.stat().st_size > 10000]
        if audio_candidates:
            audio_arg = rel_path(max(audio_candidates, key=lambda p: p.stat().st_size))
        else:
            audio_arg = rel_path(meta["file"])

        # 2. transcribe
        try:
            r2 = subprocess.run(
                [sys.executable, rel_path(SCRIPT_DIR / "transcribe.py"),
                 "--audio", audio_arg, "--out", rel_path(transcript),
                 "--model", args.model, "--lang", args.lang,
                 "--title", title, "--source-url", meta.get("source_url", src),
                 "--platform", meta.get("platform", ""), "--author", meta.get("author", "")],
                cwd=str(ROOT),
                capture_output=True, text=True,
                encoding=_SUBPROC_ENC, errors="replace", timeout=14400,
            )
        except subprocess.TimeoutExpired:
            entry["status"] = "transcribe_timeout"
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log("  转写超时，跳过")
            continue

        if r2.returncode != 0:
            entry["status"] = "transcribe_failed"
            entry["error"] = (r2.stderr or "").strip()[-300:]
            manifest[slug] = entry
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"  转写失败：{entry['error'][:120]}")
            continue

        entry["status"] = "transcribed"
        entry["transcript"] = str(transcript)
        entry["platform"] = meta.get("platform", "")
        entry["duration_s"] = dur
        manifest[slug] = entry
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        done_urls.add(src_key)
        processed += 1

        # 3. 清理临时 mp4
        try:
            for f in work.glob("*"):
                f.unlink()
            work.rmdir()
        except Exception:  # noqa: BLE001
            pass
        log(f"  ✓ 完成 → {transcript.name}")

    # 汇总
    by_status = {}
    for e in manifest.values():
        by_status[e["status"]] = by_status.get(e["status"], 0) + 1
    log("批处理结束。状态汇总：" + json.dumps(by_status, ensure_ascii=False))
    log(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
