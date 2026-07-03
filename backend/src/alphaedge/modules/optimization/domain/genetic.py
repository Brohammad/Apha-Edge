"""Genetic algorithm parameter search for strategy optimization."""

from __future__ import annotations

import random
from typing import Any


def parse_bounds(parameter_space: dict[str, object]) -> dict[str, dict[str, Any]]:
    """Convert parameter_space bounds specs to normalized internal form."""
    bounds: dict[str, dict[str, Any]] = {}
    for name, spec in parameter_space.items():
        if not isinstance(spec, dict):
            raise ValueError(
                f"parameter_space['{name}'] must be a bounds object for genetic search"
            )
        low = spec.get("low")
        high = spec.get("high")
        if low is None or high is None:
            raise ValueError(f"parameter_space['{name}'] requires 'low' and 'high'")
        ptype = str(spec.get("type", "float"))
        bounds[name] = {"type": ptype, "low": low, "high": high}
    return bounds


def random_individual(bounds: dict[str, dict[str, Any]], rng: random.Random) -> dict[str, object]:
    params: dict[str, object] = {}
    for name, spec in bounds.items():
        low, high = spec["low"], spec["high"]
        if spec["type"] == "int":
            params[name] = rng.randint(int(low), int(high))
        else:
            params[name] = round(rng.uniform(float(low), float(high)), 6)
    return params


def crossover(
    parent_a: dict[str, object],
    parent_b: dict[str, object],
    bounds: dict[str, dict[str, Any]],
    rng: random.Random,
) -> dict[str, object]:
    child: dict[str, object] = {}
    for name, spec in bounds.items():
        if rng.random() < 0.5:
            child[name] = parent_a[name]
        else:
            child[name] = parent_b[name]
        if spec["type"] == "int":
            child[name] = int(child[name])
    return child


def mutate(
    individual: dict[str, object],
    bounds: dict[str, dict[str, Any]],
    mutation_rate: float,
    rng: random.Random,
) -> dict[str, object]:
    mutated = dict(individual)
    for name, spec in bounds.items():
        if rng.random() > mutation_rate:
            continue
        low, high = spec["low"], spec["high"]
        if spec["type"] == "int":
            mutated[name] = rng.randint(int(low), int(high))
        else:
            mutated[name] = round(rng.uniform(float(low), float(high)), 6)
    return mutated


def tournament_select(
    population: list[dict[str, object]],
    fitness: list[float | None],
    rng: random.Random,
    *,
    k: int = 3,
) -> dict[str, object]:
    indices = rng.sample(range(len(population)), min(k, len(population)))
    best_idx = max(indices, key=lambda i: fitness[i] if fitness[i] is not None else float("-inf"))
    return population[best_idx]


def evolve_population(
    bounds: dict[str, dict[str, Any]],
    *,
    population_size: int,
    generations: int,
    mutation_rate: float,
    elite_count: int,
    rng: random.Random,
) -> list[dict[str, object]]:
    """Return ordered list of individuals to evaluate (elite carry-over across generations)."""
    population = [random_individual(bounds, rng) for _ in range(population_size)]
    schedule: list[dict[str, object]] = list(population)

    for _ in range(generations):
        # Placeholder fitness — runner evaluates and injects scores between generations
        fitness: list[float | None] = [None] * len(population)
        ranked = sorted(
            zip(population, fitness, strict=True),
            key=lambda x: x[1] if x[1] is not None else float("-inf"),
            reverse=True,
        )
        elites = [ind for ind, _ in ranked[:elite_count]]
        offspring: list[dict[str, object]] = list(elites)
        while len(offspring) < population_size:
            p1 = tournament_select(population, fitness, rng)
            p2 = tournament_select(population, fitness, rng)
            child = crossover(p1, p2, bounds, rng)
            child = mutate(child, bounds, mutation_rate, rng)
            offspring.append(child)
        population = offspring[:population_size]
        schedule.extend(population)
    return schedule


def next_generation(
    population: list[dict[str, object]],
    fitness: list[float | None],
    bounds: dict[str, dict[str, Any]],
    *,
    population_size: int,
    mutation_rate: float,
    elite_count: int,
    rng: random.Random,
) -> list[dict[str, object]]:
    ranked = sorted(
        zip(population, fitness, strict=True),
        key=lambda x: x[1] if x[1] is not None else float("-inf"),
        reverse=True,
    )
    elites = [ind for ind, _ in ranked[:elite_count]]
    offspring: list[dict[str, object]] = list(elites)
    while len(offspring) < population_size:
        p1 = tournament_select(population, fitness, rng)
        p2 = tournament_select(population, fitness, rng)
        child = mutate(crossover(p1, p2, bounds, rng), bounds, mutation_rate, rng)
        offspring.append(child)
    return offspring[:population_size]
