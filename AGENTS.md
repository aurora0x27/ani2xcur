# AGENTS.md

面向在本仓库工作的开发者与 AI agent 的项目导览：架构、命令、约定与常见坑。
架构细节另见 [`docs/design.md`](docs/design.md)，用户用法见 [`docs/usage.md`](docs/usage.md)。

## 1. 项目是什么

把 **Windows 光标主题**（`.inf` + `.ani` / `.cur` / `.ico`）转换成 **Linux XCursor 主题**：
多 nominal size、动态（动画）与静态光标统一、角色名映射到 freedesktop/X11 名称。

- C 核心负责**二进制容器解析**（ANI/RIFF-ACON、ICO、CUR），经 **pybind11** 暴露给 Python。
- Python 层用 Pillow 解码像素、缩放、映射角色、**纯 Python 写出 XCursor**（不依赖 `xcursorgen`）。

## 参考实现（legacy）

本项目是对两个旧仓库的重写，仅作对照参考：

- AniHelper（C，`*.ani` 拆分与元数据）：<https://github.com/aurora0x27/AniHelper>
- Ani2Xcur（Python，初版转换流程，现更名 ani2xcur-legacy）：<https://github.com/aurora0x27/ani2xcur-legacy>

## 2. 目录结构

```
ani2xur/
├── pyproject.toml            # scikit-build-core + pybind11 + pillow；dev: pytest/pytest-cov/ruff
├── CMakeLists.txt            # 编译 C 库 anicore 与 pybind11 模块 ani2xcur._anicore
├── README.md                 # 英文，面向使用者
├── AGENTS.md                 # 本文件
├── docs/{design,usage}.md     # 中文
├── scripts/gen-compile-commands.sh
├── assets/                   # 测试夹具：MikuComplete.zip、Zutomayo.zip
├── src/
│   ├── ani2xcur/             # Python 包
│   │   ├── cli.py            # argparse 子命令 convert/inspect/roles
│   │   ├── pipeline.py       # convert() 编排、find_inf()
│   │   ├── model.py          # CursorImage / CursorFrame / Cursor
│   │   ├── render.py         # 预乘 alpha 缩放、热点换算、DEFAULT_SIZES
│   │   ├── roles.py          # 角色解析（读 config/roles.json）
│   │   ├── theme.py          # CursorTheme：cursors/ + index.theme + 软链接
│   │   ├── log.py            # 分级日志
│   │   ├── config/{inf.py,roles.json}
│   │   └── formats/{win.py,xcursor.py,loader.py}
│   └── csrc/                 # C 核心
│       ├── include/anicore/anicore.h   # 公共 API
│       ├── internal.h        # 越界安全 buffer reader
│       ├── ani.c ico.c anicore.c util.c
│       └── bindings.cpp      # pybind11
└── tests/                    # pytest（单元 + 集成/回归）
```

## 3. 架构与数据流

```
CLI (cli.py)
  └─ Pipeline (pipeline.py)：inf 解析 → 角色映射 → 解码 → 缩放 → 主题写出
        ├─ C core (_anicore)：ANI / ICO / CUR 容器解析（不碰像素）
        └─ Python：Pillow 解码 + 缩放 + XCursor 写出 + 主题组装
```

数据模型（`model.py`）：

```
CursorImage: nominal, width, height, hotspot(x,y), image(RGBA)
CursorFrame: delay_ms, images: dict[nominal_size -> CursorImage]
Cursor:      name, frames[list], source(Path|None)
```

- **静态 = 单帧、`delay_ms=0`**；单帧可含多个 nominal（多尺寸 `.cur`）。
- **Alpha 约定**：`formats.win.load_cursor` → **straight RGBA**；
  `render.resize_cursor` → **premultiplied RGBA**（XCursor 写出所需）。改动时勿混淆。

C 核心 API 见 `include/anicore/anicore.h`；`anicore_parse` 自动识别格式，blob 为**自包含单图 ICO/CUR**。

## 4. 常用命令

```bash
uv sync                                   # 构建 C 扩展并安装依赖
uv run ani2xcur --help
uv run ani2xcur convert -i <dir> -o <out>
uv run ani2xcur inspect <path>... [--json]
uv run ani2xcur roles [--json]

uv run pytest                             # 单元 + 集成（约 100 项）
uv run pytest --cov=ani2xcur              # 覆盖率（约 92%）
uv run ruff check && uv run ruff format
./scripts/gen-compile-commands.sh         # 生成 build/compile_commands.json（clangd）

# 改了 C 源码后需重建：
uv sync --reinstall-package ani2xcur
```

## 5. 代码约定

- **语言**：代码、注释、提交信息、CLI 文本一律**英文**；`docs/*.md` 与 `AGENTS.md` 用**中文**。
- **风格**：`ruff`（`line-length=100`，规则 `E,F,I,UP,B,W`）；新增/修改后跑 `ruff format` + `ruff check`。
- **Python ≥ 3.10**；`dataclass`、`from __future__ import annotations`、类型注解。
- **测试**：改动行为要加/改测试；夹具在 `tests/conftest.py`（含合成 `build_cur`/`build_ani`/`png_bytes`）。
- **提交**：Conventional Commits（`feat:`/`fix:`/`test:`/`docs:`/`chore:`）。
- **CI**：`.github/workflows/ci.yml` 在 Python 3.10–3.14 矩阵上构建 + lint + 测试。

## 6. 如何扩展

- **新增/调整光标角色名**：改 `src/ani2xcur/config/roles.json`（`canonical`/`keys`/`x11`）。
  注意约束（有测试守护）：`keys` 与 `x11` 跨角色**全局唯一**；`x11` 别名不得等于**其它角色**的
  `canonical`（因此 Arrow 的 canonical 叫 `arrow`，把 freedesktop 的 `pointer` 让给 link）。
- **新增容器/负载支持**：容器结构改动放 `csrc/`（记得加进 `CMakeLists.txt`）；像素/格式解码放 `formats/`。
- **调整输出尺寸/缩放**：`render.py`（`DEFAULT_SIZES`、`resize_cursor`、`allow_upscale`）。
- **主题布局/元数据**：`theme.py`。
- **CLI 参数/子命令**：`cli.py` + `pipeline.py`。

## 7. 已知坑（改代码前务必知道）

1. **调色板 DIB 的 AND 掩码**：8bpp 等 `P` 模式光标的透明度在 1bpp AND 掩码里；
   Pillow 的 CUR 插件只对 `1`/`L` 应用掩码（会得到不透明黑底）。`formats/win.py`
   的 `decode_image`/`_as_icon` 改为经 **ICO 路径**解码来修正。别把这段删掉。
2. **PNG 负载**：Pillow 的 CUR 插件不识别 ICO/CUR 内嵌 PNG；`decode_image` 有 PNG 兜底。
3. **`.cur` 的多尺寸**：C 返回“单帧多 image”；`load_cursor` 对重复 nominal 保留较大者；
   `render` 按“最小且 ≥ 目标”择优。
4. **热点来自 C 核心**（ANI 取内嵌图标目录项），不由 Pillow 提供；缩放热点用
   `hot * target / source` 并 clamp。
5. **名称冲突**：canonical 文件名与 X11 别名不得互相覆盖；`theme.CursorTheme.write`
   会在别名覆盖真实文件时报错（不要绕过）。
6. **`.inf` 容错**：编码（UTF-8/ASCII/UTF-16 BOM）、CRLF、缺引号、`CUR_DIR`/`SCHEME_NAME`
   需忽略；文件名查找大小写不敏感。

## 8. 快速自检清单

改完后至少确认：

```bash
uv run ruff format && uv run ruff check
uv run pytest
uv run ani2xcur convert -i <theme-dir> -o /tmp/out && ls /tmp/out/<Name>/cursors | head
```

两套样例（`Moos`/`ZUTOMAYO`）应各产出 17 个角色文件 + 104 条别名软链接 + `index.theme`。
