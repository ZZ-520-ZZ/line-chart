# coding: utf-8
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from tkinter import scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

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
        self.root.title("绘图工具1.0")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TRadiobutton', indicatoron=1)

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

        self.tab_basic = ttk.Frame(nb)
        self.tab_axis = ttk.Frame(nb)
        self.tab_data = ttk.Frame(nb)
        self.tab_series = ttk.Frame(nb)
        self.tab_about = ttk.Frame(nb)

        nb.add(self.tab_basic, text='基本设置')
        nb.add(self.tab_axis, text='坐标轴设置')
        nb.add(self.tab_data, text='数据输入')
        nb.add(self.tab_series, text='数列生成')
        nb.add(self.tab_about, text='关于')

        self.setup_basic_tab()
        self.setup_axis_tab()
        self.setup_data_tab()
        self.setup_series_tab()
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
        self.note_text = scrolledtext.ScrolledText(self.tab_basic, width=40, height=4, font=('Arial', 10))
        self.note_text.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(self.tab_basic, text="显示网格:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.tab_basic, variable=self.grid_var, text="启用网格").pack(anchor=tk.W, padx=10)

        ttk.Label(self.tab_basic, text="显示图例:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.legend_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.tab_basic, variable=self.legend_var, text="显示图例").pack(anchor=tk.W, padx=10)

        ttk.Label(self.tab_basic, text="数值精度:", font=('Arial', 10)).pack(anchor=tk.W, padx=10, pady=(10, 5))
        precision_frame = ttk.Frame(self.tab_basic)
        precision_frame.pack(fill=tk.X, padx=10)
        self.precision_var = tk.IntVar(value=1)
        ttk.Spinbox(precision_frame, from_=0, to=10, textvariable=self.precision_var, width=8).pack(side=tk.LEFT)
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
        x_data_frame = ttk.LabelFrame(self.tab_data, text="X轴数据", padding=10)
        x_data_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(x_data_frame, text="数据值(逗号分隔):", font=('Arial', 10)).pack(anchor=tk.W, pady=5)
        self.x_data_entry = scrolledtext.ScrolledText(x_data_frame, width=40, height=4, font=('Arial', 10))
        self.x_data_entry.pack(fill=tk.X, pady=(0, 5))
        add_undo_support(self.x_data_entry)

        x_button_frame = ttk.Frame(x_data_frame)
        x_button_frame.pack(fill=tk.X)
        ttk.Button(x_button_frame, text="清除", command=lambda: self.x_data_entry.delete(1.0, tk.END),
                   width=8).pack(side=tk.RIGHT)
        ttk.Button(x_button_frame, text="从数列导入", command=self.import_x_from_series,
                   width=12).pack(side=tk.RIGHT, padx=5)

        curves_header = ttk.Frame(self.tab_data)
        curves_header.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(curves_header, text="Y轴曲线（可添加多个）", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(curves_header, text="+ 添加曲线", command=self.add_curve, width=10).pack(side=tk.RIGHT)

        self.curves_container = ttk.Frame(self.tab_data)
        self.curves_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.data_canvas = tk.Canvas(self.curves_container, highlightthickness=0)
        self.data_scrollbar = ttk.Scrollbar(self.curves_container, orient="vertical", command=self.data_canvas.yview)
        self.data_scroll_frame = ttk.Frame(self.data_canvas)

        self.data_scroll_frame.bind("<Configure>",
                                    lambda e: self.data_canvas.configure(scrollregion=self.data_canvas.bbox("all")))
        self.data_canvas.create_window((0, 0), window=self.data_scroll_frame, anchor="nw", width=380)
        self.data_canvas.configure(yscrollcommand=self.data_scrollbar.set)

        def on_data_mousewheel(event):
            self.data_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.data_canvas.bind("<Enter>", lambda e: self.data_canvas.bind_all("<MouseWheel>", on_data_mousewheel))
        self.data_canvas.bind("<Leave>", lambda e: self.data_canvas.unbind_all("<MouseWheel>"))

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
        ttk.Radiobutton(target_frame, text="X轴数据", variable=self.target_var, value="x").pack(side=tk.LEFT, padx=10)

        self.target_combo = ttk.Combobox(target_frame, state='readonly', width=15)
        self.target_combo.pack(side=tk.LEFT, padx=5)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_combo_change)
        self.target_combo['values'] = ["Y轴曲线1", "Y轴曲线2"]
        self.target_combo.current(0)

        button_frame = ttk.Frame(params_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="生成数列", command=self.generate_series,
                   style='Accent.TButton').pack(fill=tk.X, padx=20)

        preview_frame = ttk.LabelFrame(self.tab_series, text="生成预览", padding=10)
        preview_frame.pack(fill=tk.X, padx=10, pady=10)
        self.preview_text = scrolledtext.ScrolledText(preview_frame, width=40, height=3, font=('Arial', 10))
        self.preview_text.pack(fill=tk.X)

        self.style.map('Accent.TButton',
                       background=[('active', '#1a73e8'), ('pressed', '#1557b0')],
                       foreground=[('active', 'white'), ('pressed', 'white')])

    def setup_about_tab(self):
        about_frame = ttk.Frame(self.tab_about)
        about_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(about_frame, text="绘图工具1.0", font=('Arial', 16, 'bold')).pack(pady=(10, 5))
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
        options = []
        for i, curve in enumerate(self.curves):
            options.append(f"Y轴曲线{i + 1}")
        self.target_combo['values'] = options
        if options:
            self.target_combo.current(0)

    def on_target_combo_change(self, event=None):
        idx = self.target_combo.current()
        if idx >= 0:
            self.target_var.set(f"y{idx}")
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

        curve_frame = ttk.LabelFrame(self.data_scroll_frame, text=f"曲线 {idx + 1}", padding=8)
        curve_frame.pack(fill=tk.X, pady=5)

        header_row = ttk.Frame(curve_frame)
        header_row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(header_row, text="图例标签:", font=('Arial', 10)).pack(side=tk.LEFT)
        legend_entry = UndoEntry(header_row, width=12, font=('Arial', 10))
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

        ttk.Button(header_row, text="颜色", command=choose_curve_color, width=5).pack(side=tk.LEFT, padx=3)

        show_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(header_row, variable=show_var, text="显示").pack(side=tk.LEFT, padx=5)

        def remove_curve(frm=curve_frame, cid=curve_id):
            self.remove_curve_by_id(cid)

        ttk.Button(header_row, text="删除", command=remove_curve, width=5).pack(side=tk.RIGHT)

        ttk.Label(curve_frame, text="数据值(逗号分隔):", font=('Arial', 10)).pack(anchor=tk.W, pady=(3, 2))
        data_entry = scrolledtext.ScrolledText(curve_frame, width=40, height=3, font=('Arial', 10))
        data_entry.pack(fill=tk.X, pady=(0, 3))
        add_undo_support(data_entry)

        btn_row = ttk.Frame(curve_frame)
        btn_row.pack(fill=tk.X)
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
            curve['legend_entry'].delete(0, tk.END)
            curve['legend_entry'].insert(0, f'数据集{i + 1}')

        self.refresh_target_combo()

    def setup_right_panel(self, parent):
        canvas_frame = ttk.LabelFrame(parent, text="图表预览", padding=5)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        self.annotation = self.ax.annotate("", xy=(0, 0), xytext=(20, 20),
                                           textcoords="offset points",
                                           bbox=dict(boxstyle="round", fc="w"),
                                           arrowprops=dict(arrowstyle="->"))
        self.annotation.set_visible(False)

        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="绘制图表", command=self.plot_graph,
                   style='Accent.TButton').pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(button_frame, text="清除图表", command=self.clear_plot).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(button_frame, text="保存图表", command=self.save_plot).pack(side=tk.LEFT, expand=True, padx=5)

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
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

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
            canvas.unbind_all("<MouseWheel>")
            if self.symbol_mode.get() == 'latex' and symbol in LATEX_SYMBOLS:
                target_entry.insert(tk.END, LATEX_SYMBOLS[symbol])
            else:
                target_entry.insert(tk.END, symbol)
            symbol_window.destroy()

        def on_window_close():
            canvas.unbind_all("<MouseWheel>")
            symbol_window.destroy()

        symbol_window.protocol("WM_DELETE_WINDOW", on_window_close)

        refresh_symbols()

    def generate_series(self):
        try:
            start = float(self.start_entry.get())
            end = float(self.end_entry.get())

            if self.series_var.get() == "arithmetic":
                step = float(self.step_entry.get())
                data = np.arange(start, end + step / 2, step).tolist()
            else:
                ratio = float(self.step_entry.get())
                data = []
                current = start
                if ratio > 1:
                    while current <= end + 0.0001:
                        data.append(current)
                        current *= ratio
                elif ratio < 1:
                    while current >= end - 0.0001:
                        data.append(current)
                        current *= ratio
                else:
                    data = [start]

            if len(data) > 1000:
                messagebox.showerror("错误", "生成的数据点过多，请调整参数")
                return

            precision = self.precision_var.get()
            data_str = ','.join([f'{x:.{precision}f}' for x in data])

            self.preview_text.delete(1.0, tk.END)
            preview = data_str[:200] + '...' if len(data_str) > 200 else data_str
            self.preview_text.insert(1.0, preview)

            target = self.target_var.get()
            if target == "x":
                self.x_data_entry.delete(1.0, tk.END)
                self.x_data_entry.insert(1.0, data_str)
            elif target.startswith("y"):
                idx = int(target[1:])
                if 0 <= idx < len(self.curves):
                    self.curves[idx]['data_entry'].delete(1.0, tk.END)
                    self.curves[idx]['data_entry'].insert(1.0, data_str)

        except ValueError as e:
            messagebox.showerror("错误", f"请输入有效的数字：{str(e)}")

    def import_x_from_series(self):
        self.target_var.set("x")
        self.generate_series()

    def import_y_from_series(self, curve_id):
        for i, curve in enumerate(self.curves):
            if curve['id'] == curve_id:
                self.target_var.set(f"y{i}")
                self.target_combo.current(i)
                self.generate_series()
                break

    def on_hover(self, event):
        if event.inaxes == self.ax:
            for line in self.ax.lines:
                contains, info = line.contains(event)
                if contains:
                    x, y = event.xdata, event.ydata
                    self.annotation.xy = (x, y)
                    precision = self.precision_var.get()
                    text = f"({x:.{precision}f}, {y:.{precision}f})"
                    self.annotation.set_text(text)
                    self.annotation.set_visible(True)
                    self.canvas.draw()
                    return
        self.annotation.set_visible(False)
        self.canvas.draw()

    def parse_data(self, data_str):
        data_str = data_str.replace('，', ',').strip()
        if not data_str:
            return []
        try:
            return [float(x.strip()) for x in data_str.split(',')]
        except ValueError:
            messagebox.showerror("错误", "数据格式错误，请输入数字并用逗号分隔")
            return None

    def plot_graph(self):
        title = self.title_entry.get()
        x_label = self.x_label_entry.get()
        y_label = self.y_label_entry.get()
        x_unit = self.x_unit_entry.get()
        y_unit = self.y_unit_entry.get()

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
                active_curves.append((curve, y_data))

        if not active_curves:
            messagebox.showerror("错误", "请至少填写一条Y轴曲线数据并确保其显示状态为开启")
            return

        self.ax.clear()

        precision = self.precision_var.get()

        jitter_offset = 0.015
        curve_offsets = []

        for idx, (curve, y_data) in enumerate(active_curves):
            y_jittered = np.array(y_data) + (idx * jitter_offset)
            curve_offsets.append(idx * jitter_offset)
            color = curve['color_var'].get()
            legend = curve['legend_entry'].get().strip() or '数据集'
            marker = curve['marker']
            self.ax.plot(x_data, y_jittered, marker=marker, linestyle='-', color=color,
                         linewidth=2, markersize=8, label=legend, clip_on=False)

        full_x_label = f"{x_label} ({x_unit})" if x_unit else x_label
        full_y_label = f"{y_label} ({y_unit})" if y_unit else y_label

        self.ax.set_title(title, fontsize=14, pad=20)
        self.ax.set_xlabel(full_x_label, fontsize=12, labelpad=10)
        self.ax.set_ylabel(full_y_label, fontsize=12, labelpad=10)

        x_min = self.x_min_entry.get().strip()
        x_max = self.x_max_entry.get().strip()
        y_min = self.y_min_entry.get().strip()
        y_max = self.y_max_entry.get().strip()

        if x_min and x_max:
            try:
                self.ax.set_xlim(float(x_min), float(x_max))
            except ValueError:
                pass

        if y_min and y_max:
            try:
                self.ax.set_ylim(float(y_min), float(y_max))
            except ValueError:
                pass

        self.ax.tick_params(axis='x', direction=self.x_tick_dir.get())
        self.ax.tick_params(axis='y', direction=self.y_tick_dir.get())

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)

        if self.grid_var.get():
            self.ax.grid(True, linestyle='--', alpha=0.7)

        if self.legend_var.get():
            self.ax.legend(fontsize=10)

        self.ax.ticklabel_format(useOffset=False)
        self.ax.xaxis.set_major_formatter(lambda x, pos: f'{x:.{precision}f}')
        self.ax.yaxis.set_major_formatter(lambda x, pos: f'{x:.{precision}f}')

        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.canvas.draw()

    def save_plot(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png",
                                                 filetypes=[("PNG图片", "*.png"),
                                                            ("JPEG图片", "*.jpg"),
                                                            ("PDF文档", "*.pdf"),
                                                            ("SVG图片", "*.svg")])
        if file_path:
            self.fig.savefig(file_path, dpi=150, bbox_inches='tight')
            messagebox.showinfo("成功", "图表已保存")


if __name__ == "__main__":
    root = tk.Tk()
    app = PhysicsPlotTool(root)
    root.mainloop()
