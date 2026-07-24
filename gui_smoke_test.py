import importlib.util
import os
import sys
import tempfile
from ctypes import byref, windll
from ctypes.wintypes import RECT
from pathlib import Path

from matplotlib.container import ErrorbarContainer
from PIL import ImageGrab


TOOL_PATH = Path(os.environ.get(
    "PLOT_TOOL_PATH",
    Path(__file__).with_name("绘图工具.py")))


def load_module():
    sys.path.insert(0, str(TOOL_PATH.parent))
    spec = importlib.util.spec_from_file_location("physics_plot_tool_gui", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_entry(entry, value):
    entry.delete(0, "end")
    entry.insert(0, value)


def replace_text(text, value):
    text.delete("1.0", "end")
    text.insert("1.0", value)


def capture_window(root, output_path):
    hwnd = windll.user32.GetAncestor(root.winfo_id(), 2)
    rectangle = RECT()
    if not windll.user32.GetWindowRect(hwnd, byref(rectangle)):
        raise OSError("无法获取窗口边界")
    bbox = (rectangle.left, rectangle.top, rectangle.right, rectangle.bottom)
    ImageGrab.grab(bbox=bbox).save(output_path)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def assert_visible_buttons_within_window(module, root, tab):
    for button in descendants(tab):
        if not isinstance(button, module.ttk.Button) or not button.winfo_ismapped():
            continue
        relative_x = button.winfo_rootx() - root.winfo_rootx()
        relative_y = button.winfo_rooty() - root.winfo_rooty()
        geometry = (button.cget("text"), relative_x, relative_y,
                    button.winfo_width(), button.winfo_height())
        assert relative_x >= 0 and relative_x + button.winfo_width() <= root.winfo_width(), geometry
        assert relative_y >= 0 and relative_y + button.winfo_height() <= root.winfo_height(), geometry


def main():
    try:
        windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    module = load_module()
    root = module.tk.Tk()
    app = module.PhysicsPlotTool(root)
    root.geometry("800x600")
    root.update_idletasks()
    root.update()

    messages = []
    module.messagebox.showinfo = lambda title, message: messages.append(("info", title, message))
    module.messagebox.showerror = lambda title, message: messages.append(("error", title, message))

    with tempfile.TemporaryDirectory() as directory:
        csv_path = Path(directory) / "gui_import.csv"
        csv_path.write_text(
            "时间,实验组,对照组\n0,1,1\n1,3,2\n2,5,7\n3,7,16\n4,9,29\n",
            encoding="utf-8-sig")
        module.filedialog.askopenfilename = lambda **kwargs: str(csv_path)
        app.import_table()
        assert app.x_label_entry.get() == "时间"
        assert len(app.curves) == 2
        assert app.curves[1]["legend_entry"].get() == "对照组"

    replace_entry(app.title_entry, "GUI运行检查")
    replace_entry(app.x_unit_entry, "s")
    replace_entry(app.y_label_entry, "位移")
    replace_entry(app.y_unit_entry, "m")
    replace_text(app.note_text, "真实Tkinter控件自动填充与绘图检查")
    replace_entry(app.x_uncertainty_entry, "0.05")
    replace_entry(app.curves[0]["uncertainty_entry"], "0.1")
    replace_entry(app.curves[1]["uncertainty_entry"], "0.2")
    app.curves[0]["fit_var"].set("线性")
    app.curves[1]["fit_var"].set("二次")

    app.precision_spinbox.delete(0, "end")
    app.precision_spinbox.insert(0, "abc")
    assert app.precision_var.get() == ""
    app.precision_spinbox.insert(0, "11")
    assert app.precision_var.get() == ""
    app.precision_spinbox.insert(0, "4")
    assert app.precision_var.get() == "4"

    app.plot_graph()
    root.update_idletasks()
    root.update()

    assert root.winfo_width() == 800
    assert root.winfo_height() == 600
    canvas_widget = app.canvas.get_tk_widget()
    figure_width, figure_height = app.fig.get_size_inches() * app.fig.dpi
    canvas_size = (canvas_widget.winfo_width(), canvas_widget.winfo_height())
    figure_size = (round(figure_width), round(figure_height))
    assert abs(canvas_size[0] - figure_size[0]) <= 2, (canvas_size, figure_size)
    assert abs(canvas_size[1] - figure_size[1]) <= 2, (canvas_size, figure_size)
    assert sum(isinstance(item, ErrorbarContainer) for item in app.ax.containers) == 2
    assert list(app.ax.lines[0].get_ydata()) == [1.0, 3.0, 5.0, 7.0, 9.0]
    assert app.annotation in app.ax.texts
    assert "真实Tkinter控件自动填充与绘图检查" in [text.get_text() for text in app.ax.texts]
    fit_text = app.fit_result_text.get("1.0", "end")
    assert "线性拟合" in fit_text
    assert "二次拟合" in fit_text
    assert "R²" in fit_text and "相关系数" in fit_text

    saved_state = app.collect_project_state()
    with tempfile.TemporaryDirectory() as directory:
        project_path = Path(directory) / "gui_state.pplot"
        module.filedialog.asksaveasfilename = lambda **kwargs: str(project_path)
        app.save_project()
        replace_entry(app.title_entry, "已修改")
        module.filedialog.askopenfilename = lambda **kwargs: str(project_path)
        app.open_project()
        assert app.collect_project_state() == saved_state
        app.plot_graph()

    for button in app.command_buttons:
        mapping_state = (
            button.cget("text"), root.winfo_width(), root.winfo_height(),
            root.winfo_ismapped(), button.master.master.winfo_ismapped(),
            button.master.winfo_ismapped(), button.winfo_manager(),
            button.master.winfo_width(), button.master.winfo_height(),
            button.master.master.winfo_width(), button.master.master.winfo_height())
        assert button.winfo_ismapped(), mapping_state
        relative_x = button.winfo_rootx() - root.winfo_rootx()
        relative_y = button.winfo_rooty() - root.winfo_rooty()
        geometry = (relative_x, relative_y, button.winfo_width(), button.winfo_height())
        assert relative_x >= 0 and relative_x + button.winfo_width() <= root.winfo_width(), geometry
        assert relative_y >= 0 and relative_y + button.winfo_height() <= root.winfo_height(), geometry

    for tab in (app.tab_basic, app.tab_axis, app.tab_series, app.tab_fit, app.tab_about):
        app.notebook.select(tab)
        root.update_idletasks()
        root.update()
        assert_visible_buttons_within_window(module, root, tab)

    screenshot_dir = Path(os.environ.get("GUI_SCREENSHOT_DIR", TOOL_PATH.parent))
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    for tab, filename in ((app.tab_data, "gui_800x600_data.png"),
                          (app.tab_fit, "gui_800x600_fit.png")):
        app.notebook.select(tab)
        root.update_idletasks()
        root.update()
        capture_window(root, screenshot_dir / filename)

    width, height = root.winfo_width(), root.winfo_height()
    root.after(500, root.destroy)
    root.mainloop()
    error_messages = [message for level, title, message in messages if level == "error"]
    assert not error_messages, error_messages
    print(f"GUI_SMOKE_PASS window={width}x{height} curves=2 commands=6 fits=2")


if __name__ == "__main__":
    main()
