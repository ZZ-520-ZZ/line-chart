from pathlib import Path

import numpy as np
from PIL import Image

from app_state import CurveForm, PlotForm


OUTPUT_DIR = Path(__file__).resolve().parent / "build" / "test-output"


def render_case(name, form, expected_fit_count):
    image_bytes, fits = form.render_image(width=960, height=620)
    path = OUTPUT_DIR / f"{name}.png"
    path.write_bytes(image_bytes)
    with Image.open(path) as image:
        extrema = image.convert("RGB").getextrema()
        assert image.size == (960, 620)
        assert any(low != high for low, high in extrema), "图像内容为空"
    assert len(fits) == expected_fit_count
    return fits


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    linear = PlotForm(
        title="匀速直线运动",
        note="位移随时间变化，含测量不确定度",
        x_label="时间",
        x_unit="s",
        y_label="位移",
        y_unit="m",
        x_uncertainty="0.02",
        curves=[
            CurveForm(
                label="实验组",
                data="1,3,5,7,9",
                uncertainty="0.1",
                fit_type="linear",
            )
        ],
    )
    linear.apply_generated_series("x", "arithmetic", "0", "4", "1")
    linear_fits = render_case("linear_errorbar", linear, 1)
    assert abs(linear_fits[0].parameters["slope"] - 2.0) < 1e-10

    multi = PlotForm(
        title="多组实验对比",
        x_label="自变量",
        y_label="测量值",
        x_data="-2,-1,0,1,2",
        curves=[
            CurveForm(
                label="线性组",
                data="-3,-1,1,3,5",
                fit_type="linear",
            ),
            CurveForm(
                label="二次组",
                data="17,6,1,2,9",
                color="#00798c",
                marker="s",
                fit_type="quadratic",
            ),
        ],
    )
    multi_fits = render_case("multi_curve", multi, 2)
    assert abs(multi_fits[1].parameters["quadratic"] - 3.0) < 1e-10

    exponential = PlotForm(
        title="电容充放电指数关系",
        x_label="时间",
        x_unit="s",
        y_label="电压",
        y_unit="V",
        x_data="0,1,2,3",
        curves=[
            CurveForm(
                label="指数实验组",
                data="2,3.2974425414,5.4365636569,8.9633781407",
                color="#edae49",
                marker="^",
                fit_type="exponential",
            )
        ],
    )
    exponential_fits = render_case("exponential", exponential, 1)
    assert abs(exponential_fits[0].parameters["rate"] - 0.5) < 1e-8

    custom_x = np.linspace(0, 5, 16)
    custom_y = 2.5 * np.sin(1.2 * custom_x + 0.3) + 0.5
    custom = PlotForm(
        title="简谐振动自定义函数拟合",
        note="模型：a*sin(b*x+c)+d",
        x_label="时间",
        x_unit="s",
        y_label="位移",
        y_unit="cm",
        x_data=",".join(f"{value:.12g}" for value in custom_x),
        curves=[
            CurveForm(
                label="振动实验组",
                data=",".join(f"{value:.12g}" for value in custom_y),
                color="#CC79A7",
                marker="D",
                fit_type="custom",
                custom_expression="a*sin(b*x+c)+d",
                custom_initial_values="a=2,b=1,c=0,d=0",
            )
        ],
    )
    custom_fits = render_case("custom_fit", custom, 1)
    assert abs(custom_fits[0].parameters["a"] - 2.5) < 1e-8
    assert abs(custom_fits[0].parameters["b"] - 1.2) < 1e-8
    assert abs(custom_fits[0].parameters["c"] - 0.3) < 1e-8
    assert abs(custom_fits[0].parameters["d"] - 0.5) < 1e-8

    print("CROSS_PLATFORM_SMOKE_PASS cases=4 images=4 fits=5")


if __name__ == "__main__":
    main()
