import sys
import json
import tempfile
import unittest
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from project_io import CurveProject, ProjectState, load_project, save_project


class ProjectIoTests(unittest.TestCase):
    def test_project_round_trip_preserves_experiment_state(self):
        state = ProjectState(
            title="霍尔效应",
            note="室温测量",
            x_label="磁场",
            x_unit="mT",
            y_label="霍尔电压",
            y_unit="mV",
            x_data="0,1,2",
            x_uncertainty="0.01",
            x_min="0",
            x_max="2",
            y_min="",
            y_max="",
            x_tick_direction="in",
            y_tick_direction="in",
            show_grid=True,
            show_legend=True,
            precision="3",
            curves=(CurveProject(
                label="实验组",
                data="1,3,5",
                uncertainty="0.1,0.1,0.2",
                color="#d62728",
                visible=True,
                marker="o",
                fit_type="custom",
                custom_expression="a*sin(b*x+c)",
                custom_initial_values="a=2,b=1,c=0"),))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hall.pplot"
            save_project(path, state)
            restored = load_project(path)

        self.assertEqual(restored, state)

    def test_version_one_project_loads_with_empty_custom_fit_fields(self):
        legacy_payload = {
            "version": 1,
            "project": {
                "title": "旧工程",
                "note": "",
                "x_label": "X",
                "x_unit": "",
                "y_label": "Y",
                "y_unit": "",
                "x_data": "0,1,2",
                "x_uncertainty": "",
                "x_min": "",
                "x_max": "",
                "y_min": "",
                "y_max": "",
                "x_tick_direction": "in",
                "y_tick_direction": "in",
                "show_grid": True,
                "show_legend": True,
                "precision": "2",
                "curves": [{
                    "label": "旧曲线",
                    "data": "1,2,3",
                    "uncertainty": "",
                    "color": "#0072B2",
                    "visible": True,
                    "marker": "o",
                    "fit_type": "linear",
                }],
            },
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.pplot"
            path.write_text(json.dumps(legacy_payload), encoding="utf-8")
            restored = load_project(path)

        self.assertEqual(restored.curves[0].custom_expression, "")
        self.assertEqual(restored.curves[0].custom_initial_values, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
