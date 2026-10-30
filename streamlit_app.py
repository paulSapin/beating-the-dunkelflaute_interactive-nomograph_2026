""" Web interface of the technology- and scene-agnostic nomogram.

Run locally with: streamlit run streamlit_app.py
"""

import io
import math

import pandas as pd
import streamlit as st

from nomogram import (SimpleNomogram, evaluateExample, DEFAULT_EXAMPLE, EXPLORATION_RESULTS, POWER,
                      SHORT_TERM_CAPACITY, MINIMUM_EFFICIENCY, PROFIT_TICKS)

st.set_page_config(page_title='How to beat the Dunkelflaute', layout='wide')

# Fixed axes of panel (c): equivalent annual cost (USD/kW/year)
EAC_RANGE = (-500, 1000)


@st.cache_data
def loadResults():
    return pd.read_csv(EXPLORATION_RESULTS)


@st.cache_data(show_spinner='Drawing nomogram...')
def drawNomogram(example, dpi=300):
    fig = SimpleNomogram(results=loadResults(), power=POWER, example=example)
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=dpi)
    return buffer.getvalue()


explorationResults = loadResults()
d = DEFAULT_EXAMPLE

# Bounds of the precomputed exploration
volatilityRange = (math.ceil(explorationResults.intraDay_volatility.min()),
                   math.floor(explorationResults.intraDay_volatility.max()))

st.title('How to beat the Dunkelflaute')
st.subheader('Two stores, one power block')
st.write('Can a dual-store long-duration energy storage plant earn revenue from short-term arbitrage while '
         'holding a long-term strategic reserve?')
st.write('Set the scene, technology and finance inputs in the sidebar.')
st.write('The example is traced in green on the nomogram (A to G).')

with st.sidebar:
    st.header('Scene')
    sigma = st.slider('Intraday electricity volatility ($/MWh)', *volatilityRange, value=int(d['sigma']))
    electricityPrice = st.slider('Electricity price ($/MWh)', 0, 200, int(d['electricityPrice']))
    fuelPrice = st.slider('Fuel price ($/MWh)', 0, 240, int(d['fuelPrice']))

    st.header('Technology')
    selfDischargeRate = st.slider('Short-term self-discharge rate (%/day)', 0, 20, int(d['selfDischargeRate'] * 100))
    st.caption(f'Short-term store capacity is fixed at {SHORT_TERM_CAPACITY:g} hours.')
    shortTermEfficiency = st.slider('Short-term round-trip efficiency (%)', int(MINIMUM_EFFICIENCY * 100), 100,
                                    round(d['shortTermEfficiency'] * 100))
    reserveCapacity = st.slider('Long-term store capacity (hours)', 0, 1000, int(d['reserveCapacity']))
    longTermEfficiency = st.slider('Long-term round-trip efficiency (%)', int(MINIMUM_EFFICIENCY * 100), 100,
                                   round(d['longTermEfficiency'] * 100))
    fuelConsumption = st.slider('Long-term fuel consumption (%)', 0, 300, int(d['fuelConsumption'] * 100),
                                help='Fuel consumed per unit of electricity discharged from the long-term store.')
    powerBlockSpecificCost = st.slider('Power block specific cost ($/kW)', 0, 5000, int(d['powerBlockSpecificCost']),
                                       step=50)
    shortTermStoreSpecificCost = st.slider('Short-term store specific cost ($/kWh)', 0.0, 100.0,
                                           float(d['shortTermStoreSpecificCost']), 0.01)
    longTermStoreSpecificCost = st.slider('Long-term store specific cost ($/kWh)', 0.0, 100.0,
                                          float(d['longTermStoreSpecificCost']), 0.01)
    fixedOM = st.slider('O&M expenses ($/kW/year)', 0, 100, int(d['fixedOM']))

    st.header('Finance')
    discountRate = st.slider('Cost of capital (%)', 0.0, 20.0, float(d['discountRate'] * 100), 0.5)
    powerBlockLifetime = st.slider('Power block lifetime (years)', 1, 60, int(d['powerBlockLifetime']))
    storeLifetime = st.slider('Stores lifetime (years)', 1, 100, int(d['storeLifetime']))

example = {**DEFAULT_EXAMPLE,
           'sigma': sigma,
           'electricityPrice': electricityPrice,
           'fuelPrice': fuelPrice,
           'selfDischargeRate': selfDischargeRate / 100,
           'shortTermEfficiency': shortTermEfficiency / 100,
           'reserveCapacity': reserveCapacity,
           'longTermEfficiency': longTermEfficiency / 100,
           'fuelConsumption': fuelConsumption / 100,
           'powerBlockSpecificCost': powerBlockSpecificCost,
           'shortTermStoreSpecificCost': shortTermStoreSpecificCost,
           'longTermStoreSpecificCost': longTermStoreSpecificCost,
           'fixedOM': fixedOM,
           'discountRate': discountRate / 100,
           'powerBlockLifetime': powerBlockLifetime,
           'storeLifetime': storeLifetime}

businessCase = evaluateExample(explorationResults, POWER, example)

st.caption('Business case of the example, in $/kW/year')
columns = st.columns(5)
columns[0].metric('Intraday profit', f'{businessCase["intraDayProfit"]:.0f}')
columns[1].metric('Long-term expenses', f'{businessCase["longTermExpenses"]:.0f}')
columns[2].metric('Total annual profit', f'{businessCase["totalProfit"]:.0f}')
columns[3].metric('Annualised investment cost', f'{businessCase["AIC"]:.0f}')
columns[4].metric('Equivalent annual cost', f'{businessCase["EAC"]:.0f}')

# The nomogram axes are fixed: flag examples that fall outside them
if not PROFIT_TICKS[0] <= businessCase['totalProfit'] <= PROFIT_TICKS[-1]:
    st.warning(f'The total annual profit is outside the plotted range ({PROFIT_TICKS[0]} to {PROFIT_TICKS[-1]} '
               '$/kW/year): points D to G are off the chart. The values above remain valid.')
elif not EAC_RANGE[0] <= businessCase['EAC'] <= EAC_RANGE[1]:
    st.warning(f'The equivalent annual cost is outside the plotted range ({EAC_RANGE[0]} to {EAC_RANGE[1]} '
               '$/kW/year): points F and G are off the chart. The values above remain valid.')

image = drawNomogram(example)
left, _ = st.columns([3, 1])
left.image(image)
st.download_button('Download figure (PNG)', image, file_name='nomogram.png', mime='image/png')
