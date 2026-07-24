from __future__ import annotations

import tempfile
from pathlib import Path

import flet as ft

from app_state import (
    CURVE_COLORS,
    CurveForm,
    PlotForm,
    format_fit_results,
)


APP_NAME = "绘图工具"
FIT_OPTIONS = (
    ("none", "不拟合"),
    ("linear", "线性拟合"),
    ("quadratic", "二次拟合"),
    ("exponential", "指数拟合"),
)
MARKER_OPTIONS = (
    ("o", "圆点"),
    ("s", "方块"),
    ("^", "上三角"),
    ("D", "菱形"),
    ("v", "下三角"),
    ("P", "加号"),
    ("X", "叉号"),
    ("*", "星形"),
)


def _options(items):
    return [ft.DropdownOption(key=key, text=label) for key, label in items]


class CurveEditor:
    def __init__(self, app: PlotApplication, index: int, curve: CurveForm):
        self.app = app
        self.index = index
        self.color = curve.color
        self.label = ft.TextField(
            value=curve.label,
            label="图例名称",
            dense=True,
            expand=True,
        )
        self.visible = ft.Switch(value=curve.visible, label="显示", adaptive=True)
        self.data = ft.TextField(
            value=curve.data,
            label="Y 数据（逗号分隔）",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.uncertainty = ft.TextField(
            value=curve.uncertainty,
            label="Y 不确定度（单值或列表）",
            dense=True,
            col={"xs": 12, "sm": 6},
        )
        self.fit_type = ft.Dropdown(
            value=curve.fit_type,
            label="拟合方式",
            options=_options(FIT_OPTIONS),
            dense=True,
            col={"xs": 6, "sm": 3},
        )
        self.marker = ft.Dropdown(
            value=curve.marker,
            label="数据点",
            options=_options(MARKER_OPTIONS),
            dense=True,
            col={"xs": 6, "sm": 3},
        )
        self.swatches = []
        self.color_row = self._build_color_row()
        self.control = ft.Card(
            elevation=0,
            variant=ft.CardVariant.OUTLINED,
            content=ft.Container(
                padding=12,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                self.label,
                                self.visible,
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    tooltip="删除曲线",
                                    on_click=lambda _: self.app.remove_curve(self.index),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        self.data,
                        ft.ResponsiveRow(
                            [self.uncertainty, self.fit_type, self.marker],
                            spacing=8,
                            run_spacing=8,
                        ),
                        ft.Text("曲线颜色", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        self.color_row,
                    ],
                    spacing=9,
                ),
            ),
        )

    def _build_color_row(self):
        controls = []
        for color in CURVE_COLORS:
            swatch = ft.Container(
                width=30,
                height=30,
                bgcolor=color,
                border_radius=4,
                border=ft.Border.all(
                    3 if color == self.color else 1,
                    ft.Colors.ON_SURFACE if color == self.color else ft.Colors.OUTLINE_VARIANT,
                ),
                tooltip=color,
                on_click=lambda _, selected=color: self.select_color(selected),
            )
            self.swatches.append((color, swatch))
            controls.append(swatch)
        return ft.Row(controls, wrap=True, spacing=8, run_spacing=8)

    def select_color(self, color: str):
        self.color = color
        for value, swatch in self.swatches:
            swatch.border = ft.Border.all(
                3 if value == color else 1,
                ft.Colors.ON_SURFACE if value == color else ft.Colors.OUTLINE_VARIANT,
            )
        self.color_row.update()

    def to_form(self) -> CurveForm:
        return CurveForm(
            label=self.label.value or "",
            data=self.data.value or "",
            uncertainty=self.uncertainty.value or "",
            color=self.color,
            visible=bool(self.visible.value),
            marker=self.marker.value or "o",
            fit_type=self.fit_type.value or "none",
        )


class PlotApplication:
    def __init__(self, page: ft.Page):
        self.page = page
        self.form = PlotForm()
        self.file_picker = ft.FilePicker()
        self.curve_editors: list[CurveEditor] = []
        self.last_image: bytes | None = None
        self._create_controls()

    def _create_controls(self):
        self.title = ft.TextField(label="图表标题", value=self.form.title)
        self.note = ft.TextField(
            label="图表说明",
            value=self.form.note,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.x_label = ft.TextField(label="X 轴名称", value=self.form.x_label, col=8)
        self.x_unit = ft.TextField(label="X 单位", value=self.form.x_unit, col=4)
        self.y_label = ft.TextField(label="Y 轴名称", value=self.form.y_label, col=8)
        self.y_unit = ft.TextField(label="Y 单位", value=self.form.y_unit, col=4)
        self.x_data = ft.TextField(
            label="X 数据（逗号分隔）",
            value=self.form.x_data,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.x_uncertainty = ft.TextField(
            label="X 不确定度（单值或列表）",
            value=self.form.x_uncertainty,
        )
        self.x_min = ft.TextField(label="X 最小值", col=6)
        self.x_max = ft.TextField(label="X 最大值", col=6)
        self.y_min = ft.TextField(label="Y 最小值", col=6)
        self.y_max = ft.TextField(label="Y 最大值", col=6)
        direction_options = _options((("in", "向内"), ("out", "向外"), ("inout", "双向")))
        self.x_tick_direction = ft.Dropdown(
            label="X 刻度方向", value="in", options=direction_options, col=6
        )
        self.y_tick_direction = ft.Dropdown(
            label="Y 刻度方向",
            value="in",
            options=_options((("in", "向内"), ("out", "向外"), ("inout", "双向"))),
            col=6,
        )
        self.precision = ft.Dropdown(
            label="小数位数",
            value=self.form.precision,
            options=_options(tuple((str(value), str(value)) for value in range(11))),
            col=6,
        )
        self.show_grid = ft.Switch(value=True, label="显示网格", adaptive=True)
        self.show_legend = ft.Switch(value=True, label="显示图例", adaptive=True)
        self.curves_column = ft.Column(spacing=10)
        self.preview = ft.Image(
            src="",
            fit=ft.BoxFit.CONTAIN,
            expand=True,
            semantics_label="实验曲线预览",
        )
        self.preview_placeholder = ft.Column(
            [
                ft.Icon(ft.Icons.SHOW_CHART, size=52, color=ft.Colors.OUTLINE),
                ft.Text("输入数据后点击绘图", color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.preview_host = ft.Container(
            content=self.preview_placeholder,
            expand=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=6,
            padding=8,
        )
        self.fit_results = ft.Text(
            "绘制并选择拟合方式后，参数将显示在这里。",
            selectable=True,
            font_family="NotoSansSC",
        )
        self.status = ft.Text("尚未绘图", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.export_format = ft.Dropdown(
            value="png",
            label="文件格式",
            options=_options((("png", "PNG"), ("jpg", "JPG"), ("svg", "SVG"), ("pdf", "PDF"))),
            width=180,
        )
        self.export_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("导出图像"),
            content=self.export_format,
            actions=[
                ft.Button(content=ft.Text("取消"), on_click=self._close_export_dialog),
                ft.FilledButton(
                    content=ft.Text("导出"),
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self.export_image,
                ),
            ],
        )
        self._rebuild_curve_editors()

    def build(self):
        self.page.title = APP_NAME
        self.page.fonts = {"NotoSansSC": "fonts/NotoSansSC-VF.ttf"}
        self.page.theme = ft.Theme(
            color_scheme_seed="#00798c",
            font_family="NotoSansSC",
        )
        self.page.dark_theme = ft.Theme(
            color_scheme_seed="#edae49",
            font_family="NotoSansSC",
        )
        self.page.window.width = 1024
        self.page.window.height = 720
        self.page.window.min_width = 360
        self.page.window.min_height = 560
        self.page.padding = ft.Padding.all(0)
        self.page.appbar = ft.AppBar(
            title=ft.Text(APP_NAME, weight=ft.FontWeight.W_600),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.UPLOAD_FILE,
                    tooltip="导入 CSV / Excel",
                    on_click=self.import_data,
                ),
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN,
                    tooltip="打开工程",
                    on_click=self.open_project,
                ),
                ft.IconButton(
                    icon=ft.Icons.SAVE,
                    tooltip="保存工程",
                    on_click=self.save_project,
                ),
                ft.IconButton(
                    icon=ft.Icons.PLAY_ARROW,
                    tooltip="绘图",
                    on_click=self.draw_chart,
                ),
                ft.IconButton(
                    icon=ft.Icons.DOWNLOAD,
                    tooltip="导出图像",
                    on_click=self.show_export_dialog,
                ),
            ],
        )
        self.views = [
            self._data_view(),
            self._chart_view(),
            self._settings_view(),
            self._fit_view(),
        ]
        self.content_host = ft.Container(content=self.views[0], expand=True, padding=12)
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.change_view,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.TABLE_CHART_OUTLINED, label="数据"),
                ft.NavigationBarDestination(icon=ft.Icons.SHOW_CHART, label="图表"),
                ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="设置"),
                ft.NavigationBarDestination(icon=ft.Icons.FUNCTIONS, label="拟合"),
            ],
        )
        self.page.add(self.content_host)

    def _section_title(self, title: str, subtitle: str = ""):
        controls = [ft.Text(title, size=18, weight=ft.FontWeight.W_600)]
        if subtitle:
            controls.append(ft.Text(subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        return ft.Column(controls, spacing=2)

    def _draw_button(self, label: str = "绘图"):
        return ft.FilledButton(
            content=ft.Text(label),
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.draw_chart,
        )

    def _data_view(self):
        return ft.ListView(
            controls=[
                self._section_title("实验数据", "所有数值使用逗号分隔，不确定度可填单值或逐点列表"),
                self.x_data,
                self.x_uncertainty,
                ft.Divider(),
                ft.Row(
                    [
                        ft.Text("Y 轴曲线", size=16, weight=ft.FontWeight.W_600),
                        ft.Button(
                            content=ft.Text("添加曲线"),
                            icon=ft.Icons.ADD,
                            on_click=self.add_curve,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.curves_column,
                ft.Container(height=4),
                self._draw_button(),
            ],
            spacing=12,
            padding=ft.Padding.only(bottom=12),
            expand=True,
        )

    def _chart_view(self):
        return ft.Column(
            [
                ft.Row(
                    [
                        self._section_title("图表预览"),
                        ft.FilledButton(
                            content=ft.Text("重新绘图"),
                            icon=ft.Icons.REFRESH,
                            on_click=self.draw_chart,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.preview_host,
                self.status,
            ],
            spacing=10,
            expand=True,
        )

    def _settings_view(self):
        return ft.ListView(
            controls=[
                self._section_title("图表设置"),
                self.title,
                self.note,
                ft.ResponsiveRow([self.x_label, self.x_unit], spacing=8, run_spacing=8),
                ft.ResponsiveRow([self.y_label, self.y_unit], spacing=8, run_spacing=8),
                ft.Divider(),
                ft.Text("坐标范围", size=15, weight=ft.FontWeight.W_600),
                ft.ResponsiveRow([self.x_min, self.x_max], spacing=8, run_spacing=8),
                ft.ResponsiveRow([self.y_min, self.y_max], spacing=8, run_spacing=8),
                ft.ResponsiveRow(
                    [self.x_tick_direction, self.y_tick_direction], spacing=8, run_spacing=8
                ),
                ft.ResponsiveRow(
                    [
                        self.precision,
                        ft.Container(
                            col=6,
                            content=ft.Row([self.show_grid, self.show_legend], wrap=True),
                        ),
                    ],
                    spacing=8,
                    run_spacing=8,
                ),
                self._draw_button(),
            ],
            spacing=12,
            padding=ft.Padding.only(bottom=12),
            expand=True,
        )

    def _fit_view(self):
        return ft.Column(
            [
                self._section_title("拟合参数与质量"),
                ft.Container(
                    content=ft.ListView([self.fit_results], padding=12, expand=True),
                    expand=True,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=6,
                ),
            ],
            spacing=10,
            expand=True,
        )

    def change_view(self, event):
        index = event.control.selected_index
        self.content_host.content = self.views[index]
        self.content_host.update()

    def _show_view(self, index: int):
        self.page.navigation_bar.selected_index = index
        self.content_host.content = self.views[index]
        self.page.update()

    def _rebuild_curve_editors(self):
        self.curve_editors = [
            CurveEditor(self, index, curve) for index, curve in enumerate(self.form.curves)
        ]
        self.curves_column.controls = [editor.control for editor in self.curve_editors]

    def add_curve(self, _):
        self.sync_form()
        self.form.add_curve()
        self._rebuild_curve_editors()
        self.curves_column.update()

    def remove_curve(self, index: int):
        try:
            self.sync_form()
            self.form.remove_curve(index)
        except ValueError as exc:
            self.notify(str(exc), error=True)
            return
        self._rebuild_curve_editors()
        self.curves_column.update()

    def sync_form(self):
        self.form.title = self.title.value or ""
        self.form.note = self.note.value or ""
        self.form.x_label = self.x_label.value or ""
        self.form.x_unit = self.x_unit.value or ""
        self.form.y_label = self.y_label.value or ""
        self.form.y_unit = self.y_unit.value or ""
        self.form.x_data = self.x_data.value or ""
        self.form.x_uncertainty = self.x_uncertainty.value or ""
        self.form.x_min = self.x_min.value or ""
        self.form.x_max = self.x_max.value or ""
        self.form.y_min = self.y_min.value or ""
        self.form.y_max = self.y_max.value or ""
        self.form.x_tick_direction = self.x_tick_direction.value or "in"
        self.form.y_tick_direction = self.y_tick_direction.value or "in"
        self.form.precision = self.precision.value or "2"
        self.form.show_grid = bool(self.show_grid.value)
        self.form.show_legend = bool(self.show_legend.value)
        self.form.curves = [editor.to_form() for editor in self.curve_editors]

    def load_form(self):
        self.title.value = self.form.title
        self.note.value = self.form.note
        self.x_label.value = self.form.x_label
        self.x_unit.value = self.form.x_unit
        self.y_label.value = self.form.y_label
        self.y_unit.value = self.form.y_unit
        self.x_data.value = self.form.x_data
        self.x_uncertainty.value = self.form.x_uncertainty
        self.x_min.value = self.form.x_min
        self.x_max.value = self.form.x_max
        self.y_min.value = self.form.y_min
        self.y_max.value = self.form.y_max
        self.x_tick_direction.value = self.form.x_tick_direction
        self.y_tick_direction.value = self.form.y_tick_direction
        self.precision.value = self.form.precision
        self.show_grid.value = self.form.show_grid
        self.show_legend.value = self.form.show_legend
        self._rebuild_curve_editors()
        self.page.update()

    def draw_chart(self, _):
        try:
            self.sync_form()
            image, fits = self.form.render_image(width=960, height=620)
            spec = self.form.build_chart_spec()
        except Exception as exc:
            self.notify(str(exc), error=True)
            return
        self.last_image = image
        self.preview.src = image
        self.preview_host.content = self.preview
        self.fit_results.value = format_fit_results(fits)
        self.status.value = f"{len(spec.x_values)} 个数据点 · {len(spec.curves)} 条曲线 · {len(fits)} 个拟合结果"
        self._show_view(1)

    async def import_data(self, _):
        files = await self.file_picker.pick_files(
            dialog_title="导入实验数据",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv", "xlsx", "xlsm"],
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return
        path, temporary = self._materialize_file(files[0])
        try:
            table = self.form.import_table(path)
            self.load_form()
            self.notify(f"已导入 {len(table.x_values)} 行、{len(table.series)} 组 Y 数据")
        except Exception as exc:
            self.notify(str(exc), error=True)
        finally:
            if temporary:
                path.unlink(missing_ok=True)

    async def open_project(self, _):
        files = await self.file_picker.pick_files(
            dialog_title="打开绘图工程",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["pplot"],
            allow_multiple=False,
            with_data=True,
        )
        if not files:
            return
        path, temporary = self._materialize_file(files[0])
        try:
            self.form = PlotForm.load(path)
            self.load_form()
            self.notify("工程已恢复")
        except Exception as exc:
            self.notify(str(exc), error=True)
        finally:
            if temporary:
                path.unlink(missing_ok=True)

    async def save_project(self, _):
        try:
            self.sync_form()
            with tempfile.TemporaryDirectory() as directory:
                temp_path = Path(directory) / "绘图工程.pplot"
                self.form.save(temp_path)
                data = temp_path.read_bytes()
            saved_path = await self.file_picker.save_file(
                dialog_title="保存绘图工程",
                file_name="绘图工程.pplot",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["pplot"],
                src_bytes=data,
            )
            if saved_path:
                self.notify("工程已保存")
        except Exception as exc:
            self.notify(f"保存失败：{exc}", error=True)

    def show_export_dialog(self, _):
        self.page.show_dialog(self.export_dialog)

    def _close_export_dialog(self, _):
        self.export_dialog.open = False
        self.export_dialog.update()

    async def export_image(self, _):
        image_format = self.export_format.value or "png"
        try:
            self.sync_form()
            image, fits = self.form.render_image(image_format=image_format, width=1600, height=1000, dpi=160)
            saved_path = await self.file_picker.save_file(
                dialog_title="导出图像",
                file_name=f"实验曲线.{image_format}",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=[image_format],
                src_bytes=image,
            )
            if saved_path:
                self.last_image = image if image_format == "png" else self.last_image
                self.fit_results.value = format_fit_results(fits)
                self.notify("图像已导出")
        except Exception as exc:
            self.notify(f"导出失败：{exc}", error=True)
        finally:
            self.export_dialog.open = False
            self.page.update()

    def _materialize_file(self, picked):
        if picked.path:
            return Path(picked.path), False
        if picked.bytes is None:
            raise ValueError("无法读取所选文件")
        suffix = Path(picked.name).suffix
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        try:
            handle.write(picked.bytes)
        finally:
            handle.close()
        return Path(handle.name), True

    def notify(self, message: str, error: bool = False):
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message),
                show_close_icon=True,
                bgcolor=ft.Colors.ERROR_CONTAINER if error else None,
            )
        )


def main(page: ft.Page):
    PlotApplication(page).build()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
