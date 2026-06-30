#!/usr/bin/env python3
"""transcribe.py — 用 faster-whisper 把音频转成带时间戳的逐字稿。

本地离线运行，不需要任何 API key。首次运行会自动下载模型（缓存到本地）。
音频解码走 PyAV（faster-whisper 自带），无需单独安装 ffmpeg。

用法：
    python transcribe.py --audio "<音频文件>" --out "<逐字稿.md>" \
        [--model small] [--lang zh] [--title "..."] [--source-url "..."]

退出码 0 成功；非 0 失败。stderr 打印进度，stdout 打印一行 JSON 摘要。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True, help="逐字稿 markdown 输出路径")
    ap.add_argument("--model", default="small",
                    help="whisper 模型: tiny/base/small/medium/large-v3（默认 small）")
    ap.add_argument("--lang", default="zh", help="语言代码，默认 zh（中文）")
    ap.add_argument("--device", default="cpu", help="cpu / cuda")
    ap.add_argument("--compute-type", default="int8",
                    help="int8（CPU 推荐）/ float16（GPU 推荐）")
    ap.add_argument("--title", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--platform", default="")
    ap.add_argument("--author", default="")
    args = ap.parse_args()

    audio = Path(args.audio)
    if not audio.is_file():
        log(f"音频文件不存在: {audio}")
        return 1

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("faster-whisper 未安装。请先运行: python -m pip install faster-whisper")
        return 1

    log(f"加载模型 {args.model} ({args.device}/{args.compute_type})，首次会下载模型……")
    try:
        model = WhisperModel(args.model, device=args.device,
                             compute_type=args.compute_type)
    except Exception as e:  # noqa: BLE001
        log(f"模型加载失败: {e}")
        if args.device == "cuda":
            log("提示: GPU 模式失败可改用 --device cpu --compute-type int8")
        return 1

    log("开始转写（时长越长越久，CPU 上约 1-3 倍视频时长）……")
    try:
        segments, info = model.transcribe(
            str(audio),
            language=args.lang or None,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
    except Exception as e:  # noqa: BLE001
        log(f"转写失败: {e}")
        return 1

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    seg_list = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        seg_list.append((seg.start, seg.end, text))
        lines.append(f"[{fmt_ts(seg.start)}] {text}")
        if len(seg_list) % 20 == 0:
            log(f"  ...已转写 {len(seg_list)} 段（到 {fmt_ts(seg.end)}）")

    full_text = "\n".join(lines)
    detected = getattr(info, "language", args.lang)
    duration = getattr(info, "duration", 0) or 0

    header = [
        "---",
        "type: transcript",
        f'title: "{args.title}"' if args.title else "title:",
        f"source_url: {args.source_url}" if args.source_url else "source_url:",
        f"platform: {args.platform}" if args.platform else "platform:",
        f'author: "{args.author}"' if args.author else "author:",
        f"asr_model: faster-whisper/{args.model}",
        f"language: {detected}",
        f"duration_s: {int(duration)}",
        "---",
        "",
        f"# 逐字稿：{args.title or audio.stem}",
        "",
        f"> 由 faster-whisper（{args.model}）本地转写，仅供检索；口语、口误未修正。",
        "",
    ]
    out.write_text("\n".join(header) + full_text + "\n", encoding="utf-8")

    log(f"完成：{len(seg_list)} 段，约 {fmt_ts(duration)}")
    print(json.dumps({
        "transcript_file": str(out),
        "segments": len(seg_list),
        "language": detected,
        "duration_s": int(duration),
        "chars": len(full_text),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
