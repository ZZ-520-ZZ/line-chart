# Line Chart

面向物理实验的跨平台曲线绘图工具，应用名称为“绘图工具”。同一套 Flet 界面可运行在 Windows 和 Android，计算、拟合和工程文件逻辑由独立 Python 模块共享。

## 主要功能

- 多组 Y 数据共用一组 X 数据
- X/Y 不确定度和误差棒，支持单值或逐点列表
- 线性、二次和指数拟合
- 拟合方程、参数、R² 和相关系数
- CSV、XLSX、XLSM 数据导入
- `.pplot` 工程保存与恢复
- PNG、JPG、SVG、PDF 图像导出
- 自定义标题、说明、轴名称、单位、范围、精度、网格、图例、颜色和数据点
- 拒绝 NaN、inf、非法范围和不匹配的数据点数量
- 内置中文字体，Windows 和 Android 导出的图像均可显示中文

## 直接使用

### Windows

已构建的便携包位于 `dist/绘图工具-Windows.zip`。

发布包解压后，双击：

```text
绘图工具/绘图工具.exe
```

该文件夹是便携版，不需要预先安装 Python。不要只复制 `.exe`，它需要同目录下的 `_internal` 依赖文件夹。

### Android

已构建的安装包位于 `dist/绘图工具.apk`。

将 `绘图工具.apk` 传到 64 位 Android 手机并安装。首次侧载时，系统可能要求允许当前文件管理器安装未知来源应用。

当前 APK 构建目标为 `arm64-v8a`，适用于绝大多数近年的 Android 手机。

当前 APK 使用 Android 调试证书签名，适合自行安装和测试；发布到应用商店前需要配置并妥善保管正式发布密钥。

## 从源码运行

推荐使用 Python 3.12 或更高版本：

```powershell
git clone https://github.com/ZZ-520-ZZ/line-chart.git
cd line-chart
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

跨平台入口是 `main.py`，界面实现位于 `flet_app.py`。

原来的 Tkinter 桌面界面仍然保留：

```powershell
python "绘图工具.py"
```

## 数据输入

X 和 Y 数据使用英文逗号分隔：

```text
0,1,2,3,4
```

不确定度可填写一个统一值：

```text
0.05
```

也可填写与数据点数量相同的逐点值：

```text
0.05,0.05,0.06,0.06,0.08
```

CSV 或 Excel 的第一行为列名，第一列作为 X，其余列分别成为 Y 曲线：

| 时间 | 实验组 | 对照组 |
| ---: | ---: | ---: |
| 0 | 1 | 1 |
| 1 | 3 | 2 |
| 2 | 5 | 7 |

## 工程文件

`.pplot` 保存原始数据、不确定度、曲线设置、拟合方式、坐标范围、标题和图表说明，可在之后恢复编辑。工程文件和导出的最终图片用途不同。

Windows、Android 和旧 Tkinter 界面使用同一种 `.pplot` 格式。

## 自动化测试

运行完整测试套件：

```powershell
python run_tests.py
```

运行三组真实绘图冒烟测试：

```powershell
python cross_platform_smoke_test.py
```

冒烟测试会生成线性误差棒、多曲线线性/二次拟合和指数拟合三张图片，并检查图像尺寸、非空像素及已知拟合参数。

## 构建

Windows 便携版：

```powershell
.\build_windows.ps1
```

Android 64 位 APK：

```powershell
.\build_android.ps1
```

Flet 首次构建会下载 Flutter、JDK 17 和 Android SDK。Windows 上若 Flutter 提示无法创建符号链接，需要先在系统设置中启用“开发者模式”。

Matplotlib 在 Android 上必须作为解压包部署，`pyproject.toml` 和 Android 构建脚本已经包含该配置。

## 代码结构

| 文件 | 职责 |
| --- | --- |
| `main.py` | Windows/Android 跨平台入口 |
| `flet_app.py` | 响应式 Flet 界面与文件操作 |
| `app_state.py` | 平台无关的表单状态、校验和图片渲染 |
| `plot_core.py` | 数据解析、数列、拟合和 Matplotlib 渲染 |
| `data_io.py` | CSV 和 Excel 导入 |
| `project_io.py` | `.pplot` 工程保存与恢复 |
| `绘图工具.py` | 保留的 Tkinter 桌面界面 |
| `tests/` | 核心功能与跨平台状态测试 |
| `test_regressions.py` | 历史缺陷回归测试 |
