const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const NS = 'http://www.w3.org/2000/svg';
const BASE = '/assets/generated/';
const status = $('#atlas-status');
const audio = [$('#probe-0'), $('#probe-1')];
const play = $('#probe-play');
const scrub = $('#probe-time');
const grid = $('#history-grid');
const alphabet = 'ABCDE';
let atlas;
let lookup;
let histories = ['ABCDE', 'EDCBA'];
let chooseSlot = 0;
let heard = 0;
let position = 0;
let playing = false;
let starting = false;
let seeking = false;
let generation = 0;
let fadeFrame = 0;

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(NS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function drawGlyph(svg, paths, spokes = false) {
  const parts = [];
  if (spokes) {
    const lines = svgElement('g');
    for (let i = 0; i < 12; i++) {
      const angle = i * Math.PI / 6;
      lines.append(svgElement('line', { x1: 120 + 14 * Math.sin(angle), y1: 120 - 14 * Math.cos(angle),
        x2: 120 + 106 * Math.sin(angle), y2: 120 - 106 * Math.cos(angle), class: 'glyph-spoke' }));
    }
    parts.push(lines);
  }
  const rings = svgElement('g');
  paths.forEach((d) => rings.append(svgElement('path', { d, class: 'glyph-ring' })));
  parts.push(rings, svgElement('circle', { cx: 120, cy: 120, r: .9, class: 'glyph-center' }));
  svg.replaceChildren(...parts);
}

function displayClock(seconds) {
  return `00:${String(Math.floor(Math.max(0, seconds))).padStart(2, '0')}`;
}

function updatePosition(value, seekMedia = false) {
  position = Math.max(0, Math.min(atlas?.audio_seconds || 13.958333, value));
  scrub.value = String(position);
  $('#probe-clock').value = displayClock(position);
  if (seekMedia) audio.forEach((track) => {
    if (track.readyState >= 1) track.currentTime = Math.min(position, track.duration);
  });
  if (!playing) play.textContent = position >= 13.9 ? 'Hear again ↻' : 'Hear the question ▶';
}

function stop() {
  ++generation;
  cancelAnimationFrame(fadeFrame);
  audio.forEach((track) => track.pause());
  playing = false;
  starting = false;
  play.disabled = !atlas;
  play.setAttribute('aria-pressed', 'false');
  updatePosition(position);
}

function setHeard(index, announce = true) {
  heard = index;
  $$('[data-hear]').forEach((button) => button.setAttribute('aria-pressed', String(Number(button.dataset.hear) === index)));
  cancelAnimationFrame(fadeFrame);
  if (!playing) {
    audio.forEach((track, i) => { track.muted = i !== heard; track.volume = i === heard ? 1 : 0; });
  } else {
    const initial = audio.map((track) => track.volume);
    const start = performance.now();
    audio.forEach((track) => { track.muted = false; });
    const fade = (now) => {
      const amount = Math.min(1, (now - start) / 120);
      audio.forEach((track, i) => { track.volume = initial[i] * (1 - amount) + (i === heard ? amount : 0); });
      if (amount < 1) fadeFrame = requestAnimationFrame(fade);
      else audio.forEach((track, i) => { track.muted = i !== heard; });
    };
    fadeFrame = requestAnimationFrame(fade);
  }
  if (announce) status.textContent = `${playing ? 'Hearing' : 'Ready to hear'} ${histories[heard].split('').join(' · ')}. The other history stays at the same point in the question.`;
}

function loadPair() {
  audio.forEach((track, index) => {
    const path = BASE + lookup.get(histories[index]).audio;
    if (track.getAttribute('src') !== path || track.error) {
      track.src = path;
      track.load();
    }
  });
}

async function begin() {
  if (!atlas || starting) return;
  if (position >= 13.9) updatePosition(0, true);
  const request = ++generation;
  starting = true;
  play.disabled = true;
  status.textContent = 'Opening the two recorded answers…';
  setHeard(heard, false);
  loadPair();
  try {
    await Promise.all(audio.map((track) => track.play()));
    if (request !== generation) return;
    playing = true;
    starting = false;
    play.disabled = false;
    play.textContent = 'Pause the question Ⅱ';
    play.setAttribute('aria-pressed', 'true');
    status.textContent = `Hearing ${histories[heard].split('').join(' · ')}. Switch histories while the same question continues.`;
  } catch {
    if (request !== generation) return;
    stop();
    status.textContent = 'Playback was interrupted. Press “Hear the question” to try again.';
  }
}

function updateGridSelection() {
  $$('.history-glyph').forEach((button) => {
    const selected = button.dataset.history === histories[chooseSlot];
    button.setAttribute('aria-pressed', String(selected));
    button.dataset.other = String(button.dataset.history === histories[1 - chooseSlot]);
    button.tabIndex = selected && !button.hidden ? 0 : -1;
  });
  if (!$('.history-glyph:not([hidden])[tabindex="0"]')) {
    const first = $('.history-glyph:not([hidden])');
    if (first) first.tabIndex = 0;
  }
}

function updatePair(updateURL = true) {
  stop();
  // Changing a history cancels old media and releases its decoder. The next
  // explicit play/seek loads only the current pair, never the whole collection.
  audio.forEach((track) => {
    track.removeAttribute('src');
    track.load();
  });
  updatePosition(0);
  histories.forEach((label, side) => {
    const record = lookup.get(label);
    drawGlyph($(`#glyph-${side}`), record.paths, true);
    $(`#glyph-${side}`).setAttribute('aria-label', `${label.split('').join(', ')}: four moments in its later answer`);
    $$(`#order-${side} select`).forEach((select, index) => { select.value = label[index]; });
  });
  const left = lookup.get(histories[0]).index;
  const right = lookup.get(histories[1]).index;
  const distance = atlas.distances[left][right];
  $('#pair-distance').textContent = left === right ? 'The same history on both sides: identical recorded answers.' : `Recorded pitch difference: ${distance.toFixed(3)} Hz RMS across twelve voices and the full probe.`;
  const hash = `#${histories[0]}-${histories[1]}`;
  $('#share-pair').href = hash;
  if (updateURL) history.replaceState(null, '', hash);
  updateGridSelection();
  setHeard(heard, false);
  status.textContent = `${histories[0].split('').join(' · ')} and ${histories[1].split('').join(' · ')}. Ready for the same question.`;
}

function chooseHistory(side, label) {
  if (!lookup.has(label) || histories[side] === label) return;
  histories[side] = label;
  updatePair();
}

function readHash() {
  const match = /^#([A-E]{5})-([A-E]{5})$/.exec(location.hash);
  if (!match || !lookup.has(match[1]) || !lookup.has(match[2])) return false;
  histories = [match[1], match[2]];
  return true;
}

function buildOrders() {
  for (let side = 0; side < 2; side++) {
    const field = $(`#order-${side}`);
    for (let index = 0; index < 5; index++) {
      const select = document.createElement('select');
      select.setAttribute('aria-label', `${side === 0 ? 'First' : 'Second'} history, gesture ${index + 1}`);
      [...alphabet].forEach((letter) => select.add(new Option(letter, letter)));
      select.addEventListener('change', () => {
        const letters = [...histories[side]];
        const previous = letters.indexOf(select.value);
        [letters[index], letters[previous]] = [letters[previous], letters[index]];
        chooseHistory(side, letters.join(''));
      });
      field.append(select);
    }
    field.disabled = false;
  }
}

function buildGrid() {
  const fragment = document.createDocumentFragment();
  atlas.cases.forEach((record) => {
    const button = document.createElement('button');
    button.className = 'history-glyph';
    button.dataset.history = record.label;
    button.setAttribute('aria-label', `Choose history ${record.label.split('').join(', ')}`);
    button.setAttribute('aria-pressed', 'false');
    const svg = svgElement('svg', { viewBox: '0 0 240 240', 'aria-hidden': 'true' });
    drawGlyph(svg, record.paths);
    const caption = document.createElement('span');
    caption.textContent = record.label;
    button.append(svg, caption);
    button.addEventListener('click', () => chooseHistory(chooseSlot, record.label));
    fragment.append(button);
  });
  grid.replaceChildren(fragment);
}

play.addEventListener('click', () => playing ? stop() : begin());
$$('[data-hear]').forEach((button) => button.addEventListener('click', () => setHeard(Number(button.dataset.hear))));
audio.forEach((track) => {
  track.addEventListener('loadedmetadata', () => { track.currentTime = Math.min(position, track.duration); });
  track.addEventListener('error', () => {
    if (!track.getAttribute('src')) return;
    stop();
    status.textContent = 'A recorded answer could not load. Press “Hear the question” to try again.';
  });
});
audio[0].addEventListener('timeupdate', () => {
  if (!playing || seeking) return;
  updatePosition(audio[0].currentTime);
  if (audio[1].readyState >= 2 && Math.abs(audio[1].currentTime - position) > .08) audio[1].currentTime = Math.min(position, audio[1].duration);
});
audio[0].addEventListener('ended', () => { updatePosition(atlas.audio_seconds); stop(); status.textContent = 'The question has ended. Choose another history, or hear the pair again.'; });
scrub.addEventListener('input', () => { seeking = true; loadPair(); updatePosition(Number(scrub.value), true); });
scrub.addEventListener('change', () => { seeking = false; });
$$('[data-slot]').forEach((button) => button.addEventListener('click', () => {
  chooseSlot = Number(button.dataset.slot);
  $$('[data-slot]').forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
  updateGridSelection();
}));
$('#ending').addEventListener('change', (event) => {
  $$('.history-glyph').forEach((button) => { button.hidden = !button.dataset.history.endsWith(event.target.value); });
  $('#history-count').value = `${$$('.history-glyph:not([hidden])').length} histories`;
  updateGridSelection();
});
grid.addEventListener('keydown', (event) => {
  const buttons = $$('.history-glyph:not([hidden])');
  const current = buttons.indexOf(document.activeElement);
  if (current < 0) return;
  const columns = getComputedStyle(grid).gridTemplateColumns.split(' ').length;
  const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -columns, ArrowDown: columns }[event.key];
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : step === undefined ? null : Math.max(0, Math.min(buttons.length - 1, current + step));
  if (next === null) return;
  event.preventDefault();
  buttons.forEach((button) => { button.tabIndex = -1; });
  buttons[next].tabIndex = 0;
  buttons[next].focus();
});
$$('[data-suggestion]').forEach((button) => button.addEventListener('click', () => {
  const label = histories[0];
  const kind = button.dataset.suggestion;
  let chosen;
  if (kind === 'reverse') chosen = [...label].reverse().join('');
  else if (kind === 'earlier') chosen = label[1] + label[0] + label.slice(2);
  else {
    const index = lookup.get(label).index;
    const ranked = atlas.cases.filter((record) => record.index !== index).sort((a, b) => atlas.distances[index][a.index] - atlas.distances[index][b.index]);
    chosen = ranked[kind === 'nearest' ? 0 : ranked.length - 1].label;
  }
  chooseHistory(1, chosen);
}));
window.addEventListener('hashchange', () => { if (atlas && readHash()) updatePair(false); });
window.addEventListener('pagehide', stop);
document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });

try {
  const response = await fetch(BASE + 'histories.json');
  if (!response.ok) throw new Error('The recorded atlas could not be fetched');
  const packet = await response.json();
  if (packet.version !== 1 || packet.cases.length !== 120 || packet.distances.length !== 120) throw new Error('Incomplete atlas');
  packet.cases.forEach((record, index) => { record.index = index; });
  atlas = packet;
  lookup = new Map(atlas.cases.map((record) => [record.label, record]));
  readHash();
  buildOrders();
  buildGrid();
  $$('[data-hear], [data-suggestion]').forEach((button) => { button.disabled = false; });
  scrub.disabled = false;
  scrub.max = String(atlas.audio_seconds);
  updatePair();
} catch {
  status.textContent = 'The atlas could not load. Reload this page to try again, or read the complete study in the notebook below.';
}
