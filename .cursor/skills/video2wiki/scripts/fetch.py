#!/usr/bin/env python3
"""fetch.py — 把视频链接（或一个已有 clipping 文件）下载成本地音频。

借鉴 lark-video2note 的 download.sh 的平台识别与 cookies 策略，
改写为跨平台 Python，并改为**只下音频**（faster-whisper 用 PyAV 解码，无需 ffmpeg）。

用法：
    python fetch.py --url "<视频URL>" --out "<输出目录>"
    python fetch.py --clipping "<clippings/xxx.md>" --out "<输出目录>"

成功时向 stdout 打印一行 JSON：
    {"file":"...","title":"...","platform":"xhs","author":"...",
     "duration_s":611,"source_url":"...","size_bytes":...}

退出码：
    0 成功
    1 真失败（网络 / cookies / 格式）
    2 这不是视频（图文笔记等），调用方应改走文本处理
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def extract_source_from_clipping(path: Path) -> str | None:
    """从 Obsidian 剪藏文件的 frontmatter 里抠出 source 链接。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^source:\s*["\']?(\S+?)["\']?\s*$', text, re.MULTILINE)
    if m:
        return m.group(1)
    # 兜底：正文里第一条 http 链接
    m = re.search(r"https?://[^\s\"')]+", text)
    return m.group(0) if m else None


def detect_platform(url: str) -> str:
    u = url.lower()
    if "douyin.com" in u or "iesdouyin" in u:
        return "douyin"
    if "bilibili.com" in u or "b23.tv" in u:
        return "bilibili"
    if "xiaohongshu.com" in u or "xhslink" in u:
        return "xhs"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "generic"


NOT_A_VIDEO_HINTS = (
    "no video",
    "unsupported url",
    "no video formats",
    "no media found",
    "not a video",
    "requested format is not available",
    "there's no video",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="视频 URL 或分享文本")
    src.add_argument("--clipping", help="已有 clipping 文件路径，从中提取 source")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--cookies-browser", default="",
                    help="可选：需要登录态时从哪个浏览器读 cookies（chrome/edge/firefox）。"
                         "注意 Windows 上 Chrome/Edge 运行中会锁库，建议改用 --cookies-file")
    ap.add_argument("--cookies-file", default="",
                    help="可选：Netscape 格式 cookies.txt 路径（浏览器扩展导出，最稳）")
    args = ap.parse_args()

    # 1. 解析 URL
    if args.clipping:
        cpath = Path(args.clipping)
        if not cpath.is_file():
            log(f"clipping 文件不存在: {cpath}")
            return 1
        raw = extract_source_from_clipping(cpath)
        if not raw:
            log(f"在 {cpath.name} 的 frontmatter 里没找到 source 链接")
            return 1
    else:
        raw = args.url

    m = re.search(r"https?://[^\s\"')]+", raw)
    url = m.group(0) if m else raw.strip()
    if not url.startswith("http"):
        log(f"没有从输入里找到 URL: {raw!r}")
        return 1

    platform = detect_platform(url)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        from yt_dlp import YoutubeDL
        from yt_dlp.utils import DownloadError
    except ImportError:
        log("yt-dlp 未安装。请先运行: python -m pip install yt-dlp")
        return 1

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
    }
    # 默认不带 cookies——多数带 xsec_token 的小红书链接公开可下。
    # 仅当用户显式提供时才用 cookies（失败兜底）。
    if args.cookies_file:
        ydl_opts["cookiefile"] = args.cookies_file
    elif args.cookies_browser:
        ydl_opts["cookiesfrombrowser"] = (args.cookies_browser,)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        msg = str(e).lower()
        if any(h in msg for h in NOT_A_VIDEO_HINTS):
            log("NOT_A_VIDEO: 这条链接看起来不是视频（可能是图文笔记 / 纯文章）。"
                "建议改走文本处理流程，而不是 video2wiki。")
            log(f"原始报错: {e}")
            return 2
        log(f"下载失败: {e}")
        if platform in ("xhs", "douyin"):
            log("提示: 若是因为需要登录态，请用浏览器扩展导出 cookies.txt，"
                "再加 --cookies-file <路径> 重试（比 --cookies-browser 稳，"
                "因为 Windows 上 Chrome 运行时会锁 cookie 库）。")
        return 1
    except Exception as e:  # noqa: BLE001
        log(f"下载异常: {e}")
        return 1

    # 找到真正下载下来的文件
    file_path = None
    reqs = info.get("requested_downloads") or []
    if reqs:
        file_path = reqs[0].get("filepath")
    if not file_path:
        # 兜底：用 id 在输出目录里找
        vid = info.get("id", "")
        for p in out_dir.glob(f"{vid}.*"):
            file_path = str(p)
            break
    if not file_path or not Path(file_path).is_file():
        log("下载完成但找不到输出文件")
        return 1

    fp = Path(file_path)
    size = fp.stat().st_size
    if size < 10000:
        log(f"下载文件过小 ({size} bytes)，很可能失败")
        return 1

    result = {
        "file": fp.as_posix(),
        "title": (info.get("title") or "untitled").strip(),
        "platform": platform,
        "author": (info.get("uploader") or info.get("channel") or "unknown").strip(),
        "duration_s": int(info.get("duration") or 0),
        "source_url": url,
        "size_bytes": size,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
