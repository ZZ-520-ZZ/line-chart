from __future__ import annotations

import tempfile
from pathlib import Path

import flet as ft

from app_state import (
    CURVE_COLORS,
    CurveForm,
    PlotForm,
    format_fit_results,
    generate_series_from_text,
)
from plot_core import custom_parameter_names, parse_custom_initial_values


APP_NAME = "Plotforge"
PRIMARY = "#006B68"
PRIMARY_DARK = "#66D4CF"
FIELD_RADIUS = 6
FIT_OPTIONS = (
    ("none", "不拟合"),
    ("linear", "线性拟合"),
    ("quadratic", "二次拟合"),
    ("exponential", "指数拟合"),
    ("custom", "自定义函数拟合"),
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
        self.custom_expression = curve.custom_expression
        self.custom_initial_values = curve.custom_initial_values
        self._previous_fit_type = curve.fit_type if curve.fit_type != "custom" else "none"
        self.label = app._text_field(
            value=curve.label,
            label="图例名称",
            expand=True,
        )
        self.visible = ft.Switch(
            key=f"curve-visible-{index}-{'dark' if app.dark_mode else 'light'}",
            value=curve.visible,
            label="显示",
            adaptive=True,
            label_text_style=ft.TextStyle(
                color=app._foreground(variant=True),
                foreground=ft.Paint(color=app._foreground(variant=True)),
            ),
        )
        self.data = app._text_field(
            value=curve.data,
            label="Y 数据（逗号分隔）",
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.uncertainty = app._text_field(
            value=curve.uncertainty,
            label="Y 不确定度（单值或列表）",
            col={"xs": 12, "sm": 6},
        )
        self.fit_type = app._dropdown(
            value=curve.fit_type,
            label="拟合方式",
            options=_options(FIT_OPTIONS),
            col={"xs": 6, "sm": 3},
            on_select=self._on_fit_selected,
        )
        self.marker = app._dropdown(
            value=curve.marker,
            label="数据点",
            options=_options(MARKER_OPTIONS),
            col={"xs": 6, "sm": 3},
        )
        self.swatches = []
        self.custom_fit_button = ft.OutlinedButton(
            content=ft.Text("编辑自定义函数"),
            icon=ft.Icons.FUNCTIONS,
            on_click=lambda _: self._show_custom_fit_dialog(restore_on_cancel=False),
            style=app._button_style(),
            visible=curve.fit_type == "custom",
        )
        self.color_row = self._build_color_row()
        self.control = ft.Card(
            elevation=0,
            variant=ft.CardVariant.OUTLINED,
            content=ft.Container(
                padding=16,
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
                        self.custom_fit_button,
                        ft.Text("曲线颜色", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        self.color_row,
                    ],
                    spacing=12,
                ),
            ),
        )

    def _on_fit_selected(self, _):
        selected = self.fit_type.value or "none"
        if selected == "custom":
            self.custom_fit_button.visible = True
            self.custom_fit_button.update()
            self._show_custom_fit_dialog(restore_on_cancel=True)
            return
        self._previous_fit_type = selected
        self.custom_fit_button.visible = False
        self.custom_fit_button.update()

    def _show_custom_fit_dialog(self, restore_on_cancel=False):
        expression_field = self.app._text_field(
            label="拟合函数 y =",
            value=self.custom_expression or "a*x+b",
            hint_text="例如：a*sin(b*x+c)",
            autofocus=True,
        )
        initial_values_field = self.app._text_field(
            label="参数初值（可选）",
            value=self.custom_initial_values,
            hint_text="例如：a=1,b=1,c=0；未填写的参数默认为 1",
        )
        error_text = ft.Text("", color=ft.Colors.ERROR, size=12, visible=False)
        confirmed = False

        def close_dialog(_=None):
            dialog.open = False
            if restore_on_cancel and not confirmed:
                self.fit_type.value = self._previous_fit_type
                self.custom_fit_button.visible = False
            dialog.update()
            self.fit_type.update()
            self.custom_fit_button.update()

        def confirm(_):
            nonlocal confirmed
            try:
                expression = expression_field.value or ""
                initial_values = initial_values_field.value or ""
                parameter_names = custom_parameter_names(expression)
                parse_custom_initial_values(initial_values, parameter_names)
            except ValueError as exc:
                error_text.value = str(exc)
                error_text.visible = True
                error_text.update()
                return
            self.custom_expression = expression.strip()
            self.custom_initial_values = initial_values.strip()
            confirmed = True
            self.fit_type.value = "custom"
            self.custom_fit_button.visible = True
            dialog.open = False
            dialog.update()
            self.fit_type.update()
            self.custom_fit_button.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"配置 {self.label.value or f'Y 曲线 {self.index + 1}'} 的自定义拟合"),
            content=ft.Column(
                [
                    expression_field,
                    initial_values_field,
                    ft.Text(
                        "变量使用 x，乘方写作 **。支持 sin、cos、tan、exp、log、sqrt、abs 等函数。",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    error_text,
                ],
                tight=True,
                spacing=12,
            ),
            actions=[
                ft.TextButton(content=ft.Text("取消"), on_click=close_dialog),
                ft.FilledButton(content=ft.Text("确认"), icon=ft.Icons.CHECK, on_click=confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=close_dialog,
        )
        self.app.page.show_dialog(dialog)

    def _build_color_row(self):
        controls = []
        for color in CURVE_COLORS:
            swatch = ft.Container(
                width=32,
                height=32,
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
            custom_expression=self.custom_expression,
            custom_initial_values=self.custom_initial_values,
        )


class PlotApplication:
    def __init__(self, page: ft.Page):
        self.page = page
        self.form = PlotForm()
        self.file_picker = ft.FilePicker()
        self.curve_editors: list[CurveEditor] = []
        self.last_image: bytes | None = None
        self.dark_mode = False
        self._create_controls()

    def _foreground(self, variant: bool = False):
        if self.dark_mode:
            return "#BEC9C7" if variant else "#E0E4E2"
        return "#3F4947" if variant else "#181D1C"

    def _text_style(self, variant: bool = False, **kwargs):
        color = self._foreground(variant)
        return ft.TextStyle(color=color, foreground=ft.Paint(color=color), **kwargs)

    @staticmethod
    def _text_field(**kwargs):
        options = {
            "dense": True,
            "filled": True,
            "fill_color": ft.Colors.SURFACE_CONTAINER_LOWEST,
            "border_radius": FIELD_RADIUS,
            "border_color": ft.Colors.OUTLINE_VARIANT,
            "focused_border_color": PRIMARY,
            "focused_border_width": 2,
            "content_padding": ft.Padding.symmetric(horizontal=14, vertical=12),
        }
        options.update(kwargs)
        return ft.TextField(**options)

    @staticmethod
    def _dropdown(**kwargs):
        options = {
            "dense": True,
            "filled": True,
            "fill_color": ft.Colors.SURFACE_CONTAINER_LOWEST,
            "border_radius": FIELD_RADIUS,
            "border_color": ft.Colors.OUTLINE_VARIANT,
            "focused_border_color": PRIMARY,
            "focused_border_width": 2,
            "content_padding": ft.Padding.symmetric(horizontal=14, vertical=10),
        }
        options.update(kwargs)
        return ft.Dropdown(**options)

    def _create_controls(self):
        self.title = self._text_field(label="图表标题", value=self.form.title)
        self.note = self._text_field(
            label="图表说明",
            value=self.form.note,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.x_label = self._text_field(label="X 轴名称", value=self.form.x_label, col=8)
        self.x_unit = self._text_field(label="X 单位", value=self.form.x_unit, col=4)
        self.y_label = self._text_field(label="Y 轴名称", value=self.form.y_label, col=8)
        self.y_unit = self._text_field(label="Y 单位", value=self.form.y_unit, col=4)
        self.x_data = self._text_field(
            label="X 数据（逗号分隔）",
            value=self.form.x_data,
            multiline=True,
            min_lines=2,
            max_lines=4,
        )
        self.x_uncertainty = self._text_field(
            label="X 不确定度（单值或列表）",
            value=self.form.x_uncertainty,
        )
        self.x_min = self._text_field(label="X 最小值", col=6)
        self.x_max = self._text_field(label="X 最大值", col=6)
        self.y_min = self._text_field(label="Y 最小值", col=6)
        self.y_max = self._text_field(label="Y 最大值", col=6)
        direction_options = _options((("in", "向内"), ("out", "向外"), ("inout", "双向")))
        self.x_tick_direction = self._dropdown(
            label="X 刻度方向", value="in", options=direction_options, col=6
        )
        self.y_tick_direction = self._dropdown(
            label="Y 刻度方向",
            value="in",
            options=_options((("in", "向内"), ("out", "向外"), ("inout", "双向"))),
            col=6,
        )
        self.precision = self._dropdown(
            label="小数位数",
            value=self.form.precision,
            options=_options(tuple((str(value), str(value)) for value in range(11))),
            col=6,
        )
        self.show_grid = ft.Switch(
            value=True,
            label="显示网格",
            adaptive=True,
            label_text_style=self._text_style(variant=True),
        )
        self.show_legend = ft.Switch(
            value=True,
            label="显示图例",
            adaptive=True,
            label_text_style=self._text_style(variant=True),
        )
        self.curves_column = ft.Column(spacing=10)
        self.preview = ft.Image(
            src="",
            fit=ft.BoxFit.CONTAIN,
            expand=True,
            semantics_label="实验曲线预览",
        )
        self.preview_title = ft.Text(
            key=f"preview-title-{'dark' if self.dark_mode else 'light'}",
            value="等待绘图",
            style=self._text_style(size=16, weight=ft.FontWeight.W_600),
        )
        self.preview_placeholder = ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.SHOW_CHART, size=36, color=PRIMARY),
                    width=64,
                    height=64,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    border_radius=32,
                ),
                self.preview_title,
                ft.Text("输入实验数据后点击绘图", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        self.preview_host = ft.Container(
            content=self.preview_placeholder,
            expand=True,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=6,
            padding=8,
        )
        self.fit_results = ft.Text(
            "绘制并选择拟合方式后，参数将显示在这里。",
            selectable=True,
            font_family="NotoSansSC",
            color=self._foreground(variant=True),
        )
        self.status = ft.Text("尚未绘图", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.theme_button = ft.IconButton(
            icon=ft.Icons.DARK_MODE_OUTLINED,
            tooltip="切换深色模式",
            on_click=self.toggle_theme,
        )
        self.export_format = self._dropdown(
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
        self.series_type = self._dropdown(
            value="arithmetic",
            label="数列类型",
            options=_options((("arithmetic", "等差数列"), ("geometric", "等比数列"))),
            col={"xs": 12, "sm": 6},
        )
        self.series_target = self._dropdown(
            value="x",
            label="写入目标",
            options=[],
            col={"xs": 12, "sm": 6},
        )
        self.series_start = self._text_field(
            value="0",
            label="起始值",
            col={"xs": 12, "sm": 4},
        )
        self.series_end = self._text_field(
            value="10",
            label="结束值",
            col={"xs": 12, "sm": 4},
        )
        self.series_parameter = self._text_field(
            value="1",
            label="步长 / 公比",
            col={"xs": 12, "sm": 4},
        )
        self.series_preview = self._text_field(
            value="尚未生成",
            label="生成预览",
            read_only=True,
            multiline=True,
            min_lines=3,
            max_lines=5,
        )
        self.series_status = ft.Text(
            "最多生成 1000 个数据点",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._rebuild_curve_editors()

    @staticmethod
    def _button_style(primary: bool = False):
        if primary:
            return ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: PRIMARY,
                    ft.ControlState.HOVERED: "#005B58",
                    ft.ControlState.PRESSED: "#004D4A",
                    ft.ControlState.DISABLED: ft.Colors.SURFACE_CONTAINER_HIGHEST,
                },
                color={
                    ft.ControlState.DEFAULT: "#FFFFFF",
                    ft.ControlState.DISABLED: ft.Colors.ON_SURFACE_VARIANT,
                },
                shape=ft.RoundedRectangleBorder(radius=FIELD_RADIUS),
                padding=ft.Padding.symmetric(horizontal=18, vertical=13),
            )
        return ft.ButtonStyle(
            color=ft.Colors.ON_SURFACE,
            side=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            shape=ft.RoundedRectangleBorder(radius=FIELD_RADIUS),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        )

    @staticmethod
    def _theme(dark: bool = False):
        scheme = ft.ColorScheme(
            primary=PRIMARY_DARK if dark else PRIMARY,
            on_primary="#003735" if dark else "#FFFFFF",
            primary_container="#00504E" if dark else "#C6EFEC",
            on_primary_container="#8CF2ED" if dark else "#00201F",
            secondary="#E8C453" if dark else "#725B00",
            on_secondary="#3C2F00" if dark else "#FFFFFF",
            secondary_container="#564500" if dark else "#FFE080",
            on_secondary_container="#FFE48F" if dark else "#241A00",
            error="#FFB4AB" if dark else "#BA1A1A",
            on_error="#690005" if dark else "#FFFFFF",
            error_container="#93000A" if dark else "#FFDAD6",
            on_error_container="#FFDAD6" if dark else "#410002",
            surface="#6C7674" if dark else "#F7FAF9",
            on_surface="#FFFFFF" if dark else "#181D1C",
            on_surface_variant="#F1F4F3" if dark else "#3F4947",
            outline="#E0E4E2" if dark else "#6F7977",
            outline_variant="#46504E" if dark else "#BEC9C7",
            surface_container_lowest="#6C7674" if dark else "#FFFFFF",
            surface_container_low="#626C6A" if dark else "#F1F4F3",
            surface_container="#596361" if dark else "#EBEEED",
            surface_container_high="#505A58" if dark else "#E5E9E7",
            surface_container_highest="#46504E" if dark else "#DFE3E1",
        )
        text_theme = ft.TextTheme(
            title_large=ft.TextStyle(
                size=20, weight=ft.FontWeight.W_600, color=scheme.on_surface
            ),
            title_medium=ft.TextStyle(
                size=16, weight=ft.FontWeight.W_600, color=scheme.on_surface
            ),
            body_large=ft.TextStyle(size=15, color=scheme.on_surface),
            body_medium=ft.TextStyle(size=14, color=scheme.on_surface),
            body_small=ft.TextStyle(size=12, color=scheme.on_surface_variant),
            label_large=ft.TextStyle(
                size=14, weight=ft.FontWeight.W_600, color=scheme.on_surface
            ),
            label_medium=ft.TextStyle(size=12, color=scheme.on_surface_variant),
        )
        return ft.Theme(
            use_material3=True,
            font_family="NotoSansSC",
            color_scheme=scheme,
            scaffold_bgcolor=scheme.surface,
            appbar_theme=ft.AppBarTheme(
                bgcolor=scheme.surface_container_lowest,
                color=scheme.on_surface,
                elevation=0,
                elevation_on_scroll=1,
                toolbar_height=60,
                title_text_style=ft.TextStyle(
                    size=20, weight=ft.FontWeight.W_600, color=scheme.on_surface
                ),
            ),
            card_theme=ft.CardTheme(
                color=scheme.surface_container_lowest,
                elevation=0,
                shape=ft.RoundedRectangleBorder(radius=8),
                margin=0,
            ),
            navigation_bar_theme=ft.NavigationBarTheme(
                bgcolor=scheme.surface_container_lowest,
                indicator_color=scheme.primary_container,
                height=68,
                label_text_style={
                    ft.ControlState.SELECTED: ft.TextStyle(
                        size=12,
                        weight=ft.FontWeight.W_600,
                        color=scheme.on_surface,
                    ),
                    ft.ControlState.DEFAULT: ft.TextStyle(
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=scheme.on_surface_variant,
                    ),
                },
                indicator_shape=ft.RoundedRectangleBorder(radius=6),
            ),
            filled_button_theme=ft.FilledButtonTheme(style=PlotApplication._button_style(True)),
            outlined_button_theme=ft.OutlinedButtonTheme(style=PlotApplication._button_style()),
            icon_theme=ft.IconTheme(color=scheme.on_surface_variant),
            text_theme=text_theme,
            primary_text_theme=text_theme,
        )

    def build(self):
        self.page.title = APP_NAME
        self.page.fonts = {"NotoSansSC": "fonts/NotoSansSC-VF.ttf"}
        self.page.theme = self._theme()
        self.page.dark_theme = self._theme(dark=True)
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 1024
        self.page.window.height = 720
        self.page.window.min_width = 360
        self.page.window.min_height = 560
        self.page.padding = ft.Padding.all(0)
        self.app_title = ft.Text(
            key=f"app-title-{'dark' if self.dark_mode else 'light'}",
            value=APP_NAME,
            style=self._text_style(size=20, weight=ft.FontWeight.W_600),
        )
        self.page.appbar = ft.AppBar(
            title=self.app_title,
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
                self.theme_button,
            ],
        )
        self.views = [
            self._data_view(),
            self._series_view(),
            self._chart_view(),
            self._settings_view(),
            self._fit_view(),
        ]
        self.content_host = ft.Container(
            content=self.views[0],
            expand=True,
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            alignment=ft.Alignment.TOP_CENTER,
        )
        self.page.navigation_bar = self._navigation_bar()
        self.page.add(self.content_host)

    def _navigation_bar(self, selected_index: int = 0):
        return ft.NavigationBar(
            key=f"navigation-{'dark' if self.dark_mode else 'light'}",
            selected_index=selected_index,
            on_change=self.change_view,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.TABLE_CHART_OUTLINED, label="数据"),
                ft.NavigationBarDestination(icon=ft.Icons.FORMAT_LIST_NUMBERED, label="数列"),
                ft.NavigationBarDestination(icon=ft.Icons.SHOW_CHART, label="图表"),
                ft.NavigationBarDestination(icon=ft.Icons.TUNE, label="设置"),
                ft.NavigationBarDestination(icon=ft.Icons.FUNCTIONS, label="拟合"),
            ],
        )

    def _section_title(self, icon, title: str, subtitle: str = ""):
        title_control = ft.Text(
            key=f"section-{title}-{'dark' if self.dark_mode else 'light'}",
            value=title,
            style=self._text_style(size=20, weight=ft.FontWeight.W_600),
        )
        text_controls = [title_control]
        if subtitle:
            text_controls.append(ft.Text(subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT))
        return ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, size=22, color=PRIMARY),
                    width=40,
                    height=40,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                    border_radius=6,
                ),
                ft.Column(text_controls, spacing=2, expand=True),
            ],
            spacing=12,
        )

    def _draw_button(self, label: str = "绘图"):
        return ft.FilledButton(
            content=ft.Text(label),
            icon=ft.Icons.PLAY_ARROW,
            on_click=self.draw_chart,
            style=self._button_style(True),
        )

    def _y_curves_title(self):
        control = ft.Text(
            key=f"curves-title-{'dark' if self.dark_mode else 'light'}",
            value="Y 轴曲线",
            style=self._text_style(size=16, weight=ft.FontWeight.W_600),
        )
        return control

    def toggle_theme(self, _):
        self.sync_form()
        self.dark_mode = not self.dark_mode
        selected_index = self.page.navigation_bar.selected_index or 0
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark_mode else ft.ThemeMode.LIGHT
        self.theme_button.icon = ft.Icons.LIGHT_MODE_OUTLINED if self.dark_mode else ft.Icons.DARK_MODE_OUTLINED
        self.theme_button.tooltip = "切换浅色模式" if self.dark_mode else "切换深色模式"
        self.page.update()
        self.app_title = ft.Text(
            key=f"app-title-{'dark' if self.dark_mode else 'light'}",
            value=APP_NAME,
            style=self._text_style(size=20, weight=ft.FontWeight.W_600),
        )
        self.page.appbar.title = self.app_title
        self.page.navigation_bar = self._navigation_bar(selected_index)
        self._rebuild_curve_editors()
        self.views = [
            self._data_view(),
            self._series_view(),
            self._chart_view(),
            self._settings_view(),
            self._fit_view(),
        ]
        self.content_host.content = self.views[selected_index]
        self.page.update()

    def _data_view(self):
        return ft.ListView(
            controls=[
                self._section_title(ft.Icons.TABLE_CHART_OUTLINED, "实验数据", "所有数值使用逗号分隔，不确定度可填单值或逐点列表"),
                self.x_data,
                self.x_uncertainty,
                ft.Divider(),
                ft.Row(
                    [
                        self._y_curves_title(),
                        ft.OutlinedButton(
                            content=ft.Text("添加曲线"),
                            icon=ft.Icons.ADD,
                            on_click=self.add_curve,
                            style=self._button_style(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.curves_column,
                ft.Container(height=4),
                self._draw_button(),
            ],
            spacing=16,
            padding=ft.Padding.only(bottom=16),
            expand=True,
        )

    def _chart_view(self):
        return ft.Column(
            [
                ft.Row(
                    [
                        self._section_title(ft.Icons.SHOW_CHART, "图表预览"),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.REFRESH,
                                    tooltip="重新绘图",
                                    on_click=self.draw_chart,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DOWNLOAD,
                                    tooltip="导出图像",
                                    on_click=self.show_export_dialog,
                                ),
                            ],
                            spacing=2,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self.preview_host,
                ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, size=16), self.status], spacing=6),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            expand=True,
        )

    def _series_view(self):
        return ft.ListView(
            controls=[
                self._section_title(
                    ft.Icons.FORMAT_LIST_NUMBERED,
                    "数列生成",
                    "生成等差或等比数列，并写入 X 数据或任意 Y 曲线",
                ),
                ft.ResponsiveRow(
                    [self.series_type, self.series_target],
                    spacing=8,
                    run_spacing=8,
                ),
                ft.ResponsiveRow(
                    [self.series_start, self.series_end, self.series_parameter],
                    spacing=8,
                    run_spacing=8,
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            content=ft.Text("预览"),
                            icon=ft.Icons.PREVIEW,
                            on_click=self.preview_series,
                            style=self._button_style(),
                            expand=True,
                        ),
                        ft.FilledButton(
                            content=ft.Text("生成并写入"),
                            icon=ft.Icons.INPUT,
                            on_click=self.apply_series,
                            style=self._button_style(True),
                            expand=True,
                        ),
                    ],
                    spacing=10,
                ),
                self.series_preview,
                ft.Row(
                    [ft.Icon(ft.Icons.INFO_OUTLINE, size=16), self.series_status],
                    spacing=6,
                ),
            ],
            spacing=16,
            padding=ft.Padding.only(bottom=16),
            expand=True,
        )

    def _settings_view(self):
        return ft.ListView(
            controls=[
                self._section_title(ft.Icons.TUNE, "图表设置", "调整标题、坐标轴与显示方式"),
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
            spacing=16,
            padding=ft.Padding.only(bottom=16),
            expand=True,
        )

    def _fit_view(self):
        return ft.Column(
            [
                self._section_title(ft.Icons.FUNCTIONS, "拟合参数与质量", "显示拟合方程、参数、R² 与相关系数"),
                ft.Container(
                    content=ft.ListView([self.fit_results], padding=12, expand=True),
                    expand=True,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=6,
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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
        self._refresh_series_targets()

    def _refresh_series_targets(self):
        options = [("x", "X 数据")]
        options.extend(
            (f"curve:{index}", f"Y 曲线 {index + 1} · {curve.label or '未命名'}")
            for index, curve in enumerate(self.form.curves)
        )
        valid_targets = {key for key, _ in options}
        self.series_target.options = _options(tuple(options))
        if self.series_target.value not in valid_targets:
            self.series_target.value = "x"

    def _series_values(self):
        return generate_series_from_text(
            self.series_type.value or "arithmetic",
            self.series_start.value or "",
            self.series_end.value or "",
            self.series_parameter.value or "",
        )

    @staticmethod
    def _series_preview_text(values):
        shown = ", ".join(f"{float(value):.12g}" for value in values[:12])
        if len(values) > 12:
            shown += ", ..."
        return shown

    def preview_series(self, _):
        try:
            values = self._series_values()
        except ValueError as exc:
            self.notify(str(exc), error=True)
            return
        self.series_preview.value = self._series_preview_text(values)
        self.series_status.value = f"已生成 {len(values)} 个数据点，尚未写入"
        self.series_preview.update()
        self.series_status.update()

    def apply_series(self, _):
        try:
            self.sync_form()
            values = self.form.apply_generated_series(
                self.series_target.value or "",
                self.series_type.value or "arithmetic",
                self.series_start.value or "",
                self.series_end.value or "",
                self.series_parameter.value or "",
            )
        except ValueError as exc:
            self.notify(str(exc), error=True)
            return

        target = self.series_target.value or "x"
        if target == "x":
            self.x_data.value = self.form.x_data
            target_name = "X 数据"
        else:
            curve_index = int(target.split(":", 1)[1])
            self.curve_editors[curve_index].data.value = self.form.curves[curve_index].data
            target_name = self.form.curves[curve_index].label or f"Y 曲线 {curve_index + 1}"
        self.series_preview.value = self._series_preview_text(values)
        self.series_status.value = f"已将 {len(values)} 个数据点写入 {target_name}"
        self.series_preview.update()
        self.series_status.update()
        self.notify(f"数列已写入 {target_name}")

    def add_curve(self, _):
        self.sync_form()
        self.form.add_curve()
        self._rebuild_curve_editors()
        self.curves_column.update()
        self.series_target.update()

    def remove_curve(self, index: int):
        try:
            self.sync_form()
            self.form.remove_curve(index)
        except ValueError as exc:
            self.notify(str(exc), error=True)
            return
        self._rebuild_curve_editors()
        self.curves_column.update()
        self.series_target.update()

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
        self._show_view(2)

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
