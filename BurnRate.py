from pathlib import Path
import argparse
import csv
import glob
import os
import sys

import numpy as np
import yt

yt.set_log_level(40)

INCH_IN_METERS = 0.0254
RESULT_TABLE = Path(__file__).with_name("burn_rate_table.csv")
RESULT_COLUMNS = [
    "data_file_name",
    "burn_rate_m_per_s",
    "burn_rate_in_per_s",
    "number_of_points_used",
]


def find_field(ds, field_name):
    for field in ds.field_list:
        if field[1] == field_name:
            return field
    raise RuntimeError(f"Could not find field named {field_name}")


def plotfile_number(path):
    return int(path.name.replace("cell", ""))


def front_position(plotfile):
    ds = yt.load(str(plotfile))
    dims = np.asarray(ds.domain_dimensions, dtype=int)
    grid = ds.covering_grid(0, ds.domain_left_edge, dims)

    eta = np.asarray(grid[find_field(ds, "rigid_eta")])
    profile = eta.mean(axis=(0, 2))

    ylo = float(ds.domain_left_edge[1])
    yhi = float(ds.domain_right_edge[1])
    dy = (yhi - ylo) / dims[1]
    y = ylo + (np.arange(dims[1]) + 0.5) * dy

    shifted = profile - 0.5
    crossings = np.where(shifted[:-1] * shifted[1:] <= 0.0)[0]
    if len(crossings) == 0:
        return float(ds.current_time), None

    i = int(crossings[0])
    denominator = profile[i + 1] - profile[i]

    if denominator == 0.0:
        fraction = 0.5
    else:
        fraction = (0.5 - profile[i]) / denominator

    position = y[i] + fraction * (y[i + 1] - y[i])
    return float(ds.current_time), float(position)


def calculate_burn_rate(output_folder):
    output_folder = Path(output_folder).expanduser().resolve()
    plotfiles = sorted(output_folder.glob("*cell"), key=plotfile_number)

    if len(plotfiles) < 2:
        raise RuntimeError(f"Could not find enough plotfiles in {output_folder}")

    samples = []

    for index, plotfile in enumerate(plotfiles, start=1):
        print(f"  Plotfile {index}/{len(plotfiles)}: {plotfile.name}", flush=True)
        time, position = front_position(plotfile)

        if position is not None:
            samples.append((time, position))

    if len(samples) < 2:
        raise RuntimeError("Could not find the rigid_eta = 0.5 front in enough files")

    times = np.asarray([sample[0] for sample in samples])
    positions = np.asarray([sample[1] for sample in samples])

    slope_m_per_s, _ = np.polyfit(times, positions, 1)

    burn_rate_m_per_s = abs(float(slope_m_per_s))
    burn_rate_in_per_s = burn_rate_m_per_s / INCH_IN_METERS

    return output_folder, burn_rate_m_per_s, burn_rate_in_per_s, len(samples)


def append_result(output_folder, burn_rate_m_per_s, burn_rate_in_per_s, samples):
    columns = RESULT_COLUMNS
    table_exists = RESULT_TABLE.exists() and RESULT_TABLE.stat().st_size > 0
    if table_exists:
        with RESULT_TABLE.open(newline="") as stream:
            columns = next(csv.reader(stream))
        if not set(RESULT_COLUMNS).issubset(columns):
            raise ValueError(f"Unexpected CSV columns in {RESULT_TABLE}")

    with RESULT_TABLE.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        if not table_exists:
            writer.writeheader()
        writer.writerow({
            "data_file_name": Path(output_folder).name,
            "burn_rate_m_per_s": f"{burn_rate_m_per_s:.8g}",
            "burn_rate_in_per_s": f"{burn_rate_in_per_s:.8g}",
            "number_of_points_used": samples,
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output_folder", nargs="+",
        help="ALAMO output folders or quoted wildcard patterns, e.g. 'run_*'",
    )
    args = parser.parse_args()
    folders = {}
    for pattern in args.output_folder:
        for match in sorted(glob.glob(os.path.expanduser(pattern))):
            folder = Path(match).resolve()
            if folder.is_dir():
                folders[folder] = None
    if not folders:
        parser.error(f"No folders matched {args.output_folder!r} in {Path.cwd()}")

    runs = list(folders)

    print(f"Found {len(runs)} matching folder(s).", flush=True)
    failures = 0
    for index, folder in enumerate(runs, start=1):
        print(f"[{index}/{len(runs)}] Analyzing {folder}", flush=True)
        try:
            output_folder, burn_rate_m_per_s, burn_rate_in_per_s, samples = (
                calculate_burn_rate(folder)
            )
            append_result(output_folder, burn_rate_m_per_s, burn_rate_in_per_s,
                          samples)
        except Exception as error:
            failures += 1
            print(f"Failed {folder}: {error}", file=sys.stderr, flush=True)
            continue

        print(f"Folder name: {output_folder.name}")
        print(f"Burn rate:  {burn_rate_m_per_s:.8g} m/s")
        print(f"Burn rate:  {burn_rate_in_per_s:.8g} in/s")
        print(f"Saved row to: {RESULT_TABLE}", flush=True)

    print(f"Completed: {len(runs) - failures}; failed: {failures}.", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
