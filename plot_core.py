from dataclasses import dataclass
from typing import Sequence

import numpy as np
from matplotlib.ticker import FuncFormatter


MAX_SERIES_POINTS = 1000


@dataclass(frozen=True)
class CurveSpec:
    values: Sequence[float]
    label: str
    color: str
    marker: str
    errors: Sequence[float] | float | None = None
    fit_type: str = "none"


@dataclass(frozen=True)
class ChartSpec:
    x_values: Sequence[float]
    curves: Sequence[CurveSpec]
    x_errors: Sequence[float] | float | None = None
    title: str = ""
    note: str = ""
    x_label: str = ""
    y_label: str = ""
    x_unit: str = ""
    y_unit: str = ""
    x_limits: tuple[float | None, float | None] = (None, None)
    y_limits: tuple[float | None, float | None] = (None, None)
    x_tick_direction: str = "in"
    y_tick_direction: str = "in"
    precision: int = 1
    show_grid: bool = True
    show_legend: bool = True


@dataclass(frozen=True)
class FitResult:
    curve_label: str
    fit_type: str
    equation: str
    parameters: dict[str, float]
    r_squared: float
    correlation: float


@dataclass(frozen=True)
class RenderResult:
    annotation: object
    fit_results: tuple[FitResult, ...]


def validate_precision_text(value):
    if value == "":
        return True
    return value.isdecimal() and 0 <= int(value) <= 10


def parse_precision(value):
    if isinstance(value, bool):
        raise ValueError("数值精度必须是0到10之间的整数")
    text = str(value)
    if not text.isdecimal():
        raise ValueError("数值精度必须是0到10之间的整数")
    precision = int(text)
    if not 0 <= precision <= 10:
        raise ValueError("数值精度必须是0到10之间的整数")
    return precision


def parse_numeric_data(data_text):
    normalized = data_text.replace('，', ',').strip()
    if not normalized:
        return []

    data = []
    for index, item in enumerate(normalized.split(','), start=1):
        try:
            value = float(item.strip())
        except ValueError as exc:
            raise ValueError(f"第{index}个数据格式错误，请输入数字并用逗号分隔") from exc
        if not np.isfinite(value):
            raise ValueError(f"第{index}个数据必须是有限数字，不能使用NaN或inf")
        data.append(value)
    return data


def parse_axis_limits(min_text, max_text, axis_name):
    values = []
    for text, bound_name in ((min_text, "最小值"), (max_text, "最大值")):
        normalized = text.strip()
        if not normalized:
            values.append(None)
            continue
        try:
            value = float(normalized)
        except ValueError as exc:
            raise ValueError(f"{axis_name}{bound_name}必须是数字") from exc
        if not np.isfinite(value):
            raise ValueError(f"{axis_name}{bound_name}必须是有限数字")
        values.append(value)

    minimum, maximum = values
    if minimum is not None and maximum is not None and minimum >= maximum:
        raise ValueError(f"{axis_name}最小值必须小于最大值")
    return minimum, maximum


def generate_series_values(series_type, start, end, step_or_ratio, max_points=MAX_SERIES_POINTS):
    values = (start, end, step_or_ratio)
    if not all(np.isfinite(value) for value in values):
        raise ValueError("数列参数必须是有限数字")

    if series_type == "arithmetic":
        step = step_or_ratio
        if step == 0:
            raise ValueError("等差数列的步长不能为0")
        if start == end:
            return [start]
        if (end - start) * step < 0:
            raise ValueError("步长方向与起始值、结束值的方向不一致")

        interval_count = (end - start) / step
        if not np.isfinite(interval_count):
            raise ValueError("数列点数超出有效计算范围，请调整参数")
        point_count = int(np.floor(interval_count + 1e-12)) + 1
        if point_count > max_points:
            raise ValueError(f"生成的数据点超过{max_points}个，请调整参数")

        data = [start + index * step for index in range(point_count)]
        if data and np.isclose(data[-1], end, rtol=1e-12, atol=1e-12):
            data[-1] = end
        return data

    if series_type != "geometric":
        raise ValueError("未知的数列类型")

    ratio = step_or_ratio
    if start == end:
        return [start]
    if ratio <= 0:
        raise ValueError("等比数列的公比必须大于0")
    if ratio == 1:
        raise ValueError("公比为1时无法从起始值到达结束值")
    if start == 0:
        raise ValueError("起始值为0时无法通过等比数列到达非零结束值")

    with np.errstate(over='ignore', invalid='ignore'):
        next_value = float(np.multiply(start, ratio))
    if not np.isfinite(next_value):
        raise ValueError("数列计算结果超出有效数值范围")
    direction = 1 if end > start else -1
    if direction * (next_value - start) <= 0:
        raise ValueError("公比方向与起始值、结束值的方向不一致")

    tolerance = max(abs(start), abs(end), 1.0) * 1e-12
    data = []
    current = start
    while True:
        within_end = current <= end + tolerance if direction > 0 else current >= end - tolerance
        if not within_end:
            return data
        if len(data) >= max_points:
            raise ValueError(f"生成的数据点超过{max_points}个，请调整参数")

        data.append(current)
        with np.errstate(over='ignore', invalid='ignore'):
            next_value = float(np.multiply(current, ratio))
        if not np.isfinite(next_value):
            raise ValueError("数列计算结果超出有效数值范围")
        if next_value == current:
            raise ValueError("当前参数无法继续生成有效的等比数列")
        current = next_value


def create_annotation(ax):
    annotation = ax.annotate("", xy=(0, 0), xytext=(20, 20),
                             textcoords="offset points",
                             bbox=dict(boxstyle="round", fc="w"),
                             arrowprops=dict(arrowstyle="->"))
    annotation.set_visible(False)
    return annotation


def normalize_uncertainties(values, point_count, label):
    if values is None or (isinstance(values, str) and values == ""):
        return None
    if np.isscalar(values):
        normalized = [float(values)] * point_count
    else:
        normalized = [float(value) for value in values]
        if len(normalized) == 1:
            normalized *= point_count
    if len(normalized) != point_count:
        raise ValueError(f"{label}数量必须为1个或与数据点数量一致")
    if not all(np.isfinite(value) and value >= 0 for value in normalized):
        raise ValueError(f"{label}必须是非负有限数字")
    return normalized


def parse_uncertainty_text(data_text, point_count, label):
    if not data_text.strip():
        return None
    values = parse_numeric_data(data_text)
    return normalize_uncertainties(values, point_count, label)


def fit_curve(x_values, y_values, fit_type, curve_label, errors=None):
    if fit_type == "none":
        return None, None, None
    if fit_type == "exponential":
        if len(x_values) < 2 or len(set(x_values)) < 2:
            raise ValueError(f"{curve_label}至少需要两个不同的X值才能进行指数拟合")
        if not all(value > 0 for value in y_values):
            raise ValueError(f"{curve_label}的Y值必须全部大于0才能进行指数拟合")
        weights = None
        if errors is not None and all(error > 0 for error in errors):
            weights = np.asarray(y_values, dtype=float) / np.asarray(errors, dtype=float)
        rate, log_amplitude = np.polyfit(x_values, np.log(y_values), 1, w=weights)
        amplitude = float(np.exp(log_amplitude))
        predicted = amplitude * np.exp(rate * np.asarray(x_values))
        residual_sum = float(np.sum((np.asarray(y_values) - predicted) ** 2))
        total_sum = float(np.sum((np.asarray(y_values) - np.mean(y_values)) ** 2))
        r_squared = 1.0 if total_sum == 0 and residual_sum == 0 else 1 - residual_sum / total_sum
        correlation = float(np.corrcoef(y_values, predicted)[0, 1])
        fit_x = np.linspace(min(x_values), max(x_values), 200)
        fit_y = amplitude * np.exp(rate * fit_x)
        result = FitResult(
            curve_label=curve_label,
            fit_type=fit_type,
            equation=f"y = {amplitude:.6g} exp({rate:.6g}x)",
            parameters={"amplitude": amplitude, "rate": float(rate)},
            r_squared=float(r_squared),
            correlation=correlation)
        return fit_x, fit_y, result
    if fit_type not in ("linear", "quadratic"):
        raise ValueError(f"不支持的拟合类型：{fit_type}")
    degree = 1 if fit_type == "linear" else 2
    required_points = degree + 1
    if len(x_values) < required_points or len(set(x_values)) < required_points:
        raise ValueError(f"{curve_label}至少需要{required_points}个不同的X值才能拟合")

    weights = None
    if errors is not None and all(error > 0 for error in errors):
        weights = 1 / np.asarray(errors, dtype=float)
    coefficients = np.polyfit(x_values, y_values, degree, w=weights)
    predicted = np.polyval(coefficients, x_values)
    residual_sum = float(np.sum((np.asarray(y_values) - predicted) ** 2))
    total_sum = float(np.sum((np.asarray(y_values) - np.mean(y_values)) ** 2))
    r_squared = 1.0 if total_sum == 0 and residual_sum == 0 else 1 - residual_sum / total_sum
    if np.std(y_values) == 0 or np.std(predicted) == 0:
        correlation = 1.0 if np.allclose(y_values, predicted) else 0.0
    else:
        correlation = float(np.corrcoef(y_values, predicted)[0, 1])

    fit_x = np.linspace(min(x_values), max(x_values), 200)
    fit_y = np.polyval(coefficients, fit_x)
    if fit_type == "linear":
        slope, intercept = coefficients
        equation = f"y = {slope:.6g}x + {intercept:.6g}"
        parameters = {"slope": float(slope), "intercept": float(intercept)}
    else:
        quadratic, linear, constant = coefficients
        equation = f"y = {quadratic:.6g}x^2 + {linear:.6g}x + {constant:.6g}"
        parameters = {
            "quadratic": float(quadratic),
            "linear": float(linear),
            "constant": float(constant),
        }
    result = FitResult(
        curve_label=curve_label,
        fit_type=fit_type,
        equation=equation,
        parameters=parameters,
        r_squared=float(r_squared),
        correlation=correlation)
    return fit_x, fit_y, result


def render_chart(ax, spec):
    x_values = list(spec.x_values)
    curves = list(spec.curves)
    precision = parse_precision(spec.precision)
    if not x_values:
        raise ValueError("X轴数据不能为空")
    if not curves:
        raise ValueError("至少需要一条曲线")
    if not all(np.isfinite(value) for value in x_values):
        raise ValueError("X轴数据必须全部是有限数字")
    x_errors = normalize_uncertainties(spec.x_errors, len(x_values), "X轴不确定度")
    fit_results = []
    for curve in curves:
        if len(curve.values) != len(x_values):
            raise ValueError(f"X轴和{curve.label}数据长度不一致")
        if not all(np.isfinite(value) for value in curve.values):
            raise ValueError(f"{curve.label}的数据必须全部是有限数字")

    ax.clear()
    for curve in curves:
        y_errors = normalize_uncertainties(
            curve.errors, len(x_values), f"{curve.label}的Y轴不确定度")
        if x_errors is not None or y_errors is not None:
            ax.errorbar(x_values, curve.values, xerr=x_errors, yerr=y_errors,
                        marker=curve.marker, linestyle='-', color=curve.color,
                        linewidth=2, markersize=8, capsize=4,
                        label=curve.label, clip_on=False)
        else:
            ax.plot(x_values, curve.values, marker=curve.marker, linestyle='-',
                    color=curve.color, linewidth=2, markersize=8,
                    label=curve.label, clip_on=False)
        fit_x, fit_y, fit_result = fit_curve(
            x_values, curve.values, curve.fit_type, curve.label, y_errors)
        if fit_result is not None:
            ax.plot(fit_x, fit_y, linestyle='--', color=curve.color,
                    linewidth=1.8, label=f"{curve.label} 拟合")
            fit_results.append(fit_result)

    full_x_label = f"{spec.x_label} ({spec.x_unit})" if spec.x_unit else spec.x_label
    full_y_label = f"{spec.y_label} ({spec.y_unit})" if spec.y_unit else spec.y_label
    ax.set_title(spec.title, fontsize=14, pad=20)
    ax.set_xlabel(full_x_label, fontsize=12, labelpad=10)
    ax.set_ylabel(full_y_label, fontsize=12, labelpad=10)

    figure_width = ax.figure.get_figwidth() * ax.figure.dpi
    compact = figure_width < 500
    if spec.note:
        ax.text(0.5, -0.33 if compact else -0.2, spec.note, transform=ax.transAxes,
                ha='center', va='top', fontsize=9 if compact else 10, wrap=True)
    ax.figure.subplots_adjust(
        left=0.22 if compact else 0.12,
        right=0.97,
        top=0.86 if compact else 0.90,
        bottom=(0.38 if compact else 0.25) if spec.note else (0.20 if compact else 0.15))

    x_min, x_max = spec.x_limits
    y_min, y_max = spec.y_limits
    if x_min is not None or x_max is not None:
        ax.set_xlim(left=x_min, right=x_max)
    if y_min is not None or y_max is not None:
        ax.set_ylim(bottom=y_min, top=y_max)

    ax.tick_params(axis='x', direction=spec.x_tick_direction)
    ax.tick_params(axis='y', direction=spec.y_tick_direction)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if spec.show_grid:
        ax.grid(True, linestyle='--', alpha=0.7)
    if spec.show_legend:
        ax.legend(fontsize=8 if compact else 10)

    formatter = FuncFormatter(lambda value, position: f'{value:.{precision}f}')
    ax.xaxis.set_major_formatter(formatter)
    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda value, position: f'{value:.{precision}f}'))
    return RenderResult(
        annotation=create_annotation(ax),
        fit_results=tuple(fit_results))
