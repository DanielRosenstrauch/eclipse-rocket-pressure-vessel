# Eclipse Rocket Pressure Vessel Designer

Interactive web tool that designs a thick-walled, hemispherically-capped
pressure vessel for the gaseous-propellant stage of a two-stage hybrid rocket
targeting 30,000 ft. It searches a 3-D design grid (256,000 geometries) across
four materials and three fuels (12 combinations, ~3M evaluations) and picks the
configuration that minimizes a composite mass-vs-cost objective.

This is a Python + Streamlit translation of my MECH 315 (Stress Analysis,
Spring 2026) final project at Rice University. The original implementation was
MATLAB; the Python version reproduces every numerical result in the original
report (see `tests/`).

See a **LIVE DEMO** now at
https://eclipse-rocket-pressure-vessel-c6xq3emsxwnqzd9z2es8x7.streamlit.app/

---

## What the tool does

- Computes the maximum safe internal pressure `P_max` from a closed-form Lamé /
  Von Mises derivation at the inner wall (the worst-case location).
- Integrates the ISA-troposphere drag-work along the prescribed velocity
  profile and folds it into the energy balance `m·g·h + W_drag = E_gas`.
- Sweeps a 3-D design grid in (`r_outer`, `wall_thickness`, `L_total`) and
  filters out geometries that violate any structural or energy constraint.
- Applies a tunable composite objective
  `score = α·(m_prop/m_prop_max) + (1−α)·(cost/cost_max)`
  so the user can interpolate from cheapest design (α=0) to lightest design
  (α=1) and watch the winner change.

## Headline result (α = 0.5)

| Quantity | Value |
| --- | --- |
| Material | Duralumin 2024-T3 |
| Fuel | Hydrogen (H₂) |
| Outer radius | 2.737 in |
| Wall thickness | 0.0319 in |
| Total length | 60.0 in |
| Max operating pressure | 684 psi |
| Tank + fuel mass | 1.577 kg |
| Total cost | $9.09 |
| σ\_VM / Sy | 1.000 (sized exactly at yield) |
| Energy margin | 1.008× |

The Python optimizer reproduces these numbers from the original MATLAB report
to within numerical precision.

## Method

**Thick-walled Lamé equations** for a closed-end cylinder under internal
pressure `P_i` and external pressure `P_0` give three stresses at radial
position `r`:

```
σ_hoop(r)   = (P_i·r_i² − P_0·r_o²) / (r_o² − r_i²)  +  (r_i·r_o)²·(P_i − P_0) / (r²·(r_o² − r_i²))
σ_radial(r) = (P_i·r_i² − P_0·r_o²) / (r_o² − r_i²)  −  (r_i·r_o)²·(P_i − P_0) / (r²·(r_o² − r_i²))
σ_axial     = (P_i·r_i² − P_0·r_o²) / (r_o² − r_i²)            (uniform through the wall)
```

The Von Mises criterion at `r = r_i` collapses to a clean form:

```
σ_VM = √3 · r_o² · (P_i − P_0) / (r_o² − r_i²)  =  Sy
```

Solving for `P_i` gives the design's pressure ceiling:

```
P_max = Sy · (r_o² − r_i²) / (√3 · r_o²)  +  P_0
```

The thin-walled limit (`t ≪ r_o`, so `r_o² − r_i² ≈ 2·r_o·t`) recovers the
familiar `P_max ≈ 2·Sy·t / (√3·r_o)`, which is how I sanity-checked the
derivation.

The optimizer is vectorized — every grid cell is evaluated in a single NumPy
broadcast rather than a Python loop — so a full 12-combination, 3-million-cell
sweep finishes in well under a second.

## Run it locally

```bash
git clone https://github.com/<your-handle>/eclipse-rocket-pressure-vessel.git
cd eclipse-rocket-pressure-vessel
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open <http://localhost:8501>.

## Run the verification tests

```bash
pytest tests/ -v
```

The test suite pins the Python port to the published MATLAB report results,
including:

- σ\_VM = Sy at the inner wall (numerical self-consistency)
- Drag work integral within 5% of the report's 1.11 MJ
- Tank mass and P\_max at the published optimum (Duralumin + H₂)
- Global optimum at α = 0.5
- A sample non-optimal combination (Aluminum + H₂) row

## Repository layout

```
eclipse-rocket-pressure-vessel/
├── app.py                    # Streamlit web app
├── eclipse/
│   ├── data.py               # Material and fuel libraries + universal constants
│   ├── physics.py            # Lamé stresses, geometry, gas content
│   ├── trajectory.py         # ISA atmosphere, drag-work integral
│   └── optimize.py           # Vectorized two-pass optimizer
├── tests/
│   └── test_physics.py       # Verification against MATLAB report numbers
├── requirements.txt
└── DEPLOY.md                 # Step-by-step deploy to Streamlit Community Cloud
```

## Credits

Original MECH 315 project: **Daniel Rosenstrauch** and **Hayden Webb**,
Rice University, Spring 2026.

Python translation, Streamlit UI, and deployment: Daniel Rosenstrauch.

Released under the MIT License.
