# coding: utf-8
import tkinter as tk
import sys
from tkinter import ttk, messagebox, filedialog, colorchooser
from tkinter import scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from data_io import load_table
from plot_core import (ChartSpec, CurveSpec, create_annotation,
                       generate_series_values, parse_axis_limits,
                       parse_numeric_data, parse_precision,
                       parse_uncertainty_text, render_chart,
                       validate_precision_text)
from project_io import (CurveProject, ProjectState,
                        load_project as load_project_file,
                        save_project as save_project_file)

plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'cm'

LATEX_SYMBOLS = {
    'α': r'$\alpha$', 'β': r'$\beta$', 'γ': r'$\gamma$', 'δ': r'$\delta$',
    'ε': r'$\epsilon$', 'η': r'$\eta$', 'θ': r'$\theta$', 'λ': r'$\lambda$',
    'μ': r'$\mu$', 'ν': r'$\nu$', 'π': r'$\pi$', 'ρ': r'$\rho$',
    'σ': r'$\sigma$', 'τ': r'$\tau$', 'φ': r'$\phi$', 'ψ': r'$\psi$',
    'ω': r'$\omega$', 'Ω': r'$\Omega$', 'Δ': r'$\Delta$', 'Σ': r'$\Sigma$',
    '×': r'$\times$', '÷': r'$\div$', '±': r'$\pm$', '≈': r'$\approx$',
    '≠': r'$\neq$', '≤': r'$\leq$', '≥': r'$\geq$', '∞': r'$\infty$',
    '∝': r'$\propto$', '°': r'$^\circ$', '∑': r'$\sum$', '∏': r'$\prod$',
    '∫': r'$\int$', '∂': r'$\partial$', '∇': r'$\nabla$', '√': r'$\sqrt{}$',
    'x²': r'$x^2$', 'xⁿ': r'$x^n$', 'x₁': r'$x_1$', 'xᵢ': r'$x_i$',
    'B⃗': r'$\vec{B}$', 'E⃗': r'$\vec{E}$', 'v⃗': r'$\vec{v}$',
    'B⊥': r'$B_\perp$', 'B∥': r'$B_\parallel$',
    'sin': r'$\sin$', 'cos': r'$\cos$', 'tan': r'$\tan$',
    'log': r'$\log$', 'ln': r'$\ln$', 'exp': r'$\exp$',
    'lim': r'$\lim$', 'min': r'$\min$', 'max': r'$\max$', 'avg': r'$\mathrm{avg}$',
}

MARKERS = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h', 'H', '8']
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
          '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
FIT_OPTIONS = {
    '不拟合': 'none',
    '线性': 'linear',
    '二次': 'quadratic',
    '指数': 'exponential',
}
FIT_LABELS = {value: label for label, value in FIT_OPTIONS.items()}


class UndoEntry(tk.Entry):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.history = ['']
        self.history_index = 0
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Control-z>", self._undo)

    def _on_key_release(self, event):
        if event.state & 0x4 and event.keysym == 'z':
            return
        current_text = self.get()
        if self.history[self.history_index] == current_text:
            return
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        self.history.append(current_text)
        self.history_index += 1
        if len(self.history) > 100:
            self.history.pop(0)
            self.history_index -= 1

    def _undo(self, event):
        if self.history_index > 0:
            self.history_index -= 1
            self.delete(0, tk.END)
            self.insert(0, self.history[self.history_index])


def add_undo_support(entry):
    if isinstance(entry, scrolledtext.ScrolledText):
        entry.config(undo=True)

        def undo(event):
            try:
                entry.edit_undo()
            except tk.TclError:
                pass

        entry.bind("<Control-z>", undo)


class PhysicsPlotTool:
    def __init__(self, root):
        self.root = root
        self.root.title("绘图工具")
        self.root.geometry("900x620")
        self.root.minsize(800, 600)

        self.style = ttk.Style()
        themes = self.style.theme_names()
        theme_name = 'vista' if sys.platform == 'win32' and 'vista' in themes else 'clam'
        self.style.theme_use(theme_name)
        ui_font = 'Microsoft YaHei UI' if sys.platform == 'win32' else 'Noto Sans CJK SC'
        self.root.option_add('*Font', (ui_font, 9))
        self.root.configure(background='#f4f7f6')
        self.style.configure('TFrame', background='#f4f7f6')
        self.style.configure('TLabel', background='#f4f7f6', foreground='#18201f')
        self.style.configure('TButton', padding=(9, 5), font=(ui_font, 9))
        if theme_name == 'vista':
            self.style.configure(
                'Accent.TButton', padding=(10, 6), font=(ui_font, 9, 'bold'),
                foreground='#006b68')
            self.style.map(
                'Accent.TButton',
                foreground=[('disabled', '#7b8583'), ('pressed', '#004d4a'),
                            ('active', '#005b58'), ('!disabled', '#006b68')])
        else:
            self.style.configure(
                'Accent.TButton', padding=(10, 6), font=(ui_font, 9, 'bold'),
                foreground='white', background='#006b68')
            self.style.map(
                'Accent.TButton',
                foreground=[('disabled', '#7b8583'), ('!disabled', 'white')],
                background=[('pressed', '#004d4a'), ('active', '#005b58'),
                            ('!disabled', '#006b68')])
        self.style.configure('TLabelframe', background='#f4f7f6', padding=6)
        self.style.configure(
            'TLabelframe.Label', background='#f4f7f6', foreground='#18201f',
            font=(ui_font, 9, 'bold'))
        self.style.configure('TNotebook', background='#f4f7f6', borderwidth=0)
        self.style.configure('TNotebook.Tab', padding=(12, 7), font=(ui_font, 9))
        self.style.map(
            'TNotebook.Tab',
            foreground=[('selected', '#006b68')],
            background=[('selected', '#ffffff'), ('!selected', '#e8eeec')])
        self.style.configure('TEntry', padding=4)
        self.style.configure('TCombobox', padding=3)
        self.style.configure('TRadiobutton', background='#f4f7f6', indicatoron=1)
        self.style.configure('TCheckbutton', background='#f4f7f6')

        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.curves = []
        self.curve_frames = []
        self.next_curve_id = 1

        self.setup_ui()
        self.add_curve()
        self.add_curve()

    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_paned, width=420)
        right_frame = ttk.Frame(main_paned, width=580)
        main_paned.add(left_frame, weight=2)
        main_paned.add(right_frame, weight=3)

        self.setup_left_panel(left_frame)
        self.setup_right_panel(right_frame)

    def setup_left_panel(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True)
        self.notebook = nb

        self.tab_basic = ttk.Frame(nb)
        self.tab_axis = ttk.Frame(nb)
        self.tab_data = ttk.Frame(nb)
        self.tab_series = ttk.Frame(nb)
        self.tab_fit = ttk.Frame(nb)
        self.tab_about = ttk.Frame(nb)

        nb.add(self.tab_basic, text='基本')
        nb.add(self.tab_axis, text='坐标')
        nb.add(self.tab_data, text='数据')
        nb.add(self.tab_series, text='数列')
        nb.add(self.tab_fit, text='拟合')
        nb.add(self.tab_about, text='关于')

        self.setup_basic_tab()
        self.setup_axis_tab()
        self.setup_data_tab()
        self.setup_series_tab()
        self.setup_fit_tab()
        self.setup_about_tab()

    def setup_basic_tab(self):
        ttk.Label(self.tab_basic, text="图表标题:", font=('Arial', 10, 'bold')).pack(
            anchor=tk.W, padx=10, pady=(10, 5))
        title_row = ttk.Frame(self.tab_basic)
        title_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.title_entry = UndoEntry(title_row, width=30, font=('Arial', 10))
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(title_row, text="符", command=lambda: self.open_symbol_window(self.title_entry),
                   width=3).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(title_row, text="清除", command=lambda: self.title_entry.delete(0, tk.END),
                   width=6).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(self.tab_basic, text="图表说明:", font=('Arial', 10, 'bold')).pack(
            anchor=tk.W, padx=10, pady=(10, 5))
        self.note_text = scrolledtext.ScrolledText(self.tab_basic, width=40, height=3, font=('Arial', 10))
        self.note_text.pack(fill=tk.X, padx=10, pady=(0, 10))
        add_undo_support(self.note_text)

        ttk.Label(self.tab_basic, text="显示网格:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.tab_basic, variable=self.grid_var, text="启用网格").pack(anchor=tk.W, padx=10)

        ttk.Label(self.tab_basic, text="显示图例:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.legend_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.tab_basic, variable=self.legend_var, text="显示图例").pack(anchor=tk.W, padx=10)

        ttk.Label(self.tab_basic, text="数值精度:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        precision_frame = ttk.Frame(self.tab_basic)
        precision_frame.pack(fill=tk.X, padx=10)
        self.precision_var = tk.StringVar(value='1')
        precision_validation = (self.root.register(validate_precision_text), '%P')
        self.precision_spinbox = ttk.Spinbox(
            precision_frame, from_=0, to=10, textvariable=self.precision_var,
            width=8, validate='key', validatecommand=precision_validation)
        self.precision_spinbox.pack(side=tk.LEFT)
        ttk.Label(precision_frame, text="位小数").pack(side=tk.LEFT, padx=5)

    def setup_axis_tab(self):
        x_frame = ttk.LabelFrame(self.tab_axis, text="X轴设置", padding=10)
        x_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(x_frame, text="轴标签:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        x_label_row = ttk.Frame(x_frame)
        x_label_row.grid(row=0, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.x_label_entry = UndoEntry(x_label_row, width=18, font=('Arial', 10))
        self.x_label_entry.pack(side=tk.LEFT)
        ttk.Button(x_label_row, text="符", command=lambda: self.open_symbol_window(self.x_label_entry),
                   width=3).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(x_frame, text="单位:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        x_unit_row = ttk.Frame(x_frame)
        x_unit_row.grid(row=1, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.x_unit_entry = UndoEntry(x_unit_row, width=12, font=('Arial', 10))
        self.x_unit_entry.pack(side=tk.LEFT)
        ttk.Button(x_unit_row, text="符", command=lambda: self.open_symbol_window(self.x_unit_entry),
                   width=3).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(x_frame, text="范围:", font=('Arial', 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        x_range_frame = ttk.Frame(x_frame)
        x_range_frame.grid(row=2, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.x_min_entry = ttk.Entry(x_range_frame, width=8)
        self.x_min_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(x_range_frame, text="~").pack(side=tk.LEFT, padx=2)
        self.x_max_entry = ttk.Entry(x_range_frame, width=8)
        self.x_max_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(x_frame, text="刻度方向:", font=('Arial', 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.x_tick_dir = tk.StringVar(value='in')
        ttk.Radiobutton(x_frame, text="向外", variable=self.x_tick_dir, value='out').grid(row=3, column=1, sticky=tk.W)
        ttk.Radiobutton(x_frame, text="向内", variable=self.x_tick_dir, value='in').grid(row=3, column=1, sticky=tk.E)

        y_frame = ttk.LabelFrame(self.tab_axis, text="Y轴设置", padding=10)
        y_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(y_frame, text="轴标签:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=5)
        y_label_row = ttk.Frame(y_frame)
        y_label_row.grid(row=0, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.y_label_entry = UndoEntry(y_label_row, width=18, font=('Arial', 10))
        self.y_label_entry.pack(side=tk.LEFT)
        ttk.Button(y_label_row, text="符", command=lambda: self.open_symbol_window(self.y_label_entry),
                   width=3).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(y_frame, text="单位:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        y_unit_row = ttk.Frame(y_frame)
        y_unit_row.grid(row=1, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.y_unit_entry = UndoEntry(y_unit_row, width=12, font=('Arial', 10))
        self.y_unit_entry.pack(side=tk.LEFT)
        ttk.Button(y_unit_row, text="符", command=lambda: self.open_symbol_window(self.y_unit_entry),
                   width=3).pack(side=tk.LEFT, padx=(5, 0))

        ttk.Label(y_frame, text="范围:", font=('Arial', 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        y_range_frame = ttk.Frame(y_frame)
        y_range_frame.grid(row=2, column=1, padx=5, columnspan=2, sticky=tk.W)
        self.y_min_entry = ttk.Entry(y_range_frame, width=8)
        self.y_min_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(y_range_frame, text="~").pack(side=tk.LEFT, padx=2)
        self.y_max_entry = ttk.Entry(y_range_frame, width=8)
        self.y_max_entry.pack(side=tk.LEFT, padx=2)

        ttk.Label(y_frame, text="刻度方向:", font=('Arial', 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.y_tick_dir = tk.StringVar(value='in')
        ttk.Radiobutton(y_frame, text="向外", variable=self.y_tick_dir, value='out').grid(row=3, column=1, sticky=tk.W)
        ttk.Radiobutton(y_frame, text="向内", variable=self.y_tick_dir, value='in').grid(row=3, column=1, sticky=tk.E)

    def setup_data_tab(self):
        x_data_frame = ttk.LabelFrame(self.tab_data, text="X轴数据", padding=6)
        x_data_frame.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(x_data_frame, text="数据值（逗号分隔）:", font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 2))
        self.x_data_entry = scrolledtext.ScrolledText(x_data_frame, width=40, height=3, font=('Arial', 9))
        self.x_data_entry.pack(fill=tk.X, pady=(0, 3))
        add_undo_support(self.x_data_entry)

        x_uncertainty_row = ttk.Frame(x_data_frame)
        x_uncertainty_row.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(x_uncertainty_row, text="X不确定度（单值/列表）:", font=('Arial', 9)).pack(side=tk.LEFT)
        self.x_uncertainty_entry = UndoEntry(x_uncertainty_row, width=16, font=('Arial', 9))
        self.x_uncertainty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        x_button_frame = ttk.Frame(x_data_frame)
        x_button_frame.pack(fill=tk.X)
        ttk.Button(x_button_frame, text="清除", command=lambda: self.x_data_entry.delete(1.0, tk.END),
                   width=8).pack(side=tk.RIGHT)
        ttk.Button(x_button_frame, text="从数列导入", command=self.import_x_from_series,
                   width=12).pack(side=tk.RIGHT, padx=5)

        curves_header = ttk.Frame(self.tab_data)
        curves_header.pack(fill=tk.X, padx=8, pady=(4, 3))
        ttk.Label(curves_header, text="Y轴曲线（可添加多个）", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(curves_header, text="+ 添加曲线", command=self.add_curve, width=10).pack(side=tk.RIGHT)

        self.curves_container = ttk.Frame(self.tab_data)
        self.curves_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        self.data_canvas = tk.Canvas(self.curves_container, highlightthickness=0)
        self.data_scrollbar = ttk.Scrollbar(self.curves_container, orient="vertical", command=self.data_canvas.yview)
        self.data_scroll_frame = ttk.Frame(self.data_canvas)

        self.data_scroll_frame.bind("<Configure>",
                                    lambda e: self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all")))
        self.data_window = self.data_canvas.create_window(
            (0, 0), window=self.data_scroll_frame, anchor="nw")
        self.data_canvas.bind(
            "<Configure>",
            lambda event: self.data_canvas.itemconfigure(self.data_window, width=event.width))
        self.data_canvas.configure(yscrollcommand=self.data_scrollbar.set)

        def on_data_mousewheel(event):
            widget = event.widget
            inside_data_panel = False
            while widget is not None:
                if widget == self.curves_container:
                    inside_data_panel = True
                    break
                widget = getattr(widget, 'master', None)
            if not inside_data_panel or isinstance(event.widget, tk.Text) or event.delta == 0:
                return None
            direction = -1 if event.delta > 0 else 1
            self.data_canvas.yview_scroll(direction, "units")
            return "break"

        self.root.bind("<MouseWheel>", on_data_mousewheel, add='+')

        self.data_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_series_tab(self):
        series_type_frame = ttk.LabelFrame(self.tab_series, text="数列类型", padding=10)
        series_type_frame.pack(fill=tk.X, padx=10, pady=10)

        self.series_var = tk.StringVar(value="arithmetic")
        ttk.Radiobutton(series_type_frame, text="等差数列", variable=self.series_var, value="arithmetic").pack(
            side=tk.LEFT, padx=10)
        ttk.Radiobutton(series_type_frame, text="等比数列", variable=self.series_var, value="geometric").pack(
            side=tk.LEFT, padx=10)

        params_frame = ttk.LabelFrame(self.tab_series, text="参数设置", padding=10)
        params_frame.pack(fill=tk.X, padx=10, pady=10)

        param_form = ttk.Frame(params_frame)
        param_form.pack(fill=tk.X, padx=5)

        ttk.Label(param_form, text="起始值:", font=('Arial', 10)).grid(row=0, column=0, sticky=tk.W, pady=8, padx=5)
        self.start_entry = ttk.Entry(param_form, width=20)
        self.start_entry.grid(row=0, column=1, pady=8, sticky=tk.W)

        ttk.Label(param_form, text="结束值:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=8, padx=5)
        self.end_entry = ttk.Entry(param_form, width=20)
        self.end_entry.grid(row=1, column=1, pady=8, sticky=tk.W)

        ttk.Label(param_form, text="步长/公比:", font=('Arial', 10)).grid(row=2, column=0, sticky=tk.W, pady=8, padx=5)
        self.step_entry = ttk.Entry(param_form, width=20)
        self.step_entry.grid(row=2, column=1, pady=8, sticky=tk.W)

        target_frame = ttk.LabelFrame(self.tab_series, text="目标位置", padding=10)
        target_frame.pack(fill=tk.X, padx=10, pady=10)

        self.target_var = tk.StringVar(value="x")
        self.target_curve_ids = []
        ttk.Radiobutton(target_frame, text="X轴数据", variable=self.target_var, value="x").pack(side=tk.LEFT, padx=10)

        self.target_combo = ttk.Combobox(target_frame, state='readonly', width=15)
        self.target_combo.pack(side=tk.LEFT, padx=5)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_combo_change)
        self.target_combo['values'] = []

        button_frame = ttk.Frame(params_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="生成数列", command=self.generate_series,
                   style='Accent.TButton').pack(fill=tk.X, padx=20)

        preview_frame = ttk.LabelFrame(self.tab_series, text="生成预览", padding=10)
        preview_frame.pack(fill=tk.X, padx=10, pady=10)
        self.preview_text = scrolledtext.ScrolledText(preview_frame, width=40, height=3, font=('Arial', 10))
        self.preview_text.pack(fill=tk.X)

    def setup_fit_tab(self):
        toolbar = ttk.Frame(self.tab_fit)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(toolbar, text="拟合参数与质量", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="复制", command=self.copy_fit_results, width=7).pack(side=tk.RIGHT)
        self.fit_result_text = scrolledtext.ScrolledText(
            self.tab_fit, width=40, height=18, font=('Consolas', 10), wrap=tk.WORD)
        self.fit_result_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.fit_result_text.insert('1.0', "绘制并选择拟合方式后，参数将显示在这里。")
        self.fit_result_text.config(state=tk.DISABLED)

    def copy_fit_results(self):
        text = self.fit_result_text.get('1.0', tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def show_fit_results(self, fit_results):
        if fit_results:
            blocks = []
            for result in fit_results:
                blocks.append(
                    f"{result.curve_label} - {FIT_LABELS.get(result.fit_type, result.fit_type)}拟合\n"
                    f"方程: {result.equation}\n"
                    f"R² = {result.r_squared:.6f}\n"
                    f"相关系数 r = {result.correlation:.6f}")
            text = "\n\n".join(blocks)
        else:
            text = "当前曲线未选择拟合方式。"
        self.fit_result_text.config(state=tk.NORMAL)
        self.fit_result_text.delete('1.0', tk.END)
        self.fit_result_text.insert('1.0', text)
        self.fit_result_text.config(state=tk.DISABLED)

    def clear_fit_results(self):
        self.show_fit_results(())

    def setup_about_tab(self):
        about_frame = ttk.Frame(self.tab_about)
        about_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(about_frame, text="绘图工具", font=('Arial', 16, 'bold')).pack(pady=(10, 5))
        ttk.Label(about_frame, text="物理实验专用折线绘图工具", font=('Arial', 11)).pack(pady=5)

        ttk.Separator(about_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        ttk.Label(about_frame, text="功能特点:", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        features = [
            "• 支持多条曲线同时绘制与对比",
            "• 丰富的物理符号与LaTeX公式支持",
            "• 可自定义坐标轴范围与样式",
            "• 支持等差数列和等比数列生成",
            "• 多种格式导出（PNG/JPG/PDF/SVG）",
        ]
        for f in features:
            ttk.Label(about_frame, text=f, font=('Arial', 10)).pack(anchor=tk.W, pady=2)

        ttk.Separator(about_frame, orient='horizontal').pack(fill=tk.X, pady=15)

        contact_frame = ttk.LabelFrame(about_frame, text="联系方式", padding=15)
        contact_frame.pack(fill=tk.X, pady=10)

        ttk.Label(contact_frame, text="如有问题或建议，欢迎联系我修改~",
                  font=('Arial', 10)).pack(pady=(0, 10))

        qq_frame = ttk.Frame(contact_frame)
        qq_frame.pack(pady=5)
        ttk.Label(qq_frame, text="QQ:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.qq_label = ttk.Label(qq_frame, text="2727003517", font=('Arial', 11, 'bold'), foreground='#1a73e8')
        self.qq_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(qq_frame, text="复制", command=self.copy_qq, width=6).pack(side=tk.LEFT, padx=5)

    def copy_qq(self):
        self.root.clipboard_clear()
        self.root.clipboard_append("2727003517")
        messagebox.showinfo("提示", "QQ号已复制到剪贴板")

    def refresh_target_combo(self):
        options = [f"Y轴曲线{i + 1}" for i in range(len(self.curves))]
        self.target_curve_ids = [curve['id'] for curve in self.curves]
        self.target_combo['values'] = options
        target = self.target_var.get()
        if target.startswith("y:"):
            try:
                curve_id = int(target.split(":", 1)[1])
                self.target_combo.current(self.target_curve_ids.index(curve_id))
                return
            except (ValueError, IndexError):
                pass
        self.target_var.set("x")
        self.target_combo.set("")

    def on_target_combo_change(self, event=None):
        idx = self.target_combo.current()
        if 0 <= idx < len(self.target_curve_ids):
            self.target_var.set(f"y:{self.target_curve_ids[idx]}")
            self.target_combo.selection_clear()

    def add_curve(self):
        if len(self.curves) >= 10:
            messagebox.showinfo("提示", "最多支持10条曲线")
            return

        curve_id = self.next_curve_id
        self.next_curve_id += 1
        idx = len(self.curves)

        color = COLORS[idx % len(COLORS)]
        marker = MARKERS[idx % len(MARKERS)]

        curve_frame = ttk.LabelFrame(self.data_scroll_frame, text=f"曲线 {idx + 1}", padding=6)
        curve_frame.pack(fill=tk.X, pady=3)

        header_row = ttk.Frame(curve_frame)
        header_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(header_row, text="图例:", font=('Arial', 9)).pack(side=tk.LEFT)
        legend_entry = UndoEntry(header_row, width=9, font=('Arial', 9))
        legend_entry.insert(0, f'数据集{idx + 1}')
        legend_entry.pack(side=tk.LEFT, padx=3)
        ttk.Button(header_row, text="符",
                   command=lambda e=legend_entry: self.open_symbol_window(e),
                   width=2).pack(side=tk.LEFT, padx=2)

        color_var = tk.StringVar(value=color)

        def choose_curve_color(var=color_var, frm=curve_frame):
            c = colorchooser.askcolor(title="选择颜色", initialcolor=var.get())[1]
            if c:
                var.set(c)

        ttk.Button(header_row, text="颜色", command=choose_curve_color, width=4).pack(side=tk.LEFT, padx=2)

        show_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(header_row, variable=show_var, text="显示").pack(side=tk.LEFT, padx=2)

        def remove_curve(frm=curve_frame, cid=curve_id):
            self.remove_curve_by_id(cid)

        ttk.Label(curve_frame, text="数据值（逗号分隔）:", font=('Arial', 9)).pack(anchor=tk.W, pady=(2, 1))
        data_entry = scrolledtext.ScrolledText(curve_frame, width=40, height=2, font=('Arial', 9))
        data_entry.pack(fill=tk.X, pady=(0, 3))
        add_undo_support(data_entry)

        analysis_row = ttk.Frame(curve_frame)
        analysis_row.pack(fill=tk.X, pady=(0, 3))
        ttk.Label(analysis_row, text="Y不确定度:", font=('Arial', 9)).pack(side=tk.LEFT)
        uncertainty_entry = UndoEntry(analysis_row, width=11, font=('Arial', 9))
        uncertainty_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 8))
        ttk.Label(analysis_row, text="拟合:", font=('Arial', 9)).pack(side=tk.LEFT)
        fit_var = tk.StringVar(value='不拟合')
        fit_combo = ttk.Combobox(
            analysis_row, textvariable=fit_var,
            values=list(FIT_OPTIONS), state='readonly', width=7)
        fit_combo.pack(side=tk.LEFT, padx=(3, 0))

        btn_row = ttk.Frame(curve_frame)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="删除", command=remove_curve, width=6).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="清除",
                   command=lambda e=data_entry: e.delete(1.0, tk.END),
                   width=6).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="从数列导入",
                   command=lambda cid=curve_id: self.import_y_from_series(cid),
                   width=10).pack(side=tk.RIGHT, padx=5)

        curve_info = {
            'id': curve_id,
            'frame': curve_frame,
            'legend_entry': legend_entry,
            'data_entry': data_entry,
            'uncertainty_entry': uncertainty_entry,
            'fit_var': fit_var,
            'color_var': color_var,
            'show_var': show_var,
            'marker': marker,
        }
        self.curves.append(curve_info)
        self.curve_frames.append(curve_frame)
        self.refresh_target_combo()

    def remove_curve_by_id(self, curve_id):
        if len(self.curves) <= 1:
            messagebox.showinfo("提示", "至少保留一条曲线")
            return

        for i, curve in enumerate(self.curves):
            if curve['id'] == curve_id:
                curve['frame'].destroy()
                self.curves.pop(i)
                self.curve_frames.pop(i)
                break

        for i, curve in enumerate(self.curves):
            curve['frame'].config(text=f"曲线 {i + 1}")

        self.refresh_target_combo()

    def setup_right_panel(self, parent):
        canvas_frame = ttk.LabelFrame(parent, text="图表预览", padding=5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        canvas_widget.bind('<Configure>', self.sync_figure_size, add='+')

        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.create_annotation()

        button_frame = ttk.Frame(parent)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=3, pady=(2, 0))
        for column in range(3):
            button_frame.columnconfigure(column, weight=1, uniform='commands')

        commands = [
            ("绘制图表", self.plot_graph, 'Accent.TButton'),
            ("清空图表", self.clear_plot, None),
            ("导出图片", self.save_plot, None),
            ("导入表格", self.import_table, None),
            ("打开工程", self.open_project, None),
            ("保存工程", self.save_project, None),
        ]
        self.command_buttons = []
        for index, (text, command, style) in enumerate(commands):
            options = {'text': text, 'command': command}
            if style:
                options['style'] = style
            button = ttk.Button(button_frame, **options)
            button.grid(row=index // 3, column=index % 3, sticky='ew', padx=2, pady=1)
            self.command_buttons.append(button)
        canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def sync_figure_size(self, event):
        self.root.after_idle(self.apply_canvas_size)

    def apply_canvas_size(self):
        canvas_widget = self.canvas.get_tk_widget()
        width = canvas_widget.winfo_width()
        height = canvas_widget.winfo_height()
        if width < 100 or height < 100:
            return
        figure_width, figure_height = self.fig.get_size_inches() * self.fig.dpi
        if abs(figure_width - width) <= 2 and abs(figure_height - height) <= 2:
            return
        self.fig.set_size_inches(
            width / self.fig.dpi,
            height / self.fig.dpi,
            forward=False)
        self.canvas.draw_idle()

    @staticmethod
    def set_entry(entry, value):
        entry.delete(0, tk.END)
        entry.insert(0, str(value))

    @staticmethod
    def set_text(text_widget, value):
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', str(value))

    @staticmethod
    def format_values(values):
        return ','.join(f'{value:.12g}' for value in values)

    def resize_curves(self, target_count):
        if not 1 <= target_count <= 10:
            raise ValueError("曲线数量必须在1到10之间")
        while len(self.curves) < target_count:
            self.add_curve()
        while len(self.curves) > target_count:
            curve = self.curves.pop()
            curve['frame'].destroy()
            self.curve_frames.pop()
        for index, curve in enumerate(self.curves):
            curve['frame'].config(text=f"曲线 {index + 1}")
        self.refresh_target_combo()

    def import_table(self):
        file_path = filedialog.askopenfilename(
            title="导入实验数据",
            filetypes=[("表格文件", "*.csv *.xlsx *.xlsm"),
                       ("CSV文件", "*.csv"),
                       ("Excel文件", "*.xlsx *.xlsm")])
        if not file_path:
            return
        try:
            table = load_table(file_path)
            self.resize_curves(len(table.series))
        except (OSError, ValueError) as exc:
            messagebox.showerror("导入失败", str(exc))
            return

        self.set_text(self.x_data_entry, self.format_values(table.x_values))
        self.set_entry(self.x_label_entry, table.x_label)
        self.set_entry(self.x_uncertainty_entry, '')
        for curve, imported in zip(self.curves, table.series):
            self.set_entry(curve['legend_entry'], imported.label)
            self.set_text(curve['data_entry'], self.format_values(imported.values))
            self.set_entry(curve['uncertainty_entry'], '')
            curve['fit_var'].set('不拟合')
            curve['show_var'].set(True)
        messagebox.showinfo("导入完成", f"已导入{len(table.x_values)}个数据点和{len(table.series)}条曲线")

    def collect_project_state(self):
        return ProjectState(
            title=self.title_entry.get(),
            note=self.note_text.get('1.0', tk.END).strip(),
            x_label=self.x_label_entry.get(),
            x_unit=self.x_unit_entry.get(),
            y_label=self.y_label_entry.get(),
            y_unit=self.y_unit_entry.get(),
            x_data=self.x_data_entry.get('1.0', tk.END).strip(),
            x_uncertainty=self.x_uncertainty_entry.get(),
            x_min=self.x_min_entry.get(),
            x_max=self.x_max_entry.get(),
            y_min=self.y_min_entry.get(),
            y_max=self.y_max_entry.get(),
            x_tick_direction=self.x_tick_dir.get(),
            y_tick_direction=self.y_tick_dir.get(),
            show_grid=self.grid_var.get(),
            show_legend=self.legend_var.get(),
            precision=self.precision_var.get(),
            curves=tuple(CurveProject(
                label=curve['legend_entry'].get(),
                data=curve['data_entry'].get('1.0', tk.END).strip(),
                uncertainty=curve['uncertainty_entry'].get(),
                color=curve['color_var'].get(),
                visible=curve['show_var'].get(),
                marker=curve['marker'],
                fit_type=FIT_OPTIONS.get(curve['fit_var'].get(), 'none'))
                for curve in self.curves))

    def apply_project_state(self, state):
        self.resize_curves(max(1, len(state.curves)))
        for entry, value in (
                (self.title_entry, state.title),
                (self.x_label_entry, state.x_label),
                (self.x_unit_entry, state.x_unit),
                (self.y_label_entry, state.y_label),
                (self.y_unit_entry, state.y_unit),
                (self.x_uncertainty_entry, state.x_uncertainty),
                (self.x_min_entry, state.x_min),
                (self.x_max_entry, state.x_max),
                (self.y_min_entry, state.y_min),
                (self.y_max_entry, state.y_max)):
            self.set_entry(entry, value)
        self.set_text(self.note_text, state.note)
        self.set_text(self.x_data_entry, state.x_data)
        self.x_tick_dir.set(state.x_tick_direction)
        self.y_tick_dir.set(state.y_tick_direction)
        self.grid_var.set(state.show_grid)
        self.legend_var.set(state.show_legend)
        self.precision_var.set(state.precision)

        for curve, saved in zip(self.curves, state.curves):
            self.set_entry(curve['legend_entry'], saved.label)
            self.set_text(curve['data_entry'], saved.data)
            self.set_entry(curve['uncertainty_entry'], saved.uncertainty)
            curve['color_var'].set(saved.color)
            curve['show_var'].set(saved.visible)
            curve['marker'] = saved.marker
            curve['fit_var'].set(FIT_LABELS.get(saved.fit_type, '不拟合'))
        self.clear_fit_results()

    def save_project(self):
        file_path = filedialog.asksaveasfilename(
            title="保存工程", defaultextension=".pplot",
            filetypes=[("物理绘图工程", "*.pplot")])
        if not file_path:
            return
        try:
            save_project_file(file_path, self.collect_project_state())
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("保存失败", f"工程保存失败：{exc}")
            return
        messagebox.showinfo("保存成功", "工程已保存")

    def open_project(self):
        file_path = filedialog.askopenfilename(
            title="打开工程", filetypes=[("物理绘图工程", "*.pplot")])
        if not file_path:
            return
        try:
            state = load_project_file(file_path)
            self.apply_project_state(state)
        except (OSError, ValueError) as exc:
            messagebox.showerror("打开失败", str(exc))
            return
        messagebox.showinfo("打开成功", "工程已恢复")

    def create_annotation(self):
        self.annotation = create_annotation(self.ax)

    def open_symbol_window(self, target_entry):
        symbol_window = tk.Toplevel(self.root)
        symbol_window.title("物理常用符号")
        symbol_window.geometry("420x450")
        symbol_window.minsize(350, 350)

        mode_frame = ttk.Frame(symbol_window)
        mode_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(mode_frame, text="插入模式:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.symbol_mode = tk.StringVar(value='latex')
        ttk.Radiobutton(mode_frame, text="LaTeX公式", variable=self.symbol_mode, value='latex').pack(side=tk.LEFT,
                                                                                                        padx=10)
        ttk.Radiobutton(mode_frame, text="纯文本", variable=self.symbol_mode, value='text').pack(side=tk.LEFT,
                                                                                                     padx=10)

        category_frame = ttk.Frame(symbol_window)
        category_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(category_frame, text="分类:", font=('Arial', 10)).pack(side=tk.LEFT)
        self.symbol_category = tk.StringVar(value='希腊字母')
        categories = ['希腊字母', '数学符号', '上下标', '矢量', '函数']
        category_combo = ttk.Combobox(category_frame, textvariable=self.symbol_category, values=categories,
                                      state='readonly', width=12)
        category_combo.pack(side=tk.LEFT, padx=5)

        container = ttk.Frame(symbol_window)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        symbol_frame = ttk.Frame(canvas)

        symbol_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=symbol_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_mousewheel(event):
            if event.delta == 0:
                return None
            direction = -1 if event.delta > 0 else 1
            canvas.yview_scroll(direction, "units")
            return "break"

        symbol_window.bind("<MouseWheel>", on_mousewheel, add='+')

        scroll_up_btn = ttk.Button(container, text="▲", width=3,
                                   command=lambda: canvas.yview_scroll(-1, "units"))
        scroll_down_btn = ttk.Button(container, text="▼", width=3,
                                     command=lambda: canvas.yview_scroll(1, "units"))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        scroll_up_btn.pack(side=tk.TOP, padx=(5, 0), pady=(0, 3))
        scroll_down_btn.pack(side=tk.BOTTOM, padx=(5, 0), pady=(3, 0))

        category_symbols = {
            '希腊字母': ['α', 'β', 'γ', 'δ', 'ε', 'η', 'θ', 'λ', 'μ', 'ν',
                       'π', 'ρ', 'σ', 'τ', 'φ', 'ψ', 'ω', 'Ω', 'Δ', 'Σ'],
            '数学符号': ['×', '÷', '±', '≈', '≡', '≠', '≤', '≥', '∞', '∝',
                       '°', '′', '″', '∑', '∏', '∫', '∂', '∇', '√'],
            '上下标': ['x²', 'xⁿ', 'x₁', 'xᵢ', 'B⊥', 'B∥'],
            '矢量': ['B⃗', 'E⃗', 'v⃗'],
            '函数': ['sin', 'cos', 'tan', 'log', 'ln', 'exp', 'lim', 'min', 'max', 'avg'],
        }

        def refresh_symbols(*args):
            for widget in symbol_frame.winfo_children():
                widget.destroy()
            cat = self.symbol_category.get()
            symbols = category_symbols.get(cat, [])
            for i, symbol in enumerate(symbols):
                row = i // 5
                col = i % 5
                btn = ttk.Button(symbol_frame, text=symbol, width=6,
                                 command=lambda s=symbol: insert_symbol(s))
                btn.grid(row=row, column=col, padx=4, pady=4)

        self.symbol_category.trace_add('write', refresh_symbols)

        def insert_symbol(symbol):
            if self.symbol_mode.get() == 'latex' and symbol in LATEX_SYMBOLS:
                target_entry.insert(tk.END, LATEX_SYMBOLS[symbol])
            else:
                target_entry.insert(tk.END, symbol)
            symbol_window.destroy()

        def on_window_close():
            symbol_window.destroy()

        symbol_window.protocol("WM_DELETE_WINDOW", on_window_close)

        refresh_symbols()

    def generate_series(self):
        try:
            start = float(self.start_entry.get())
            end = float(self.end_entry.get())
            step_or_ratio = float(self.step_entry.get())
            data = generate_series_values(self.series_var.get(), start, end, step_or_ratio)
            precision = self.get_precision()
            data_str = ','.join([f'{x:.{precision}f}' for x in data])

            self.preview_text.delete(1.0, tk.END)
            preview = data_str[:200] + '...' if len(data_str) > 200 else data_str
            self.preview_text.insert(1.0, preview)

            target = self.target_var.get()
            if target == "x":
                self.x_data_entry.delete(1.0, tk.END)
                self.x_data_entry.insert(1.0, data_str)
            elif target.startswith("y:"):
                curve_id = int(target.split(":", 1)[1])
                curve = next((item for item in self.curves if item['id'] == curve_id), None)
                if curve is None:
                    raise ValueError("目标曲线已不存在，请重新选择")
                curve['data_entry'].delete(1.0, tk.END)
                curve['data_entry'].insert(1.0, data_str)

        except (ValueError, OverflowError, tk.TclError) as e:
            messagebox.showerror("错误", f"请输入有效的数字：{str(e)}")

    def get_precision(self):
        return parse_precision(self.precision_var.get())

    def import_x_from_series(self):
        self.target_var.set("x")
        self.generate_series()

    def import_y_from_series(self, curve_id):
        for i, curve in enumerate(self.curves):
            if curve['id'] == curve_id:
                self.target_var.set(f"y:{curve_id}")
                self.target_combo.current(i)
                self.generate_series()
                break

    def on_hover(self, event):
        if event.inaxes == self.ax:
            for line in self.ax.lines:
                contains, info = line.contains(event)
                if contains:
                    indices = info.get('ind', [])
                    if not indices:
                        continue
                    point_index = indices[0]
                    x_values, y_values = line.get_data()
                    x = float(x_values[point_index])
                    y = float(y_values[point_index])
                    self.annotation.xy = (x, y)
                    try:
                        precision = self.get_precision()
                    except (ValueError, tk.TclError):
                        precision = 1
                    text = f"({x:.{precision}f}, {y:.{precision}f})"
                    self.annotation.set_text(text)
                    self.annotation.set_visible(True)
                    self.canvas.draw_idle()
                    return
        self.annotation.set_visible(False)
        self.canvas.draw_idle()

    def parse_data(self, data_str):
        try:
            return parse_numeric_data(data_str)
        except ValueError as exc:
            messagebox.showerror("错误", str(exc))
            return None

    def plot_graph(self):
        title = self.title_entry.get()
        x_label = self.x_label_entry.get()
        y_label = self.y_label_entry.get()
        x_unit = self.x_unit_entry.get()
        y_unit = self.y_unit_entry.get()
        note = self.note_text.get("1.0", tk.END).strip()

        x_data_str = self.x_data_entry.get("1.0", tk.END).strip()

        if not x_data_str:
            messagebox.showerror("错误", "请填写X轴数据")
            return

        x_data = self.parse_data(x_data_str)
        if x_data is None:
            return

        active_curves = []
        for curve in self.curves:
            data_str = curve['data_entry'].get("1.0", tk.END).strip()
            if data_str and curve['show_var'].get():
                y_data = self.parse_data(data_str)
                if y_data is None:
                    return
                if len(x_data) != len(y_data):
                    legend = curve['legend_entry'].get().strip() or '数据集'
                    messagebox.showerror("错误",
                                         f"X轴和{legend}数据长度不一致：X有{len(x_data)}个，{legend}有{len(y_data)}个")
                    return
                try:
                    y_errors = parse_uncertainty_text(
                        curve['uncertainty_entry'].get(), len(x_data),
                        f"{curve['legend_entry'].get().strip() or '数据集'}的Y不确定度")
                except ValueError as exc:
                    messagebox.showerror("错误", str(exc))
                    return
                active_curves.append(CurveSpec(
                    values=y_data,
                    label=curve['legend_entry'].get().strip() or '数据集',
                    color=curve['color_var'].get(),
                    marker=curve['marker'],
                    errors=y_errors,
                    fit_type=FIT_OPTIONS.get(curve['fit_var'].get(), 'none')))

        if not active_curves:
            messagebox.showerror("错误", "请至少填写一条Y轴曲线数据并确保其显示状态为开启")
            return

        try:
            precision = self.get_precision()
            x_errors = parse_uncertainty_text(
                self.x_uncertainty_entry.get(), len(x_data), "X不确定度")
            x_limits = parse_axis_limits(
                self.x_min_entry.get(), self.x_max_entry.get(), "X轴")
            y_limits = parse_axis_limits(
                self.y_min_entry.get(), self.y_max_entry.get(), "Y轴")
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("错误", str(exc))
            return

        spec = ChartSpec(
            x_values=x_data,
            curves=active_curves,
            x_errors=x_errors,
            title=title,
            note=note,
            x_label=x_label,
            y_label=y_label,
            x_unit=x_unit,
            y_unit=y_unit,
            x_limits=x_limits,
            y_limits=y_limits,
            x_tick_direction=self.x_tick_dir.get(),
            y_tick_direction=self.y_tick_dir.get(),
            precision=precision,
            show_grid=self.grid_var.get(),
            show_legend=self.legend_var.get())
        try:
            self.apply_canvas_size()
            render_result = render_chart(self.ax, spec)
        except ValueError as exc:
            messagebox.showerror("拟合或绘图错误", str(exc))
            return
        self.annotation = render_result.annotation
        self.show_fit_results(render_result.fit_results)
        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.create_annotation()
        self.clear_fit_results()
        self.canvas.draw()

    def save_plot(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG图片", "*.png"),
                                                            ("JPEG图片", "*.jpg"),
                                                            ("PDF文档", "*.pdf"),
                                                            ("SVG图片", "*.svg")])
        if not file_path:
            return
        try:
            self.fig.savefig(file_path, dpi=150, bbox_inches='tight')
        except Exception as exc:
            messagebox.showerror("保存失败", f"图表保存失败：{exc}")
            return
        messagebox.showinfo("成功", "图表已保存")


if __name__ == "__main__":
    root = tk.Tk()
    app = PhysicsPlotTool(root)
    root.mainloop()
