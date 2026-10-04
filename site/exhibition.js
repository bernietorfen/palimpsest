const $ = (selector) => document.querySelector(selector);
const mainFilm = $('#main-film');
const enterFilm = $('#enter-film');
const filmStatus = $('#film-status');
const pair = [$('#first-phrase'), $('#return-phrase')];
const comparePlay = $('#compare-play');
const compareTime = $('#compare-time');
const compareClock = $('#compare-clock');
const compareStatus = $('#compare-status');
let selectedVoice = 0;
let pairPlaying = false;
let pairPosition = 0;
let pairSeeking = false;
let volumeFrame = 0;

function clock(seconds) {
  const rounded = Math.max(0, Math.floor(seconds || 0));
  return `${String(Math.floor(rounded / 60)).padStart(2, '0')}:${String(rounded % 60).padStart(2, '0')}`;
}

function loadMedia(video) {
  if (!video.getAttribute('src')) {
    video.src = video.dataset.src;
    video.load();
  }
}

function stopPair() {
  pair.forEach((video) => video.pause());
  pairPlaying = false;
  comparePlay.setAttribute('aria-pressed', 'false');
  comparePlay.textContent = pairPosition >= 45.95 ? 'Replay comparison ↻' : 'Play comparison ▶';
}

async function playFilm(position = null) {
  stopPair();
  if (position !== null) {
    if (mainFilm.readyState >= 1) mainFilm.currentTime = position;
    else mainFilm.addEventListener('loadedmetadata', () => { mainFilm.currentTime = position; }, { once: true });
  }
  loadMedia(mainFilm);
  mainFilm.controls = true;
  enterFilm.hidden = true;
  filmStatus.textContent = 'Opening the film…';
  try {
    await mainFilm.play();
    filmStatus.textContent = '';
  } catch {
    filmStatus.textContent = 'Use the video’s play control to begin.';
  }
}

enterFilm.addEventListener('click', () => playFilm());
mainFilm.addEventListener('play', stopPair);
mainFilm.addEventListener('playing', () => { filmStatus.textContent = ''; });
mainFilm.addEventListener('error', () => {
  filmStatus.textContent = 'The film could not load. Try its download link below.';
});
document.querySelectorAll('[data-seek]').forEach((button) => {
  button.addEventListener('click', () => {
    mainFilm.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    playFilm(Number(button.dataset.seek));
  });
});

function setPairPosition(position) {
  pairPosition = Math.max(0, Math.min(46, position));
  compareTime.value = String(pairPosition);
  compareClock.value = clock(pairPosition);
  if (!pairPlaying) comparePlay.textContent = pairPosition >= 45.95 ? 'Replay comparison ↻' : 'Play comparison ▶';
  pair.forEach((video) => {
    if (video.readyState >= 1) video.currentTime = Math.min(pairPosition, video.duration || 46);
  });
}

pair.forEach((video) => {
  video.addEventListener('loadedmetadata', () => { video.currentTime = pairPosition; });
  video.addEventListener('error', () => {
    stopPair();
    compareStatus.textContent = 'The comparison could not load. Both phrases are also in the complete film.';
  });
});

async function playPair() {
  mainFilm.pause();
  if (pairPosition >= 45.95) setPairPosition(0);
  cancelAnimationFrame(volumeFrame);
  pair.forEach((video, index) => {
    video.muted = index !== selectedVoice;
    video.volume = index === selectedVoice ? 1 : 0;
    loadMedia(video);
  });
  comparePlay.disabled = true;
  compareStatus.textContent = 'Opening both phrases…';
  try {
    await Promise.all(pair.map((video) => video.play()));
    pairPlaying = true;
    comparePlay.textContent = 'Pause comparison Ⅱ';
    comparePlay.setAttribute('aria-pressed', 'true');
    compareStatus.textContent = `Hearing the ${selectedVoice === 0 ? 'first question' : 'returning question'}. Switch voices while the two histories play together.`;
  } catch {
    stopPair();
    compareStatus.textContent = 'Playback was interrupted. Press play to try again.';
  } finally {
    comparePlay.disabled = false;
  }
}

comparePlay.addEventListener('click', () => pairPlaying ? stopPair() : playPair());
pair[0].addEventListener('timeupdate', () => {
  // Paused seeks are controlled by the slider. An older queued media event
  // must not replace a newer requested position while the decoder catches up.
  if (pairSeeking || !pairPlaying) return;
  pairPosition = pair[0].currentTime;
  compareTime.value = String(Math.min(pairPosition, 46));
  compareClock.value = clock(pairPosition);
  if (pairPlaying && pair[1].readyState >= 2 && Math.abs(pair[1].currentTime - pairPosition) > 0.12) {
    pair[1].currentTime = Math.min(pairPosition, pair[1].duration);
  }
  if (pairPosition >= 46) stopPair();
});
pair[0].addEventListener('ended', stopPair);
compareTime.addEventListener('input', () => {
  pairSeeking = true;
  pair.forEach(loadMedia);
  setPairPosition(Number(compareTime.value));
});
compareTime.addEventListener('change', () => { pairSeeking = false; });

document.querySelectorAll('[data-listen]').forEach((button) => {
  button.addEventListener('click', () => {
    selectedVoice = button.dataset.listen === 'first' ? 0 : 1;
    document.querySelectorAll('[data-listen]').forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
    cancelAnimationFrame(volumeFrame);
    const start = performance.now();
    const initial = pair.map((video) => video.volume);
    // A brief crossfade avoids a hard waveform jump at an arbitrary sample.
    pair.forEach((video) => { video.muted = false; });
    const fade = (now) => {
      const t = Math.min(1, (now - start) / 120);
      pair.forEach((video, index) => { video.volume = initial[index] * (1 - t) + (index === selectedVoice ? t : 0); });
      if (t < 1) volumeFrame = requestAnimationFrame(fade);
      else pair.forEach((video, index) => { video.muted = index !== selectedVoice; });
    };
    volumeFrame = requestAnimationFrame(fade);
    compareStatus.textContent = `Hearing the ${selectedVoice === 0 ? 'first question' : 'returning question'}${pairPlaying ? '.' : ' when playback begins.'}`;
  });
});

const dialog = $('#sculpture-dialog');
const sculptureStatus = $('#sculpture-status');
const stateNames = { '000': 'Unwritten', '165': 'Inscription', '358': 'Remnant' };
if (matchMedia('(pointer: coarse)').matches) $('#sculpture-instructions').textContent = 'Drag to turn · Pinch to approach';
let viewer = null;
let viewerRequest = 0;
let viewerAbort = null;

document.querySelectorAll('[data-sculpture]').forEach((button) => {
  button.addEventListener('click', async () => {
    mainFilm.pause();
    stopPair();
    const state = button.dataset.sculpture;
    const request = ++viewerRequest;
    viewerAbort?.abort();
    viewerAbort = new AbortController();
    $('#sculpture-title').textContent = stateNames[state];
    $('#download-sculpture').href = `/assets/generated/state-${state}.glb`;
    sculptureStatus.textContent = 'Opening the sculpture…';
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    try {
      const { SculptureViewer } = await import('./sculpture.js');
      if (request !== viewerRequest) return;
      viewer = new SculptureViewer($('#sculpture-canvas'));
      await viewer.load(`/assets/generated/state-${state}.glb`, viewerAbort.signal);
      if (request !== viewerRequest) return;
      sculptureStatus.textContent = '';
      $('#sculpture-canvas').focus();
    } catch (error) {
      if (request !== viewerRequest || error.name === 'AbortError') return;
      viewer?.dispose();
      viewer = null;
      sculptureStatus.textContent = 'The 3D view is unavailable in this browser. You can download the sculpture below.';
    }
  });
});
$('#close-sculpture').addEventListener('click', () => dialog.close());
$('#reset-sculpture').addEventListener('click', () => viewer?.reset());
dialog.addEventListener('close', () => {
  ++viewerRequest;
  viewerAbort?.abort();
  viewer?.dispose();
  viewer = null;
  document.body.style.overflow = '';
});
dialog.addEventListener('click', (event) => {
  if (event.target !== dialog) return;
  const box = dialog.getBoundingClientRect();
  if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
});

// The catalog points to the separately preserved editions and their final files.
fetch('/edition.json').then((response) => {
  if (!response.ok) throw new Error('Edition manifest unavailable');
  return response.json();
}).then((edition) => {
  if (!Array.isArray(edition.downloads) || !edition.downloads.length) return;
  const links = edition.downloads.map((entry) => {
    const url = new URL(entry.url, location.origin);
    if (url.origin !== location.origin && url.origin !== 'https://github.com') throw new Error('Unexpected download origin');
    const link = document.createElement('a');
    link.href = url.href;
    if (url.origin === location.origin) link.download = '';
    const title = document.createElement('span');
    const detail = document.createElement('span');
    title.textContent = entry.title;
    detail.textContent = `${entry.detail} ↓`;
    link.append(title, detail);
    return link;
  });
  $('#download-list').replaceChildren(...links);
}).catch(() => {});
