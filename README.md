# Crop CSP

Solves a crop-assignment constraint problem over a small field graph and visualizes it with `networkx` + `matplotlib`.

## Requirements

- Python 3.9+

## Setup

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Windows (cmd)

```cmd
py -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

## Run

With the venv activated:

```
python csp.py                       # default scenario
python csp.py --scenario tiny       # smaller scenario for quick checks
python csp.py --scenario mixed_soil # stronger tradeoffs
python csp.py --scenario random     # generates a fresh random scenario
python csp.py --no-draw             # text only, no matplotlib
python csp.py --plot-space          # also open the objective-space scatter
```

For random scenarios you can pin the result with `--seed 42`, or tune the size with `--n-plots 6` and `--edge-prob 0.3`. Note that very dense random graphs can be infeasible since there are only 5 crops. Just rerun with a different seed if that happens.

You get up to three picks: `max_profit`, `max_reliability`, and `balanced`. Unless you pass `--no-draw`, they're drawn side-by-side as colored graphs. If the Pareto front collapses to one or two distinct solutions (the same assignment maximises both objectives), the output says so and shows fewer picks instead of inventing a tradeoff.

With `--plot-space`, a second window opens after the main drawing. It scatters every hard-feasible assignment in (expected profit, reliability) space, draws the Pareto front as an orange curve, and labels the three named picks. Useful for seeing how big the tradeoff actually is and where the picks sit relative to the rest of the search space.

## What the numbers mean

Each Pareto pick reports three values:

- **Expected profit** (the primary optimisation target). For each plot:
  `expected_profit_per_plot = (revenue * yield_factor - cost) * size`
  where `yield_factor ∈ [0.4, 1.0]` is derived from how well the assigned crop matches the plot's soil and water. Cost is always paid in full, so a really bad fit can push expected profit negative on a plot. Summed across plots, this is what the farmer can actually expect to make.
- **Baseline profit** (reference number, not optimised). Same formula with `yield_factor = 1.0` everywhere. This is the optimistic upper bound — what you'd make if every crop hit its full baseline yield. The `realised X%` figure is `expected / baseline`.
- **Reliability** (the second optimisation target). Soil/water fit signal, scaled by plot size. Independent of revenue/cost: useful as a sustainability / monoculture-risk proxy on top of expected profit. Reported as a raw score, a percentage of the scenario's range, and a band (`poor` < 50%, `fair` 50–70%, `good` 70–85%, `excellent` ≥ 85%). Per hectare it ranges from `-5` (wrong soil + 4-unit water gap) to `+4` (matching soil + perfect water).

The Pareto front uses expected profit and reliability. The tradeoff is "earn more now in conditions the crop tolerates" vs "earn less now but maintain good growing conditions across the farm."

## Hard constraints

1. Same crop can't be planted two years in a row on the same plot.
2. Two adjacent plots can't host crops from the same disease group. Groups (from the project notes):
   - wheat + barley (share *Blumeria graminis*, *Fusarium*)
   - potato + carrot (share *Streptomyces* / common scab)
   This subsumes "same crop can't be adjacent" and adds the cross-crop disease cases.

## Testing your own scenario

Scenarios live in [scenarios.py](scenarios.py). To add one, write a function that returns a `Scenario` and add it to the `PRESETS` dict at the bottom. Then run `--scenario <name>`.

A scenario needs:

- `plots`: list of plot ids
- `neighbors`: list of `(plot, plot)` edges
- `previous_crop`: what grew there last year
- `soil`: `"sand"`, `"clay"`, or `"humus"` per plot
- `water_access`: `1` (dry) to `5` (wet) per plot
- `size` (optional): hectares per plot. Defaults to 1.0 if omitted. Profit and reliability scale with size.

Crop facts (soil suitability, water need, cost, revenue) live in the `CROPS` table in the same file. Tweak the numbers to see how the tradeoff shifts. Disease groups live in `DISEASE_GROUPS` in the same file.

## Deactivate

```
deactivate
```
