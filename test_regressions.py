import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

DEFAULT_TOOL_PATH = Path(__file__).with_name("绘图工具1.0.py")


def load_tool_module():
    tool_path = Path(os.environ.get("PLOT_TOOL_PATH", DEFAULT_TOOL_PATH))
    if str(tool_path.parent) not in sys.path:
        sys.path.insert(0, str(tool_path.parent))
    spec = importlib.util.spec_from_file_location("physics_plot_tool", tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Value:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class Entry(Value):
    def delete(self, *args):
        self.value = ""

    def insert(self, index, value):
        self.value = str(value)


class Text(Entry):
    def get(self, *args):
        return self.value

    def config(self, **kwargs):
        pass


class Frame:
    def __init__(self):
        self.destroyed = False
        self.label = None

    def destroy(self):
        self.destroyed = True

    def config(self, **kwargs):
        self.label = kwargs.get("text", self.label)


class Combo:
    def __init__(self):
        self.values = []
        self.index = -1
        self.text = ""

    def __setitem__(self, key, value):
        if key == "values":
            self.values = list(value)

    def current(self, index=None):
        if index is None:
            return self.index
        self.index = index
        self.text = self.values[index] if index >= 0 else ""

    def set(self, value):
        self.text = value
        self.index = self.values.index(value) if value in self.values else -1

    def selection_clear(self):
        pass


class Canvas:
    def __init__(self):
        self.draw_calls = 0
        self.draw_idle_calls = 0

    def draw(self):
        self.draw_calls += 1

    def draw_idle(self):
        self.draw_idle_calls += 1

    def get_tk_widget(self):
        return self

    def winfo_width(self):
        return 600

    def winfo_height(self):
        return 400


def make_plot_tool(module, note="实验说明"):
    tool = module.PhysicsPlotTool.__new__(module.PhysicsPlotTool)
    tool.fig = module.Figure(figsize=(6, 4), dpi=100)
    tool.ax = tool.fig.add_subplot(111)
    tool.canvas = Canvas()
    tool.title_entry = Entry("测试图")
    tool.note_text = Text(note)
    tool.x_label_entry = Entry("时间")
    tool.y_label_entry = Entry("位移")
    tool.x_unit_entry = Entry("s")
    tool.y_unit_entry = Entry("m")
    tool.x_data_entry = Text("1,2,3")
    tool.x_uncertainty_entry = Entry("")
    tool.x_min_entry = Entry("")
    tool.x_max_entry = Entry("")
    tool.y_min_entry = Entry("")
    tool.y_max_entry = Entry("")
    tool.x_tick_dir = Value("in")
    tool.y_tick_dir = Value("in")
    tool.grid_var = Value(True)
    tool.legend_var = Value(True)
    tool.precision_var = Value(1)
    tool.curves = [
        {
            "id": 11,
            "legend_entry": Entry("A"),
            "data_entry": Text("10,20,30"),
            "uncertainty_entry": Entry(""),
            "fit_var": Value("不拟合"),
            "color_var": Value("#ff0000"),
            "show_var": Value(True),
            "marker": "o",
        },
        {
            "id": 22,
            "legend_entry": Entry("B"),
            "data_entry": Text("40,50,60"),
            "uncertainty_entry": Entry(""),
            "fit_var": Value("不拟合"),
            "color_var": Value("#0000ff"),
            "show_var": Value(True),
            "marker": "s",
        },
    ]
    tool.annotation = tool.ax.annotate("", xy=(0, 0))
    tool.annotation.set_visible(False)
    tool.fit_result_text = Text("")
    return tool


def series_probe(args):
    module = load_tool_module()
    errors = []
    module.messagebox.showerror = lambda title, message: errors.append(message)
    tool = module.PhysicsPlotTool.__new__(module.PhysicsPlotTool)
    tool.start_entry = Entry(args.start)
    tool.end_entry = Entry(args.end)
    tool.step_entry = Entry(args.step)
    tool.series_var = Value(args.kind)
    tool.precision_var = Value(3)
    tool.preview_text = Text("")
    tool.x_data_entry = Text("")
    tool.target_var = Value("x")
    tool.curves = []
    try:
        tool.generate_series()
        print(json.dumps({"data": tool.x_data_entry.value, "errors": errors}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"exception": type(exc).__name__, "message": str(exc)}, ensure_ascii=False))
        return 2


class PlotToolRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_tool_module()

    def setUp(self):
        self.errors = []
        self.infos = []
        self.original_showerror = self.module.messagebox.showerror
        self.original_showinfo = self.module.messagebox.showinfo
        self.original_save_dialog = self.module.filedialog.asksaveasfilename
        self.module.messagebox.showerror = lambda title, message: self.errors.append(message)
        self.module.messagebox.showinfo = lambda title, message: self.infos.append(message)

    def tearDown(self):
        self.module.messagebox.showerror = self.original_showerror
        self.module.messagebox.showinfo = self.original_showinfo
        self.module.filedialog.asksaveasfilename = self.original_save_dialog

    def run_series(self, kind, start, end, step, timeout=1.5):
        command = [
            sys.executable,
            str(Path(__file__)),
            "--series-probe",
            kind,
            str(start),
            str(end),
            str(step),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        return completed.returncode, payload

    def test_plot_preserves_original_y_values(self):
        tool = make_plot_tool(self.module)
        tool.plot_graph()
        self.assertEqual(list(tool.ax.lines[0].get_ydata()), [10.0, 20.0, 30.0])
        self.assertEqual(list(tool.ax.lines[1].get_ydata()), [40.0, 50.0, 60.0])

    def test_annotation_survives_plot_and_uses_actual_data_point(self):
        tool = make_plot_tool(self.module)
        tool.plot_graph()
        self.assertIn(tool.annotation, tool.ax.texts)
        line = tool.ax.lines[0]
        line.contains = lambda event: (True, {"ind": [1]})
        event = type("Event", (), {"inaxes": tool.ax, "xdata": 1.7, "ydata": 19.2})()
        tool.on_hover(event)
        self.assertEqual(tool.annotation.xy, (2.0, 20.0))
        self.assertEqual(tool.annotation.get_text(), "(2.0, 20.0)")
        self.assertEqual(tool.canvas.draw_calls, 1)
        self.assertEqual(tool.canvas.draw_idle_calls, 1)

    def test_note_is_rendered(self):
        tool = make_plot_tool(self.module, note="自由落体实验")
        tool.plot_graph()
        self.assertIn("自由落体实验", [text.get_text() for text in tool.ax.texts])

    def test_deleting_curve_preserves_custom_legends(self):
        tool = self.module.PhysicsPlotTool.__new__(self.module.PhysicsPlotTool)
        first = {"id": 1, "frame": Frame(), "legend_entry": Entry("保留A")}
        middle = {"id": 2, "frame": Frame(), "legend_entry": Entry("删除B")}
        last = {"id": 3, "frame": Frame(), "legend_entry": Entry("保留C")}
        tool.curves = [first, middle, last]
        tool.curve_frames = [item["frame"] for item in tool.curves]
        tool.refresh_target_combo = lambda: None
        tool.remove_curve_by_id(2)
        self.assertEqual([c["legend_entry"].get() for c in tool.curves], ["保留A", "保留C"])

    def test_target_selection_tracks_stable_curve_id(self):
        tool = self.module.PhysicsPlotTool.__new__(self.module.PhysicsPlotTool)
        tool.curves = [{"id": 101}, {"id": 202}]
        tool.target_var = Value("y:202")
        tool.target_combo = Combo()
        tool.refresh_target_combo()
        self.assertEqual(tool.target_combo.current(), 1)
        tool.curves.pop()
        tool.refresh_target_combo()
        self.assertEqual(tool.target_var.get(), "x")
        self.assertEqual(tool.target_combo.current(), -1)

    def test_invalid_axis_limit_reports_error(self):
        tool = make_plot_tool(self.module)
        tool.x_min_entry = Entry("abc")
        tool.plot_graph()
        self.assertTrue(any("X轴" in message for message in self.errors))
        self.assertEqual(len(tool.ax.lines), 0)

    def test_non_finite_experiment_data_is_rejected(self):
        for data, target in (("0,nan,2", "x"), ("10,inf,30", "y"), ("10,-inf,30", "y")):
            with self.subTest(data=data, target=target):
                self.errors.clear()
                tool = make_plot_tool(self.module)
                if target == "x":
                    tool.x_data_entry = Text(data)
                else:
                    tool.curves[0]["data_entry"] = Text(data)
                tool.plot_graph()
                self.assertTrue(any("有限" in message for message in self.errors))
                self.assertEqual(len(tool.ax.lines), 0)

    def test_precision_text_validation_interface(self):
        core_path = Path(os.environ.get("PLOT_TOOL_PATH", DEFAULT_TOOL_PATH)).with_name("plot_core.py")
        self.assertTrue(core_path.exists(), "应将纯校验逻辑提取到plot_core.py")
        core = sys.modules["plot_core"]
        for valid in ("", "0", "5", "10"):
            self.assertTrue(core.validate_precision_text(valid))
        for invalid in ("-1", "11", "1.5", "abc", " "):
            self.assertFalse(core.validate_precision_text(invalid))
        self.assertEqual(core.parse_precision("7"), 7)
        with self.assertRaises(ValueError):
            core.parse_precision("abc")

    def test_plot_core_render_interface_enforces_invariants(self):
        core = sys.modules["plot_core"]
        figure = self.module.Figure(figsize=(4, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = core.ChartSpec(
            x_values=[0, 1, 2],
            curves=[core.CurveSpec([1, 3, 5], "线性数据", "#d62728", "o")],
            title="核心模块测试",
            precision="2")
        result = core.render_chart(axis, spec)
        self.assertEqual(list(axis.lines[0].get_ydata()), [1, 3, 5])
        self.assertIn(result.annotation, axis.texts)

        invalid = core.ChartSpec(
            x_values=[0, float("nan")],
            curves=[core.CurveSpec([1, 2], "非法数据", "#000000", "o")])
        with self.assertRaisesRegex(ValueError, "有限"):
            core.render_chart(axis, invalid)

    def test_save_failure_is_reported_without_callback_exception(self):
        tool = make_plot_tool(self.module)
        self.module.filedialog.asksaveasfilename = lambda **kwargs: "Z:/不可写/图.png"

        def fail_save(*args, **kwargs):
            raise OSError("拒绝访问")

        tool.fig.savefig = fail_save
        tool.save_plot()
        self.assertTrue(any("保存失败" in message and "拒绝访问" in message for message in self.errors))
        self.assertEqual(self.infos, [])

    def test_mousewheel_handling_does_not_modify_global_bindings(self):
        source_path = Path(os.environ.get("PLOT_TOOL_PATH", DEFAULT_TOOL_PATH))
        source = source_path.read_text(encoding="utf-8")
        self.assertNotIn(".bind_all(", source)
        self.assertNotIn(".unbind_all(", source)

    def test_one_sided_axis_limit_is_applied(self):
        tool = make_plot_tool(self.module)
        tool.x_min_entry = Entry("0")
        tool.plot_graph()
        self.assertAlmostEqual(tool.ax.get_xlim()[0], 0.0)

    def test_arithmetic_zero_step_is_rejected_without_exception(self):
        returncode, payload = self.run_series("arithmetic", 0, 10, 0)
        self.assertEqual(returncode, 0)
        self.assertTrue(payload["errors"])
        self.assertIn("步长", payload["errors"][0])

    def test_huge_arithmetic_series_is_rejected_before_allocation(self):
        started = time.perf_counter()
        with self.assertRaisesRegex(ValueError, "超过1000个"):
            self.module.generate_series_values("arithmetic", 0, 1, 1e-12)
        self.assertLess(time.perf_counter() - started, 0.1)

    def test_dangerous_geometric_cases_return_promptly(self):
        cases = [(0, 10, 2), (-1, 10, 2), (0, 0, 0), (-1, -10, -1)]
        for start, end, ratio in cases:
            with self.subTest(case=(start, end, ratio)):
                returncode, payload = self.run_series("geometric", start, end, ratio)
                self.assertEqual(returncode, 0)
                self.assertTrue(payload["errors"] or payload["data"])

    def test_valid_series_groups(self):
        cases = [
            ("arithmetic", 0, 1, 0.25, "0.000,0.250,0.500,0.750,1.000"),
            ("arithmetic", 3, -1, -1, "3.000,2.000,1.000,0.000,-1.000"),
            ("geometric", 1, 16, 2, "1.000,2.000,4.000,8.000,16.000"),
            ("geometric", 16, 1, 0.5, "16.000,8.000,4.000,2.000,1.000"),
        ]
        for kind, start, end, step, expected in cases:
            with self.subTest(case=(kind, start, end, step)):
                returncode, payload = self.run_series(kind, start, end, step)
                self.assertEqual(returncode, 0)
                self.assertEqual(payload["errors"], [])
                self.assertEqual(payload["data"], expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--series-probe", action="store_true")
    parser.add_argument("kind", nargs="?")
    parser.add_argument("start", nargs="?")
    parser.add_argument("end", nargs="?")
    parser.add_argument("step", nargs="?")
    parsed = parser.parse_args()
    if parsed.series_probe:
        raise SystemExit(series_probe(parsed))
    unittest.main(argv=[sys.argv[0]], verbosity=2)
