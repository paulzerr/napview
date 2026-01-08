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
const CUSTOM_LIMIT = 3;
const CUSTOM_PREFIX = "Custom ";
const DEFAULT_THEME = {
    background: "#1e1e1e",
    grid: "#cfcfcf",
    axisText: "#ffffff",
    legendText: "#ffffff"
};

function paletteSlice(name, count) {
    const palette = PALETTES[name] || PALETTES[DEFAULT_PALETTE];
    return palette.colors.slice(0, count);
}

function normalizeCustomPalettes(raw) {
    const list = Array.isArray(raw) ? raw : [];
    const normalized = [];
    for (const entry of list) {
        if (!entry || typeof entry !== 'object') {
            continue;
        }
        const name = typeof entry.name === 'string' ? entry.name : `${CUSTOM_PREFIX}${normalized.length + 1}`;
        const colors = entry.colors && typeof entry.colors === 'object' ? entry.colors : {};
        const theme = entry.theme && typeof entry.theme === 'object' ? entry.theme : {};
        normalized.push({
            name,
            colors: {
                chart1: Array.isArray(colors.chart1) ? colors.chart1 : [],
                chart2: Array.isArray(colors.chart2) ? colors.chart2 : []
            },
            theme: {
                background: typeof theme.background === 'string' ? theme.background : DEFAULT_THEME.background,
                grid: typeof theme.grid === 'string' ? theme.grid : DEFAULT_THEME.grid,
                axisText: typeof theme.axisText === 'string' ? theme.axisText : DEFAULT_THEME.axisText,
                legendText: typeof theme.legendText === 'string' ? theme.legendText : DEFAULT_THEME.legendText
            }
        });
        if (normalized.length >= CUSTOM_LIMIT) {
            break;
        }
    }
    return normalized;
}

function findCustomPalette(palettes, name) {
    return palettes.find(palette => palette.name === name);
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
                this.chart = createChart(this.chartId, this.dataSets, this.config.colors, this.config.labels, this.config.theme);
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
    theme: { ...DEFAULT_THEME }
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
        const storedTheme = config.chart_theme && typeof config.chart_theme === 'object' ? config.chart_theme : {};
        const defaults = defaultColorsForPalette(palette);
        const stored = config.chart_colors && typeof config.chart_colors === 'object' ? config.chart_colors : {};
        let customPalettes = normalizeCustomPalettes(config.chart_custom_palettes);
        if (palette === 'custom' && customPalettes.length === 0) {
            const fallbackColors = {
                chart1: Array.isArray(stored.chart1) ? stored.chart1 : defaults.chart1,
                chart2: Array.isArray(stored.chart2) ? stored.chart2 : defaults.chart2
            };
            const fallbackTheme = {
                background: typeof storedTheme.background === 'string' ? storedTheme.background : DEFAULT_THEME.background,
                grid: typeof storedTheme.grid === 'string' ? storedTheme.grid : DEFAULT_THEME.grid,
                axisText: typeof storedTheme.axisText === 'string' ? storedTheme.axisText : DEFAULT_THEME.axisText,
                legendText: typeof storedTheme.legendText === 'string' ? storedTheme.legendText : DEFAULT_THEME.legendText
            };
            const customName = `${CUSTOM_PREFIX}1`;
            customPalettes = [{
                name: customName,
                colors: fallbackColors,
                theme: fallbackTheme
            }];
            palette = customName;
        }
        const selectedCustom = findCustomPalette(customPalettes, palette);
        return {
            palette,
            colors: {
                chart1: selectedCustom ? selectedCustom.colors.chart1 : defaults.chart1,
                chart2: selectedCustom ? selectedCustom.colors.chart2 : defaults.chart2
            },
            theme: {
                background: selectedCustom ? selectedCustom.theme.background : (typeof storedTheme.background === 'string' ? storedTheme.background : DEFAULT_THEME.background),
                grid: selectedCustom ? selectedCustom.theme.grid : (typeof storedTheme.grid === 'string' ? storedTheme.grid : DEFAULT_THEME.grid),
                axisText: selectedCustom ? selectedCustom.theme.axisText : (typeof storedTheme.axisText === 'string' ? storedTheme.axisText : DEFAULT_THEME.axisText),
                legendText: selectedCustom ? selectedCustom.theme.legendText : (typeof storedTheme.legendText === 'string' ? storedTheme.legendText : DEFAULT_THEME.legendText)
            },
            customPalettes
        };
    } catch (error) {
        console.error('Error loading color config:', error);
        return {
            palette: DEFAULT_PALETTE,
            colors: defaultColorsForPalette(DEFAULT_PALETTE),
            theme: { ...DEFAULT_THEME },
            customPalettes: []
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

function setupColorDialog(initialPalette, initialColors, initialTheme, initialCustomPalettes) {
    const dialog = document.getElementById('colorDialog');
    const openButton = document.getElementById('colorOptionsButton');
    const closeButton = document.getElementById('closeColors');
    const saveButton = document.getElementById('saveColors');
    const resetButton = document.getElementById('resetColors');
    const duplicateButton = document.getElementById('duplicateColors');
    const paletteSelect = document.getElementById('paletteSelect');
    const chart1List = document.getElementById('chart1ColorList');
    const chart2List = document.getElementById('chart2ColorList');
    const plotBackground = document.getElementById('plotBackground');
    const plotGrid = document.getElementById('plotGrid');
    const plotAxisText = document.getElementById('plotAxisText');
    const plotLegendText = document.getElementById('plotLegendText');
    let customPalettes = initialCustomPalettes.slice();
    let baseTheme = { ...initialTheme };

    function refreshPaletteOptions(selectedValue) {
        paletteSelect.innerHTML = '';
        Object.entries(PALETTES).forEach(([key, palette]) => {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = palette.label;
            paletteSelect.appendChild(option);
        });
        customPalettes.forEach((customPalette) => {
            const option = document.createElement('option');
            option.value = customPalette.name;
            option.textContent = customPalette.name;
            paletteSelect.appendChild(option);
        });
        if (selectedValue) {
            paletteSelect.value = selectedValue;
        }
    }

    const markCustom = () => {
        const selected = paletteSelect.value;
        const isCustom = !!findCustomPalette(customPalettes, selected);
        if (!isCustom) {
            return;
        }
    };

    const applyColors = (colors) => {
        buildColorList(chart1List, chart1Config.labels.slice(2), colors.chart1, markCustom);
        buildColorList(chart2List, chart2Config.labels.slice(2), colors.chart2, markCustom);
    };

    function applyTheme(theme) {
        plotBackground.value = theme.background;
        plotGrid.value = theme.grid;
        plotAxisText.value = theme.axisText;
        plotLegendText.value = theme.legendText;
    }

    function isCustomSelection() {
        return !!findCustomPalette(customPalettes, paletteSelect.value);
    }

    function updateEditability() {
        const editable = isCustomSelection();
        chart1List.querySelectorAll('input[type="color"]').forEach(input => {
            input.disabled = !editable;
        });
        chart2List.querySelectorAll('input[type="color"]').forEach(input => {
            input.disabled = !editable;
        });
        plotBackground.disabled = !editable;
        plotGrid.disabled = !editable;
        plotAxisText.disabled = !editable;
        plotLegendText.disabled = !editable;
        duplicateButton.disabled = customPalettes.length >= CUSTOM_LIMIT;
    }

    paletteSelect.addEventListener('change', () => {
        const selected = paletteSelect.value;
        const custom = findCustomPalette(customPalettes, selected);
        if (custom) {
            applyColors(custom.colors);
            applyTheme(custom.theme);
        } else {
            applyColors(defaultColorsForPalette(selected));
            applyTheme(baseTheme);
        }
        updateEditability();
    });

    refreshPaletteOptions(initialPalette);
    paletteSelect.value = PALETTES[initialPalette] || findCustomPalette(customPalettes, initialPalette) ? initialPalette : DEFAULT_PALETTE;
    applyColors(initialColors);
    applyTheme(initialTheme);
    updateEditability();

    openButton.addEventListener('click', () => {
        dialog.style.display = 'flex';
    });

    closeButton.addEventListener('click', () => {
        dialog.style.display = 'none';
    });

    resetButton.addEventListener('click', () => {
        paletteSelect.value = DEFAULT_PALETTE;
        applyColors(defaultColorsForPalette(DEFAULT_PALETTE));
        applyTheme(DEFAULT_THEME);
        updateEditability();
    });

    duplicateButton.addEventListener('click', () => {
        if (customPalettes.length >= CUSTOM_LIMIT) {
            return;
        }
        const usedNames = new Set(customPalettes.map(palette => palette.name));
        let nextName = "";
        for (let i = 1; i <= CUSTOM_LIMIT; i += 1) {
            const name = `${CUSTOM_PREFIX}${i}`;
            if (!usedNames.has(name)) {
                nextName = name;
                break;
            }
        }
        if (!nextName) {
            return;
        }
        const chart1Colors = Array.from(chart1List.querySelectorAll('input[type="color"]')).map(input => input.value);
        const chart2Colors = Array.from(chart2List.querySelectorAll('input[type="color"]')).map(input => input.value);
        const theme = {
            background: plotBackground.value,
            grid: plotGrid.value,
            axisText: plotAxisText.value,
            legendText: plotLegendText.value
        };
        customPalettes.push({
            name: nextName,
            colors: { chart1: chart1Colors, chart2: chart2Colors },
            theme
        });
        refreshPaletteOptions(nextName);
        paletteSelect.value = nextName;
        updateEditability();
    });

    saveButton.addEventListener('click', async () => {
        const paletteToSave = paletteSelect.value;
        const isCustom = isCustomSelection();
        const themeToSave = {
            background: plotBackground.value,
            grid: plotGrid.value,
            axisText: plotAxisText.value,
            legendText: plotLegendText.value
        };
        let chart1Colors = [];
        let chart2Colors = [];
        if (isCustom) {
            chart1Colors = Array.from(chart1List.querySelectorAll('input[type="color"]')).map(input => input.value);
            chart2Colors = Array.from(chart2List.querySelectorAll('input[type="color"]')).map(input => input.value);
            const selectedCustom = findCustomPalette(customPalettes, paletteToSave);
            if (selectedCustom) {
                selectedCustom.colors = { chart1: chart1Colors, chart2: chart2Colors };
                selectedCustom.theme = themeToSave;
            }
        } else {
            chart1Colors = defaultColorsForPalette(paletteToSave).chart1;
            chart2Colors = defaultColorsForPalette(paletteToSave).chart2;
        }

        const saved = await saveColorConfig({
            chart_palette: paletteToSave,
            chart_colors: {
                chart1: chart1Colors,
                chart2: chart2Colors
            },
            chart_theme: {
                background: themeToSave.background,
                grid: themeToSave.grid,
                axisText: themeToSave.axisText,
                legendText: themeToSave.legendText
            },
            chart_custom_palettes: customPalettes
        });

        if (saved) {
            chart1Config.colors = chart1Colors;
            chart2Config.colors = chart2Colors;
            chart1Config.theme = {
                background: themeToSave.background,
                grid: themeToSave.grid,
                axisText: themeToSave.axisText,
                legendText: themeToSave.legendText
            };
            chart2Config.theme = { ...chart1Config.theme };
            baseTheme = { ...chart1Config.theme };
            chart1Plotter.reset();
            chart2Plotter.reset();
            dialog.style.display = 'none';
        }
    });
}

async function initCharts() {
    const config = await loadColorConfig();
    chart1Config.colors = config.colors.chart1;
    chart2Config.colors = config.colors.chart2;
    chart1Config.theme = { ...config.theme };
    chart2Config.theme = { ...config.theme };
    setupColorDialog(config.palette, config.colors, config.theme, config.customPalettes);
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
