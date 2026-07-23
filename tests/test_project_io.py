import sys
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
                fit_type="linear"),))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hall.pplot"
            save_project(path, state)
            restored = load_project(path)

        self.assertEqual(restored, state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
