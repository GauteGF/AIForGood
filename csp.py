import argparse

from crop_csp import CropCSP
from scenarios import PRESETS, random_scenario


def main():
    parser = argparse.ArgumentParser(description="Crop CSP with soft constraint tradeoffs.")
    parser.add_argument("--scenario", choices=PRESETS.keys(), default="default")
    parser.add_argument("--no-draw", action="store_true", help="print options only, skip matplotlib")
    parser.add_argument("--plot-space", action="store_true",
                        help="also open a scatter plot of all feasible assignments in (profit, reliability) space")
    parser.add_argument("--seed", type=int, default=None, help="seed for --scenario random")
    parser.add_argument("--n-plots", type=int, default=None, help="plot count for --scenario random")
    parser.add_argument("--edge-prob", type=float, default=0.4, help="edge probability for --scenario random")
    args = parser.parse_args()

    if args.scenario == "random":
        scenario = random_scenario(n_plots=args.n_plots, edge_prob=args.edge_prob, seed=args.seed)
    else:
        scenario = PRESETS[args.scenario]()

    solver = CropCSP(scenario)
    options = solver.pareto_options()

    print(f"scenario: {scenario.name}")
    print(f"  {len(scenario.plots)} plots, {len(scenario.neighbors)} adjacencies")
    for p in scenario.plots:
        print(f"  {p}: soil={scenario.soil[p]:<5} water={scenario.water_access[p]}  "
              f"size={scenario.size[p]} ha  previous={scenario.previous_crop[p]}")
    print()

    if not options:
        print("No feasible solution (hard constraints unsatisfiable).")
        return

    lo, hi = solver.reliability_bounds()
    print(f"{len(solver.solve_all())} hard-feasible assignments. Pareto picks:\n")
    print("  expected profit = (revenue * yield_factor - cost) * size, summed across plots")
    print("                    yield_factor in [0.4, 1.0] based on soil + water fit")
    print("  baseline profit = the same sum at yield_factor = 1.0 everywhere (optimistic)")
    print(f"  reliability     = soil/water fit score, scenario range [{lo:.1f} .. {hi:.1f}]\n")

    if len(options) == 1:
        print("Note: this scenario has a single Pareto-optimal solution. The same assignment")
        print("      maximises both expected profit and reliability, so there is no")
        print("      tradeoff to choose between.\n")
    elif len(options) == 2:
        print("Note: this scenario has only two distinct Pareto-optimal solutions. There is")
        print("      a real tradeoff between them but no meaningful 'balanced' middle pick.\n")

    for opt in options:
        pct = solver.reliability_pct(opt.reliability)
        band = solver.reliability_band(pct)
        yield_pct = (
            100.0 * opt.expected_profit / opt.baseline_profit
            if opt.baseline_profit > 0 else 0.0
        )
        print(f"[{opt.name}]")
        print(f"  expected profit: {opt.expected_profit:>7.0f} kr  "
              f"(baseline {opt.baseline_profit:.0f}, realised {yield_pct:.0f}%)")
        print(f"  reliability:     {opt.reliability:>7.1f}     ({pct:.0f}%, {band})")
        for plot in scenario.plots:
            print(f"    {plot}: {opt.assignment[plot]}")
        print()

    if not args.no_draw:
        solver.draw_options(options)
        if args.plot_space:
            solver.draw_solution_space(options)


if __name__ == "__main__":
    main()
