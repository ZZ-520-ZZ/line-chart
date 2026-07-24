# 绘图工具（Line Chart）

[![CI](https://github.com/ZZ-520-ZZ/line-chart/actions/workflows/ci.yml/badge.svg)](https://github.com/ZZ-520-ZZ/line-chart/actions/workflows/ci.yml)

面向物理实验数据处理的跨平台曲线绘图应用。主界面使用 Flet，可运行于 Windows、Android 和 Linux；旧版 Tkinter 界面作为 Windows 兼容入口保留。绘图、拟合、数据导入和工程文件逻辑由独立 Python 模块共享。

## 功能

- 多条 Y 曲线共享一组 X 数据，原始测量值不会被自动偏移或修改
- X/Y 不确定度与误差棒，支持统一数值或逐点列表
- 线性、二次和指数拟合
- 显示拟合方程、参数、R² 和相关系数
- 导入 CSV、XLSX、XLSM 实验数据
- 使用 `.pplot` 保存和恢复完整绘图工程
- 导出 PNG、JPG、SVG、PDF 图像
- 自定义标题、图表说明、坐标轴、单位、范围、精度、网格和图例
- 多组高辨识度曲线颜色和数据点样式
- 响应式手机/桌面布局以及可切换深色模式
- 拒绝 NaN、inf、非法坐标范围和不匹配的数据点数量
- 内置 Noto Sans SC 字体，保证跨平台中文显示

## 环境要求

- Python 3.12 或更高版本
- Windows 10/11、Ubuntu 或兼容 Linux 发行版
- 构建 Android APK 时需要 Flutter、JDK 17 和 Android SDK

## 安装与运行

```powershell
git clone https://github.com/ZZ-520-ZZ/line-chart.git
cd line-chart
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Linux 激活虚拟环境：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

主程序入口是 `main.py`，跨平台界面位于 `flet_app.py`。

运行 Tkinter 兼容版：

```powershell
python "绘图工具.py"
```

## 数据格式

X 和 Y 数据使用英文逗号分隔：

```text
0,1,2,3,4
```

不确定度可以填写一个统一值：

```text
0.05
```

也可以填写与数据点数量一致的逐点数值：

```text
0.05,0.05,0.06,0.06,0.08
```

CSV 或 Excel 文件的第一行应为列名，第一列作为 X，其余列分别导入为 Y 曲线：

| 时间 | 实验组 | 对照组 |
| ---: | ---: | ---: |
| 0 | 1 | 1 |
| 1 | 3 | 2 |
| 2 | 5 | 7 |

## 工程文件

`.pplot` 工程文件保存以下内容：

- 原始 X/Y 数据和不确定度
- 曲线名称、颜色、数据点和显示状态
- 拟合方式
- 标题、图表说明、坐标轴和单位
- 坐标范围、精度、网格和图例设置

Windows、Android 和 Tkinter 兼容版使用同一种工程格式。工程文件用于继续编辑，导出的图片用于提交报告或打印。

## 自动化测试

运行 27 项单元测试和历史缺陷回归测试：

```powershell
python run_tests.py
```

运行三组真实绘图测试：

```powershell
python cross_platform_smoke_test.py
```

三组测试覆盖：

1. 线性运动数据与 X/Y 误差棒
2. 两条曲线的线性和二次拟合
3. 指数数据与指数拟合

测试会检查输出图片尺寸、非空像素、拟合结果数量和已知参数，并将图片写入 `build/test-output/`。

Windows 上还可以运行 Tkinter 真实窗口测试：

```powershell
python gui_smoke_test.py
```

GitHub Actions 会在每次 push 和 Pull Request 时，使用 Python 3.12 在 Windows 与 Ubuntu 上自动运行 27 项测试和三组绘图测试，并上传生成的图片作为 CI 构建产物。当前仅配置 CI，不包含自动发布、证书签名或应用商店上传。

## 构建应用

构建 Windows 便携版：

```powershell
.\build_windows.ps1
```

构建 Android 64 位 APK：

```powershell
.\build_android.ps1
```

构建结果写入本地 `dist/` 目录，该目录不会提交到 Git 仓库。Android 构建目标为 `arm64-v8a`，最低 API 24。默认 APK 使用调试证书，正式发布前需要配置并保管独立的发布密钥。

Windows 上首次运行 Flet 构建时，如果 Flutter 提示无法创建符号链接，需要在系统设置中启用“开发者模式”。Matplotlib 在 Android 上需要解压部署，相关设置已包含在 `pyproject.toml` 和构建脚本中。

## 项目结构

| 文件 | 职责 |
| --- | --- |
| `main.py` | Flet 跨平台入口 |
| `flet_app.py` | 响应式界面、深色模式和文件操作 |
| `app_state.py` | 表单状态、校验和图片渲染接口 |
| `plot_core.py` | 数据解析、数列生成、拟合与 Matplotlib 绘图 |
| `data_io.py` | CSV 和 Excel 导入 |
| `project_io.py` | `.pplot` 工程保存与恢复 |
| `绘图工具.py` | Tkinter 兼容入口 |
| `tests/` | 核心功能测试 |
| `test_regressions.py` | 历史缺陷回归测试 |
| `cross_platform_smoke_test.py` | 三组真实绘图测试 |
| `gui_smoke_test.py` | Windows Tkinter 窗口测试 |
| `.github/workflows/ci.yml` | Windows/Ubuntu 持续集成配置 |

## 仓库

GitHub：<https://github.com/ZZ-520-ZZ/line-chart>
