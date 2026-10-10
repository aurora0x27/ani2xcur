# 设计说明（design.md）

> 本文档描述 ani2xcur 的目标架构与数据流。随实现推进逐步补全。

## 1. 总体分层

```
            ┌──────────────────────────────────────────────┐
            │                 CLI (cli.py)                  │
            │        convert / inspect / roles              │
            └───────────────┬──────────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────────┐
            │          Pipeline / Theme 组装                │
            │  inf 解析 → 角色映射 → 解码 → 缩放 → 写出      │
            └───────┬───────────────────────┬──────────────┘
                    │                       │
        ┌───────────▼─────────┐   ┌─────────▼─────────────┐
        │  C core (_anicore)  │   │  Python: Pillow / 缩放 │
        │  ANI / ICO / CUR    │   │  XCursor 写出 (纯 Python)│
        │  容器解析           │   │                        │
        └─────────────────────┘   └───────────────────────┘
```

## 2. 职责边界

- **C 核心**只解析二进制容器，不接触像素：产出元数据（宽高、热点、每帧延迟）
  与每帧的原始图像负载 blob。
- **Python 层**用 Pillow 将 blob 解码为 RGBA，负责缩放、热点换算、角色映射、
  XCursor 写出与主题目录组装。

## 3. 数据流

```
Windows 主题目录 (.inf + .ani / .cur)
   │  C 核心解析 + Pillow 解码
   ▼
Cursor（多帧）→ 多 nominal size 的 RGBA 图
   │  纯 Python XCursor writer
   ▼
<ThemeName>/cursors/*.xcur (+ 别名软链接) + index.theme
```

## 4. 关键约定

- 延迟单位统一为毫秒（`jiffies * 1000 / 60`）。
- 静态 `.cur` 视为只有一帧、`delay = 0` 的 `Cursor`。
- 热点随尺寸等比缩放：`hot' = hot * target / source`。
- 角色名通过 canonical role + 同义名映射，未知键降级为独立光标。
