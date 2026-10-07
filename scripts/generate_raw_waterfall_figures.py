from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
if (SCRIPT_DIR.parent / "ml").exists():
    ROOT = SCRIPT_DIR.parent
elif (SCRIPT_DIR.parent.parent / "ml").exists():
    ROOT = SCRIPT_DIR.parent.parent
else:
    ROOT = SCRIPT_DIR.parent

FIGURES_DIR = ROOT / "overleaf_thesis" / "figures"
if not FIGURES_DIR.exists() and (SCRIPT_DIR.parent / "figures").exists():
    FIGURES_DIR = SCRIPT_DIR.parent / "figures"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def format_value(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number.is_integer():
        return str(int(number))
    return f"{number:.3f}".rstrip("0").rstrip(".")


def draw_waterfall(
    title: str,
    base_value: float,
    final_value: float,
    rows: list[tuple[str, str, float]],
    output_path: Path,
    xlabel: str,
) -> None:
    # Rows are passed from base to final. Display largest contributors at top.
    display_rows = list(reversed(rows))
    fig_height = max(6.0, 0.43 * len(display_rows) + 1.6)
    fig, ax = plt.subplots(figsize=(11, fig_height))

    running = base_value
    starts: list[float] = []
    widths: list[float] = []
    colors: list[str] = []
    labels: list[str] = []

    for feature, raw_value, contribution in rows:
        start = running if contribution >= 0 else running + contribution
        starts.append(start)
        widths.append(abs(contribution))
        colors.append("#ff0051" if contribution >= 0 else "#008bfb")
        labels.append(feature if raw_value == "" else f"{format_value(raw_value)} = {feature}")
        running += contribution

    starts = list(reversed(starts))
    widths = list(reversed(widths))
    colors = list(reversed(colors))
    labels = list(reversed(labels))
    contribs = list(reversed([r[2] for r in rows]))

    y_pos = list(range(len(display_rows)))
    ax.barh(y_pos, widths, left=starts, color=colors, height=0.78, edgecolor="white", linewidth=1)

    span = max(abs(final_value - base_value), max(abs(v) for v in contribs), 1.0)
    for y, start, width, contribution in zip(y_pos, starts, widths, contribs):
        text_x = start + width / 2
        label = f"{contribution:+.2f}".rstrip("0").rstrip(".")
        if width < (span * 0.05):
            text_x = start + width + 0.02 * (final_value - base_value)
            ha = "left"
            text_color = "#ff0051" if contribution >= 0 else "#008bfb"
        else:
            ha = "center"
            text_color = "white"
        ax.text(text_x, y, label, va="center", ha=ha, fontsize=10, color=text_color)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.axvline(base_value, color="#777777", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.axvline(final_value, color="#777777", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.text(base_value, len(display_rows) + 0.15, f"E[f(X)] = {base_value:.3f}", ha="center", va="bottom", fontsize=10, color="#555555")
    ax.text(final_value, -0.85, f"f(x) = {final_value:.3f}", ha="center", va="bottom", fontsize=11, color="#555555")
    ax.set_title(title, fontsize=13, pad=18)
    ax.set_xlabel(xlabel)
    ax.grid(axis="y", linestyle=":", alpha=0.35)
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def build_classification_waterfall() -> None:
    raw_rows = read_csv_rows(ROOT / "ml" / "classification" / "data" / "not_processed" / "X_test.csv")
    sample = raw_rows[52]

    contributions = [
        ("29 other features", "", 0.23),
        ("is_data_expert", sample["is_data_expert"], 0.13),
        ("machine_learning", sample["machine_learning"], 0.13),
        ("communication", sample["communication"], -0.14),
        ("da_score_v2", sample["da_score_v2"], 0.14),
        ("de_score", sample["de_score"], 0.14),
        ("tech_soft_ratio", sample["tech_soft_ratio"], 0.16),
        ("ce_score", sample["ce_score"], 0.18),
        ("sql", sample["sql"], 0.19),
        ("ds_score", sample["ds_score"], 0.19),
        ("da_score", sample["da_score"], 0.31),
        ("python", sample["python"], 0.36),
        ("problem_solving", sample["problem_solving"], 0.84),
        ("gpa", sample["gpa"], 0.94),
        ("is_heavy_ml", sample["is_heavy_ml"], 2.20),
    ]

    draw_waterfall(
        title="Why the classifier predicted Machine Learning Engineer (raw feature values)",
        base_value=-0.673,
        final_value=5.329,
        rows=contributions,
        output_path=FIGURES_DIR / "classification_waterfall_raw_values.png",
        xlabel="Model output contribution",
    )


def build_demand_waterfall() -> None:
    raw_rows = read_csv_rows(ROOT / "ml" / "demand prediction" / "data" / "before_preprocessor" / "X_test.csv")
    sample = raw_rows[27]

    contributions = [
        ("is_month_end", sample["is_month_end"], 0.10),
        ("is_may_holidays", sample["is_may_holidays"], -0.76),
        ("is_nauryz_week", sample["is_nauryz_week"], 1.89),
        ("is_early_summer_recovery", sample["is_early_summer_recovery"], 6.52),
        ("is_q2_low", sample["is_q2_low"], 7.07),
        ("is_main_hiring_peak", sample["is_main_hiring_peak"], -12.22),
        ("is_summer_hiring_peak", sample["is_summer_hiring_peak"], -17.53),
        ("diff_3", sample["diff_3"], 28.21),
        ("residual_lag2", sample["residual_lag2"], 31.97),
        ("is_may_slowdown", sample["is_may_slowdown"], 33.96),
        ("rolling_std_4", sample["rolling_std_4"], 55.04),
        ("residual_lag1", sample["residual_lag1"], 109.50),
        ("job_title_unified", sample["job_title_unified"], 289.23),
        ("expanding_std", sample["expanding_std"], 1844.49),
    ]

    draw_waterfall(
        title="Why the demand model predicted high vacancies (raw feature values)",
        base_value=2123.516,
        final_value=4500.981,
        rows=contributions,
        output_path=FIGURES_DIR / "demand_waterfall_raw_values.png",
        xlabel="Predicted vacancies contribution",
    )


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    build_classification_waterfall()
    build_demand_waterfall()
    print("Saved:")
    print(FIGURES_DIR / "classification_waterfall_raw_values.png")
    print(FIGURES_DIR / "demand_waterfall_raw_values.png")


if __name__ == "__main__":
    main()
