"""Bayesian optimization via Optuna (optional dependency)."""

from __future__ import annotations

from typing import Any


def suggest_parameters(trial: object, parameter_space: dict[str, object]) -> dict[str, object]:
    """Map parameter bounds to Optuna trial suggestions."""
    params: dict[str, object] = {}
    for name, spec in parameter_space.items():
        if not isinstance(spec, dict):
            raise ValueError(
                f"parameter_space['{name}'] must be a bounds object for bayesian search"
            )
        low = spec["low"]
        high = spec["high"]
        ptype = str(spec.get("type", "float"))
        if ptype == "int":
            params[name] = trial.suggest_int(name, int(low), int(high))  # type: ignore[attr-defined]
        else:
            params[name] = trial.suggest_float(name, float(low), float(high))  # type: ignore[attr-defined]
    return params


def default_optimizer_config(config: dict[str, object] | None) -> dict[str, Any]:
    merged = {"n_trials": 20, "n_startup_trials": 5}
    if config:
        merged.update(config)
    return merged
