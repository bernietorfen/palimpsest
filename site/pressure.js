const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const NS = 'http://www.w3.org/2000/svg';
const BASE = '/assets/generated/';
const PAPER = '#ede8da', INK = '#293c3e', OCHRE = '#8f602e';
const COLORS = ['#69776b', '#436b75', '#ac7137', '#293e42'];
const canvas = $('#pressure-map');
const context = canvas.getContext('2d');
const status = $('#pressure-status');
let record, glyphs, mapping;
let level = 2, selected = 0, reader = 'nearest';
let resizeFrame = 0;

function element(name, attributes = {}) {
  const node = document.createElementNS(NS, name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
  return node;
}

function glyphValues(index) {
  return Array.from({ length: 4 }, (_, ring) => Array.from({ length: 12 }, (_, voice) =>
    glyphs.getInt16((index * 48 + ring * 12 + voice) * 2, true) / 32767));
}

function ringPath(values, ring) {
  const points = values.map((value, i) => {
    const angle = i * Math.PI / 6, radius = 40 + ring * 24 + 18 * value;
    return [140 + radius * Math.sin(angle), 140 - radius * Math.cos(angle)];
  });
  let d = `M${points[0].map((n) => n.toFixed(3)).join(',')}`;
  for (let i = 0; i < 12; i++) {
    const a = points[(i + 11) % 12], b = points[i], c = points[(i + 1) % 12], e = points[(i + 2) % 12];
    d += ` C${(b[0] + (c[0] - a[0]) / 6).toFixed(3)},${(b[1] + (c[1] - a[1]) / 6).toFixed(3)}`;
    d += ` ${(c[0] - (e[0] - b[0]) / 6).toFixed(3)},${(c[1] - (e[1] - b[1]) / 6).toFixed(3)}`;
    d += ` ${c[0].toFixed(3)},${c[1].toFixed(3)}`;
  }
  return d + ' Z';
}

function drawGlyph(svg, index) {
  const group = element('g');
  for (let i = 0; i < 12; i++) {
    const angle = i * Math.PI / 6;
    group.append(element('line', { x1: 140 + 22 * Math.sin(angle), y1: 140 - 22 * Math.cos(angle),
      x2: 140 + 132 * Math.sin(angle), y2: 140 - 132 * Math.cos(angle), stroke: '#c7c2b4', 'stroke-width': .45 }));
  }
  glyphValues(index).forEach((values, ring) => group.append(element('path', {
    d: ringPath(values, ring), fill: 'none', stroke: COLORS[ring], 'stroke-width': 1.05,
  })));
  group.append(element('circle', { cx: 140, cy: 140, r: 1.2, fill: OCHRE }));
  svg.replaceChildren(group);
}

function predicted(point) { return point[reader === 'nearest' ? 2 : 3]; }
function spaced(label) { return label.split('').join(' · '); }
function coordinates(x, y) { return [mapping.x + x * mapping.scale, mapping.y - y * mapping.scale]; }

function drawMap() {
  if (!record || !context) return;
  const bounds = canvas.getBoundingClientRect();
  const width = bounds.width, height = bounds.height;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.fillStyle = PAPER; context.fillRect(0, 0, width, height);
  const [xmin, xmax, ymin, ymax] = record.extent;
  const scale = Math.min((width - 38) / (xmax - xmin), (height - 48) / (ymax - ymin));
  mapping = { scale, x: width / 2 - (xmin + xmax) * scale / 2, y: height / 2 + (ymin + ymax) * scale / 2 - 7 };
  const current = record.levels[level];
  context.lineWidth = .5; context.strokeStyle = '#c7c2b45c';
  context.beginPath();
  current.points.forEach((point, i) => {
    const from = coordinates(...record.canonical_positions[Math.floor(i / 8)]), to = coordinates(...point);
    context.moveTo(...from); context.lineTo(...to);
  });
  context.stroke();
  for (let correct = 0; correct <= 1; correct++) {
    context.fillStyle = correct ? INK : OCHRE;
    context.globalAlpha = correct ? .60 : .85;
    context.beginPath();
    current.points.forEach((point, i) => {
      if (Number(predicted(point) === Math.floor(i / 8)) !== correct) return;
      const [x, y] = coordinates(...point), radius = correct ? 1.55 : 1.95;
      context.moveTo(x + radius, y); context.arc(x, y, radius, 0, Math.PI * 2);
    });
    context.fill();
  }
  context.globalAlpha = 1; context.fillStyle = PAPER; context.strokeStyle = '#6e7d74'; context.lineWidth = .65;
  context.beginPath();
  record.canonical_positions.forEach((point) => {
    const [x, y] = coordinates(...point);
    context.moveTo(x + 2.5, y); context.arc(x, y, 2.5, 0, Math.PI * 2);
  });
  context.fill(); context.stroke();
  const point = current.points[selected], truth = Math.floor(selected / 8), choice = predicted(point);
  const position = coordinates(...point), origin = coordinates(...record.canonical_positions[truth]);
  context.strokeStyle = INK; context.lineWidth = 1;
  context.beginPath(); context.moveTo(...origin); context.lineTo(...position); context.stroke();
  context.setLineDash([3, 3]);
  context.strokeStyle = choice === truth ? INK : OCHRE;
  context.beginPath(); context.moveTo(...position); context.lineTo(...coordinates(...record.canonical_positions[choice])); context.stroke();
  context.setLineDash([]);
  context.fillStyle = choice === truth ? INK : OCHRE;
  context.beginPath(); context.arc(...position, 4, 0, Math.PI * 2); context.fill();
  context.beginPath(); context.arc(...position, 8, 0, Math.PI * 2); context.stroke();
  context.font = '10px sans-serif'; context.fillStyle = '#5f6860'; context.textAlign = 'left';
  context.fillText('Two components of the answer', 7, height - 7);
  context.textAlign = 'right'; context.fillText('65.5% of ideal variation', width - 7, height - 7);
  canvas.dataset.case = String(selected); canvas.dataset.reader = reader;
}

function caseHash() {
  return `#${record.levels[level].percent}-${record.histories[Math.floor(selected / 8)]}-${selected % 8 + 1}-${reader}`;
}

function readHash() {
  const match = location.hash.match(/^#(1|3|10)-([ABCDE]{5})-([1-8])-(nearest|corrected)$/);
  if (!match || !record.histories.includes(match[2])) return false;
  level = record.levels.findIndex((item) => item.percent === Number(match[1]));
  selected = record.histories.indexOf(match[2]) * 8 + Number(match[3]) - 1;
  reader = match[4];
  return true;
}

function render(announce = true, updateHash = true) {
  const current = record.levels[level], point = current.points[selected], truth = Math.floor(selected / 8);
  const choice = predicted(point), correct = choice === truth;
  const label = record.histories[truth], chosen = record.histories[choice];
  $$('button[data-level]').forEach((button) => button.setAttribute('aria-pressed', String(Number(button.dataset.level) === level)));
  $$('button[data-reader]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.reader === reader)));
  $$('button[data-trial]').forEach((button) => button.setAttribute('aria-pressed', String(Number(button.dataset.trial) === selected % 8)));
  $('#written-order').value = label;
  $('#identified-count').textContent = `${current[reader + '_correct']} / 960`;
  $('#written-label').textContent = spaced(label); $('#chosen-label').textContent = spaced(chosen);
  const result = $('#case-result');
  result.textContent = correct ? 'The written history is recognized.' : `The reader chooses ${spaced(chosen)}.`;
  result.dataset.correct = String(correct);
  drawGlyph($('#measured-glyph'), current.glyph_offset + selected);
  drawGlyph($('#chosen-glyph'), choice);
  $('#measured-glyph').setAttribute('aria-label', `Measured reply of ${spaced(label)}, pressure realization ${selected % 8 + 1}`);
  $('#chosen-glyph').setAttribute('aria-label', `Ideal reply of the chosen history ${spaced(chosen)}`);
  $('#pressure-factors').replaceChildren(...current.pressure_factors[selected].map((factor, position) => {
    const item = document.createElement('li'), letter = document.createElement('strong'), value = document.createElement('span');
    letter.textContent = label[position];
    const difference = (factor - 1) * 100;
    value.textContent = `${difference >= 0 ? '+' : '−'}${Math.abs(difference).toFixed(2)}%`;
    item.append(letter, value); return item;
  }));
  $('#case-distances').textContent = `Distance to its own ideal answer: ${point[4].toFixed(4)} Hz RMS. After allowing pressure: ${point[5].toFixed(4)} Hz RMS.`;
  const misses = current.points.some((item, index) => predicted(item) !== Math.floor(index / 8));
  $('#next-misread').disabled = !misses;
  $('#next-misread').textContent = misses ? 'Find a misread history ↗' : 'All 960 histories identified';
  $('#reader-explanation').textContent = reader === 'nearest'
    ? 'This reader asks: which ideal history has the closest complete answer? Uneven pressure can move a reply toward a different history.'
    : 'This reader allows each history five ways to bend its answer as pressure changes. It compares what remains after that adjustment.';
  const hash = caseHash(); $('#share-pressure').href = hash;
  if (updateHash && location.hash !== hash) history.replaceState(null, '', hash);
  drawMap();
  if (announce) status.textContent = `${current.percent}% pressure limit. ${spaced(label)}, realization ${selected % 8 + 1}. ${correct ? 'History identified.' : `Read as ${spaced(chosen)}.`} ${current[reader + '_correct']} of 960 histories identified.`;
}

function exportPair() {
  const current = record.levels[level], truth = Math.floor(selected / 8), choice = predicted(current.points[selected]);
  const svg = element('svg', { xmlns: NS, width: 1200, height: 850, viewBox: '0 0 1200 850' });
  const title = element('title'); title.textContent = 'PALIMPSEST — An imperfect hand'; svg.append(title);
  const metadata = element('metadata');
  metadata.textContent = JSON.stringify({ artwork: 'PALIMPSEST / An imperfect hand', author: 'Codex', version: 1,
    seed: record.seed, pressure_limit_percent: current.percent, realization: selected % 8 + 1,
    written_order: record.histories[truth], chosen_order: record.histories[choice], reader,
    pressure_factors_display: current.pressure_factors[selected], source_report_sha256: record.source_report_sha256,
    glyph_times_seconds: record.glyph_times_seconds, glyph_center: record.glyph_center,
    glyph_scale_hz: record.glyph_scale_hz, maximum_display_error_hz: record.glyph_maximum_display_error_hz,
    measured_pitch_deviations_hz: glyphValues(current.glyph_offset + selected).map((row) => row.map((value) => value * record.glyph_scale_hz)),
    chosen_pitch_deviations_hz: glyphValues(choice).map((row) => row.map((value) => value * record.glyph_scale_hz)),
    scope: 'Four sampled moments, twelve voices, common scale. Display-quantized values; complete precision is in the scientific edition.',
  }); svg.append(metadata);
  svg.append(element('rect', { width: 1200, height: 850, fill: PAPER }));
  const text = (x, y, content, size = 18, family = 'sans-serif', color = INK) => {
    const node = element('text', { x, y, fill: color, 'font-family': family, 'font-size': size });
    node.textContent = content; svg.append(node);
  };
  text(60, 51, 'PALIMPSEST / STUDY III', 14); text(1010, 51, 'CODEX / 2026', 14);
  svg.append(element('line', { x1: 60, x2: 1140, y1: 72, y2: 72, stroke: '#c7c2b4' }));
  text(60, 145, 'An imperfect hand', 60, 'Georgia, serif');
  text(60, 183, `Up to ${current.percent}% pressure variation · ${reader === 'nearest' ? 'Nearest ideal answer' : 'Allow for pressure'} · Realization ${selected % 8 + 1}`, 18);
  [$('#measured-glyph'), $('#chosen-glyph')].forEach((source, index) => {
    const group = element('g', { transform: `translate(${index ? 660 : 100},220) scale(1.45)` });
    group.append(source.firstElementChild.cloneNode(true)); svg.append(group);
  });
  text(100, 667, 'WRITTEN', 13); text(660, 667, 'READ AS', 13);
  text(100, 708, spaced(record.histories[truth]), 34, 'Georgia, serif');
  text(660, 708, spaced(record.histories[choice]), 34, 'Georgia, serif', truth === choice ? INK : OCHRE);
  text(60, 758, 'Rings: 0, 4, 8, 12 seconds. Twelve voice directions. Same reference and scale on both sides.', 15);
  text(60, 786, 'Pressure changes: ' + current.pressure_factors[selected].map((value, i) => `${record.histories[truth][i]} ${((value - 1) * 100).toFixed(2)}%`).join(' / '), 15);
  text(60, 816, `Display error ≤ ${record.glyph_maximum_display_error_hz.toFixed(7)} Hz. Full-precision measurements determine the labels.`, 13, 'sans-serif', '#5f6860');
  const blob = new Blob([new XMLSerializer().serializeToString(svg)], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = `palimpsest-imperfect-${current.percent}-${record.histories[truth]}-${selected % 8 + 1}-${reader}.svg`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  status.textContent = 'The pair is exported as an SVG with its measured ring values and case details embedded.';
}

function validate(data) {
  if (data.version !== 1 || data.histories.length !== 120 || new Set(data.histories).size !== 120 ||
      data.histories.some((label) => !/^[ABCDE]{5}$/.test(label) || new Set(label).size !== 5) ||
      data.glyph_shape.join(',') !== '3000,4,12' || data.glyph_file !== 'pressure-glyphs-v1.bin' ||
      !Number.isFinite(data.glyph_scale_hz) || data.glyph_scale_hz <= 0 || data.levels.length !== 3 ||
      data.extent.length !== 4 || !data.extent.every(Number.isFinite) ||
      data.extent[0] >= data.extent[1] || data.extent[2] >= data.extent[3] ||
      data.canonical_positions.length !== 120 || data.canonical_positions.some((point) => point.length !== 2 || !point.every(Number.isFinite))) {
    throw new Error('The study record has an unsupported shape.');
  }
  data.levels.forEach((item, index) => {
    if (item.percent !== [1, 3, 10][index] || item.glyph_offset !== 120 + index * 960 ||
        item.tested !== 960 || item.points.length !== 960 || item.pressure_factors.length !== 960 ||
        item.points.some((point) => point.length !== 6 || !point.every(Number.isFinite) ||
          [point[2], point[3]].some((value) => !Number.isInteger(value) || value < 0 || value >= 120)) ||
        item.pressure_factors.some((values) => values.length !== 5 || values.some((value) => !Number.isFinite(value) || value < .899999 || value > 1.100001)) ||
        ['nearest', 'corrected'].some((method, column) => item[method + '_correct'] !== item.points.filter((point, i) => point[column + 2] === Math.floor(i / 8)).length)) {
      throw new Error('A saved study level is incomplete or inconsistent.');
    }
  });
  return data;
}

async function open() {
  try {
    const response = await fetch(BASE + 'pressure-study-v1.json');
    if (!response.ok) throw new Error('The measured record could not be opened.');
    record = validate(await response.json());
    const binary = await fetch(BASE + record.glyph_file);
    if (!binary.ok) throw new Error('The measured glyphs could not be opened.');
    const buffer = await binary.arrayBuffer();
    if (buffer.byteLength !== 288000) throw new Error('The glyph record is incomplete.');
    glyphs = new DataView(buffer);
    if (!context) throw new Error('This browser cannot display the measured map.');
    $('#written-order').replaceChildren(...record.histories.map((label) => {
      const option = document.createElement('option'); option.value = label; option.textContent = label; return option;
    }));
    $('#trial-buttons').replaceChildren(...Array.from({ length: 8 }, (_, index) => {
      const button = document.createElement('button'); button.textContent = String(index + 1);
      button.dataset.trial = String(index); button.setAttribute('aria-label', `Pressure realization ${index + 1}`);
      button.setAttribute('aria-pressed', 'false'); return button;
    }));
    selected = record.example.case; level = record.example.level;
    readHash();
    $$('button[data-level]').forEach((button) => button.addEventListener('click', () => { level = Number(button.dataset.level); render(); }));
    $$('button[data-reader]').forEach((button) => button.addEventListener('click', () => { reader = button.dataset.reader; render(); }));
    $$('button[data-trial]').forEach((button) => button.addEventListener('click', () => { selected = Math.floor(selected / 8) * 8 + Number(button.dataset.trial); render(); }));
    $('#written-order').addEventListener('change', (event) => { selected = record.histories.indexOf(event.target.value) * 8 + selected % 8; render(); });
    $('#next-misread').addEventListener('click', () => {
      const points = record.levels[level].points;
      for (let step = 1; step <= points.length; step++) {
        const candidate = (selected + step) % points.length;
        if (predicted(points[candidate]) !== Math.floor(candidate / 8)) { selected = candidate; render(); break; }
      }
    });
    $('#export-pressure').addEventListener('click', exportPair);
    canvas.addEventListener('click', (event) => {
      const bounds = canvas.getBoundingClientRect(), x = event.clientX - bounds.left, y = event.clientY - bounds.top;
      let best = -1, distance = 18 ** 2;
      record.levels[level].points.forEach((point, index) => {
        const [px, py] = coordinates(...point), squared = (x - px) ** 2 + (y - py) ** 2;
        if (squared < distance) { best = index; distance = squared; }
      });
      if (best >= 0) { selected = best; render(); }
    });
    window.addEventListener('hashchange', () => { if (readHash()) render(true, false); });
    const observer = new ResizeObserver(() => { cancelAnimationFrame(resizeFrame); resizeFrame = requestAnimationFrame(drawMap); });
    observer.observe(canvas);
    $$('fieldset[disabled], select[disabled], #export-pressure').forEach((control) => { control.disabled = false; });
    $('#glyph-precision').textContent = `The compact display stores ring values to within ${record.glyph_maximum_display_error_hz.toFixed(7)} Hz of the measured values. Full-precision trajectories determine every label.`;
    document.body.dataset.pressureReady = 'true';
    render();
  } catch (error) {
    status.textContent = `${error.message} Reload to try again. The result table and study edition remain available below.`;
    document.body.dataset.pressureReady = 'error';
  }
}

open();
