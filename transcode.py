#!/usr/bin/env python3
"""
作品集视频转码脚本 —— 还原自对话中验证过的方案。

最终技术路线（以合并后的交接文档为准）：
  GitHub Releases 托管完整 MP4 + 原生 <video> 直链；不用 HLS / m3u8 / hls.js。

转码目标：
  H.264 (libx264) + AAC，moov 前置(faststart) 支持边下边播，
  偶数宽高(H.264 硬性要求)，按目标体积反算码率(两遍编码精确控制)，
  封面抽取避开片头黑帧。

依赖：ffmpeg / ffprobe（本机需先安装，例如 `brew install ffmpeg`）。

用法：
  # 精确控制体积（推荐，换真实正片时用）：两遍编码，把文件压到目标 MB 以内
  python3 transcode.py source/work-01.mov --target-mb 45 --out out/work-01.mp4

  # 快速模式（单次 CRF，适合占位/预览片）
  python3 transcode.py source/work-01.mov --crf 26 --out out/work-01.mp4

  # 抽封面（自动跳过片头黑帧）
  python3 transcode.py out/work-01.mp4 --poster out/poster-01.jpg

转码完成后：
  1) 在 GitHub 仓库建一个 Release（tag 例如 videos），把 mp4 作为附件上传；
  2) 把 app.js 里对应作品的 mp4 改成该 Release 直链；
  3) 第 1 部还要同步改 index.html 里 <source id="srcMp4"> 的默认地址；
  4) git add/commit/push，等 Pages 构建完成后刷新即可。
"""

import argparse
import json
import math
import os
import subprocess
import sys

AUDIO_BITRATE = 128  # kbps, AAC


def run(cmd, capture=False):
    if not capture:
        print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, capture_output=capture, text=capture)


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=width,height,codec_type",
         "-of", "json", path],
        check=True, capture_output=True, text=True,
    ).stdout
    data = json.loads(out)
    duration = float(data["format"]["duration"])
    w = h = 0
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w, h = int(s["width"]), int(s["height"])
            break
    return duration, w, h


def even_scale(w, h, max_width):
    """按最大宽度等比缩放，并把宽高强制取偶数（H.264 要求偶数宽高）。"""
    if max_width and w > max_width:
        h = round(h * max_width / w)
        w = max_width
    w -= w % 2
    h -= h % 2
    return w, h


def transcode(src, out, target_mb, crf, max_width, quick):
    duration, w, h = probe(src)
    vw, vh = even_scale(w, h, max_width)
    print(f"源: {w}x{h}, {duration:.1f}s -> 输出 {vw}x{vh}, {duration:.1f}s")

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    scale = f"scale={vw}:{vh}"

    if target_mb:
        # 按目标体积反算视频码率：总码率 = 体积 / 时长，扣掉音频
        total_kbps = target_mb * 8192 / duration  # MB -> kbit, / s
        vbit = int(total_kbps - AUDIO_BITRATE)
        vbit = max(200, min(vbit, 8000))  # 合理区间，避免畸形值
        print(f"目标 {target_mb}MB -> 视频码率 {vbit}kbps + 音频 {AUDIO_BITRATE}kbps")

        common = [
            "-c:v", "libx264", "-preset", "veryfast",
            "-b:v", f"{vbit}k", "-vf", scale,
            "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE}k",
            "-movflags", "+faststart",
        ]
        # 两遍编码：-pass 必须是字符串，不能传整数
        run(["ffmpeg", "-y", "-i", src, *common, "-pass", "1",
             "-an", "-f", "mp4", os.devnull])
        run(["ffmpeg", "-y", "-i", src, *common, "-pass", "2", out])
    else:
        # 快速模式：单次 CRF
        q = crf or 26
        print(f"快速模式 CRF={q}")
        run(["ffmpeg", "-y", "-i", src,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", str(q),
             "-vf", scale,
             "-c:a", "aac", "-b:a", f"{AUDIO_BITRATE}k",
             "-movflags", "+faststart", out])

    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"完成: {out} ({size_mb:.1f} MB)")


def extract_poster(src, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    duration, w, h = probe(src)
    # 取片长 12% 处，避开片头黑帧
    t = max(1.0, duration * 0.12)
    print(f"抽封面: t={t:.1f}s")
    run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", src,
         "-frames:v", "1", "-q:v", "2", out])
    print(f"封面: {out} ({os.path.getsize(out)/1024:.0f} KB)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src", help="输入视频路径")
    p.add_argument("--out", help="输出 mp4 路径")
    p.add_argument("--target-mb", type=float, help="目标体积(MB)，两遍编码精确控制")
    p.add_argument("--crf", type=int, help="单次快速模式 CRF(18-32)，越小越清晰")
    p.add_argument("--max-width", type=int, default=960, help="最大宽度(默认960)，等比缩放")
    p.add_argument("--poster", help="只抽封面到该路径")
    args = p.parse_args()

    if args.poster:
        extract_poster(args.src, args.poster)
        return
    if not args.out:
        print("错误：需要 --out 指定输出路径", file=sys.stderr)
        sys.exit(2)
    transcode(args.src, args.out, args.target_mb, args.crf,
              args.max_width, args.crf is not None)


if __name__ == "__main__":
    main()
