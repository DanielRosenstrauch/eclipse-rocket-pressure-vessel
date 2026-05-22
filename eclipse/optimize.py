"""Two-pass design-space optimization.

Mirrors the MATLAB script's structure:

  Pass 1 - For every (material, fuel) pair, sweep the 3D (r0, t, L_total) grid,
           compute P_max from the thick-walled formula, then compute tank mass,
           gas mass, stored energy, required energy, and feasibility.  Collect
           the per-cell mprop and cost arrays for all feasible cells.

  Pass 2 - Find global m_prop_max and cost_max across all 12 combinations, then
           apply the weighted score and pick the per-combination minimum and
           the global minimum.

Vectorized via NumPy ndgrid (np.meshgrid with indexing="ij").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np

from .data import (
    FUELS,
    G_ACCEL,
    INCH_TO_M,
    M_REST_DEFAULT,
    MATERIALS,
    P_ATM,
    PSI_TO_PA,
    Fuel,
    Material,
)
from .physics import (
    gas_mass,
    interior_volume,
    metal_shell_volume,
    moles_stored,
    p_max_thick_walled,
    stresses_at_inner_wall,
)
from .trajectory import drag_work, energy_needed


@dataclass
class DesignSpace:
    """Grid bounds for the (r0, t, L_total) sweep, in SI units."""

    r0_min: float
    r0_max: float
    t_min: float
    t_max: float
    L_min: float
    L_max: float
    nr: int = 80
    nt: int = 80
    nL: int = 40

    @classmethod
    def default(cls) -> "DesignSpace":
        r0_max_m = (5.75 / 2.0) * INCH_TO_M
        L_max_m = 60.0 * INCH_TO_M
        return cls(
            r0_min=0.05 * r0_max_m,
            r0_max=r0_max_m,
            t_min=0.5e-3,
            t_max=25e-3,
            L_min=5.0 * INCH_TO_M,
            L_max=L_max_m,
        )

    def grids(self):
        r_vec = np.linspace(self.r0_min, self.r0_max, self.nr)
        t_vec = np.linspace(self.t_min, self.t_max, self.nt)
        L_vec = np.linspace(self.L_min, self.L_max, self.nL)
        R3, T3, L3 = np.meshgrid(r_vec, t_vec, L_vec, indexing="ij")
        return r_vec, t_vec, L_vec, R3, T3, L3


@dataclass
class OptimalDesign:
    """The chosen design for a single (material, fuel) pair."""

    material: Material
    fuel: Fuel
    r_outer: float        # [m]
    r_inner: float        # [m]
    thickness: float      # [m]
    L_total: float        # [m]
    L_cyl: float          # [m]
    p_max: float          # [Pa]
    sigma_hoop: float     # [Pa]
    sigma_radial: float   # [Pa]
    sigma_axial: float    # [Pa]
    sigma_VM: float       # [Pa]
    m_tank: float         # [kg]
    m_fuel: float         # [kg]
    m_prop: float         # [kg]
    m_total: float        # [kg]
    e_gas: float          # [J]
    e_needed: float       # [J]
    cost: float           # [$]
    score: float

    @property
    def margin(self) -> float:
        return self.e_gas / self.e_needed if self.e_needed else float("inf")

    @property
    def p_max_psi(self) -> float:
        return self.p_max / PSI_TO_PA


@dataclass
class OptimizationResult:
    """Container for everything Pass 2 produces."""

    alpha: float
    drag_work_J: float
    m_prop_max: float
    cost_max: float
    per_combination: List[OptimalDesign] = field(default_factory=list)
    global_optimum: OptimalDesign | None = None


def _evaluate_combo(
    material: Material,
    fuel: Fuel,
    R3, T3, L3,
    valid: np.ndarray,
    V_metal: np.ndarray,
    V_inner: np.ndarray,
    m_rest: float,
    h_target_ft: float,
    drag_work_J: float,
    p_external: float,
):
    """Compute the full feasibility + cost arrays for one material/fuel pair."""
    Ri = R3 - T3
    P_max = p_max_thick_walled(R3, Ri, material.yield_strength, p_external)
    m_tank = material.density * V_metal

    n_moles = moles_stored(P_max, V_inner)
    E_gas = n_moles * fuel.energy_density
    m_fuel = gas_mass(n_moles, fuel.molar_mass)
    m_total = m_rest + m_tank + m_fuel
    E_needed_arr = energy_needed(m_total, h_target_ft, drag_work_J)

    feasible = valid & (E_gas >= E_needed_arr)

    m_prop = m_tank + m_fuel
    cost = m_tank * material.cost + m_fuel * fuel.cost

    return {
        "P_max": P_max, "m_tank": m_tank, "m_fuel": m_fuel,
        "m_prop": m_prop, "cost": cost, "E_gas": E_gas,
        "E_needed": E_needed_arr, "feasible": feasible,
    }


def optimize(
    alpha: float = 0.5,
    materials: Sequence[Material] = MATERIALS,
    fuels: Sequence[Fuel] = FUELS,
    design_space: DesignSpace | None = None,
    m_rest: float = M_REST_DEFAULT,
    h_target_ft: float = 30_000.0,
    drag_work_J: float | None = None,
    p_external: float = P_ATM,
    cd: float = 0.75,
    nose_cone_d_in: float = 6.0,
) -> OptimizationResult:
    """Run the two-pass optimization and return all per-combination results.

    Parameters
    ----------
    alpha : 0..1 weighting on mass (vs. cost) in the composite score.
    drag_work_J : if None, computed from ``cd``, ``nose_cone_d_in``, ``h_target_ft``.
    """
    if design_space is None:
        design_space = DesignSpace.default()

    if drag_work_J is None:
        drag_work_J = drag_work(h_target_ft, cd, nose_cone_d_in)

    r_vec, t_vec, L_vec, R3, T3, L3 = design_space.grids()
    Ri3 = R3 - T3
    L_cyl3 = L3 - 2.0 * R3

    valid = (
        (T3 < R3)
        & (Ri3 > 0)
        & (L_cyl3 > 0)
        & (L3 <= design_space.L_max + 1e-12)
        & (R3 <= design_space.r0_max + 1e-12)
    )

    V_metal = metal_shell_volume(R3, Ri3, L3)
    V_inner = interior_volume(Ri3, R3, L3)

    # --- Pass 1: collect arrays per combination ---
    combo_results = []
    m_prop_max = -np.inf
    cost_max = -np.inf

    for material in materials:
        for fuel in fuels:
            arrs = _evaluate_combo(
                material, fuel,
                R3, T3, L3, valid, V_metal, V_inner,
                m_rest, h_target_ft, drag_work_J, p_external,
            )
            if not np.any(arrs["feasible"]):
                combo_results.append((material, fuel, None))
                continue
            f = arrs["feasible"]
            m_prop_max = max(m_prop_max, float(np.nanmax(arrs["m_prop"][f])))
            cost_max = max(cost_max, float(np.nanmax(arrs["cost"][f])))
            combo_results.append((material, fuel, arrs))

    # If no feasible designs anywhere, bail out cleanly.
    if not np.isfinite(m_prop_max) or not np.isfinite(cost_max):
        return OptimizationResult(
            alpha=alpha, drag_work_J=drag_work_J, m_prop_max=0.0, cost_max=0.0
        )

    # --- Pass 2: weighted score and per-combo + global optimum ---
    result = OptimizationResult(
        alpha=alpha, drag_work_J=drag_work_J,
        m_prop_max=m_prop_max, cost_max=cost_max,
    )

    best_overall: OptimalDesign | None = None
    for material, fuel, arrs in combo_results:
        if arrs is None:
            continue
        score = (
            alpha * (arrs["m_prop"] / m_prop_max)
            + (1.0 - alpha) * (arrs["cost"] / cost_max)
        )
        score = np.where(arrs["feasible"], score, np.inf)
        idx = int(np.argmin(score))
        if not np.isfinite(score.flat[idx]):
            continue
        ir, it, iL = np.unravel_index(idx, score.shape)

        br = float(R3[ir, it, iL])
        bt = float(T3[ir, it, iL])
        bri = br - bt
        bL = float(L3[ir, it, iL])
        bLcyl = bL - 2.0 * br
        bP = float(arrs["P_max"][ir, it, iL])
        sh, sr, sa, svm = stresses_at_inner_wall(br, bri, bP, p_external)
        bmtank = float(arrs["m_tank"][ir, it, iL])
        bmfuel = float(arrs["m_fuel"][ir, it, iL])
        bmprop = bmtank + bmfuel
        bcost = bmtank * material.cost + bmfuel * fuel.cost

        design = OptimalDesign(
            material=material, fuel=fuel,
            r_outer=br, r_inner=bri, thickness=bt,
            L_total=bL, L_cyl=bLcyl,
            p_max=bP,
            sigma_hoop=sh, sigma_radial=sr, sigma_axial=sa, sigma_VM=svm,
            m_tank=bmtank, m_fuel=bmfuel, m_prop=bmprop,
            m_total=m_rest + bmprop,
            e_gas=float(arrs["E_gas"][ir, it, iL]),
            e_needed=float(arrs["E_needed"][ir, it, iL]),
            cost=bcost, score=float(score.flat[idx]),
        )
        result.per_combination.append(design)
        if best_overall is None or design.score < best_overall.score:
            best_overall = design

    result.global_optimum = best_overall
    return result
