# 设计说明（design.md）

> 本文档描述 ani2xcur 的架构、数据模型与关键实现约定。
> 使用者指南见 [`usage.md`](usage.md)；任务与进度见仓库根目录 `task.md`。

## 1. 总体分层

```
            ┌──────────────────────────────────────────────┐
            │                 CLI (cli.py)                  │
            │        convert / inspect / roles              │
            └───────────────┬──────────────────────────────┘
                            │
            ┌───────────────▼──────────────────────────────┐
            │            Pipeline（pipeline.py）            │
            │  inf 解析 → 角色映射 → 解码 → 缩放 → 主题写出  │
            └───────┬───────────────────────┬──────────────┘
                    │                       │
        ┌───────────▼─────────┐   ┌─────────▼─────────────┐
        │  C core (_anicore)  │   │  Python: Pillow / 缩放 │
        │  ANI / ICO / CUR    │   │  XCursor 写出（纯 Python）│
        │  容器解析           │   │                        │
        └─────────────────────┘   └───────────────────────┘
```

模块一览（`src/ani2xcur/`）：

| 模块 | 职责 |
| --- | --- |
| `cli.py` | `argparse` 子命令、参数校验、友好报错 |
| `pipeline.py` | `convert()` 编排；`find_inf()` 定位描述文件 |
| `config/inf.py` | 容错解析 Windows `.inf` 的 `[Strings]` |
| `roles.py` + `config/roles.json` | canonical 角色表、同义名与 X11 别名 |
| `formats/win.py` | `_anicore` 薄封装：容器解析 → `Cursor`、`describe()` |
| `formats/loader.py` | 统一加载容器或普通图片源 |
| `formats/xcursor.py` | XCursor 二进制读写 |
| `model.py` | `CursorImage` / `CursorFrame` / `Cursor` 数据模型 |
| `render.py` | 预乘 alpha 下多 size 缩放与热点换算 |
| `theme.py` | 主题目录、`index.theme`、别名软链接 |
| `log.py` | 分级日志（trace/info/warn/fatal） |

## 2. 职责边界

- **C 核心**只解析二进制容器，**不接触像素**：产出元数据（宽高、热点、每帧延迟）
  与每帧的原始图像负载（打包成自包含的单图 ICO/CUR blob）。
- **Python 层**用 Pillow 解码像素，负责缩放、热点换算、角色映射、XCursor 写出
  与主题目录组装。

## 3. 数据模型（`model.py`）

```
CursorImage:  nominal, width, height, hotspot(x, y), image(RGBA)
CursorFrame:  delay_ms, images: dict[nominal_size -> CursorImage]
Cursor:       name, frames: list[CursorFrame], source(Path | None)
```

- 动画与静态统一：静态 `.cur` 即“只有一帧、`delay_ms = 0`”的 `Cursor`。
- 单帧可含多个 `nominal`（多尺寸 `.cur`、ANI 内嵌多尺寸）。
- **Alpha 约定**：`formats.win.load_cursor` 产出 **straight RGBA**（同源图标）；
  `render.resize_cursor` 产出 **premultiplied RGBA**（XCursor 写出所需）。

## 4. 数据流

```
Windows 主题目录 (.inf + .ani / .cur)
   │  C 核心解析容器 + Pillow 解码像素
   ▼
Cursor（多帧、straight RGBA）
   │  render.resize_cursor：预乘 → LANCZOS 缩放 → 热点换算
   ▼
Cursor（多 nominal size、premultiplied RGBA）
   │  formats.xcursor.write + theme.CursorTheme.write
   ▼
<ThemeName>/cursors/*.xcur (+ 别名软链接) + index.theme + cursor.theme
```

## 5. C 核心（`src/csrc/`）

公共接口（`include/anicore/anicore.h`）：

```c
typedef struct {
    uint32_t nominal, width, height, hotspot_x, hotspot_y;
    const uint8_t *blob; size_t blob_size;   /* 单图 ICO/CUR，owned */
} anicore_image;

typedef struct { uint32_t delay_ms; uint32_t image_count; anicore_image *images; } anicore_frame;

typedef struct {
    uint32_t width, height, hotspot_x, hotspot_y;
    uint32_t frame_count; anicore_frame *frames;
} anicore_cursor;

anicore_status anicore_parse(const uint8_t *buf, size_t len, anicore_cursor *out);
void           anicore_free(anicore_cursor *cur);
const char    *anicore_strerror(anicore_status st);
```

- `anicore_parse` 自动识别 ANI / ICO / CUR；pybind11 层导出 `Cursor/Frame/Image`
  （blob 为 `bytes`），解析失败抛 `ValueError`。
- 所有 buffer 访问经 `internal.h` 的越界安全 reader。

### 5.1 ANI（`ani.c`）

RIFF/ACON 容器，关心四个 chunk：

| chunk | 含义 |
| --- | --- |
| `anih` | 动画头：帧/步数、逻辑尺寸 `cx/cy`、`jifRate`、flags |
| `seq ` | 每步对应的 icon 索引（可选） |
| `rate` | 每步时长（jiffies，可选） |
| `LIST fram` | icon 列表，每个 `icon` 子块是一个完整 ICO/CUR |

- 步数 = `seq` 长度（无则 `cSteps`，再退回 icon 数）。
- 每步一个 `anicore_frame`；`seq` 决定使用哪个 icon。
- 延迟：`raw = rate[i]`；为 0 或缺省时回退 `jifRate`；`delay_ms = round(raw*1000/60)`。
- 逻辑尺寸优先取 `anih.cx/cy`，为 0 时回退首帧图像尺寸。

### 5.2 ICO / CUR（`ico.c`）

- ICO(type=1)/CUR(type=2) 同构：6 字节头 + 16 字节目录项；目录宽高 `0 → 256`；
  CUR 目录项的第 4/6 字节是热点坐标。
- 每个目录项被重新打包成**自包含的单图容器**（header+1 项+负载），负载可为
  **DIB**（BITMAPINFOHEADER）或 **PNG**。
- `.cur` 多图 → 单个 `anicore_frame` 含多个 `anicore_image`。

## 6. 角色映射与广泛适配（`roles.py` + `config/roles.json`）

`roles.json` 为 `{"roles": [...]}`，每个 canonical 角色含 `keys`（inf 同义键）
与 `x11`（Linux 光标名 + 历史别名，依据现成主题 Bibata 的别名表校正）：

```json
{
  "canonical": "work",
  "description": "Working in background (Windows: AppStarting)",
  "keys": ["work", "working", "appstarting", "app_starting", "working_in_background"],
  "x11": ["left_ptr_watch", "progress", "half-busy", "00000000000000020006000e7e9ffc3f", ...]
}
```

- `resolve(key)` 大小写不敏感；未知键返回 `None`（上层降级为独立光标）。
- **键名与别名全局唯一**；且别名不得与其它角色的 canonical 同名
  （例如 Arrow 的 canonical 命名为 `arrow`，把 freedesktop 语义的 `pointer`
  让给 link 作别名，`pointer -> link`、`left_ptr -> arrow`）。

## 7. 渲染（`render.py`）

- **预乘 alpha 空间缩放**：`premultiply`（`ImageChops.multiply`）→ `LANCZOS`
  → 保持预乘，避免透明边缘颜色渗色，输出即 XCursor 所需格式。
- **热点换算**：`round(hot * target / source)` 并按目标 clamp。
- **多源择优**：对每个目标尺寸选“最小且 ≥ 目标”的源图（优先下采样）；
  无源且禁止放大则跳过该尺寸（`allow_upscale` 默认允许，保证小源也能出全集）。

## 8. XCursor 写出（`formats/xcursor.py`）

- 文件 = 16 字节头（`Xcur`, 版本 1.0, TOC 数）+ 每项 12 字节 TOC + 图像块。
- 图像块 = 36 字节头（size/type/subtype(nominal)/version/w/h/xhot/yhot/delay）
  + `w*h*4` 像素。
- 像素为**预乘 ARGB**，小端即 `B,G,R,A` 字节序（= Pillow `raw "BGRA"`）。
- 输出顺序 frame-major：同 nominal 的块按帧序排列，libXcursor 据此播放动画。
- 自带 reader 用于回读校验。

## 9. 主题组装（`theme.py`）

```
<output>/<Name>/
├── cursors/<role>            # 真实 XCursor 文件（canonical 角色名）
├── cursors/<alias> -> <role> # 每条 X11 别名的相对软链接
├── index.theme               # [Icon Theme] Name/Comment(/Inherits)
└── cursor.theme              # 旧式兼容文件
```

- 目录名经 `_safe_dirname` 清洗；重跑幂等。
- 防御：若别名会覆盖其它角色的真实文件则报错（不静默损坏）。

## 10. 兼容性与边缘情况

- **调色板 DIB 的 AND 掩码**：8bpp 等 `P` 模式光标透明度在 1bpp AND 掩码中，
  Pillow 的 CUR 插件只对 `1`/`L` 应用掩码，会得到不透明黑底；`decode_image`
  经 ICO 路径（`_as_icon` 重写容器类型与 planes/bitcount）解码修正。
- **PNG 负载**：CUR 插件不识别，`decode_image` 兜底直接从 PNG 流解码。
- **文件名**：大小写不敏感回退；递归查找 `.inf`；多个 `.inf` 取最浅者或
  `--inf` 指定；缺失文件告警跳过；重复角色保留首个；未知键降级。
- **单文件/图片输入**：`convert` 接受单个容器或图片文件。
- **逐项容错**：坏文件告警跳过并计入失败，其余照常转换；CLI 以非零码反馈。

## 11. 测试策略

- **单元**：C 容器解析（对样例文件断言字段 + 合成 ANI/CUR 构造器）；inf/roles；
  XCursor 读写 round-trip；渲染与预乘。
- **集成/回归**：以 `assets/MikuComplete.zip`、`assets/Zutomayo.zip` 为夹具，
  端到端 `convert` 并断言目录结构、尺寸集、动画帧/延迟、软链接、`index.theme`。
- **交叉校验**：与旧 `ani-helper -json`（legacy）比对元数据；手写 DIB 解码对照
  Pillow 掩码结果。
- **覆盖率与 CI**：`pytest-cov`（约 92%）；GitHub Actions 在 Python 3.10–3.14
  矩阵上构建 + lint + 测试。
