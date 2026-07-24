import sys
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.container import ErrorbarContainer
from matplotlib.figure import Figure

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from plot_core import (
    ChartSpec,
    CurveSpec,
    custom_parameter_names,
    parse_custom_initial_values,
    parse_uncertainty_text,
    render_chart,
)


class PlotCoreFeatureTests(unittest.TestCase):
    def test_axes_cross_at_data_origin_when_zero_is_visible(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[-1, 0, 1],
            curves=[CurveSpec(
                values=[-2, 0, 2],
                label="origin",
                color="#d62728",
                marker="o")],
            show_grid=False,
            show_legend=False)

        render_chart(axis, spec)

        self.assertEqual(axis.spines["left"].get_position(), ("data", 0))
        self.assertEqual(axis.spines["bottom"].get_position(), ("data", 0))
        self.assertEqual(axis.xaxis.label.get_position(), (0.5, -0.1))
        self.assertEqual(axis.yaxis.label.get_position(), (-0.1, 0.5))

    def test_axes_remain_at_frame_edges_when_zero_is_outside_view(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[1, 2, 3],
            curves=[CurveSpec(
                values=[4, 5, 6],
                label="positive range",
                color="#1f77b4",
                marker="s")],
            show_grid=False,
            show_legend=False)

        render_chart(axis, spec)

        self.assertEqual(axis.spines["left"].get_position(), ("outward", 0))
        self.assertEqual(axis.spines["bottom"].get_position(), ("outward", 0))

    def test_both_axes_remain_at_edges_when_only_one_zero_axis_is_visible(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[-1, 0, 1],
            curves=[CurveSpec(
                values=[4, 5, 6],
                label="partial origin range",
                color="#2ca02c",
                marker="^")],
            show_grid=False,
            show_legend=False)

        render_chart(axis, spec)

        self.assertEqual(axis.spines["left"].get_position(), ("outward", 0))
        self.assertEqual(axis.spines["bottom"].get_position(), ("outward", 0))

    def test_uncertainty_text_supports_scalar_or_point_values(self):
        self.assertEqual(parse_uncertainty_text("0.2", 3, "Y不确定度"), [0.2, 0.2, 0.2])
        self.assertEqual(parse_uncertainty_text("0.1,0.2,0.3", 3, "Y不确定度"), [0.1, 0.2, 0.3])
        self.assertIsNone(parse_uncertainty_text("", 3, "Y不确定度"))
        with self.assertRaisesRegex(ValueError, "非负"):
            parse_uncertainty_text("0.1,-0.2,0.3", 3, "Y不确定度")
        with self.assertRaisesRegex(ValueError, "数量"):
            parse_uncertainty_text("0.1,0.2", 3, "Y不确定度")

    def test_linear_fit_with_uncertainty_returns_physics_results(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 1, 2, 3],
            x_errors=[0.05, 0.05, 0.05, 0.05],
            curves=[CurveSpec(
                values=[1, 3, 5, 7],
                errors=[0.1, 0.1, 0.1, 0.1],
                label="匀速实验",
                color="#d62728",
                marker="o",
                fit_type="linear")])

        result = render_chart(axis, spec)

        self.assertTrue(any(isinstance(item, ErrorbarContainer) for item in axis.containers))
        self.assertEqual(list(axis.lines[0].get_ydata()), [1, 3, 5, 7])
        self.assertEqual(len(result.fit_results), 1)
        fit = result.fit_results[0]
        self.assertAlmostEqual(fit.parameters["slope"], 2.0, places=10)
        self.assertAlmostEqual(fit.parameters["intercept"], 1.0, places=10)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=10)
        self.assertAlmostEqual(fit.correlation, 1.0, places=10)

    def test_quadratic_fit_recovers_known_parameters(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[-2, -1, 0, 1, 2],
            curves=[CurveSpec(
                values=[17, 6, 1, 2, 9],
                label="非线性实验",
                color="#2ca02c",
                marker="s",
                fit_type="quadratic")])

        result = render_chart(axis, spec)

        fit = result.fit_results[0]
        self.assertAlmostEqual(fit.parameters["quadratic"], 3.0, places=10)
        self.assertAlmostEqual(fit.parameters["linear"], -2.0, places=10)
        self.assertAlmostEqual(fit.parameters["constant"], 1.0, places=10)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=10)

    def test_exponential_fit_recovers_known_parameters(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 1, 2, 3],
            curves=[CurveSpec(
                values=[2.0, 3.2974425414, 5.4365636569, 8.9633781407],
                label="指数实验",
                color="#ff7f0e",
                marker="^",
                fit_type="exponential")])

        result = render_chart(axis, spec)

        fit = result.fit_results[0]
        self.assertAlmostEqual(fit.parameters["amplitude"], 2.0, places=8)
        self.assertAlmostEqual(fit.parameters["rate"], 0.5, places=8)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=8)
        self.assertAlmostEqual(fit.correlation, 1.0, places=8)

    def test_custom_fit_recovers_linear_parameters(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[-2, -1, 0, 1, 2],
            curves=[CurveSpec(
                values=[-3, -1, 1, 3, 5],
                label="自定义线性实验",
                color="#0072B2",
                marker="o",
                fit_type="custom",
                custom_expression="a*x+b",
                custom_initial_values={"a": 1.0, "b": 0.0})])

        result = render_chart(axis, spec)

        fit = result.fit_results[0]
        self.assertEqual(fit.equation, "y = a*x+b")
        self.assertAlmostEqual(fit.parameters["a"], 2.0, places=8)
        self.assertAlmostEqual(fit.parameters["b"], 1.0, places=8)
        self.assertAlmostEqual(fit.r_squared, 1.0, places=10)

    def test_custom_fit_accepts_exact_initial_parameters(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 1, 2],
            curves=[CurveSpec(
                values=[1, 3, 5],
                label="精确初值实验",
                color="#009E73",
                marker="s",
                fit_type="custom",
                custom_expression="a*x+b",
                custom_initial_values={"a": 2.0, "b": 1.0})])

        result = render_chart(axis, spec)

        self.assertEqual(result.fit_results[0].parameters, {"a": 2.0, "b": 1.0})
        self.assertEqual(result.fit_results[0].r_squared, 1.0)

    def test_custom_fit_recovers_exponential_parameters(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 0.5, 1, 1.5, 2, 2.5],
            curves=[CurveSpec(
                values=[2.0, 2.5680508334, 3.2974425414, 4.2340000332,
                        5.4365636569, 6.9806859149],
                label="自定义指数实验",
                color="#D55E00",
                marker="^",
                fit_type="custom",
                custom_expression="a*exp(b*x)",
                custom_initial_values={"a": 1.5, "b": 0.3})])

        result = render_chart(axis, spec)

        fit = result.fit_results[0]
        self.assertAlmostEqual(fit.parameters["a"], 2.0, places=6)
        self.assertAlmostEqual(fit.parameters["b"], 0.5, places=6)
        self.assertGreater(fit.r_squared, 0.999999999)

    def test_custom_fit_rejects_unsafe_expression(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 1, 2],
            curves=[CurveSpec(
                values=[1, 2, 3],
                label="危险表达式",
                color="#0072B2",
                marker="o",
                fit_type="custom",
                custom_expression="__import__('os').system('whoami')")])

        with self.assertRaisesRegex(ValueError, "不允许|函数"):
            render_chart(axis, spec)

    def test_custom_expression_parameters_and_defaults_are_validated(self):
        names = custom_parameter_names("y = a*sin(b*x+c)+d")

        self.assertEqual(names, ("a", "b", "c", "d"))
        self.assertEqual(
            parse_custom_initial_values("a=2,c=0.5", names),
            {"a": 2.0, "b": 1.0, "c": 0.5, "d": 1.0},
        )
        with self.assertRaisesRegex(ValueError, "不在自定义函数中"):
            parse_custom_initial_values("unknown=1", names)

    def test_custom_fit_reports_non_convergence(self):
        figure = Figure(figsize=(5, 3), dpi=100)
        axis = figure.add_subplot(111)
        spec = ChartSpec(
            x_values=[0, 1, 2],
            curves=[CurveSpec(
                values=[0, 1, 2],
                label="不可收敛实验",
                color="#0072B2",
                marker="o",
                fit_type="custom",
                custom_expression="a**2*x",
                custom_initial_values={"a": 0.0})])

        with self.assertRaisesRegex(ValueError, "未收敛"):
            render_chart(axis, spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
