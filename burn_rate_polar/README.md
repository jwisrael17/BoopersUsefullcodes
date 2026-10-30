# Burn-rate orientation comparison

## Your h,k,l CSV

Save your measurements with these headers (the spelling `expermental` is accepted):

```csv
h,k,l,expermental,simulated
1,0,0,2.0,2.1
1,1,0,2.5,2.6
1,1,1,2.7,2.8
0,1,0,3.0,2.9
```

Run with the CSV path as the argument:

```bash
python3 plot_burn_rate.py "My material.csv"
```

This uses **My material** as the plot title and saves
`polar_plots/My material_polar.png`. Each CSV gets its own filename as its title,
including when several files are supplied in one command. `--title` can override
this. `experimental` is also accepted in place of `expermental`. Header spaces
and capitalization are ignored. Both rates must be in **mm/s**.

Each row contains the face indices `h,k,l` and the two corresponding rates.
These face normals are interpreted in a **cubic** crystal, relative to (100).
Keep one set of test conditions per file. A blank rate is skipped; both rates
cannot be blank on the same row. Example values above are invented.

## Simple three-column CSV

Create a plain-text file named `my_data.csv` in your Ubuntu editor:

```csv
face,experimental_burn_rate,simulated_burn_rate
100,2.0,2.1
110,2.5,2.6
111,2.7,2.8
010,3.0,2.9
```

These are example values. Enter both burn rates in **mm/s**, then run:

```bash
python3 plot_burn_rate.py my_data.csv
```

This saves `polar_plots/my_data_polar.png`, with experiment and simulation on
the same polar graph. Run again after editing your data. For several plots:

```bash
python3 plot_burn_rate.py material_A.csv material_B.csv
```

Each simple CSV produces one plot. Keep the test conditions and rate measurement
definition consistent within each file. The simple format does not record or
check heat flux and cutoff time; use separate files for different conditions.
The extended format below can group conditions automatically.

Faces are **cubic crystal plane indices**, with the angle between each face's
normal and the (100) normal. This assumes burning along the face normal.
Different faces can have the same angle; labels retain the individual indices.
For non-cubic materials use the Cartesian-vector extended format below instead.
Write `010` as shown to retain its leading zero. `(110)` is also accepted.
For negative or multi-digit indices, use spaces, for example `(1 -1 0)` or
`(10 1 0)`. Faces containing commas must be quoted: `"(1,-1,0)"`.
Leave a rate blank if unavailable, retaining the comma. Blank rates are skipped,
not treated as zero. Both rates cannot be blank in the same row.

## Extended format

Create polar scatter plots comparing experimental and simulation burn rates.
Each input CSV is processed independently. Within each file, a separate plot is
created for every exact heat-flux / laser-cutoff-time combination. Experiment
uses blue circles and simulation uses orange triangles. Optional radial error
bars and orientation-vector labels are included.

## Install and run

Run these commands from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python plot_burn_rate.py examples/comparison.csv --title "Example data"
```

The example is invented data. It produces two PNG files in `polar_plots/`.
No display is required, so the script also works on a compute node.

Copy `examples/comparison.csv` to a new filename and replace the measurements.
Repeat the command for each dataset or process multiple files together:

```bash
python plot_burn_rate.py material_A.csv material_B.csv --output-dir results
python plot_burn_rate.py material_A.csv --format svg --no-labels
```

Rerunning the same command replaces its generated plot files. Old files from
conditions removed from the CSV are not deleted. Use a new output directory
when you want to keep different versions. Input filenames must have distinct
stems when processed together. Each file should represent one material and
one consistent burn-rate measurement definition/window.

## Input columns

| Column | Meaning |
| --- | --- |
| `source` | `experiment` or `simulation` |
| `u,v,w` | Three components of the burn-propagation direction |
| `heat_flux_kw_m2` | Applied heat flux in kW/m² |
| `cutoff_s` | Laser cutoff time in seconds, using the same time origin |
| `burn_rate_mm_s` | Nonnegative burn rate in mm/s |
| `rate_error_mm_s` | Optional symmetric error-bar half-width in mm/s; blank is allowed |

The optional error column can be omitted entirely. Choose a consistent error
definition (for example, standard deviation or a confidence-interval half-width)
and state it in your figure caption. Each row is plotted separately; replicates
are not averaged. Error bars extending below zero are rejected.

`BurnRate.py` in the repository root reports m/s and in/s. Multiply its m/s
results by **1000** before putting them in `burn_rate_mm_s`, and supply the
orientation, heat flux, and cutoff metadata for each simulation yourself.

## Orientation assumptions

By default, vectors are crystallographic directions in a **cubic** crystal.
The reference is +[100], the normal to (100). The plotted angle is
`acos(dot(unit_direction, unit_normal))`. Vector magnitude does not matter;
zero vectors are rejected. The angle ranges from 0 to 180 degrees, so opposite
directions are not folded together. The plot displays 0–90 degrees if all
directions fall in that range, otherwise 0–180 degrees.

For a non-cubic crystal, first convert your crystallographic direction vectors
and the reciprocal-lattice (100) normal into the **same Cartesian frame**.
Supply the Cartesian directions in `u,v,w` and the Cartesian normal with:

```bash
python plot_burn_rate.py cartesian_data.csv --normal 1 0 0
```

Replace those normal components with the appropriate values for your frame.
For another reference, also change `--reference-label "your reference"`.

Different 3D vectors can have the same angle from the reference. This plot
retains vector labels but does not preserve the azimuth about the normal.
For a directional anisotropy curve, use directions in a specified rotation
plane. Points are not connected because arbitrary directions need not lie
along a common angular sweep.

## Comparing test conditions

Use the same units and condition values in both sources to overlay them.
Conditions are matched exactly, without rounding or interpolation. An unmatched
condition still produces a plot and prints a notice that only one source is
present. A single file containing only experiment or only simulation is allowed.
Do not interpret changing heat flux or cutoff time as an orientation effect.
Use a consistent burn-rate measurement window (during heating, after cutoff,
or a clearly defined interval) in both datasets.

## Verification

```bash
python -m unittest discover -s tests -v
```
