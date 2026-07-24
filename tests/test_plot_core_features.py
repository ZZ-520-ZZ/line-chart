import sys
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.container import ErrorbarContainer
from matplotlib.figure import Figure

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from plot_core import ChartSpec, CurveSpec, parse_uncertainty_text, render_chart


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
