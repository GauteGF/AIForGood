from __future__ import annotations

import math
from dataclasses import dataclass

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
from constraint import Problem

from scenarios import CROPS, Scenario, disease_tag


# Per-plot per-hectare reliability is soil_fit + water_fit, which sits in [-5, +4].
SOIL_MATCH_BONUS = 2
SOIL_MISMATCH_PENALTY = -3
WATER_FIT_CAP = 2  # water_fit = WATER_FIT_CAP - |access - need|

# Yield multiplier mapped from per-hectare reliability. Cost is paid in full
# regardless of yield, so a really bad fit can drive realised profit negative.
YIELD_FLOOR = 0.4
YIELD_CEILING = 1.0


CROP_COLORS = {
    "wheat":  "#a7923e",
    "potato": "#765b00",
    "carrot": "#ff9501",
    "barley": "#27ae60",
    "corn":   "#ffee00",
}

SOIL_SHORT = {"sand": "Sa", "clay": "Cl", "humus": "Hu"}


@dataclass
class Option:
    name: str
    assignment: dict[str, str]
    expected_profit: float  # yield-adjusted
    reliability: float
    baseline_profit: float  # at yield_factor = 1.0 everywhere


class CropCSP:
    def __init__(self, scenario: Scenario, crops: dict = CROPS):
        self.scenario = scenario
        self.crops = crops
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.Graph:
        g = nx.Graph()
        g.add_nodes_from(self.scenario.plots)
        g.add_edges_from(self.scenario.neighbors)
        return g

    def _build_problem(self) -> Problem:
        problem = Problem()
        crop_names = list(self.crops.keys())

        for plot in self.scenario.plots:
            problem.addVariable(plot, crop_names)

        # Disease-group adjacency. Also covers "same crop can't be adjacent".
        for a, b in self.scenario.neighbors:
            problem.addConstraint(lambda x, y: disease_tag(x) != disease_tag(y), (a, b))

        for plot, prev in self.scenario.previous_crop.items():
            problem.addConstraint(lambda c, prev=prev: c != prev, (plot,))

        return problem

    def solve_all(self) -> list[dict]:
        return self._build_problem().getSolutions()

    @staticmethod
    def _yield_factor(soil_fit: int, water_fit: int) -> float:
        per_ha = soil_fit + water_fit
        normalized = (per_ha + 5) / 9.0  # [-5, +4] -> [0, 1]
        return YIELD_FLOOR + (YIELD_CEILING - YIELD_FLOOR) * normalized

    def score(self, assignment: dict[str, str]) -> tuple[float, float, float]:
        expected = 0.0
        baseline = 0.0
        reliability = 0.0
        for plot, crop in assignment.items():
            info = self.crops[crop]
            size = self.scenario.size[plot]
            soil = self.scenario.soil[plot]

            soil_fit = SOIL_MATCH_BONUS if soil in info["soils"] else SOIL_MISMATCH_PENALTY
            water_fit = WATER_FIT_CAP - abs(self.scenario.water_access[plot] - info["water"])
            yf = self._yield_factor(soil_fit, water_fit)

            expected += (info["revenue"] * yf - info["cost"]) * size
            baseline += (info["revenue"] - info["cost"]) * size
            reliability += (soil_fit + water_fit) * size

        return expected, reliability, baseline

    def pareto_options(self) -> list[Option]:
        solutions = self.solve_all()
        if not solutions:
            return []

        # (assignment, expected_profit, reliability, baseline_profit)
        scored = [(s, *self.score(s)) for s in solutions]

        # Dominance is checked on profit and reliability only; baseline rides along.
        front: list[tuple[dict, float, float, float]] = []
        for cand in scored:
            _, cp, cr, _ = cand
            dominated = any(op >= cp and orr >= cr and (op > cp or orr > cr)
                            for _, op, orr, _ in scored)
            if not dominated:
                front.append(cand)

        max_profit = max(front, key=lambda t: (t[1], t[2]))
        max_rel = max(front, key=lambda t: (t[2], t[1]))

        p_lo = min(t[1] for t in front)
        p_hi = max(t[1] for t in front)
        r_lo = min(t[2] for t in front)
        r_hi = max(t[2] for t in front)

        def norm(v, lo, hi):
            return 0.5 if hi == lo else (v - lo) / (hi - lo)

        balanced = min(front, key=lambda t: (norm(t[1], p_lo, p_hi) - 1) ** 2
                                           + (norm(t[2], r_lo, r_hi) - 1) ** 2)

        picks: list[Option] = []
        seen: set[tuple] = set()
        for label, item in [("max_profit", max_profit), ("max_reliability", max_rel), ("balanced", balanced)]:
            key = tuple(sorted(item[0].items()))
            if key in seen:
                continue
            seen.add(key)
            picks.append(Option(
                name=label,
                assignment=item[0],
                expected_profit=item[1],
                reliability=item[2],
                baseline_profit=item[3],
            ))
        return picks

    def reliability_bounds(self) -> tuple[float, float]:
        # Per-hectare reliability is in [-5, +4]; scale by total hectares.
        total_size = sum(self.scenario.size.values())
        best_per_ha = SOIL_MATCH_BONUS + WATER_FIT_CAP
        worst_per_ha = SOIL_MISMATCH_PENALTY + (WATER_FIT_CAP - 4)
        return worst_per_ha * total_size, best_per_ha * total_size

    def reliability_pct(self, reliability: float) -> float:
        lo, hi = self.reliability_bounds()
        return 50.0 if hi == lo else 100.0 * (reliability - lo) / (hi - lo)

    @staticmethod
    def reliability_band(pct: float) -> str:
        if pct >= 85:
            return "excellent"
        if pct >= 70:
            return "good"
        if pct >= 50:
            return "fair"
        return "poor"

    def _node_sizes(self) -> list[int]:
        sizes = [self.scenario.size[n] for n in self.graph.nodes()]
        lo, hi = min(sizes), max(sizes)
        if hi == lo:
            return [1400] * len(sizes)
        return [800 + int(1400 * (s - lo) / (hi - lo)) for s in sizes]

    def _layout(self, seed: int) -> dict:
        # Normalising to the unit square keeps disconnected components from
        # being pushed to the far corners by spring_layout.
        pos = nx.spring_layout(self.graph, seed=seed)
        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        x_lo, x_hi = min(xs), max(xs)
        y_lo, y_hi = min(ys), max(ys)

        def norm(v, lo, hi):
            return 0.5 if hi == lo else (v - lo) / (hi - lo)

        return {n: (norm(pos[n][0], x_lo, x_hi), norm(pos[n][1], y_lo, y_hi)) for n in pos}

    def draw_options(self, options: list[Option], layout_seed: int = 42) -> None:
        if not options:
            print("no feasible solutions to draw")
            return

        pos = self._layout(layout_seed)
        nodes = list(self.graph.nodes())
        sizes = self._node_sizes()
        size_by_node = dict(zip(nodes, sizes))

        fig, axes = plt.subplots(1, len(options), figsize=(6 * len(options), 6))
        if len(options) == 1:
            axes = [axes]

        for ax, opt in zip(axes, options):
            colors = [CROP_COLORS[opt.assignment[n]] for n in nodes]

            nx.draw_networkx_edges(self.graph, pos, ax=ax, edge_color="#bbb")
            nx.draw_networkx_nodes(
                self.graph, pos, ax=ax,
                node_color=colors, node_size=sizes,
                edgecolors="#333", linewidths=1.0,
            )
            nx.draw_networkx_labels(
                self.graph, pos, ax=ax,
                labels={n: n for n in nodes},
                font_size=10,
            )
            # Offset metadata text by the node's radius so it sits just outside the circle.
            for n in nodes:
                x, y = pos[n]
                meta = (f"{SOIL_SHORT[self.scenario.soil[n]]} · "
                        f"W{self.scenario.water_access[n]} · "
                        f"{self.scenario.size[n]}ha")
                radius_pts = math.sqrt(size_by_node[n] / math.pi)
                ax.annotate(
                    meta, xy=(x, y), xytext=(0, -(radius_pts + 6)),
                    textcoords="offset points",
                    ha="center", va="top", fontsize=7, color="#555",
                )

            pct = self.reliability_pct(opt.reliability)
            band = self.reliability_band(pct)
            yield_pct = (
                100.0 * opt.expected_profit / opt.baseline_profit
                if opt.baseline_profit > 0 else 0.0
            )
            ax.set_title(
                f"{opt.name}\n"
                f"expected profit: {opt.expected_profit:.0f} kr  "
                f"(baseline {opt.baseline_profit:.0f} · realised {yield_pct:.0f}%)\n"
                f"reliability: {opt.reliability:.1f}  ({pct:.0f}%, {band})",
                fontsize=10,
            )
            ax.set_axis_off()
            ax.margins(0.25)

        legend_handles = [mpatches.Patch(color=c, label=name) for name, c in CROP_COLORS.items()]
        fig.legend(
            handles=legend_handles, loc="lower center",
            ncol=len(CROP_COLORS), frameon=False, fontsize=9,
        )
        title = f"scenario: {self.scenario.name}"
        if len(options) == 1:
            title += "   |   single Pareto-optimal solution (no tradeoff to make)"
        elif len(options) == 2:
            title += "   |   only two distinct Pareto-optimal solutions (no balanced middle)"
        fig.suptitle(title, fontsize=11)
        plt.tight_layout(rect=(0, 0.06, 1, 0.92))
        plt.show()

    def draw_solution_space(self, options: list[Option] | None = None) -> None:
        solutions = self.solve_all()
        if not solutions:
            print("no feasible solutions to plot")
            return

        scored = [self.score(s) for s in solutions]
        profits = [s[0] for s in scored]
        reliabilities = [s[1] for s in scored]

        front_idx = []
        for i, (p, r, _) in enumerate(scored):
            dominated = any(op >= p and orr >= r and (op > p or orr > r)
                            for op, orr, _ in scored)
            if not dominated:
                front_idx.append(i)

        _, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(
            profits, reliabilities,
            c="#cccccc", s=28, alpha=0.6, edgecolors="none",
            label=f"all feasible ({len(solutions)})",
        )

        front_pts = sorted((profits[i], reliabilities[i]) for i in front_idx)
        fx = [p for p, _ in front_pts]
        fy = [r for _, r in front_pts]
        ax.plot(fx, fy, color="#e67e22", lw=1.5, alpha=0.7, zorder=2)
        ax.scatter(
            fx, fy,
            c="#e67e22", s=70, edgecolors="black", linewidths=0.6,
            label=f"pareto front ({len(front_idx)})", zorder=3,
        )

        if options:
            for opt in options:
                ax.scatter(
                    [opt.expected_profit], [opt.reliability],
                    c="#c0392b", s=140, edgecolors="black", linewidths=1.2, zorder=4,
                )
                ax.annotate(
                    opt.name, (opt.expected_profit, opt.reliability),
                    xytext=(8, 6), textcoords="offset points",
                    fontsize=10, fontweight="bold",
                )

        ax.set_xlabel("expected profit (kr)")
        ax.set_ylabel("reliability")
        ax.set_title(f"objective space: {self.scenario.name}")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
        plt.tight_layout()
        plt.show()
