"""Print a simulation run's burn rate in m/s and in/s without writing a CSV."""

import argparse
import sys
from pathlib import Path

from BurnRate import calculate_burn_rate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_folder", type=Path,
                        help="ALAMO output folder containing the numbered *cell plotfiles")
    args = parser.parse_args()
    folder = args.output_folder.expanduser()
    if not folder.is_dir():
        parser.error(f"Not an output folder: {folder}")
    try:
        folder, meters_per_second, inches_per_second, samples = calculate_burn_rate(folder)
    except Exception as error:
        print(f"Failed: {error}", file=sys.stderr)
        return 1
    print(f"Data folder: {folder}")
    print(f"Burn rate: {meters_per_second:.8g} m/s")
    print(f"Burn rate: {inches_per_second:.8g} in/s")
    print(f"Number of points used: {samples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
