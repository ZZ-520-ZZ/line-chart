# Line Chart

一个面向物理实验数据处理的桌面绘图工具。使用 Tkinter 构建界面，使用 Matplotlib 完成曲线、误差棒和拟合结果绘制。

程序支持在 `800 x 600` 窗口中直接使用全部主要操作，适合录入多组实验数据、检查拟合质量并导出图片。

![数据与图表界面](docs/images/gui-data.png)

## 功能

- 同时绘制多组 Y 数据，共用一组 X 数据
- 自定义标题、坐标名称、单位、范围、网格、图例、颜色和数据点样式
- 支持 X/Y 不确定度和误差棒，不确定度可填写单值或逐点列表
- 支持线性、二次和指数拟合
- 显示拟合方程、参数、决定系数 R² 和相关系数
- 从 CSV、XLSX、XLSM 表格导入数据
- 将当前数据和绘图设置保存为 `.pplot` 工程，并在之后恢复编辑
- 导出 PNG、JPG、SVG、PDF 等 Matplotlib 支持的图片格式
- 悬停数据点时显示实际数据坐标
- 拒绝 NaN、inf、非法精度和危险的数列参数

![拟合结果界面](docs/images/gui-fit.png)

## 环境要求

- Python 3.10 或更高版本
- Windows、Linux 或 macOS
- Linux 用户可能需要额外安装 Tkinter，例如 Ubuntu/Debian 上的 `python3-tk`

## 安装

```bash
git clone https://github.com/ZZ-520-ZZ/line-chart.git
cd line-chart
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Linux/macOS：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 运行

```bash
python "绘图工具.py"
```

## 数据输入

X 和 Y 数据使用英文逗号分隔，例如：

```text
0,1,2,3,4
```

不确定度可以填写一个统一值：

```text
0.05
```

也可以填写与数据点数量相同的逐点值：

```text
0.05,0.05,0.06,0.06,0.08
```

### 表格导入格式

CSV 或 Excel 表格的第一行为列名，第一列作为 X，其他列分别作为 Y 曲线：

| 时间 | 实验组 | 对照组 |
| ---: | ---: | ---: |
| 0 | 1 | 1 |
| 1 | 3 | 2 |
| 2 | 5 | 7 |

## 工程文件

“保存工程”会生成 `.pplot` 文件，记录原始数据、不确定度、曲线设置、拟合方式、坐标范围、标题和图表说明等状态。

`.pplot` 是可继续编辑的工程文件；“导出图片”生成的是最终图片，两者用途不同。

## 自动化测试

运行完整测试套件：

```bash
python run_tests.py
```

测试覆盖数据解析、数列边界、非有限值拒绝、曲线增删、误差棒、三种拟合、CSV/Excel 导入以及工程保存恢复。

真实 Tkinter 界面检查脚本：

```bash
python gui_smoke_test.py
```

该脚本会打开一个短暂的测试窗口，并验证 `800 x 600` 布局、按钮可见性、表格导入、误差棒、拟合和工程往返。

## 代码结构

| 文件 | 职责 |
| --- | --- |
| `绘图工具.py` | Tkinter 界面与用户操作协调 |
| `plot_core.py` | 数据校验、数列生成、拟合与图表渲染 |
| `data_io.py` | CSV 和 Excel 导入 |
| `project_io.py` | `.pplot` 工程保存与恢复 |
| `test_regressions.py` | 历史缺陷回归测试 |
| `tests/` | 核心功能单元测试 |

运行程序时，请保持 `绘图工具.py`、`plot_core.py`、`data_io.py` 和 `project_io.py` 位于同一目录。
