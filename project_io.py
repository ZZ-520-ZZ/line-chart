import json
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_VERSION = 1


@dataclass(frozen=True)
class CurveProject:
    label: str
    data: str
    uncertainty: str
    color: str
    visible: bool
    marker: str
    fit_type: str


@dataclass(frozen=True)
class ProjectState:
    title: str
    note: str
    x_label: str
    x_unit: str
    y_label: str
    y_unit: str
    x_data: str
    x_uncertainty: str
    x_min: str
    x_max: str
    y_min: str
    y_max: str
    x_tick_direction: str
    y_tick_direction: str
    show_grid: bool
    show_legend: bool
    precision: str
    curves: tuple[CurveProject, ...]


def save_project(file_path, state):
    payload = {
        "version": PROJECT_VERSION,
        "project": asdict(state),
    }
    Path(file_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8")


def load_project(file_path):
    try:
        payload = json.loads(Path(file_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"工程文件无法读取：{exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != PROJECT_VERSION:
        raise ValueError("工程文件版本不受支持")
    project = payload.get("project")
    if not isinstance(project, dict):
        raise ValueError("工程文件缺少项目数据")
    try:
        curves = tuple(CurveProject(**curve) for curve in project.get("curves", []))
        return ProjectState(**{**project, "curves": curves})
    except (TypeError, ValueError) as exc:
        raise ValueError(f"工程文件结构无效：{exc}") from exc
