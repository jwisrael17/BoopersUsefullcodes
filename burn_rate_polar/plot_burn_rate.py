"""Compare experiment and simulation by orientation, grouped by test conditions."""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save files on desktops and headless compute nodes.
import matplotlib.pyplot as plt
import numpy as np


REQUIRED = {
    "source", "u", "v", "w", "heat_flux_kw_m2", "cutoff_s", "burn_rate_mm_s"
}
STYLES = {
    "experiment": {"color": "tab:blue", "marker": "o", "label": "Experiment"},
    "simulation": {"color": "tab:orange", "marker": "^", "label": "Simulation"},
}


@dataclass(frozen=True)
class Measurement:
    source: str
    vector: tuple
    flux: float
    cutoff: float
    rate: float
    error: object = None


def angle_from_normal(vector, normal=(1, 0, 0)):
    """Return radians from a reference normal; both vectors share Cartesian axes."""
    unit_vectors = []
    for value in (vector, normal):
        value = np.asarray(value, dtype=float)
        if value.shape != (3,) or not np.all(np.isfinite(value)):
            raise ValueError("Vectors must contain three finite numbers.")
        scale = np.max(np.abs(value))
        if scale == 0:
            raise ValueError("Vectors cannot be zero.")
        value = value / scale
        unit_vectors.append(value / np.linalg.norm(value))
    return float(np.arccos(np.clip(np.dot(*unit_vectors), -1, 1)))


def load_measurements(path):
    measurements = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            try:
                source = row["source"].strip().lower()
                if source not in STYLES:
                    raise ValueError("source must be experiment or simulation")
                vector = tuple(float(row[key]) for key in ("u", "v", "w"))
                angle_from_normal(vector)
                flux, cutoff, rate = (
                    float(row[key]) for key in
                    ("heat_flux_kw_m2", "cutoff_s", "burn_rate_mm_s")
                )
                error_text = (row.get("rate_error_mm_s") or "").strip()
                error = float(error_text) if error_text else None
                values = [flux, cutoff, rate] + ([] if error is None else [error])
                if any(not np.isfinite(x) or x < 0 for x in values):
                    raise ValueError("Rates, errors, fluxes, and times must be finite and nonnegative")
                if error is not None and error > rate:
                    raise ValueError("Error bar extends below zero; use a suitable uncertainty representation")
                measurements.append(Measurement(source, vector, flux, cutoff, rate, error))
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValueError(f"{path}, line {line}: {exc}") from exc
    if not measurements:
        raise ValueError(f"{path}: no measurements")
    return measurements


def group_conditions(measurements):
    groups = {}
    for row in measurements:
        groups.setdefault((row.flux, row.cutoff), []).append(row)
    return groups


def plot_condition(rows, normal, title, reference_label, output, annotate):
    fig, ax = plt.subplots(figsize=(8, 7), subplot_kw={"projection": "polar"})
    angles = [angle_from_normal(row.vector, normal) for row in rows]
    limit = 90 if max(angles) <= np.pi / 2 + 1e-10 else 180
    radial_max = max(row.rate + (row.error or 0) for row in rows)
    for source, style in STYLES.items():
        selected = [row for row in rows if row.source == source]
        if not selected:
            continue
        ax.scatter([angle_from_normal(row.vector, normal) for row in selected],
                   [row.rate for row in selected], s=65, zorder=3, clip_on=False, **style)
        for row in selected:
            angle = angle_from_normal(row.vector, normal)
            if row.error is not None:
                ax.errorbar(angle, row.rate, yerr=row.error, fmt="none",
                            ecolor=style["color"], capsize=3)
            if annotate:
                label = "[" + ", ".join(f"{x:g}" for x in row.vector) + "]"
                offset = 8 if source == "experiment" else -15
                if angle < 1e-10 and source == "simulation":
                    offset = 24  # Keep endpoint labels clear of radial tick labels.
                ax.annotate(label, (angle, row.rate), xytext=(6, offset),
                            textcoords="offset points", fontsize=8, color=style["color"])
    ax.set_theta_zero_location("E")
    ax.set_thetamin(0)
    ax.set_thetamax(limit)
    ax.set_thetagrids(np.arange(0, limit + 1, 15))
    ax.set_ylim(0, max(radial_max * 1.25, 1))
    ax.grid(alpha=0.5)
    ax.set_title(f"{title}\nHeat flux: {rows[0].flux:g} kW/m²; "
                 f"laser cutoff: {rows[0].cutoff:g} s", pad=30)
    ax.set_xlabel(f"Angle from {reference_label}\nRadius: burn rate (mm/s)", labelpad=25)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="One or more measurement CSV files")
    parser.add_argument("--output-dir", type=Path, default=Path("polar_plots"))
    parser.add_argument("--title", default="Burn rate vs. orientation")
    parser.add_argument("--normal", nargs=3, type=float, default=(1, 0, 0),
                        metavar=("NX", "NY", "NZ"), help="Reference normal in the same Cartesian frame")
    parser.add_argument("--reference-label", default="(100) normal")
    parser.add_argument("--format", choices=("png", "pdf", "svg"), default="png")
    parser.add_argument("--no-labels", action="store_true", help="Hide vector annotations")
    args = parser.parse_args()
    try:
        angle_from_normal(args.normal, args.normal)
        # Validate all inputs before producing any plots.
        datasets = [(path, load_measurements(path)) for path in args.inputs]
        stems = [path.stem for path, _ in datasets]
        if len(stems) != len(set(stems)):
            raise ValueError("Input filenames must have distinct stems to avoid output collisions.")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for path, measurements in datasets:
            groups = group_conditions(measurements)
            for index, (condition, rows) in enumerate(sorted(groups.items()), start=1):
                flux, cutoff = condition
                output = args.output_dir / (
                    f"{path.stem}_{index:03d}_flux-{flux:g}_cutoff-{cutoff:g}.{args.format}"
                )
                if {row.source for row in rows} != set(STYLES):
                    print(f"Note: {path.name}, flux={flux:g}, cutoff={cutoff:g}: "
                          "only one data source is present.")
                plot_condition(rows, args.normal, args.title, args.reference_label,
                               output, not args.no_labels)
                print(f"Saved {output}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
