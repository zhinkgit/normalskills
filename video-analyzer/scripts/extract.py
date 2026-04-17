#!/usr/bin/env python3
"""
视频帧提取工具 - 为 Claude 视觉分析准备连续帧图像
"""

import sys
import json
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_ffmpeg(config):
    stored = config.get("ffmpeg_path", "")
    if stored and (Path(stored).is_file() or shutil.which(stored)):
        return stored
    if stored:
        print(f"[WARN] config.json 中的 ffmpeg 路径无效: {stored}，重新搜索...")

    found = shutil.which("ffmpeg")
    if found:
        config["ffmpeg_path"] = found
        save_config(config)
        print(f"[INFO] 找到 ffmpeg: {found}，已写入 config.json")
        return found

    print("未找到 ffmpeg，请输入完整路径（例如 C:/ffmpeg/bin/ffmpeg.exe）：")
    path = input().strip().strip("\"'")
    p = Path(path)
    if p.is_file():
        config["ffmpeg_path"] = str(p)
        save_config(config)
        return str(p)
    sys.exit("[ERROR] 无效的 ffmpeg 路径")


def get_ffprobe(ffmpeg_path):
    p = Path(ffmpeg_path)
    candidate = p.parent / ("ffprobe" + p.suffix)
    return str(candidate) if candidate.is_file() else (shutil.which("ffprobe") or "ffprobe")


def get_video_info(ffprobe, video_path):
    cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
           "-show_streams", "-show_format", str(video_path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(r.stdout)
        vs = next((s for s in data.get("streams", []) if s["codec_type"] == "video"), {})
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))
        fps_str = vs.get("r_frame_rate", "0/1")
        num, den = map(int, fps_str.split("/"))
        fps = round(num / den, 3) if den else 0
        return {
            "duration": round(duration, 3),
            "width": int(vs.get("width", 0)),
            "height": int(vs.get("height", 0)),
            "fps": fps,
            "codec": vs.get("codec_name", "unknown"),
            "size_mb": round(int(fmt.get("size", 0)) / 1024 / 1024, 2),
            "total_frames": round(duration * fps)
        }
    except Exception as e:
        print(f"[WARN] 获取视频信息失败: {e}", file=sys.stderr)
        return {}


def calc_extract_fps(duration, original_fps, max_frames):
    """
    根据视频时长和最大帧数计算合适的提取帧率。
    - 短视频（<10s）尽量高帧率，保留细节
    - 长视频自动降低，控制总帧数
    """
    if duration <= 0:
        return 1.0
    target = max_frames / duration
    # 不超过原始帧率，最低 0.5fps
    return round(max(0.5, min(target, original_fps)), 4)


def fmt_time(seconds):
    if seconds is None:
        return "unknown"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def extract_frames(ffmpeg, video_path, output_dir, fps):
    """提取帧并解析时间戳，返回帧列表。"""
    frames_dir = output_dir / "frames"
    frames_dir.mkdir(exist_ok=True)

    cmd = [
        ffmpeg, "-i", str(video_path),
        "-vf", f"fps={fps:.4f},showinfo",
        "-q:v", "2",
        str(frames_dir / "frame_%04d.jpg"),
        "-y"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # 从 showinfo 解析精确时间戳
    timestamps = []
    for line in result.stderr.split("\n"):
        if "pts_time" in line and "showinfo" in line:
            m = re.search(r"pts_time:([\d.]+)", line)
            if m:
                timestamps.append(float(m.group(1)))

    frame_files = sorted(frames_dir.glob("frame_*.jpg"))
    frames = []
    for i, f in enumerate(frame_files):
        ts = timestamps[i] if i < len(timestamps) else i / fps
        frames.append({
            "index": i + 1,
            "file": str(f),
            "timestamp": round(ts, 3),
            "timestamp_str": fmt_time(ts)
        })
    return frames


def main():
    if len(sys.argv) < 2:
        print("用法: python extract.py <视频路径> [--fps N] [--max-frames N]")
        print("  --fps N        强制指定提取帧率（覆盖自动计算）")
        print("  --max-frames N 最多提取帧数，默认 60")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        sys.exit(f"[ERROR] 文件不存在: {video_path}")

    # 解析可选参数
    fps_override = None
    max_frames = 60
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--fps" and i + 1 < len(sys.argv):
            fps_override = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--max-frames" and i + 1 < len(sys.argv):
            max_frames = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    config = load_config()
    ffmpeg = get_ffmpeg(config)
    ffprobe = get_ffprobe(ffmpeg)

    output_dir = video_path.parent / "video-analyzer" / video_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] 视频: {video_path.name}")
    video_info = get_video_info(ffprobe, video_path)
    if video_info:
        print(f"[INFO] {video_info['width']}x{video_info['height']}  "
              f"{video_info['fps']}fps  "
              f"时长={fmt_time(video_info['duration'])}  "
              f"总帧≈{video_info['total_frames']}")

    duration = video_info.get("duration", 10)
    orig_fps = video_info.get("fps", 30)
    fps = fps_override or calc_extract_fps(duration, orig_fps, max_frames)
    est = max(1, round(duration * fps))
    print(f"[INFO] 提取帧率: {fps}fps  预计: {est} 张  输出: {output_dir}")

    frames = extract_frames(ffmpeg, video_path, output_dir, fps)
    print(f"[INFO] 提取完成: {len(frames)} 张帧")

    manifest = {
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "video": {"path": str(video_path), "name": video_path.name, **video_info},
        "extract_fps": fps,
        "output_dir": str(output_dir),
        "frame_count": len(frames),
        "frames": frames
    }
    manifest_path = output_dir / "frames_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 输出供 Claude 直接使用的列表
    print(f"\nMANIFEST={manifest_path}")
    print("\n帧列表（index | 时间戳 | 文件路径）：")
    for fr in frames:
        print(f"  {fr['index']:4d} | {fr['timestamp_str']} | {fr['file']}")


if __name__ == "__main__":
    main()
