"""
Technology- and scene-agnostic nomogram for dual-store long-duration electricity storage (web app version of
technology_agnostic_nomogram.py, from the paper repository).

Panels:
    (a) Short-term market: annual intraday arbitrage profit vs intraday price
        volatility, for a range of round-trip efficiencies and self-discharge rates
        (2nd-order polynomial fits of the exploration results);
    (b) Long-term market: total annual profit after inter-year (Dunkelflaute)
        charging expenses;
    (c) Business case: equivalent annual cost (EAC) vs annualised investment cost (AIC).
The example (A -> G, in green) is drawn on fixed axes.

Run ``python nomogram.py`` to write the default example to nomogram.png.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.ticker as ticker
from matplotlib import font_manager
import numpy as np
import pandas as pd
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

textFontSize = 9

# Matplotlib style (as the paper figures). Liberation Sans (SIL Open Font License) has the metrics of Arial and
# stands in for it where Arial is not installed (e.g. in the browser)
for font in (Path(__file__).resolve().parent / 'fonts').glob('*.ttf'):
    font_manager.fontManager.addfont(font)
mpl.rcParams.update(mpl.rcParamsDefault)
mpl.rcParams.update({
    "text.usetex": False,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"],
    "lines.linewidth": 0.5,
    "font.size": textFontSize,
})


""" ASSUMPTIONS """

EXPLORATION_RESULTS = Path(__file__).resolve().parent / 'data' / 'multiHorizonStorageExploration.csv'

# Figure width (double column of the paper)
FIGURE_WIDTH_CM = 18.5

# Short-term store capacity of the exploration results (hours)
SHORT_TERM_CAPACITY = 10

# Smallest round-trip efficiency drawn on the nomogram
MINIMUM_EFFICIENCY = 0.2

# Markers of the worked-example points A to G
POINT_STYLE = {'markersize': 4.5, 'alpha': 0.7, 'markeredgewidth': 0}

# Total annual profit axis of panels (b) and (c) (USD/kW/year)
PROFIT_TICKS = list(range(-200, 801, 200))

# Rated power used to normalise the annual profits of the exploration results (kW)
POWER = 100e3

# Default example
DEFAULT_EXAMPLE = {'sigma': 40,                      # USD/MWh
                   'electricityPrice': 20,           # USD/MWh
                   'fuelPrice': 40,                  # USD/MWh
                   'selfDischargeRate': 0,           # 1/day
                   'shortTermEfficiency': 0.6,
                   'reserveCapacity': 100,           # hours
                   'longTermEfficiency': 0.6,
                   'fuelConsumption': 0,             # per kWh discharged from the long-term store
                   'powerBlockSpecificCost': 1500,   # USD/kW
                   'shortTermStoreSpecificCost': 10, # USD/kWh
                   'longTermStoreSpecificCost': 10,  # USD/kWh
                   'fixedOM': 10,                    # USD/kW/year
                   'capacityPayment': 0,             # USD/kW/year
                   'discountRate': 0.05,
                   'powerBlockLifetime': 30,         # years
                   'storeLifetime': 60}              # years


""" BUSINESS CASE """


def capitalRecoveryFactor(discountRate: float, lifetime: float) -> float:
    r, n = discountRate, lifetime
    return r / (1 - 1 / (1 + r) ** n) if r > 0 else 1 / n


def intraDayProfit(results: pd.DataFrame, power: float, example: dict) -> float:
    """Annual intraday profit (USD/kW/year) of the example, interpolated linearly in round-trip efficiency and
    self-discharge rate between the fitted curves of panel (a)."""

    etaRange = np.sort(np.unique(results.intraDay_roundtripEfficiency))
    rangeSDR = np.sort(np.unique(results.intraDay_selfDischargeRate))

    profits = []
    for SDR in rangeSDR:
        _profits = []
        for eta in etaRange:
            _results = results[(results.intraDay_roundtripEfficiency == eta) &
                               (results.intraDay_selfDischargeRate == SDR)]
            # Same 2nd-order polynomial as plotted on the nomogram
            p = np.polyfit(_results.intraDay_volatility.values, _results.annualIntraDayProfit.values / power, deg=2)
            _profits.append(np.polyval(p, example['sigma']))
        profits.append(np.interp(example['shortTermEfficiency'], etaRange, _profits))

    return float(np.interp(example['selfDischargeRate'], rangeSDR, profits))


def evaluateExample(results: pd.DataFrame, power: float, example: dict) -> dict:
    """Business case of the example (all per unit power, in USD/kW/year)."""

    CRF_p = capitalRecoveryFactor(example['discountRate'], example['powerBlockLifetime'])
    CRF_s = capitalRecoveryFactor(example['discountRate'], example['storeLifetime'])
    dt = example['reserveCapacity']
    AIC = (CRF_p * example['powerBlockSpecificCost']
           + CRF_s * (example['shortTermStoreSpecificCost'] * SHORT_TERM_CAPACITY
                      + example['longTermStoreSpecificCost'] * dt))
    P_el = example['electricityPrice'] / 1000
    P_f = example['fuelPrice'] / 1000
    longTermExpenses = dt * (P_el / example['longTermEfficiency'] + P_f * example['fuelConsumption']) + example['fixedOM']
    interYearProfit = example['capacityPayment'] - longTermExpenses
    shortTermProfit = intraDayProfit(results, power, example)
    totalProfit = shortTermProfit + interYearProfit

    return {'AIC': AIC,
            'intraDayProfit': shortTermProfit,
            'longTermExpenses': longTermExpenses,
            'interYearProfit': interYearProfit,
            'totalProfit': totalProfit,
            'EAC': AIC - totalProfit}


""" NOMOGRAM """


def SimpleNomogram(results: pd.DataFrame, power: float, example: dict, *, resolution: int = 1000) -> Figure:
    """
    Draw the nomogram. ``power`` (kW) normalises the annual intraday profits of the
    exploration results; ``example`` holds the worked example shown in green. The axes are fixed: they do not
    depend on the example.
    """

    lineStyles: list = ['-', ':', '--', '-.', (0, (3, 10, 1, 10))]

    # Create figure canvas
    w = FIGURE_WIDTH_CM / 2.54
    fig = Figure(figsize=(w, w), constrained_layout=True)
    FigureCanvasAgg(fig)

    n_p = example['powerBlockLifetime']
    n_s = example['storeLifetime']
    c_p = example['powerBlockSpecificCost']
    c_st = example['shortTermStoreSpecificCost']
    c_lt = example['longTermStoreSpecificCost']
    E_om = example['fixedOM']
    dt_st = SHORT_TERM_CAPACITY
    businessCase = evaluateExample(results, power, example)
    AIC = businessCase['AIC']
    interYearProfit = businessCase['interYearProfit']

    """ 0. Inputs description """

    # Create subplot
    ax = fig.add_subplot(2, 2, 1)

    data = [
        ['', r'', 'Symbol', r'Example'],
        ['', r'Intraday electricity volatility', r'$\sigma_\mathrm{el}$', rf'{int(example["sigma"])} \$/MWh'],
        ['Scene', r'Electricity price', r'$C_\mathrm{el}$', rf'{int(example["electricityPrice"])} \$/MWh'],
        ['', r'Fuel price', r'$C_\mathrm{fuel}$', rf'{int(example["fuelPrice"])} \$/MWh'],
        ['', r'Short-term self-discharge rate', r'$\lambda_\mathrm{st}$', rf'{example["selfDischargeRate"] * 100:g} %/day'],
        ['', r'Short-term store capacity', r'$\Delta t_\mathrm{st}$ (fixed)', rf'{dt_st} hours'],
        ['', r'Short-term round-trip efficiency', r'$\eta_\mathrm{st}$', rf'{example["shortTermEfficiency"] * 100:g} %'],
        ['', r'Long-term store capacity', r'$\Delta t_\mathrm{lt}$',
         rf'{int(example["reserveCapacity"])} hours'],
        ['Technology', r'Long-term round-trip efficiency', r'$\eta_\mathrm{lt}$', rf'{example["longTermEfficiency"] * 100:g} %'],
        ['', 'Long-term fuel consumption\n', r'$r_\mathrm{fuel}$', rf'{example["fuelConsumption"] * 100:g} %'],
        ['', r'Power block specific cost', r'$c_\mathrm{p}$', rf'{c_p:g} \$/kW'],
        ['', r'Short-term store specific cost', r'$c_\mathrm{st}$', rf'{c_st:g} \$/kWh'],
        ['', r'Long-term store specific cost', r'$c_\mathrm{lt}$', rf'{c_lt:g} \$/kWh'],
        ['', r'O&M expenses', r'$E_\mathrm{O&M}$', rf'{E_om:g} \$/kW/year'],
        ['', r'Cost of capital', r'$i$', rf'{example["discountRate"] * 100:g} %'],
        ['', r'Power block lifetime', r'$n_\mathrm{p}$', rf'{n_p} years'],
        ['', r'Stores lifetime', r'$n_\mathrm{s}$', rf'{n_s} years'],
        [r' $\,$ $\qquad$ $\,$ Finance', 'Capital recovery factors',
         r'$\mathrm{CRF}_k\,=\,\frac{i(1+i)^{n_k}}{(1+i)^{n_k} - 1}$', '']
    ]

    length = len(data)
    fuelRow = next(i for i, row in enumerate(data) if row[1].startswith('Long-term fuel consumption'))

    # Pop the headers from the data array
    column_headers = data.pop(0)

    # Table data needs to be non-numeric text. Format the data
    cell_text = []
    for row in data:
        cell_text.append([x for x in row])

    # Add a table at the bottom of the axes
    table = ax.table(cellText=cell_text,
                     cellLoc='left',
                     colLoc='left',
                     colLabels=column_headers,
                     bbox=[-0.2, -0, 1.2, 1.06],  # (x0, y0, width, height) where (x0,y0) = lower left coordinates
                     edges='TB')

    cells = table.get_celld()
    cells[0, 0].set_text_props(fontweight='bold')
    cells[0, 1].set_text_props(fontweight='bold')
    cells[0, 2].set_text_props(fontweight='bold')
    cells[0, 3].set_text_props(fontweight='bold')
    cells[0, 0].visible_edges = 'B'
    cells[0, 1].visible_edges = 'B'
    cells[0, 2].visible_edges = 'B'
    cells[0, 3].visible_edges = 'B'
    cells[length - 1, 0].visible_edges = 'T'
    cells[length - 1, 1].visible_edges = 'T'
    cells[length - 1, 2].visible_edges = 'T'
    cells[length - 1, 3].visible_edges = 'T'
    for i in range(length):
        cells[i, 3].set_text_props(color='green')
        cells[i, 3].set_width(0.35)
        cells[i, 2].set_width(0.35)
        cells[i, 1].set_width(0.7)
        cells[i, 0].set_width(0.1)
        cells[i, 0].get_text().set_rotation(90)
        cells[i, 0].set_text_props(fontweight='bold')

    # Group separators (column 0): Scene, Technology, Finance
    last = length - 1
    for i in range(1, length):
        cells[i, 0].visible_edges = 'B' if i in (3, last - 4, last) else ''
    for j in range(1, 4):
        cells[last, j].visible_edges = 'B'

    # Make the fuel and last rows taller to accommodate the note and the stacked CRF fraction
    lastRowHeight = cells[length - 1, 1].get_height()
    for j in range(4):
        cells[fuelRow, j].set_height(lastRowHeight * 1.5)
        cells[length - 1, j].set_height(lastRowHeight * 1.5)

    # Scaling is the only influence we have over top and bottom cell padding. Make the rows taller.
    table.scale(1, 1)
    table.auto_set_font_size(False)
    table.set_fontsize(textFontSize - 1)

    # Unit of the fuel consumption, in a smaller font below the description (cells are placed on drawing)
    fig.canvas.draw()
    for row, note in [(fuelRow, r'(per kWh$_\mathrm{el}$ discharged)')]:
        cell = cells[row, 1]
        ax.text(cell.get_x() + cell.PAD * cell.get_width(), cell.get_y() + 0.3 * cell.get_height(), note,
                transform=ax.transAxes, ha='left', va='center', fontsize=textFontSize - 2)

    # Hide axes border
    ax.axis('off')


    """ 1. Potential yearly profit VS volatility """

    # Create subplot
    ax = fig.add_subplot(2, 2, 2)

    # Initialise min-max values
    maximumIntraDayYearlyProfit = 0
    minimumIntraDayYearlyProfit = math.inf
    maximumVolatility = 0
    minimumVolatility = math.inf

    # Example: intraday profit interpolated between the fitted curves
    xp = businessCase['intraDayProfit']
    yp = example['sigma']

    # Plot volatility-dependent energy-arbitrage profit for no self-discharge rate
    intraDay_dt_range = np.flip(np.sort(np.unique(results.intraDay_dischargeDuration)))
    for intraDay_dt, lineStyle in zip(intraDay_dt_range, lineStyles[:len(intraDay_dt_range)]):

        # Select results
        _results = results[results.intraDay_dischargeDuration == intraDay_dt]

        # Select range of roundtrip efficiencies
        etaRange = np.flip(np.sort(np.unique(_results.intraDay_roundtripEfficiency)))
        etaRange = etaRange[etaRange >= MINIMUM_EFFICIENCY]

        for eta in etaRange:
            # Select results
            __results = _results[_results.intraDay_roundtripEfficiency == eta]
            ___results = __results[__results.intraDay_selfDischargeRate == 0]

            # Fit and plot a 2nd-order polynomial
            y = ___results.intraDay_volatility.values
            x = ___results.annualIntraDayProfit.values / power
            p = np.polyfit(y, x, deg=2)
            y = np.linspace(start=min(y), stop=max(y), num=resolution)
            x = np.polyval(p, y)
            if eta == etaRange[0]:
                ax.plot(x, y, lineStyle, color='k', label=f'{int(eta * 100)} %')
            else:
                ax.plot(x, y, lineStyle, color='k', label=f'{int(eta * 100)}')

            # Gather max and min
            maximumIntraDayYearlyProfit = max([maximumIntraDayYearlyProfit, max(x)])
            minimumIntraDayYearlyProfit = min([minimumIntraDayYearlyProfit, min(x)])
            maximumVolatility = max([maximumVolatility, max(y)])
            minimumVolatility = min([minimumVolatility, min(y)])

    # End-of-line legend annotation
    ya = maximumVolatility
    for line in ax.lines:
        label = str(line.get_label())

        x = line.get_xdata()
        y = line.get_ydata()
        xa = np.interp(ya, y, x)

        # Annotate the end of the line
        ax.annotate(text=label + '  ',
                    xy=(xa, ya),
                    textcoords="offset points",
                    xytext=(-10, 7),
                    va='center', ha='left',
                    fontsize=textFontSize - 1)

        # Remove label
        line.set_label('_nolegend_')

    # Create legends for various self-discharge rates
    rangeSDR = np.unique(results.intraDay_selfDischargeRate)
    for SDR, lineStyle in zip(rangeSDR[:-1], lineStyles[:len(rangeSDR)]):
        ax.plot([], [], lineStyle, color='k', label=f' {int(SDR * 100)} %/day')
    leg = ax.legend(frameon=False, loc='lower right', bbox_to_anchor=(0.99, 0.1), fontsize=textFontSize - 2)
    leg.set_title(r'Short-term self-discharge rate, $\lambda_\mathrm{st}$')
    leg.get_title().set_fontsize(textFontSize - 2)

    # Plot volatility-dependent energy-arbitrage profit for various (>0) self-discharge rates
    rangeSDR = rangeSDR[1:-1]
    for SDR, lineStyle in zip(rangeSDR, lineStyles[1:len(rangeSDR) + 1]):

        intraDay_dt_range = np.flip(np.sort(np.unique(results.intraDay_dischargeDuration)))

        for intraDay_dt in intraDay_dt_range:

            # Select results
            _results = results[results.intraDay_dischargeDuration == intraDay_dt]

            # Select range of roundtrip efficiencies
            etaRange = np.flip(np.sort(np.unique(_results.intraDay_roundtripEfficiency)))
            etaRange = etaRange[etaRange >= MINIMUM_EFFICIENCY]

            for eta in etaRange:
                # Select results
                __results = _results[_results.intraDay_roundtripEfficiency == eta]
                ___results = __results[__results.intraDay_selfDischargeRate == SDR]

                # Fit and plot a 2nd-order polynomial
                y = ___results.intraDay_volatility.values
                x = ___results.annualIntraDayProfit.values / power
                p = np.polyfit(y, x, deg=2)
                y = np.linspace(start=min(y), stop=max(y), num=resolution)
                x = np.polyval(p, y)
                ax.plot(x, y, lineStyle, color='k')

                # Gather max and min
                maximumIntraDayYearlyProfit = max([maximumIntraDayYearlyProfit, max(x)])
                minimumIntraDayYearlyProfit = min([minimumIntraDayYearlyProfit, min(x)])
                maximumVolatility = max([maximumVolatility, max(y)])
                minimumVolatility = min([minimumVolatility, min(y)])

    # Generate x-axis ticks
    y_min = minimumVolatility
    y_max = maximumVolatility
    wishTicks = list(np.arange(0, 200, 20))
    y_ticks = [y for y in wishTicks if y_min < y < y_max]
    y_ticks.append(wishTicks[wishTicks.index(y_ticks[-1]) + 1])
    y_ticks.append(wishTicks[wishTicks.index(y_ticks[0]) - 1])
    y_ticks.sort()

    # Log-scale x-axis
    ax.set_ylim([y_ticks[0], y_ticks[-1]])
    ax.set_yticks(y_ticks, y_ticks)
    ax.get_yaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.get_yaxis().set_minor_formatter(ticker.NullFormatter())

    # Generate y-axis ticks
    x_max = maximumIntraDayYearlyProfit
    wishTicks = list(np.arange(0, 1000, 100))
    x_ticks = [x for x in wishTicks if x < x_max]
    x_ticks.append(wishTicks[wishTicks.index(x_ticks[-1]) + 1])
    x_ticks.sort()

    # Log-scale y-axis
    ax.set_xlim([x_ticks[0], x_ticks[-1]])
    # Blank the tick label under point C (the intraday profit of the example), keeping the tick
    ax.set_xticks(x_ticks, [f'{x:g}' if x in (x_ticks[0], x_ticks[-1]) or abs(x - xp) >= 40 else ''
                            for x in x_ticks])
    ax.get_xaxis().set_minor_formatter(ticker.NullFormatter())

    # Apply font to ticklabels
    for tick in ax.get_xticklabels():
        tick.set_fontname("sans-serif")

    # Add example
    ax.plot([x_ticks[-1], xp], [yp, yp], '-g', linewidth=1.5)
    ax.plot([xp, xp], [y_ticks[0], yp], '-g', linewidth=1.5)
    ax.plot([xp, xp], [y_ticks[-1], yp], '--g', linewidth=1.5)
    ax.plot(x_ticks[-1], yp, 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='A',
                color='green',
                fontweight='bold',
                xy=(x_ticks[-1], yp),
                textcoords="offset points",
                xytext=(-5, 2),
                va='bottom', ha='right',
                fontsize=textFontSize - 1)

    ax.plot(xp, yp, 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='B',
                color='green',
                fontweight='bold',
                xy=(xp, yp),
                textcoords="offset points",
                xytext=(4, 2),
                va='bottom', ha='left',
                fontsize=textFontSize - 1)

    ax.plot(xp, y_ticks[-1], 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='C',
                color='green',
                fontweight='bold',
                xy=(xp, y_ticks[-1]),
                textcoords="offset points",
                xytext=(-2, 5),
                va='bottom', ha='left',
                fontsize=textFontSize - 1)

    definition = r'Short-term round-trip efficiency, $\eta_\mathrm{st}$'
    ax.text(x=.05, y=.97,
             s=definition,
             ha='left', va='top',
             transform=ax.transAxes,
             bbox=dict(facecolor='white', edgecolor='none', pad=3),
             fontsize=textFontSize - 1)

    # Sub-figure caption
    ax.text(x=.99, y=.01,
             s=r'(a) Short-term market',
             color='cornflowerblue',
             ha='right', va='bottom',
             fontweight='bold',
             transform=ax.transAxes)
    # Label axes
    ax.set_ylabel(r'Intraday electricity volatility, $\sigma_\mathrm{el}$ (\$/MWh)')
    ax.set_xlabel(r'Annual intraday profit (\$/kW/year)')
    ax.xaxis.set_label_position('top')
    ax.xaxis.tick_top()
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()

    """ 2. Annual expenditure VS annual intraday profit """

    # Create subplot
    ax = fig.add_subplot(2, 2, 4)

    # Initialise min-max values
    maximumAnnualProfit = - math.inf
    minimumAnnualProfit = math.inf

    range_powerSpecificChargingExpense = np.linspace(400, 0, 5)
    x = np.linspace(minimumIntraDayYearlyProfit, maximumIntraDayYearlyProfit, 100)
    for powerSpecificChargingExpense in range_powerSpecificChargingExpense:
        y = (x - powerSpecificChargingExpense)
        if powerSpecificChargingExpense == range_powerSpecificChargingExpense[-1]:
            ax.plot(x, y, 'k', label=rf'{int(powerSpecificChargingExpense)}')
        else:
            ax.plot(x, y, 'k', label=rf'{int(powerSpecificChargingExpense)}')

        # Gather max and min
        maximumAnnualProfit = max([maximumAnnualProfit, max(y)])
        minimumAnnualProfit = min([minimumAnnualProfit, min(y)])

    # End-of-line legend annotation
    xa = maximumIntraDayYearlyProfit

    for line in ax.lines:

        # Get position
        label = line.get_label()
        x = line.get_xdata()
        y = line.get_ydata()
        ya = np.interp(xa, x, y)

        if line == ax.lines[-1]:

            # Annotate the end of the line
            ax.text(xa - 60, ya - 30, r'$E_\mathrm{lt}\,=\,$' + str(label) + r' \$/kW/year',
                    va='center', ha='right',
                    rotation=45,
                    rotation_mode='anchor',
                    transform_rotates_text=True,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.5),
                    fontsize=textFontSize - 1)

        else:

            # Annotate the end of the line
            ax.text(xa - 20, ya - 20, ' ' + str(label) + '',
                    va='center', ha='left',
                    rotation=45,
                    rotation_mode='anchor',
                    transform_rotates_text=True,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.1),
                    fontsize=textFontSize - 1)

        # Remove label
        line.set_label('_nolegend_')

    # Add multiple levels
    range_powerSpecificChargingProfit = np.linspace(-400, 0, 21)
    x = np.linspace(minimumIntraDayYearlyProfit, maximumIntraDayYearlyProfit, 100)
    for powerSpecificChargingProfit in range_powerSpecificChargingProfit:
        y = x + powerSpecificChargingProfit
        ax.plot(x, y, '0.5', linewidth=0.2)

    # Generate x-axis ticks
    x_max = maximumIntraDayYearlyProfit
    wishTicks = list(np.arange(0, 1000, 100))
    x_ticks = [y for y in wishTicks if y < x_max]
    x_ticks.append(wishTicks[wishTicks.index(x_ticks[-1]) + 1])
    x_ticks.sort()

    # Log-scale y-axis
    ax.set_xlim([x_ticks[0], x_ticks[-1]])
    ax.set_xticks(x_ticks)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.get_xaxis().set_minor_formatter(ticker.NullFormatter())

    # Generate y-axis ticks
    minimumAnnualProfit = -200
    maximumAnnualProfit = 600
    y_ticks = PROFIT_TICKS
    ax.set_ylim([y_ticks[0], y_ticks[-1]])
    ax.set_yticks(y_ticks, y_ticks)
    ax.get_yaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.get_yaxis().set_minor_formatter(ticker.NullFormatter())

    # Add example
    yp = xp + interYearProfit
    ax.plot([x_ticks[0] - 200, xp], [yp, yp], '-g', linewidth=1.5, clip_on=False)
    ax.plot([xp, xp], [y_ticks[-1] + 200, yp], '-g', linewidth=1.5, clip_on=False)
    ax.plot([x_ticks[-1], xp], [yp, yp], '--g', linewidth=1.5, clip_on=False)

    ax.plot(xp, yp, 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='D',
                color='green',
                fontweight='bold',
                xy=(xp, yp),
                textcoords="offset points",
                xytext=(4, -4),
                bbox=dict(facecolor='white', edgecolor='none', pad=0.5),
                va='top', ha='left',
                fontsize=textFontSize - 1)

    ax.plot(x_ticks[-1], yp, 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='E',
                color='green',
                fontweight='bold',
                xy=(x_ticks[-1], yp),
                textcoords="offset points",
                xytext=(-4, -4),
                bbox=dict(facecolor='white', edgecolor='none', pad=0.5),
                va='top', ha='right',
                fontsize=textFontSize - 1)

    dft = r'Long-term expenses ' + '\n'
    dft = dft + r'$E_\mathrm{lt}\,=\,\Delta t_\mathrm{lt}$'
    dft = dft + r'$\left(\dfrac{C_\mathrm{el}}{\eta_\mathrm{lt}}+r_\mathrm{fuel}C_\mathrm{fuel}\right)\,+\,E_\mathrm{O&M}$'
    ax.text(x=.95, y=.05,
             s=dft,
             ha='right', va='bottom',
             transform=ax.transAxes,
             fontsize=textFontSize - 2)


    ax.text(x=.99, y=.99,
             s=r'(b) Long-term market',
             color='cornflowerblue',
             ha='right', va='top',
             fontweight='bold',
             transform=ax.transAxes)

    ax.set_ylabel(r'Total annual profit (\$/kW/year)')
    ax.set_xlabel(r'Annual intraday profit (\$/kW/year)')
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()

    """ 4. Annual expenditure VS annual intraday profit """

    # Create subplot
    ax = fig.add_subplot(2, 2, 3)
    maximumAnnualProfit_panelc = 640
    y = np.linspace(minimumAnnualProfit, maximumAnnualProfit_panelc, resolution)

    # Initialise min-max values
    maximumPEAC = -math.inf
    minimumPEAC = math.inf

    range_annualisedInvestmentCost = [200, 400, 600, 800, 1000]

    for annualisedInvestmentCost in range_annualisedInvestmentCost:
        x = annualisedInvestmentCost - y
        if annualisedInvestmentCost == range_annualisedInvestmentCost[-1]:
            ax.plot(x, y, 'k', label=rf'AIC = {int(annualisedInvestmentCost)} \$/kW/year')
        else:
            ax.plot(x, y, 'k', label=rf'{int(annualisedInvestmentCost)}')

        # Gather max and min
        maximumPEAC = max([maximumPEAC, max(x)])
        minimumPEAC = min([minimumPEAC, min(x)])

    # End-of-line legend annotation
    ya = maximumAnnualProfit_panelc

    for line in ax.lines:

        if line == ax.lines[-1]:

            label = line.get_label()

            x = line.get_xdata()
            y = line.get_ydata()
            xa = np.interp(ya, y, x)

            # Annotate the end of the line
            ax.text(xa - 20, ya + 20, str(label) + '  ',
                    va='center', ha='left',
                    rotation=-45,
                    rotation_mode='anchor',
                    transform_rotates_text=True,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.),
                    fontsize=textFontSize - 1)

        else:

            label = line.get_label()

            x = line.get_xdata()
            y = line.get_ydata()
            xa = np.interp(ya, y, x)

            # Annotate the end of the line
            ax.text(xa - 20, ya + 20, str(label) + '  ',
                    va='center', ha='left',
                    rotation=-45,
                    rotation_mode='anchor',
                    transform_rotates_text=True,
                    bbox=dict(facecolor='white', edgecolor='none', pad=0.),
                    fontsize=textFontSize - 1)

        # Remove label
        line.set_label('_nolegend_')

    # Add mid-level lines
    range_annualisedInvestmentCost = np.linspace(100, 1000, 19)
    for annualisedInvestmentCost in range_annualisedInvestmentCost:
        x = annualisedInvestmentCost - y
        ax.plot(x, y, '0.5', linewidth=0.2)

    # Add 0-th EAC line
    y0 = np.linspace(-2000, maximumAnnualProfit, resolution)
    ax.plot(np.zeros_like(y0), y0, '--k')

    definition = r'Annualised investment cost '

    ax.text(x=.99, y=.98,
             s=definition,
             fontsize=textFontSize - 2,
             ha='right', va='top',
             transform=ax.transAxes)

    definition = r'$\mathrm{AIC}=\mathrm{CRF}_\mathrm{p}\,c_\mathrm{p}\,+\,\mathrm{CRF}_\mathrm{s}\left(c_\mathrm{st}\,\Delta t_\mathrm{st}\,+\,c_\mathrm{lt}\,\Delta t_\mathrm{lt}\right)$' 
    
    ax.text(x=.99, y=.93,
             s=definition,
             fontsize=textFontSize - 2,
             ha='right', va='top',
             transform=ax.transAxes)

    # Generate x-axis ticks
    x_min = max(minimumPEAC, -500)
    x_max = min(maximumPEAC, 1000)
    wishTicks = [x * 500 for x in range(-20, 20)]
    x_ticks = [x for x in wishTicks if x_min < x < x_max]
    x_ticks.append(wishTicks[wishTicks.index(x_ticks[-1]) + 1])
    x_ticks.append(wishTicks[wishTicks.index(x_ticks[0]) - 1])
    x_ticks.sort()
    ax.set_xlim([x_ticks[0], x_ticks[-1]])
    exampleTick = round((AIC - yp) / 10) * 10
    x_ticks = [x for x in x_ticks if x in (x_ticks[0], x_ticks[-1]) or abs(x - exampleTick) >= 150]
    ax.set_xticks(x_ticks, x_ticks)
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(50))
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.get_xaxis().set_minor_formatter(ticker.NullFormatter())

    # Generate y-axis ticks (shared with panel (b))
    y_ticks = PROFIT_TICKS
    ax.set_ylim([y_ticks[0], y_ticks[-1]])
    ax.set_yticks(y_ticks, y_ticks)
    ax.get_yaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.get_yaxis().set_minor_formatter(ticker.NullFormatter())

    # Add example
    xp = AIC - yp
    ax.plot([xp, x_ticks[-1]], [yp, yp], '-g', linewidth=1.5)
    ax.plot([xp, xp], [y_ticks[0], yp], '-g', linewidth=1.5)
    ax.set_xticks(list(ax.get_xticks()) + [exampleTick])
    ax.get_xticklabels()[-1].set_color('green')
    ax.get_xticklabels()[-1].set_horizontalalignment('center')
    ax.get_xticklabels()[-1].set_rotation(0)

    ax.plot(xp, yp, 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='F',
                color='green',
                fontweight='bold',
                xy=(xp, yp),
                textcoords="offset points",
                xytext=(-4, 4),
                bbox=dict(facecolor='white', edgecolor='none', pad=0.5),
                va='bottom', ha='right',
                fontsize=textFontSize - 1)

    ax.plot(xp, y_ticks[0], 'og', zorder=2, clip_on=False, **POINT_STYLE)
    ax.annotate(text='G',
                color='green',
                fontweight='bold',
                xy=(xp, y_ticks[0]),
                textcoords="offset points",
                xytext=(4, 4),
                bbox=dict(facecolor='white', edgecolor='none', pad=0.5),
                va='bottom', ha='left',
                fontsize=textFontSize - 1)

    ax.text(x=.01, y=.99,
             s=r'(c) Business case',
             color='cornflowerblue',
             ha='left', va='top',
             fontweight='bold',
             transform=ax.transAxes)

    # Label axes
    ax.set_xlabel(r'Equivalent annual cost (EAC) (\$/kW/year)')
    ax.set_ylabel(r'Total annual profit (\$/kW/year)')

    return fig


if __name__ == '__main__':
    results = pd.read_csv(EXPLORATION_RESULTS)
    SimpleNomogram(results, POWER, DEFAULT_EXAMPLE).savefig('nomogram.png', dpi=300)
    print('Saved nomogram.png')
