import sys
import tempfile
import unittest
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from app_state import CurveForm, PlotForm, format_fit_results


class PlotFormTests(unittest.TestCase):
    def test_build_spec_validates_curve_length(self):
        form = PlotForm(x_data="0,1,2", curves=[CurveForm(data="1,2")])

        with self.assertRaisesRegex(ValueError, "X轴有3个点"):
            form.build_chart_spec()

    def test_render_multiple_curves_preserves_measurements(self):
        form = PlotForm(
            title="多组实验",
            x_data="0,1,2,3",
            x_uncertainty="0.02",
            curves=[
                CurveForm(
                    label="线性组",
                    data="1,3,5,7",
                    uncertainty="0.1",
                    fit_type="linear",
                ),
                CurveForm(
                    label="二次组",
                    data="1,2,9,22",
                    uncertainty="0.2,0.2,0.3,0.3",
                    color="#00798c",
                    marker="s",
                    fit_type="quadratic",
                ),
            ],
        )
        original_data = [curve.data for curve in form.curves]

        image, fits = form.render_image(width=720, height=480)

        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(image), 10_000)
        self.assertEqual([curve.data for curve in form.curves], original_data)
        self.assertEqual(len(fits), 2)
        self.assertAlmostEqual(fits[0].parameters["slope"], 2.0, places=10)
        self.assertIn("R²", format_fit_results(fits))

    def test_project_round_trip_uses_existing_pplot_format(self):
        form = PlotForm(
            title="霍尔效应",
            note="室温测量",
            x_data="0,1,2",
            curves=[CurveForm(label="实验组", data="1,3,5", fit_type="linear")],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hall.pplot"
            form.save(path)
            restored = PlotForm.load(path)

        self.assertEqual(restored.to_project(), form.to_project())

    def test_csv_import_replaces_curves_and_keeps_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.csv"
            path.write_text("时间,实验组,对照组\n0,1,2\n1,3,4\n", encoding="utf-8")
            form = PlotForm()

            table = form.import_table(path)

        self.assertEqual(table.x_label, "时间")
        self.assertEqual(form.x_data, "0,1")
        self.assertEqual([curve.label for curve in form.curves], ["实验组", "对照组"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
