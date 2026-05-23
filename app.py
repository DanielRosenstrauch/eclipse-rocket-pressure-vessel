"""Streamlit web demo for the Eclipse Rocket pressure-vessel optimization.

Run locally:
    streamlit run app.py

Live demo: see README for the deployed Streamlit Community Cloud URL.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from eclipse.data import (
    FUELS,
    INCH_TO_M,
    MATERIALS,
    PSI_TO_PA,
    material_by_name,
    fuel_by_name,
)
from eclipse.optimize import DesignSpace, optimize
from eclipse.physics import (
    interior_volume,
    lame_stresses,
    metal_shell_volume,
    moles_stored,
    p_max_thick_walled,
    stresses_at_inner_wall,
    von_mises,
)
from eclipse.trajectory import drag_work, energy_needed


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Eclipse Rocket Pressure Vessel Designer",
    page_icon="\U0001F680",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Cached runners
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def cached_drag_work(h_ft: float, cd: float, d_in: float) -> float:
    return drag_work(h_ft, cd, d_in)


@st.cache_data(show_spinner="Running 256,000-point optimization...")
def cached_optimize(
    alpha: float,
    m_rest: float,
    h_target_ft: float,
    cd: float,
    nose_d_in: float,
    nr: int,
    nt: int,
    nL: int,
):
    ds = DesignSpace.default()
    ds.nr, ds.nt, ds.nL = nr, nt, nL
    return optimize(
        alpha=alpha,
        m_rest=m_rest,
        h_target_ft=h_target_ft,
        cd=cd,
        nose_cone_d_in=nose_d_in,
        design_space=ds,
    )


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

st.sidebar.title("Design Controls")

st.sidebar.markdown("**Composite objective**")
alpha = st.sidebar.slider(
    "alpha (0 = cheapest, 1 = lightest)",
    min_value=0.0, max_value=1.0, value=0.5, step=0.05,
    help="score = alpha * (m_prop/m_max) + (1-alpha) * (cost/cost_max)",
)

with st.sidebar.expander("Mission parameters", expanded=False):
    m_rest = st.number_input("Rest-of-rocket mass [kg]", value=85.0, min_value=1.0)
    h_target_ft = st.number_input("Target altitude [ft]", value=30_000.0, min_value=1_000.0)
    cd = st.number_input("Drag coefficient Cd", value=0.75, min_value=0.0)
    nose_d_in = st.number_input("Nose cone diameter [in]", value=6.0, min_value=0.1)

with st.sidebar.expander("Design grid resolution", expanded=False):
    nr = st.slider("r0 points", 20, 120, 80)
    nt = st.slider("t points", 20, 120, 80)
    nL = st.slider("L points", 10, 80, 40)
    st.caption(f"Total grid points per combination: **{nr*nt*nL:,}**")

st.sidebar.markdown("---")
st.sidebar.caption(
    "Source: MECH 315 (Spring 2026) Eclipse Rocket Pressure Vessel report. "
    "Translated to Python by Daniel Rosenstrauch."
)


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

st.title("\U0001F680 Eclipse Rocket Pressure Vessel Designer")
st.markdown(
    "Interactive thick-walled (Lamé) pressure vessel optimization. "
    "Adjust the mass-vs-cost weighting alpha or the mission parameters on the left; "
    "every plot updates live."
)

# Run optimization
W_drag = cached_drag_work(h_target_ft, cd, nose_d_in)
result = cached_optimize(alpha, m_rest, h_target_ft, cd, nose_d_in, nr, nt, nL)
opt = result.global_optimum

if opt is None:
    st.error("No feasible designs at these parameters. Try a different mission or grid.")
    st.stop()


# ---------- KPI strip ----------

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Material", opt.material.name.split(" (")[0])
k2.metric("Fuel", opt.fuel.name)
k3.metric("Propulsion mass", f"{opt.m_prop:.3f} kg")
k4.metric("Total cost", f"${opt.cost:.2f}")
k5.metric("P_max", f"{opt.p_max_psi:.0f} psi")

st.caption(
    f"Drag work: {result.drag_work_J/1e6:.3f} MJ • "
    f"Energy margin: {opt.margin:.3f}x • "
    f"sigma_VM / Sy = {opt.sigma_VM / opt.material.yield_strength:.5f} "
    f"(vessel sized exactly at yield)"
)


# ---------- Tabs ----------

tab_design, tab_stress, tab_compare, tab_explorer, tab_about = st.tabs([
    "Optimal Design", "Stress Profile", "All 12 Combinations",
    "Design Space Explorer", "About",
])


# ---------------------------------------------------------------------------
# Tab 1: Optimal Design
# ---------------------------------------------------------------------------

with tab_design:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Geometry")
        df_geo = pd.DataFrame(
            [
                ("Outer radius r_o", f"{opt.r_outer*1000:.2f} mm", f"{opt.r_outer/INCH_TO_M:.3f} in"),
                ("Inner radius r_i", f"{opt.r_inner*1000:.2f} mm", f"{opt.r_inner/INCH_TO_M:.3f} in"),
                ("Wall thickness t", f"{opt.thickness*1000:.3f} mm", f"{opt.thickness/INCH_TO_M:.4f} in"),
                ("Total length L", f"{opt.L_total*1000:.1f} mm", f"{opt.L_total/INCH_TO_M:.2f} in"),
                ("Cylinder length L_cyl", f"{opt.L_cyl*1000:.1f} mm", f"{opt.L_cyl/INCH_TO_M:.2f} in"),
                ("Wall/radius ratio t/r_i", f"{opt.thickness/opt.r_inner:.4f}", "thick if > 0.1"),
            ],
            columns=["Quantity", "SI", "Imperial"],
        )
        st.dataframe(df_geo, hide_index=True, width="stretch")

        st.subheader("Mass and Cost Breakdown")
        df_mass = pd.DataFrame(
            [
                ("Tank (shell)", opt.m_tank, opt.m_tank * opt.material.cost),
                ("Fuel (gas)", opt.m_fuel, opt.m_fuel * opt.fuel.cost),
                ("Total propulsion", opt.m_prop, opt.cost),
            ],
            columns=["Component", "Mass [kg]", "Cost [$]"],
        )
        st.dataframe(
            df_mass, hide_index=True, width="stretch",
            column_config={
                "Mass [kg]": st.column_config.NumberColumn(format="%.4f"),
                "Cost [$]": st.column_config.NumberColumn(format="$%.2f"),
            },
        )

    with right:
        st.subheader("Stresses at Inner Wall")
        df_stress = pd.DataFrame(
            [
                ("Hoop sigma_theta", opt.sigma_hoop / 1e6),
                ("Radial sigma_r", opt.sigma_radial / 1e6),
                ("Axial sigma_phi", opt.sigma_axial / 1e6),
                ("Von Mises sigma_VM", opt.sigma_VM / 1e6),
                ("Yield strength Sy", opt.material.yield_strength / 1e6),
            ],
            columns=["Stress component", "Value [MPa]"],
        )
        st.dataframe(
            df_stress, hide_index=True, width="stretch",
            column_config={
                "Value [MPa]": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        st.subheader("Energy Balance")
        df_energy = pd.DataFrame(
            [
                ("Stored E_gas", opt.e_gas / 1e6),
                ("Required E_needed", opt.e_needed / 1e6),
                ("Margin (E_gas / E_needed)", opt.margin),
            ],
            columns=["Quantity", "Value"],
        )
        st.dataframe(
            df_energy, hide_index=True, width="stretch",
            column_config={
                "Value": st.column_config.NumberColumn(format="%.4f"),
            },
        )

        st.subheader("Composite Score")
        st.markdown(
            f"`score = {alpha:.2f} * (m_prop / {result.m_prop_max:.3f}) + "
            f"{1-alpha:.2f} * (cost / ${result.cost_max:.2f})`"
        )
        st.markdown(f"**Score = {opt.score:.5f}** (lower is better)")


# ---------------------------------------------------------------------------
# Tab 2: Stress through the wall
# ---------------------------------------------------------------------------

with tab_stress:
    st.subheader("Stress Distribution Through the Wall (Lamé)")
    st.markdown(
        "All three principal stresses as a function of radial position. "
        "Worst-case at the inner wall (r = r_i), which is what sets P_max."
    )

    r_axis = np.linspace(opt.r_inner, opt.r_outer, 200)
    sh, sr, sa = lame_stresses(r_axis, opt.r_outer, opt.r_inner, opt.p_max)
    svm = von_mises(sh, sr, sa)

    df_curve = pd.DataFrame({
        "r [mm]": r_axis * 1000,
        "sigma_hoop": sh / 1e6,
        "sigma_radial": sr / 1e6,
        "sigma_axial": sa / 1e6,
        "sigma_VM": svm / 1e6,
    }).melt(id_vars="r [mm]", var_name="component", value_name="Stress [MPa]")

    fig = px.line(df_curve, x="r [mm]", y="Stress [MPa]", color="component")
    fig.add_hline(
        y=opt.material.yield_strength / 1e6,
        line_dash="dash", line_color="red",
        annotation_text=f"Sy = {opt.material.yield_strength/1e6:.0f} MPa",
    )
    fig.update_layout(height=480)
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "The Von Mises curve peaks at the inner wall exactly at Sy, confirming "
        "the closed-form derivation of P_max from sigma_VM = sqrt(3) * r_o^2 * (P_i - P_0) / (r_o^2 - r_i^2)."
    )


# ---------------------------------------------------------------------------
# Tab 3: All 12 combinations
# ---------------------------------------------------------------------------

with tab_compare:
    st.subheader("Optimal Design per (Material, Fuel) Pair")
    rows = []
    for d in result.per_combination:
        rows.append({
            "Material": d.material.name,
            "Fuel": d.fuel.name,
            "r [in]": d.r_outer / INCH_TO_M,
            "t [in]": d.thickness / INCH_TO_M,
            "L [in]": d.L_total / INCH_TO_M,
            "P_max [psi]": d.p_max_psi,
            "m_tank [kg]": d.m_tank,
            "m_fuel [kg]": d.m_fuel,
            "m_prop [kg]": d.m_prop,
            "Cost [$]": d.cost,
            "Score": d.score,
        })
    df = pd.DataFrame(rows).sort_values("Score").reset_index(drop=True)
    # Mark the global optimum row with a leading star
    df.insert(
        0, "",
        [
            "⭐" if (r["Material"] == opt.material.name and r["Fuel"] == opt.fuel.name) else ""
            for _, r in df.iterrows()
        ],
    )

    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "r [in]": st.column_config.NumberColumn(format="%.3f"),
            "t [in]": st.column_config.NumberColumn(format="%.4f"),
            "L [in]": st.column_config.NumberColumn(format="%.2f"),
            "P_max [psi]": st.column_config.NumberColumn(format="%.0f"),
            "m_tank [kg]": st.column_config.NumberColumn(format="%.3f"),
            "m_fuel [kg]": st.column_config.NumberColumn(format="%.4f"),
            "m_prop [kg]": st.column_config.NumberColumn(format="%.4f"),
            "Cost [$]": st.column_config.NumberColumn(format="$%.2f"),
            "Score": st.column_config.NumberColumn(format="%.5f"),
        },
    )
    st.caption("⭐ marks the globally optimal combination at the current alpha.")

    st.subheader("Mass vs. Cost Trade-off")
    fig2 = px.scatter(
        df, x="Cost [$]", y="m_prop [kg]",
        color="Material", symbol="Fuel",
        hover_data=["P_max [psi]", "r [in]", "t [in]", "L [in]", "Score"],
        size=[60] * len(df),
        size_max=18,
    )
    fig2.update_layout(height=480)
    st.plotly_chart(fig2, width="stretch")


# ---------------------------------------------------------------------------
# Tab 4: Design Space Explorer (alpha sweep)
# ---------------------------------------------------------------------------

with tab_explorer:
    st.subheader("How the Globally Optimal Choice Changes with alpha")
    st.markdown(
        "Sweep the weighting parameter from pure-cost (alpha=0) to pure-mass (alpha=1) "
        "and watch which (material, fuel) combination wins."
    )

    alphas = np.linspace(0.0, 1.0, 21)
    sweep_rows = []
    for a in alphas:
        r = cached_optimize(float(round(a, 3)), m_rest, h_target_ft, cd, nose_d_in, nr, nt, nL)
        if r.global_optimum is None:
            continue
        g = r.global_optimum
        sweep_rows.append({
            "alpha": a,
            "Winner": f"{g.material.name.split(' (')[0]} + {g.fuel.name.split(' (')[0]}",
            "m_prop [kg]": g.m_prop,
            "Cost [$]": g.cost,
            "Score": g.score,
        })
    sweep_df = pd.DataFrame(sweep_rows)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=sweep_df["alpha"], y=sweep_df["m_prop [kg]"],
        mode="lines+markers", name="m_prop [kg]", yaxis="y1",
    ))
    fig3.add_trace(go.Scatter(
        x=sweep_df["alpha"], y=sweep_df["Cost [$]"],
        mode="lines+markers", name="Cost [$]", yaxis="y2",
    ))
    fig3.update_layout(
        height=460,
        xaxis_title="alpha (0 = cheapest, 1 = lightest)",
        yaxis=dict(title="Propulsion mass [kg]"),
        yaxis2=dict(title="Cost [$]", overlaying="y", side="right"),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig3, width="stretch")

    st.dataframe(
        sweep_df, hide_index=True, width="stretch",
        column_config={
            "alpha": st.column_config.NumberColumn(format="%.2f"),
            "m_prop [kg]": st.column_config.NumberColumn(format="%.4f"),
            "Cost [$]": st.column_config.NumberColumn(format="$%.2f"),
            "Score": st.column_config.NumberColumn(format="%.5f"),
        },
    )

    st.markdown("---")
    st.subheader("Feasibility Map at L = L_max")
    st.markdown(
        "For the current optimum's material and fuel, this map shows feasible "
        "(green) vs infeasible (white) designs over the (r_o, t) plane at maximum length."
    )

    # Build a 2D slice at L = L_max
    L_slice = opt.L_total
    r0_max_m = (5.75 / 2.0) * INCH_TO_M
    r_vec = np.linspace(0.05 * r0_max_m, r0_max_m, 120)
    t_vec = np.linspace(0.5e-3, 25e-3, 120)
    R2, T2 = np.meshgrid(r_vec, t_vec, indexing="ij")
    Ri2 = R2 - T2
    Lcyl2 = L_slice - 2.0 * R2

    valid2 = (T2 < R2) & (Ri2 > 0) & (Lcyl2 > 0)
    P2 = p_max_thick_walled(R2, Ri2, opt.material.yield_strength)
    V_metal2 = metal_shell_volume(R2, Ri2, np.full_like(R2, L_slice))
    V_inner2 = interior_volume(Ri2, R2, np.full_like(R2, L_slice))
    n2 = moles_stored(P2, V_inner2)
    Egas2 = n2 * opt.fuel.energy_density
    mfuel2 = n2 * opt.fuel.molar_mass
    mtank2 = opt.material.density * V_metal2
    mtot2 = m_rest + mtank2 + mfuel2
    En2 = energy_needed(mtot2, h_target_ft, result.drag_work_J)
    feas2 = valid2 & (Egas2 >= En2)

    margin = np.where(feas2, Egas2 / En2, np.nan)

    fig4 = go.Figure(data=go.Heatmap(
        x=r_vec / INCH_TO_M, y=t_vec / INCH_TO_M, z=margin.T,
        colorscale="Viridis", colorbar=dict(title="E_gas / E_needed"),
        hovertemplate="r_o = %{x:.3f} in<br>t = %{y:.4f} in<br>margin = %{z:.3f}<extra></extra>",
    ))
    fig4.add_trace(go.Scatter(
        x=[opt.r_outer / INCH_TO_M], y=[opt.thickness / INCH_TO_M],
        mode="markers", marker=dict(size=14, color="red", symbol="star"),
        name="Optimum", hovertext="Optimum",
    ))
    fig4.update_layout(
        height=520,
        xaxis_title="Outer radius r_o [in]",
        yaxis_title="Wall thickness t [in]",
        title=f"Feasibility at L = {L_slice/INCH_TO_M:.1f} in ({opt.material.name} + {opt.fuel.name})",
    )
    st.plotly_chart(fig4, width="stretch")


# ---------------------------------------------------------------------------
# Tab 5: About
# ---------------------------------------------------------------------------

with tab_about:
    st.markdown(
        """
### About this project

This is a Python + Streamlit translation of the **MECH 315 (Stress Analysis,
Spring 2026) Eclipse Rocket Pressure Vessel** project, originally written in
MATLAB. The optimization sizes a thick-walled, hemispherically-capped
pressure vessel to store gaseous propellant for the second stage of a
hybrid rocket reaching 30,000 ft.

**Method:** Lamé equations for stress through the wall, Von Mises yield
criterion at the inner wall (the worst-case location), ideal-gas treatment
of the propellant, ISA-troposphere drag model, and a fully-vectorized two-pass
optimization over a 256,000-point design grid for each of 12 material/fuel
combinations.

**Key formula (P_max derivation):**

```
sigma_VM = sqrt(3) * r_o^2 * (P_i - P_0) / (r_o^2 - r_i^2)  = Sy
=>  P_max = Sy * (r_o^2 - r_i^2) / (sqrt(3) * r_o^2)  +  P_0
```

**Verification:** the Python implementation matches the MATLAB report
within numerical precision on all 12 combinations, the global optimum,
and the drag-work integral. See `tests/test_physics.py`.

**Original team:** Daniel Rosenstrauch and Hayden Webb, Rice University,
Spring 2026.

**Source code and full PDF report:** see the GitHub repository for this app.
"""
    )
