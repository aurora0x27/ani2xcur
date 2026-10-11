# 使用指南（usage.md）

> 面向使用者的命令详解与常见问题。架构与实现见 [`design.md`](design.md)。

## 1. 安装

```bash
# 用 uv 安装为独立命令
uv tool install .

# 或用 pipx
pipx install .

# 或在源码目录内直接运行
uv sync
uv run ani2xcur --help
```

需要 Python ≥ 3.10；构建 C 扩展需要 C/C++ 编译器与 CMake（仅安装时用到）。

## 2. 快速开始

```bash
# 1) 转换一个包含 .inf 与 .ani / .cur 的 Windows 主题目录
ani2xcur convert --input ./windows-theme --output ./out

# 2) 安装到用户图标目录
mkdir -p ~/.icons
cp -r ./out/<ThemeName> ~/.icons/

# 3) 激活
#   GNOME:
gsettings set org.gnome.desktop.interface cursor-theme '<ThemeName>'
#   KDE / 通用: 系统设置 → 外观 → 光标，选择该主题
```

`<ThemeName>` 默认取 `.inf` 的 `SCHEME_NAME`（两测试用例为 `Moos`、`ZUTOMAYO`）。

## 3. `convert`

```
ani2xcur convert --input DIR --output DIR
                 [--sizes 16,24,32,48,64,96,128]
                 [--name NAME] [--inf PATH]
                 [--no-upscale] [--dry-run]
                 [--log-level {trace,info,warn,fatal}]
```

| 选项 | 说明 |
| --- | --- |
| `-i, --input` | 输入：主题目录，或单个 `.ani`/`.cur`/`.ico`/图片文件 |
| `-o, --output` | 输出目录；主题写到 `<output>/<ThemeName>/` |
| `--sizes` | 逗号分隔的目标 nominal 尺寸（默认 `16,24,32,48,64,96,128`） |
| `--name` | 覆盖主题名（默认取 `SCHEME_NAME`，单文件则取文件名） |
| `--inf` | 目录含多个 `.inf` 时显式指定一个 |
| `--no-upscale` | 禁止把小于目标尺寸的源放大（这些尺寸将被跳过） |
| `-n, --dry-run` | 只显示将要做什么，不写文件 |
| `--log-level` | 日志级别，默认 `info` |

示例：

```bash
# 只要 24/32/48 三种尺寸
ani2xcur convert -i ./theme -o ./out --sizes 24,32,48

# 先预览
ani2xcur convert -i ./theme -o ./out --dry-run --log-level trace

# 单个动态光标
ani2xcur convert -i "./Normal Select.ani" -o ./out --sizes 32,48
```

输出结构：

```
<output>/<ThemeName>/
├── cursors/
│   ├── arrow                 # 每个 canonical 角色的真实 XCursor 文件
│   ├── left_ptr -> arrow     # 每条 X11 别名一个相对软链接
│   ├── default -> arrow
│   ├── pointer -> link
│   └── ...
├── index.theme               # [Icon Theme] Name/Comment(/Inherits)
└── cursor.theme
```

## 4. `inspect`

打印容器元数据（不解码像素），可为单个文件或整个目录：

```bash
ani2xcur inspect ./theme
ani2xcur inspect "./Work.ani" ./Person.cur
ani2xcur inspect ./out/Moos/cursors/left_ptr --json
```

文本输出示例：

```
./Work.ani
  kind:    ani
  size:    160x160
  hotspot: (8, 9)
  frames:  23
  sizes:   [160]
  delays:  [117] ms
```

## 5. `roles`

列出 canonical 角色、其 inf 同义键与 X11 别名（`--json` 便于脚本处理）：

```bash
ani2xcur roles
ani2xcur roles --json
```

## 6. 常见问题（FAQ）

**Q：为什么转换后的光标尺寸和原图不同？**
Windows 光标通常只有一种光栅尺寸。`convert` 会把每帧缩放到 `--sizes` 指定的
nominal 尺寸（默认 16–128），热点按比例换算。若某尺寸大于所有源图且使用了
`--no-upscale`，该尺寸会被跳过。

**Q：某主题里有些角色缺失，会报错吗？**
不会。`.inf` 中指向的文件不存在时告警并跳过；重复角色保留首个；无法识别的
键会降级为一个以键名命名的独立光标（不含标准别名）。

**Q：目录里有多个 `.inf`？**
默认取路径最浅的一个；同级多个会报错，请用 `--inf <path>` 指定。

**Q：动态光标没动 / 帧数不对？**
用 `ani2xcur inspect <file>` 查看 `frames` 与 `delays`。延迟来自 ANI 的 `rate`
（缺省回退 `jifRate`）。部分桌面（如某些 Wayland 合成器）对动画光标支持有限，
这与文件本身无关。

**Q：想要某些标准光标名（如 `crosshair`）？**
用 `ani2xcur roles` 查看全部 canonical 角色与 X11 别名；转换会为每个出现的角色
建立对应的软链接。若你的桌面需要某个 Windows 方案里没有的角色，它不会被生成。

**Q：能否不改动系统就试用？**
`convert` 只写入 `--output`，不会安装到 `~/.icons` 或修改桌面设置；是否安装、
是否激活由你决定（见“快速开始”）。

**Q：退出码含义？**
`0` 成功；`1` 运行错误或存在转换失败的条目（其余条目仍会写入）；`2` 命令行参数
错误（argparse）。设置环境变量 `ANI2XCUR_DEBUG=1` 可在出错时打印完整 traceback。
