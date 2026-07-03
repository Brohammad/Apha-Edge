import random

from alphaedge.modules.optimization.domain.genetic import (
    crossover,
    mutate,
    next_generation,
    parse_bounds,
    random_individual,
)


def test_parse_bounds():
    space = {
        "fast_period": {"type": "int", "low": 3, "high": 10},
        "threshold": {"type": "float", "low": 0.1, "high": 0.9},
    }
    bounds = parse_bounds(space)
    assert bounds["fast_period"]["type"] == "int"


def test_genetic_operators():
    rng = random.Random(7)
    bounds = parse_bounds({"x": {"type": "int", "low": 1, "high": 5}})
    pop = [random_individual(bounds, rng) for _ in range(4)]
    fitness = [1.0, 0.5, None, 0.8]
    nxt = next_generation(
        pop,
        fitness,
        bounds,
        population_size=4,
        mutation_rate=0.5,
        elite_count=1,
        rng=rng,
    )
    assert len(nxt) == 4
    child = crossover(pop[0], pop[1], bounds, rng)
    assert "x" in child
    assert isinstance(mutate(child, bounds, 1.0, rng)["x"], int)
