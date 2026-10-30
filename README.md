# Two stores, one power block

*How to beat the Dunkelflaute.*

An interactive version of the technology-agnostic nomogram of the paper *Beating the Dunkelflaute: unlocking
very long-duration storage economics with two stores behind one power block* (Sapin et al., Joule, 2026). It
asks whether a dual-store plant, with a short-term and a long-term store behind the same power block, can earn
revenue from intraday arbitrage while holding a strategic reserve for the rare, long periods of low wind and
solar output.

Set the scene (volatility, electricity and fuel prices), the technology (efficiencies, store sizes, costs) and
the finance assumptions. The example is
traced through the nomogram from A to G. The nomogram is the figure of the paper: its axes are fixed and do
not change with the inputs.

**Online:** <https://paulsapin.github.io/beating-the-dunkelflaute_interactive-nomograph_2026/>. The code and
data behind the paper's figures are in
[Beating-the-Dunkelflaute_SapinEtAl_Joule_2026](https://github.com/paulSapin/Beating-the-Dunkelflaute_SapinEtAl_Joule_2026).

## Default values

| Input | Default |
|---|---|
| Intraday electricity volatility | 40 $/MWh |
| Electricity price | 20 $/MWh |
| Fuel price | 40 $/MWh |
| Short-term self-discharge rate | 0 %/day |
| Short-term store capacity (fixed) | 10 hours |
| Short-term round-trip efficiency | 60 % |
| Long-term store capacity | 100 hours |
| Long-term round-trip efficiency | 60 % |
| Long-term fuel consumption | 0 % |
| Power block specific cost | 1,500 $/kW |
| Short-term store specific cost | 10 $/kWh |
| Long-term store specific cost | 10 $/kWh |
| O&M expenses | 10 $/kW/year |
| Cost of capital | 5 % |
| Power block lifetime | 30 years |
| Stores lifetime | 60 years |

## Reading the nomogram

| Panel | Step | What it gives |
|---|---|---|
| (a) Short-term market | A → B → C | Annual intraday arbitrage profit, from volatility, short-term efficiency and self-discharge rate |
| (b) Long-term market | D → E | Total annual profit, after the long-term expenses |
| (c) Business case | F → G | Equivalent annual cost (EAC), once the annualised investment cost is included |

All quantities are per unit of rated power ($/kW/year).

- Long-term expenses: `E_lt = Δt_lt (C_el / η_lt + r_fuel C_fuel) + E_O&M`
- Annualised investment cost: `AIC = CRF_p c_p + CRF_s (c_st Δt_st + c_lt Δt_lt)`
- Capital recovery factors: `CRF_k = i (1 + i)^n_k / ((1 + i)^n_k - 1)`, for the power block (p) and the stores (s)
- Equivalent annual cost: `EAC = AIC - (intraday profit - E_lt)`

A negative EAC means the intraday profit pays for the plant, reserve included.

## Run locally

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Run on GitHub Pages (no server)

`index.html` runs the same Streamlit app entirely in the browser with [stlite](https://github.com/whitphx/stlite)
(Python compiled to WebAssembly by Pyodide). Publish the repository with GitHub Pages (Settings → Pages →
Deploy from a branch → `main`, root): the page loads Python and the packages on the first visit (a few
seconds), then updates the nomogram locally as the inputs change. To test it locally:

```
python -m http.server
```

and open http://localhost:8000.

`python nomogram.py` writes the example with the default values to `nomogram.png` without the web interface.

## Data

`data/multiHorizonStorageExploration.csv` holds the precomputed intraday arbitrage results behind panel (a):
the annual profit of a 100 MW plant with a 10-hour short-term store, optimised against day-ahead prices for
7 European countries (France, Germany, Italy, Norway, Spain, Sweden, UK) over 2020-2024, for round-trip
efficiencies from 10 to 100 % and self-discharge rates from 0 to 50 %/day. It was generated with
[pyTexLib](https://github.com/paulSapin/pyTexLib). Charging and discharging are both limited to the rated
power.

The curves of panel (a) are second-order polynomial fits of profit against intraday volatility. The example is
interpolated linearly between these fits in round-trip efficiency and self-discharge rate.

## Limitations

- The short-term store is fixed at 10 hours.
- Volatility is limited to the range covered by the data (about 3 to 104 $/MWh).
- The long-term store is charged once a year at the electricity price given; revenue from discharging the
  reserve and capacity payments are not included.
- Examples beyond the fixed axes are flagged; their values are still given above the figure.

## Licence

MIT, see [LICENSE](LICENSE). The Liberation Sans fonts in `fonts/` (used in place of Arial where it is not
installed) are under the SIL Open Font License, see `fonts/LICENSE-LiberationSans`.
