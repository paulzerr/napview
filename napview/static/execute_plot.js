import { createChart, resetChart } from './d3_chart.js';

const PALETTES = {
    "okabe-ito": {
        label: "Okabe–Ito (color-blind safe)",
        colors: ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442"]
    },
    "tol-bright": {
        label: "Tol Bright",
        colors: ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
    },
    "colorbrewer-set2": {
        label: "ColorBrewer Set2",
        colors: ["#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854", "#FFD92F", "#E5C494", "#B3B3B3"]
    },
    "colorbrewer-set3": {
        label: "ColorBrewer Set3",
        colors: ["#8DD3C7", "#FFFFB3", "#BEBADA", "#FB8072", "#80B1D3", "#FDB462", "#B3DE69", "#FCCDE5", "#D9D9D9", "#BC80BD", "#CCEBC5", "#FFED6F"]
    },
    "tableau-10": {
        label: "Tableau 10",
        colors: ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"]
    }
};
const DEFAULT_PALETTE = "okabe-ito";
const CUSTOM_PALETTE = "custom";
const DEFAULT_THEME = {
    background: "#1e1e1e",
    grid: "#cfcfcf",
    axisText: "#ffffff",
    legendText: "#ffffff"
};
const ZOOM_MIN_MINUTES = 2;
const ZOOM_MAX_MINUTES = 120;
const WAITING_PLACEHOLDER_MESSAGE = "Waiting for data...\nThis may take up to one minute.\nSleep stage estimates stabilize after about 5 minutes.";
let lastAnalyzerStatusMessage = WAITING_PLACEHOLDER_MESSAGE;

function paletteSlice(name, count) {
    const palette = PALETTES[name] || PALETTES[DEFAULT_PALETTE];
    return palette.colors.slice(0, count);
}

function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
}

function setChartPlaceholderMessage(message) {
    document.querySelectorAll(".chart-placeholder").forEach((placeholder) => {
        placeholder.innerText = message;
    });
}

async function refreshAnalyzerStatusMessage() {
    try {
        const response = await fetch('/analyzer_status');
        if (!response.ok) {
            return;
        }
        const status = await response.json();
        const message = status.model_bootstrap_error || WAITING_PLACEHOLDER_MESSAGE;
        if (message === lastAnalyzerStatusMessage) {
            return;
        }
        lastAnalyzerStatusMessage = message;
        setChartPlaceholderMessage(message);
    } catch {
        return;
    }
}

class DataPlotter {
    constructor(chartId, config) {
        this.chartId = chartId;
        this.config = config;
        this.chart = null;
        this.dataSets = null;
    }

    containerReady() {
        const el = document.getElementById(this.chartId);
        return el && el.clientWidth > 0 && el.clientHeight > 0;
    }

    reset() {
        resetChart(this.chartId);
        this.chart = null;
    }

    async plotChart() {

            const response = await fetch(this.config.endpoint);
            const data = await response.json();

            this.dataSets = [];
            for (const fieldName of this.config.fields) {
                const fieldData = data[fieldName].map(entry => ({
                    x: entry.x * 1000,
                    y: entry.y
                }));
                this.dataSets.push(fieldData);
            }

            if (!this.containerReady() || !this.hasEnoughData()) {
                return;
            }

            if (!this.chart) {
                this.chart = createChart(
                    this.chartId,
                    this.dataSets,
                    this.config.colors,
                    this.config.labels,
                    this.config.theme,
                    this.config.onZoomChange
                );
                if (typeof this.config.onZoomChange === 'function') {
                    const domain = this.chart.xScale.domain();
                    this.config.onZoomChange(domain[1] - domain[0]);
                }
            } else {
                this.chart.update(this.dataSets);
            }
    }

    hasEnoughData() {
        return this.dataSets && this.dataSets.every(dataSet => dataSet.length >= 2);
    }

    startPlotting(interval = 500) {

        setInterval(() => {
            this.plotChart();
        }, interval);


    }
}

// Configure the charts
const chart1Config = {
    endpoint: '/data1',
    fields: ['n1', 'n2', 'n3', 'rem', 'w'],
    labels: ["probability", "time", "N1", "N2", "N3", "REM", "W"],
    colors: paletteSlice(DEFAULT_PALETTE, 5),
    theme: { ...DEFAULT_THEME },
    onZoomChange: null
};

const chart2Config = {
    endpoint: '/data2',
    fields: ['alpha_power', 'beta_power', 'theta_power', 'delta_power'],
    labels: ["power", "time", 'alpha', 'beta', 'theta', 'delta'],
    colors: paletteSlice(DEFAULT_PALETTE, 4),
    theme: { ...DEFAULT_THEME }

};

const chart3Config = {
    endpoint: '/data2',
    fields: ['alpha_power', 'beta_power', 'theta_power', 'delta_power'],
    labels: ["power", "time", 'alpha', 'beta', 'theta', 'delta'],
    colors: paletteSlice(DEFAULT_PALETTE, 4),
    theme: { ...DEFAULT_THEME }

};

const chart4Config = {
    endpoint: '/data1',
    fields: ['n1', 'n2', 'n3', 'rem', 'w'],
    labels: ["probability", "time", "N1", "N2", "N3", "REM", "W"],
    colors: paletteSlice(DEFAULT_PALETTE, 5),
    theme: { ...DEFAULT_THEME }
};

// Create instances of the DataPlotter class for each chart
const chart1Plotter = new DataPlotter("d3Plot1", chart1Config);
const chart2Plotter = new DataPlotter("d3Plot2", chart2Config);
// const chart3Plotter = new DataPlotter("d3Plot3", chart3Config);
// const chart4Plotter = new DataPlotter("d3Plot4", chart4Config);

function defaultColorsForPalette(name) {
    return {
        chart1: paletteSlice(name, chart1Config.fields.length),
        chart2: paletteSlice(name, chart2Config.fields.length)
    };
}

async function loadColorConfig() {
    try {
        const response = await fetch('/load_config');
        const config = await response.json();
        let palette = typeof config.chart_palette === 'string' ? config.chart_palette : DEFAULT_PALETTE;
        if (!PALETTES[palette] && palette !== CUSTOM_PALETTE) {
            palette = DEFAULT_PALETTE;
        }
        const storedTheme = config.chart_theme && typeof config.chart_theme === 'object' ? config.chart_theme : {};
        const defaults = defaultColorsForPalette(DEFAULT_PALETTE);
        const stored = config.chart_colors && typeof config.chart_colors === 'object' ? config.chart_colors : {};
        const customColors = {
            chart1: Array.isArray(stored.chart1) ? stored.chart1 : defaults.chart1,
            chart2: Array.isArray(stored.chart2) ? stored.chart2 : defaults.chart2
        };
        const activeColors = palette === CUSTOM_PALETTE ? customColors : defaultColorsForPalette(palette);
        return {
            palette,
            colors: {
                chart1: activeColors.chart1,
                chart2: activeColors.chart2
            },
            theme: {
                background: typeof storedTheme.background === 'string' ? storedTheme.background : DEFAULT_THEME.background,
                grid: typeof storedTheme.grid === 'string' ? storedTheme.grid : DEFAULT_THEME.grid,
                axisText: typeof storedTheme.axisText === 'string' ? storedTheme.axisText : DEFAULT_THEME.axisText,
                legendText: typeof storedTheme.legendText === 'string' ? storedTheme.legendText : DEFAULT_THEME.legendText
            },
            customColors
        };
    } catch (error) {
        console.error('Error loading color config:', error);
        return {
            palette: DEFAULT_PALETTE,
            colors: defaultColorsForPalette(DEFAULT_PALETTE),
            theme: { ...DEFAULT_THEME },
            customColors: defaultColorsForPalette(DEFAULT_PALETTE)
        };
    }
}

async function saveColorConfig(configUpdates) {
    const response = await fetch('/update_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configUpdates)
    });
    const result = await response.json();
    return result && result.status === 'Configuration updated';
}

function buildColorList(container, labels, colors, onInput) {
    container.innerHTML = '';
    labels.forEach((label, index) => {
        const row = document.createElement('div');
        row.className = 'color-row';
        const name = document.createElement('span');
        name.textContent = label;
        const input = document.createElement('input');
        input.type = 'color';
        input.value = colors[index];
        input.addEventListener('input', onInput);
        row.appendChild(name);
        row.appendChild(input);
        container.appendChild(row);
    });
}

function setupColorDialog(initialPalette, initialColors, initialCustomColors) {
    const dialog = document.getElementById('colorDialog');
    const openButton = document.getElementById('colorOptionsButton');
    const cancelButton = document.getElementById('closeColors');
    const applyButton = document.getElementById('saveColors');
    const paletteSelect = document.getElementById('paletteSelect');
    const chart1List = document.getElementById('chart1ColorList');
    const chart2List = document.getElementById('chart2ColorList');
    let currentState = {
        palette: initialPalette,
        colors: initialColors,
        customColors: { ...initialCustomColors }
    };
    let draftState = null;

    function refreshPaletteOptions(selectedValue) {
        paletteSelect.innerHTML = '';
        Object.entries(PALETTES).forEach(([key, palette]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = palette.label;
            paletteSelect.appendChild(option);
        });
        const customOption = document.createElement('option');
        customOption.value = CUSTOM_PALETTE;
        customOption.textContent = 'Custom';
        paletteSelect.appendChild(customOption);
        paletteSelect.value = selectedValue;
    }

    function readColors() {
        return {
            chart1: Array.from(chart1List.querySelectorAll('input[type="color"]')).map(input => input.value),
            chart2: Array.from(chart2List.querySelectorAll('input[type="color"]')).map(input => input.value)
        };
    }

    function applyColors(colors) {
        buildColorList(chart1List, chart1Config.labels.slice(2), colors.chart1, handleColorInput);
        buildColorList(chart2List, chart2Config.labels.slice(2), colors.chart2, handleColorInput);
    }

    function ensureValidPalette(value) {
        if (value === CUSTOM_PALETTE || PALETTES[value]) {
            return value;
        }
        return DEFAULT_PALETTE;
    }

    function renderFromState(state) {
        const palette = ensureValidPalette(state.palette);
        const colors = palette === CUSTOM_PALETTE ? state.customColors : defaultColorsForPalette(palette);
        refreshPaletteOptions(palette);
        applyColors(colors);
    }

    function handleColorInput() {
        if (!draftState) {
            return;
        }
        const selected = paletteSelect.value;
        if (selected !== CUSTOM_PALETTE) {
            draftState.customColors = readColors();
            draftState.palette = CUSTOM_PALETTE;
            paletteSelect.value = CUSTOM_PALETTE;
        } else {
            draftState.customColors = readColors();
        }
    }

    paletteSelect.addEventListener('change', () => {
        if (!draftState) {
            return;
        }
        const selected = ensureValidPalette(paletteSelect.value);
        draftState.palette = selected;
        if (selected === CUSTOM_PALETTE) {
            applyColors(draftState.customColors);
        } else {
            applyColors(defaultColorsForPalette(selected));
        }
    });

    openButton.addEventListener('click', () => {
        draftState = {
            palette: currentState.palette,
            colors: currentState.colors,
            customColors: { ...currentState.customColors }
        };
        renderFromState(draftState);
        dialog.style.display = 'flex';
    });

    cancelButton.addEventListener('click', () => {
        dialog.style.display = 'none';
    });

    applyButton.addEventListener('click', async () => {
        if (!draftState) {
            return;
        }
        const paletteToSave = ensureValidPalette(paletteSelect.value);
        let appliedColors = null;
        const updates = {
            chart_palette: paletteToSave
        };
        if (paletteToSave === CUSTOM_PALETTE) {
            draftState.customColors = readColors();
            appliedColors = draftState.customColors;
            updates.chart_colors = appliedColors;
        } else {
            appliedColors = defaultColorsForPalette(paletteToSave);
        }

        const saved = await saveColorConfig(updates);
        if (saved) {
            chart1Config.colors = appliedColors.chart1;
            chart2Config.colors = appliedColors.chart2;
            chart1Plotter.reset();
            chart2Plotter.reset();
            currentState = {
                palette: paletteToSave,
                colors: appliedColors,
                customColors: { ...draftState.customColors }
            };
            dialog.style.display = 'none';
        }
    });

    renderFromState(currentState);
}

async function initCharts() {
    const config = await loadColorConfig();
    chart1Config.colors = config.colors.chart1;
    chart2Config.colors = config.colors.chart2;
    chart1Config.theme = { ...config.theme };
    chart2Config.theme = { ...config.theme };
    const zoomSlider = document.getElementById('zoomSlider');
    if (zoomSlider) {
        zoomSlider.min = String(ZOOM_MIN_MINUTES);
        zoomSlider.max = String(ZOOM_MAX_MINUTES);
        zoomSlider.step = "1";
        chart1Config.onZoomChange = (windowMs) => {
            if (!Number.isFinite(windowMs) || windowMs <= 0) {
                return;
            }
            const minutes = clamp(windowMs / 60000, ZOOM_MIN_MINUTES, ZOOM_MAX_MINUTES);
            zoomSlider.value = minutes.toFixed(0);
        };
        zoomSlider.addEventListener('input', () => {
            if (!chart1Plotter.chart || !chart1Plotter.chart.zoomBehavior) {
                return;
            }
            const domain = chart1Plotter.chart.xScale.domain();
            const baseSpanMs = domain[1] - domain[0];
            if (!Number.isFinite(baseSpanMs) || baseSpanMs <= 0) {
                return;
            }
            const minutes = clamp(parseFloat(zoomSlider.value), ZOOM_MIN_MINUTES, ZOOM_MAX_MINUTES);
            const zoomLevel = baseSpanMs / (minutes * 60000);
            chart1Plotter.chart.zoomBehavior.scaleTo(chart1Plotter.chart.zoomTarget, zoomLevel);
        });
    }
    setupColorDialog(config.palette, config.colors, config.customColors);
    await refreshAnalyzerStatusMessage();
    setInterval(() => {
        refreshAnalyzerStatusMessage();
    }, 2000);
    chart1Plotter.startPlotting();
    chart2Plotter.startPlotting();
}

initCharts();
// chart3Plotter.startPlotting();
// chart4Plotter.startPlotting();

let resizeTimer = null;
window.addEventListener("resize", () => {
    if (resizeTimer) {
        clearTimeout(resizeTimer);
    }
    resizeTimer = setTimeout(() => {
        chart1Plotter.reset();
        chart2Plotter.reset();
    }, 150);
});
