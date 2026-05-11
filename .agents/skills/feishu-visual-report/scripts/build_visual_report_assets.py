#!/usr/bin/env python3
"""Build a Markdown draft and chart assets for visual Feishu analysis reports."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager


def configure_fonts():
    candidates = [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            prop = font_manager.FontProperties(fname=str(path))
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False


def fmt_value(value):
    if isinstance(value, float):
        return f"{value:.2%}" if 0 <= value <= 1 else f"{value:.2f}"
    return str(value)


def write_markdown(spec, out_dir):
    lines = []
    lines.append(f"# {spec['title']}")
    lines.append("")
    lines.append("## 结论卡片")
    lines.append("")
    lines.append(spec.get("verdict", "待补充结论。"))
    lines.append("")
    lines.append("## 数据口径")
    lines.append("")
    if spec.get("period"):
        lines.append(f"- 周期：{spec['period']}")
    if spec.get("audience"):
        lines.append(f"- 人群：{spec['audience']}")
    for item in spec.get("assumptions", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 关键指标")
    lines.append("")
    for item in spec.get("metrics", []):
        lines.append(f"- {item['name']}：{fmt_value(item['value'])}")
    lines.append("")
    if spec.get("groups"):
        lines.append("## 分组数据")
        lines.append("")
        for group in spec["groups"]:
            group_name = group.get("group", "未命名分组")
            lines.append(f"- {group_name}")
            for key, value in group.items():
                if key == "group":
                    continue
                lines.append(f"- {key}：{fmt_value(value)}")
        lines.append("")
    lines.append("## 分析与解读")
    lines.append("")
    for item in spec.get("diagnosis", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 建议")
    lines.append("")
    for item in spec.get("recommendations", []):
        lines.append(f"- {item}")
    lines.append("")
    path = out_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def plot_group_rates(spec, charts_dir):
    groups = spec.get("groups") or []
    rate_keys = [key for key in ("visit_rate", "order_rate", "redeem_rate", "unsubscribe_rate") if any(key in g for g in groups)]
    if not groups or not rate_keys:
        return []

    labels = [g.get("group", f"组{i + 1}") for i, g in enumerate(groups)]
    paths = []
    zh = {
        "visit_rate": "来访率",
        "order_rate": "下单率",
        "redeem_rate": "核销率",
        "unsubscribe_rate": "退订率",
    }
    colors = ["#1F7A4D", "#8A8F98", "#E7A23A", "#B94A48"]

    for rate_key in rate_keys:
        values = [float(g.get(rate_key, 0) or 0) * 100 for g in groups]
        fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
        bars = ax.bar(labels, values, color=colors[: len(labels)])
        ax.set_title(f"{zh.get(rate_key, rate_key)}对比", fontsize=14, pad=14)
        ax.set_ylabel("%")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.2f}%", ha="center", va="bottom", fontsize=10)
        fig.tight_layout()
        path = charts_dir / f"{rate_key}.png"
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def write_airy_brief(spec, chart_paths, out_dir):
    lines = [
        f"# Airy 美化需求：{spec['title']}",
        "",
        "请把这份分析做成图文结合的内部复盘文档。",
        "",
        "## 视觉要求",
        "",
        "- 顶部放一句话结论卡片。",
        "- 中部放关键指标卡和 A/B 对比图。",
        "- 下部放漏斗诊断和下一步建议。",
        "- 风格简洁、业务汇报感强，不要营销海报风。",
        "",
        "## 图表资产",
        "",
    ]
    for path in chart_paths:
        lines.append(f"- {path}")
    path = out_dir / "airy_brief.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path to visual report JSON spec")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    args = parser.parse_args()

    configure_fonts()
    spec_path = Path(args.spec).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    report_path = write_markdown(spec, out_dir)
    chart_paths = plot_group_rates(spec, charts_dir)
    airy_path = write_airy_brief(spec, chart_paths, out_dir)

    print(json.dumps({
        "report": str(report_path),
        "charts": [str(path) for path in chart_paths],
        "airy_brief": str(airy_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
