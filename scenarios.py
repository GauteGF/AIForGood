import random
from dataclasses import dataclass, field


# water is on the same 1..5 scale as a plot's water_access. cost/revenue per hectare.
CROPS: dict[str, dict] = {
    "wheat":  {"soils": {"clay", "humus"}, "water": 3, "cost": 100, "revenue": 220},
    "barley": {"soils": {"clay", "humus"}, "water": 1, "cost":  90, "revenue": 180},
    "potato": {"soils": {"sand", "humus"}, "water": 4, "cost": 150, "revenue": 320},
    "carrot": {"soils": {"sand", "humus"}, "water": 3, "cost": 130, "revenue": 280},
    "corn":   {"soils": {"clay", "humus"}, "water": 5, "cost": 180, "revenue": 400},
}

SOIL_TYPES = {"sand", "clay", "humus"}

# Crops grouped here can't be planted next to each other.
# wheat+barley share Blumeria graminis (powdery mildew) and Fusarium.
# potato+carrot share Streptomyces (common scab).
DISEASE_GROUPS: list[set[str]] = [
    {"wheat", "barley"},
    {"potato", "carrot"},
]


def disease_tag(crop: str) -> str:
    for i, group in enumerate(DISEASE_GROUPS):
        if crop in group:
            return f"group{i}"
    return f"solo:{crop}"


@dataclass
class Scenario:
    plots: list[str]
    neighbors: list[tuple[str, str]]
    previous_crop: dict[str, str]
    soil: dict[str, str]
    water_access: dict[str, int]
    size: dict[str, float] = field(default_factory=dict)
    name: str = "unnamed"

    def __post_init__(self):
        bad_soil = {p: s for p, s in self.soil.items() if s not in SOIL_TYPES}
        if bad_soil:
            raise ValueError(f"unknown soil types: {bad_soil}")
        bad_water = {p: w for p, w in self.water_access.items() if not 1 <= w <= 5}
        if bad_water:
            raise ValueError(f"water_access must be 1..5: {bad_water}")
        missing = (set(self.plots) - self.soil.keys()) | (set(self.plots) - self.water_access.keys())
        if missing:
            raise ValueError(f"plots missing soil/water entries: {missing}")

        for p in self.plots:
            self.size.setdefault(p, 1.0)
        bad_size = {p: s for p, s in self.size.items() if s <= 0}
        if bad_size:
            raise ValueError(f"plot sizes must be > 0: {bad_size}")


def default() -> Scenario:
    return Scenario(
        name="default",
        plots=["p1", "p2", "p3", "p4", "p5"],
        neighbors=[("p1", "p2"), ("p1", "p3"), ("p2", "p3"), ("p4", "p5")],
        previous_crop={"p1": "wheat", "p2": "potato", "p3": "carrot", "p4": "corn", "p5": "barley"},
        soil={"p1": "clay", "p2": "humus", "p3": "sand", "p4": "clay", "p5": "sand"},
        water_access={"p1": 3, "p2": 4, "p3": 2, "p4": 5, "p5": 3},
        size={"p1": 1.5, "p2": 0.8, "p3": 1.2, "p4": 2.0, "p5": 1.0},
    )


def tiny() -> Scenario:
    return Scenario(
        name="tiny",
        plots=["a", "b"],
        neighbors=[("a", "b")],
        previous_crop={"a": "wheat", "b": "corn"},
        soil={"a": "humus", "b": "clay"},
        water_access={"a": 3, "b": 4},
        size={"a": 1.0, "b": 1.5},
    )


def mixed_soil() -> Scenario:
    # Plots are mismatched on purpose so high-revenue crops can't fit everywhere.
    return Scenario(
        name="mixed_soil",
        plots=["n1", "n2", "n3", "n4", "n5", "n6"],
        neighbors=[("n1", "n2"), ("n2", "n3"), ("n3", "n4"), ("n4", "n5"), ("n5", "n6"), ("n1", "n6")],
        previous_crop={"n1": "wheat", "n2": "barley", "n3": "potato", "n4": "carrot", "n5": "corn", "n6": "wheat"},
        soil={"n1": "sand", "n2": "sand", "n3": "clay", "n4": "humus", "n5": "clay", "n6": "sand"},
        water_access={"n1": 2, "n2": 1, "n3": 3, "n4": 4, "n5": 5, "n6": 2},
        size={"n1": 0.5, "n2": 0.5, "n3": 2.0, "n4": 1.0, "n5": 1.5, "n6": 0.8},
    )


def random_scenario(
    n_plots: int | None = None,
    edge_prob: float = 0.4,
    seed: int | None = None,
) -> Scenario:
    # Dense graphs with many plots can be infeasible (only 5 crops, neighbour
    # constraint = a graph-colouring problem). Lower edge_prob or pick a new
    # seed if that happens.
    rng = random.Random(seed)
    n = n_plots if n_plots is not None else rng.randint(3, 7)
    plots = [f"r{i + 1}" for i in range(n)]
    crop_names = list(CROPS.keys())
    soil_options = sorted(SOIL_TYPES)

    neighbors: list[tuple[str, str]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if rng.random() < edge_prob:
                neighbors.append((plots[i], plots[j]))

    return Scenario(
        name=f"random(n={n}, seed={seed})",
        plots=plots,
        neighbors=neighbors,
        previous_crop={p: rng.choice(crop_names) for p in plots},
        soil={p: rng.choice(soil_options) for p in plots},
        water_access={p: rng.randint(1, 5) for p in plots},
        size={p: round(rng.uniform(0.5, 2.5), 1) for p in plots},
    )


PRESETS = {
    "default": default,
    "tiny": tiny,
    "mixed_soil": mixed_soil,
    "random": random_scenario,
}
