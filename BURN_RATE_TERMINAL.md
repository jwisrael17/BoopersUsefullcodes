# Terminal burn-rate command

From the repository root, run:

```bash
python3 BurnRateTerminal.py /path/to/simulation/output_folder
```

The argument is the ALAMO output **folder containing the numbered `*cell`
plotfiles**, as in the original burn-rate script. A single snapshot does not
provide the front motion over time required to calculate a rate.

This command prints progress followed by the burn rate in **m/s** and **in/s**,
and the number of front-position samples used. It does not need a time argument
and does not write a CSV. Keep `BurnRateTerminal.py` next to `BurnRate.py`;
it reuses the same front tracking and linear fit rather than duplicating them.
It uses the existing NumPy and yt dependencies from `BurnRate.py`.

The calculation tracks the first `rigid_eta = 0.5` crossing in the profile
averaged over x and z, then fits y position versus time. The existing conversion
assumes the simulation coordinates are meters and times are seconds.

The batch command remains:

```bash
python3 BurnRate.py 'run_*' 0.0075
```

The batch command appends results to `burn_rate_table.csv`. Its last argument
is the numeric time metadata recorded in the table; it does not select a
fitting interval.
