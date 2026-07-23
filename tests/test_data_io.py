import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from data_io import load_table


class DataIoTests(unittest.TestCase):
    def test_csv_first_column_becomes_x_and_remaining_columns_become_curves(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.csv"
            path.write_text(
                "时间,位移,速度\n0,1,2\n1,3,4\n2,5,6\n",
                encoding="utf-8-sig")

            table = load_table(path)

        self.assertEqual(table.x_label, "时间")
        self.assertEqual(table.x_values, (0.0, 1.0, 2.0))
        self.assertEqual([series.label for series in table.series], ["位移", "速度"])
        self.assertEqual(table.series[0].values, (1.0, 3.0, 5.0))
        self.assertEqual(table.series[1].values, (2.0, 4.0, 6.0))

    def test_xlsx_uses_the_same_table_interface_as_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(["磁场", "霍尔电压"])
            sheet.append([0, 0.1])
            sheet.append([1, 0.4])
            sheet.append([2, 0.9])
            workbook.save(path)

            table = load_table(path)

        self.assertEqual(table.x_label, "磁场")
        self.assertEqual(table.x_values, (0.0, 1.0, 2.0))
        self.assertEqual(table.series[0].label, "霍尔电压")
        self.assertEqual(table.series[0].values, (0.1, 0.4, 0.9))


if __name__ == "__main__":
    unittest.main(verbosity=2)
