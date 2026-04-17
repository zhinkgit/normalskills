# video-analyzer

嵌入式软件开发调试用视频分析技能。用 ffmpeg 从视频中提取连续帧，再由 Claude 视觉逐帧分析画面内容，定位异常时间点。

## 适用场景

- 装置显示屏录像中的数据跳位、编号不连续
- 界面状态异常、逻辑错误
- 操作过程中的意外行为定位
- 任何需要"看视频找问题"的嵌入式调试场景

异常判断完全由 Claude 视觉完成，每次根据你描述的具体现象来分析，不依赖预设规则。

## 使用方式

直接告诉 Claude 视频路径和要找的现象，技能会自动触发：

> "分析这个视频 D:/videos/test.mp4，看看显示屏里的报告编号有没有跳号"

## 文件结构

```
video-analyzer/
├── SKILL.md          # 技能定义（触发条件 + Claude 工作流程）
├── config.json       # ffmpeg 路径（首次运行自动生成）
├── scripts/
│   └── extract.py   # 帧提取脚本
└── README.md
```

输出目录自动创建在视频同级：

```
<视频所在目录>/
└── video-analyzer/
    └── <视频名>/
        ├── frames/              # 提取的帧图像
        └── frames_manifest.json # 帧列表（含时间戳）
```

## extract.py 参数

```
python extract.py <视频路径> [--fps N] [--max-frames N]
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `--fps N` | 强制指定提取帧率 | 自动（最多60帧） |
| `--max-frames N` | 最多提取帧数 | 60 |

## config.json

首次运行时自动搜索 ffmpeg 并写入，也可手动编辑：

```json
{
  "ffmpeg_path": "C:/ffmpeg/bin/ffmpeg.exe"
}
```

## 依赖

- ffmpeg（需自行安装，[下载地址](https://ffmpeg.org/download.html)）
- Python 3.x（标准库，无需额外安装）
