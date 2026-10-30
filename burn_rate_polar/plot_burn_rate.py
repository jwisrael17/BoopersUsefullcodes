"""Compare experiment and simulation by orientation, grouped by test conditions."""

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save files on desktops and headless compute nodes.
import matplotlib.pyplot as plt
import numpy as np


REQUIRED = {
    "source", "u", "v", "w", "heat_flux_kw_m2", "cutoff_s", "burn_rate_mm_s"
}
SIMPLE_COLUMNS = {"face", "experimental_burn_rate", "simulated_burn_rate"}
HKL_COLUMNS = {"h", "k", "l", "experimental_burn_rate", "simulated_burn_rate"}
HEADER_ALIASES = {
    "expermental": "experimental_burn_rate",
    "experimental": "experimental_burn_rate",
    "simulated": "simulated_burn_rate",
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
    face: str = ""


def parse_face(text):
    """Read cubic faces like 110, (110), or a quoted '(1, -1, 0)'."""
    text = text.strip().strip("()[]").strip()
    if re.fullmatch(r"[0-9]{3}", text):
        vector = tuple(int(x) for x in text)
    else:
        parts = re.split(r"[\s,]+", text)
        if len(parts) != 3 or any(not re.fullmatch(r"[+-]?\d+", p) for p in parts):
            raise ValueError("face must look like 100, (110), or a quoted '(1, -1, 0)'")
        vector = tuple(int(p) for p in parts)
    angle_from_normal(vector)
    return vector


def read_simple_row(row):
    if "face" in row:
        vector = parse_face(row["face"])
    else:
        vector = tuple(float(row[key]) for key in ("h", "k", "l"))
        angle_from_normal(vector)
    face = "(" + " ".join(f"{x:g}" for x in vector) + ")"
    measurements = []
    for source, column in (("experiment", "experimental_burn_rate"),
                           ("simulation", "simulated_burn_rate")):
        text = (row[column] or "").strip()
        if not text:
            continue
        rate = float(text)
        if not np.isfinite(rate) or rate < 0:
            raise ValueError("Burn rates must be finite and nonnegative")
        measurements.append(Measurement(source, vector, None, None, rate, face=face))
    if not measurements:
        raise ValueError("Provide at least one burn rate for each face")
    return measurements


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
        reader.fieldnames = [HEADER_ALIASES.get(name.strip().lower(), name.strip().lower())
                             for name in (reader.fieldnames or [])]
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{path}: duplicate column names")
        fields = set(reader.fieldnames or [])
        hkl = bool(fields & {"h", "k", "l"})
        simple = "face" in fields or hkl
        columns = HKL_COLUMNS if hkl else (SIMPLE_COLUMNS if simple else REQUIRED)
        missing = columns - fields
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            try:
                if None in row:
                    raise ValueError("Too many columns; put faces containing commas inside double quotes")
                if any(value is None for value in row.values()):
                    raise ValueError("Missing columns in this row; keep empty fields as commas")
                if simple:
                    measurements.extend(read_simple_row(row))
                    continue
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
    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={"projection": "polar"})
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
                label = row.face or ("[" + ", ".join(f"{x:g}" for x in row.vector) + "]")
                offset = 8 if source == "experiment" else -15
                if angle < 1e-10 and source == "simulation":
                    offset = 24  # Keep endpoint labels clear of radial tick labels.
                ax.annotate(label, (angle, row.rate), xytext=(6, offset),
                            textcoords="offset points", fontsize=8, color=style["color"])
    ax.set_theta_zero_location("E")
    ax.set_thetamin(0)
    ax.set_thetamax(limit)
    ax.set_thetagrids(np.arange(0, limit + 1, 15))
    # Fit small rates too: a fixed minimum of 1 compresses them at the origin.
    ax.set_ylim(0, radial_max * 1.10 if radial_max > 0 else 1)
    ax.grid(alpha=0.5)
    if rows[0].flux is not None:
        title += (f"\nHeat flux: {rows[0].flux:g} kW/m²; "
                  f"laser cutoff: {rows[0].cutoff:g} s")
    ax.set_title(title, pad=30)
    ax.set_xlabel(f"Angle from {reference_label}\nRadius: burn rate (mm/s)", labelpad=25)
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="One or more measurement CSV files")
    parser.add_argument("--output-dir", type=Path, default=Path("polar_plots"))
    parser.add_argument("--title", help="Override the default title (CSV filename without extension)")
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
                suffix = (f"_{index:03d}_flux-{flux:g}_cutoff-{cutoff:g}"
                          if flux is not None else "_polar")
                output = args.output_dir / f"{path.stem}{suffix}.{args.format}"
                if {row.source for row in rows} != set(STYLES):
                    print(f"Note: {path.name}{suffix}: "
                          "only one data source is present.")
                plot_condition(rows, args.normal, args.title if args.title is not None else path.stem,
                               args.reference_label,
                               output, not args.no_labels)
                print(f"Saved {output}")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
