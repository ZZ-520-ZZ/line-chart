from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from math import isfinite
from pathlib import Path

from matplotlib import font_manager, rcParams
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from data_io import ImportedTable, load_table
from plot_core import (
    ChartSpec,
    CurveSpec,
    FitResult,
    generate_series_values,
    parse_axis_limits,
    parse_numeric_data,
    parse_precision,
    parse_uncertainty_text,
    render_chart,
)
from project_io import CurveProject, ProjectState, load_project, save_project


CURVE_COLORS = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#6A51A3",
    "#4D4D4D",
    "#56B4E9",
)
CURVE_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "*")
FIT_NAMES = {
    "none": "不拟合",
    "linear": "线性",
    "quadratic": "二次",
    "exponential": "指数",
}


def configure_plot_font() -> None:
    font_path = Path(__file__).resolve().parent / "assets" / "fonts" / "NotoSansSC-VF.ttf"
    if font_path.exists():
        font_manager.fontManager.addfont(font_path)
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
    rcParams["axes.unicode_minus"] = False


configure_plot_font()


@dataclass
class CurveForm:
    label: str = "数据集1"
    data: str = ""
    uncertainty: str = ""
    color: str = CURVE_COLORS[0]
    visible: bool = True
    marker: str = "o"
    fit_type: str = "none"

    def to_project(self) -> CurveProject:
        return CurveProject(
            label=self.label,
            data=self.data,
            uncertainty=self.uncertainty,
            color=self.color,
            visible=self.visible,
            marker=self.marker,
            fit_type=self.fit_type,
        )

    @classmethod
    def from_project(cls, curve: CurveProject) -> CurveForm:
        return cls(**curve.__dict__)


@dataclass
class PlotForm:
    title: str = "物理实验曲线图"
    note: str = ""
    x_label: str = "X"
    x_unit: str = ""
    y_label: str = "Y"
    y_unit: str = ""
    x_data: str = ""
    x_uncertainty: str = ""
    x_min: str = ""
    x_max: str = ""
    y_min: str = ""
    y_max: str = ""
    x_tick_direction: str = "in"
    y_tick_direction: str = "in"
    show_grid: bool = True
    show_legend: bool = True
    precision: str = "2"
    curves: list[CurveForm] = field(default_factory=lambda: [CurveForm()])

    def add_curve(self, label: str | None = None) -> CurveForm:
        index = len(self.curves)
        curve = CurveForm(
            label=label or f"数据集{index + 1}",
            color=CURVE_COLORS[index % len(CURVE_COLORS)],
            marker=CURVE_MARKERS[index % len(CURVE_MARKERS)],
        )
        self.curves.append(curve)
        return curve

    def remove_curve(self, index: int) -> None:
        if len(self.curves) <= 1:
            raise ValueError("至少保留一条曲线")
        del self.curves[index]

    def apply_generated_series(
        self,
        target: str,
        series_type: str,
        start_text: str,
        end_text: str,
        step_or_ratio_text: str,
    ) -> list[float]:
        values = generate_series_from_text(
            series_type,
            start_text,
            end_text,
            step_or_ratio_text,
        )
        formatted = _format_values(values)
        if target == "x":
            self.x_data = formatted
            return values

        prefix = "curve:"
        if not target.startswith(prefix):
            raise ValueError("请选择有效的数列写入目标")
        try:
            curve_index = int(target[len(prefix):])
        except ValueError:
            raise ValueError("所选曲线已不存在，请重新选择写入目标") from None
        if not 0 <= curve_index < len(self.curves):
            raise ValueError("所选曲线已不存在，请重新选择写入目标")
        curve = self.curves[curve_index]
        curve.data = formatted
        return values

    def build_chart_spec(self) -> ChartSpec:
        x_values = parse_numeric_data(self.x_data)
        if not x_values:
            raise ValueError("请输入 X 轴数据")

        precision = parse_precision(self.precision)
        x_limits = parse_axis_limits(self.x_min, self.x_max, "X轴")
        y_limits = parse_axis_limits(self.y_min, self.y_max, "Y轴")
        x_errors = parse_uncertainty_text(
            self.x_uncertainty, len(x_values), "X轴不确定度"
        )

        curves = []
        for curve in self.curves:
            if not curve.visible:
                continue
            values = parse_numeric_data(curve.data)
            if not values:
                raise ValueError(f"{curve.label or '未命名曲线'}没有数据")
            if len(values) != len(x_values):
                raise ValueError(
                    f"X轴有{len(x_values)}个点，但{curve.label or '未命名曲线'}有{len(values)}个点"
                )
            errors = parse_uncertainty_text(
                curve.uncertainty, len(x_values), f"{curve.label}的Y轴不确定度"
            )
            curves.append(
                CurveSpec(
                    values=values,
                    label=curve.label or "未命名曲线",
                    color=curve.color,
                    marker=curve.marker,
                    errors=errors,
                    fit_type=curve.fit_type,
                )
            )

        if not curves:
            raise ValueError("至少启用一条曲线")
        return ChartSpec(
            x_values=x_values,
            curves=curves,
            x_errors=x_errors,
            title=self.title,
            note=self.note,
            x_label=self.x_label,
            y_label=self.y_label,
            x_unit=self.x_unit,
            y_unit=self.y_unit,
            x_limits=x_limits,
            y_limits=y_limits,
            x_tick_direction=self.x_tick_direction,
            y_tick_direction=self.y_tick_direction,
            precision=precision,
            show_grid=self.show_grid,
            show_legend=self.show_legend,
        )

    def render_image(
        self,
        image_format: str = "png",
        width: int = 960,
        height: int = 620,
        dpi: int = 120,
    ) -> tuple[bytes, tuple[FitResult, ...]]:
        figure = Figure(figsize=(width / dpi, height / dpi), dpi=dpi)
        FigureCanvasAgg(figure)
        axis = figure.add_subplot(111)
        result = render_chart(axis, self.build_chart_spec())
        output = BytesIO()
        figure.savefig(output, format=image_format, dpi=dpi)
        figure.clear()
        return output.getvalue(), result.fit_results

    def import_table(self, file_path: str | Path) -> ImportedTable:
        table = load_table(file_path)
        self.x_label = table.x_label
        self.x_data = _format_values(table.x_values)
        self.curves = []
        for index, series in enumerate(table.series):
            self.curves.append(
                CurveForm(
                    label=series.label,
                    data=_format_values(series.values),
                    color=CURVE_COLORS[index % len(CURVE_COLORS)],
                    marker=CURVE_MARKERS[index % len(CURVE_MARKERS)],
                )
            )
        return table

    def to_project(self) -> ProjectState:
        return ProjectState(
            title=self.title,
            note=self.note,
            x_label=self.x_label,
            x_unit=self.x_unit,
            y_label=self.y_label,
            y_unit=self.y_unit,
            x_data=self.x_data,
            x_uncertainty=self.x_uncertainty,
            x_min=self.x_min,
            x_max=self.x_max,
            y_min=self.y_min,
            y_max=self.y_max,
            x_tick_direction=self.x_tick_direction,
            y_tick_direction=self.y_tick_direction,
            show_grid=self.show_grid,
            show_legend=self.show_legend,
            precision=self.precision,
            curves=tuple(curve.to_project() for curve in self.curves),
        )

    @classmethod
    def from_project(cls, project: ProjectState) -> PlotForm:
        values = {
            key: value
            for key, value in project.__dict__.items()
            if key != "curves"
        }
        values["curves"] = [CurveForm.from_project(curve) for curve in project.curves]
        if not values["curves"]:
            values["curves"] = [CurveForm()]
        return cls(**values)

    def save(self, file_path: str | Path) -> None:
        save_project(file_path, self.to_project())

    @classmethod
    def load(cls, file_path: str | Path) -> PlotForm:
        return cls.from_project(load_project(file_path))


def format_fit_results(results: tuple[FitResult, ...]) -> str:
    if not results:
        return "当前曲线未启用拟合。"
    blocks = []
    for result in results:
        parameter_text = "\n".join(
            f"  {name}: {value:.8g}" for name, value in result.parameters.items()
        )
        blocks.append(
            f"{result.curve_label} · {FIT_NAMES.get(result.fit_type, result.fit_type)}拟合\n"
            f"{result.equation}\n{parameter_text}\n"
            f"R²: {result.r_squared:.8g}\n相关系数: {result.correlation:.8g}"
        )
    return "\n\n".join(blocks)


def generate_series_from_text(
    series_type: str,
    start_text: str,
    end_text: str,
    step_or_ratio_text: str,
) -> list[float]:
    fields = (
        ("起始值", start_text),
        ("结束值", end_text),
        ("步长或公比", step_or_ratio_text),
    )
    parsed = []
    for label, text in fields:
        try:
            value = float(text)
        except (TypeError, ValueError):
            raise ValueError(f"{label}必须是数字") from None
        if not isfinite(value):
            raise ValueError(f"{label}必须是有限数字")
        parsed.append(value)
    return generate_series_values(series_type, *parsed)


def _format_values(values) -> str:
    return ",".join(f"{float(value):.12g}" for value in values)
