'use strict';

const catalog = window.IDP_CATALOG;
if (!catalog) { throw new Error('Missing catalog'); }
const byId = id => catalog.assets.find(a => a.id === id || a.aliases.includes(id));
const dialog = document.getElementById('viewer');

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function openMedia(asset, startTime = 0) {
  document.querySelectorAll('video').forEach(video => video.pause());
  const area = document.getElementById('dialog-media');
  area.replaceChildren();
  document.getElementById('dialog-title').textContent = asset.title;
  document.getElementById('dialog-caption').textContent = asset.caption;
  const downloadLink = document.getElementById('dialog-download');
  if (downloadLink) {
    downloadLink.href = asset.src;
    downloadLink.textContent = 'Download ↓';
  }
  if (asset.kind === 'figure') {
    const img = new Image(); img.src = asset.src; img.alt = asset.title; area.append(img);
  } else if (asset.kind === 'video') {
    const video = document.createElement('video');
    video.src = asset.src; video.controls = true; video.playsInline = true; video.preload = 'metadata';
    if (asset.thumbnail) video.poster = asset.thumbnail;
    if (startTime > 0) {
      video.addEventListener('loadedmetadata', () => {
        if (Number.isFinite(video.duration)) video.currentTime = Math.min(startTime, Math.max(0, video.duration - .05));
      }, { once: true });
    }
    area.append(video);
  } else {
    area.append(el('p', 'dialog-placeholder', 'Editable source / document. Download to inspect at full resolution.'));
  }
  dialog.showModal();
}
function closeMedia() { dialog.close(); document.getElementById('dialog-media').replaceChildren(); }
document.getElementById('close-viewer').addEventListener('click', closeMedia);
dialog.addEventListener('close', () => document.getElementById('dialog-media').replaceChildren());
dialog.addEventListener('click', e => {
  if (e.target !== dialog) return;
  const b = dialog.getBoundingClientRect();
  if (e.clientX < b.left || e.clientX > b.right || e.clientY < b.top || e.clientY > b.bottom) closeMedia();
});

function videoCard(asset, { title, caption, label, muted = false, preload = 'none', ariaLabel, className = 'video-card', analysisAsset, headingFirst = false }) {
  const article = el('article', className);
  const video = document.createElement('video');
  video.controls = true; video.playsInline = true; video.preload = preload;
  if (muted) video.muted = true;
  const revision = asset.sha256 ? '?v=' + asset.sha256.slice(0, 12) : '';
  video.src = asset.src + revision;
  if (asset.thumbnail) video.poster = asset.thumbnail + revision;
  video.setAttribute('aria-label', ariaLabel || title);
  const body = el('div', 'card-body');
  const heading = el('div', 'card-heading');
  if (headingFirst) {
    heading.append(el('h3', '', title));
    if (label) heading.append(el('span', 'video-label', label));
  } else {
    if (label) body.append(el('span', 'video-label', label));
    body.append(el('h3', '', title));
  }
  body.append(el('p', '', caption));
  const actions = el('div', 'video-actions');
  const enlarge = el('button', 'video-action', 'Enlarge video');
  enlarge.type = 'button';
  enlarge.setAttribute('aria-label', `Enlarge ${ariaLabel || title}`);
  enlarge.addEventListener('click', () => openMedia({ ...asset, title: ariaLabel || title, caption }, video.currentTime));
  actions.append(enlarge);
  if (analysisAsset) {
    const analysis = el('button', 'video-action', 'View trajectory');
    analysis.type = 'button';
    analysis.setAttribute('aria-label', `View trajectory for ${ariaLabel || title}`);
    analysis.addEventListener('click', () => openMedia({ ...analysisAsset, title: `${ariaLabel || title} / Trajectory analysis` }));
    actions.append(analysis);
  }
  body.append(actions);
  if (headingFirst) article.append(heading);
  article.append(video, body);
  return article;
}

// Assets already embedded in the main sections stay out of the supplementary grid.
const used = new Set();
const heroVideo = document.getElementById('hero-video');
const hero = byId(heroVideo.dataset.hero) || byId('idp-home-teaser') || byId('idp-project-video');
if (hero) {
  used.add(hero.id);
  const video = heroVideo;
  const revision = '?v=' + hero.sha256.slice(0, 12);
  video.src = hero.src + revision;
  const widescreen = ['idp-home-teaser', 'idp-project-video', 'idp-focused-highlight', 'idp-research-montage'].includes(hero.id);
  video.classList.toggle('research-montage', widescreen);
  video.classList.toggle('comparison-edit', !widescreen);
  video.poster = hero.thumbnail ? hero.thumbnail + revision : '';
  if (hero.id === 'idp-home-teaser') {
    const speed = document.getElementById('hero-speed');
    speed.hidden = false;
    video.addEventListener('timeupdate', () => { speed.textContent = video.currentTime < 17 ? '1×' : '2×'; });
  }
  if (['idp-research-montage', 'idp-home-teaser'].includes(hero.id)) {
    video.loop = true;
    if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      video.autoplay = true;
      video.play().catch(() => {});
    }
  }
}
document.querySelectorAll('[data-hero-time]').forEach(button => {
  button.addEventListener('click', () => {
    const video = document.getElementById('full-video');
    const seek = () => { video.currentTime = Math.min(Number(button.dataset.heroTime), video.duration); };
    if (Number.isFinite(video.duration)) seek();
    else video.addEventListener('loadedmetadata', seek, { once: true });
    video.play().catch(() => {});
  });
});
document.querySelectorAll('video[data-video]').forEach(video => {
  const a = byId(video.dataset.video);
  if (!a) return;
  used.add(a.id);
  const v = '?v=' + a.sha256.slice(0, 12);
  video.src = a.src + v;
  video.poster = a.thumbnail ? a.thumbnail + v : '';
});

// Figure modal uses the visible figure caption and title rather than internal catalog metadata.
document.querySelectorAll('[data-feature]').forEach(figure => {
  const a = byId(figure.dataset.feature);
  if (!a) { figure.hidden = true; return; }
  used.add(a.id);
  const img = figure.querySelector('img');
  if (a.width) { img.width = a.width; img.height = a.height; }
  img.src = a.src;
  const figcaption = figure.querySelector('figcaption');
  const strong = figcaption ? figcaption.querySelector('strong') : null;
  const visibleTitle = strong
    ? `${strong.textContent.replace(/:$/, '').trim()}${img.alt ? ' — ' + img.alt : ''}`
    : (img.alt || a.title);
  const prefix = strong ? strong.textContent : '';
  const visibleCaption = (figcaption && prefix)
    ? figcaption.textContent.replace(prefix, '').trim()
    : (figcaption ? figcaption.textContent.trim() : a.caption);
  figure.querySelector('button').addEventListener('click', () => openMedia({
    ...a,
    title: visibleTitle,
    caption: visibleCaption
  }));
});

const features = [
  ['ral-guidance-inspection', 'Guidance record inspection', 'Runtime reconstruction of current observation, nearest expert reference, and policy guidance state from saved inference records.']
];
const featuredRoot = document.getElementById('featured-videos');
features.forEach(([id, title, caption], i) => {
  const a = byId(id);
  if (!a) return;
  used.add(a.id);
  featuredRoot.append(videoCard(a, { title, caption, label: i % 2 ? 'Diagnostic view' : 'Real-robot recording', preload: 'none' }));
});

const trajectoryVideos = [
  ['fig9-sync-dgb-dp-stop', 'DGB', 'DP + Stop', 'Stop during intrusion, then continue the task.'],
  ['fig9-sync-dgb-dp-rmp', 'DGB', 'DP + RMPflow', 'Reactive avoidance with policy continuation.'],
  ['fig9-sync-dgb-dp-rmp-lpb', 'DGB', 'IDP', 'RMPflow avoidance with Recovery-aware LPB guidance.'],
  ['fig9-sync-sao-dp-stop', 'SAO', 'DP + Stop', 'Sudden-obstacle stop baseline.'],
  ['fig9-sync-sao-dp-rmp', 'SAO', 'DP + RMPflow', 'Reactive avoidance with policy continuation.'],
  ['fig9-sync-sao-dp-rmp-lpb', 'SAO', 'IDP', 'RMPflow avoidance with Recovery-aware LPB guidance.']
];
const trajectoryTasks = [['DGB', 'Dynamic global blocking'], ['SAO', 'Suddenly appearing obstacle']];
const trajectoryRoot = document.getElementById('trajectory-videos');
const tabList = el('div', 'segmented');
tabList.setAttribute('role', 'tablist');
tabList.setAttribute('aria-label', 'Rollout task');
const tabs = [];
const panels = [];

function comparisonControls(grid) {
  const videos = Array.from(grid.querySelectorAll('video'));
  const bar = el('div', 'comparison-bar');
  const note = el('p', 'comparison-note', 'Representative trials · independent recordings');
  note.setAttribute('role', 'status');
  const controls = el('div', 'comparison-controls');
  const toggle = el('button', 'comparison-button comparison-button--primary', 'Play all');
  const replay = el('button', 'comparison-button', 'Replay all');
  toggle.type = replay.type = 'button';
  controls.append(toggle, replay);
  bar.append(note, controls);

  const refresh = () => {
    toggle.textContent = videos.some(video => !video.paused && !video.ended) ? 'Pause all' : 'Play all';
  };
  let request = 0;
  const play = () => {
    const currentRequest = ++request;
    const attempts = videos.map(video => {
      if (video.ended) video.currentTime = 0;
      return video.play();
    });
    refresh();
    Promise.allSettled(attempts).then(results => {
      if (currentRequest !== request) return;
      note.textContent = results.some(result => result.status === 'rejected' && result.reason?.name !== 'AbortError')
        ? 'Some videos could not play. Use their individual controls.'
        : 'Representative trials · independent recordings';
      refresh();
    });
  };
  toggle.addEventListener('click', () => {
    if (videos.some(video => !video.paused && !video.ended)) {
      request++;
      videos.forEach(video => video.pause());
      refresh();
    } else play();
  });
  replay.addEventListener('click', () => {
    request++;
    videos.forEach(video => { video.pause(); video.currentTime = 0; });
    play();
  });
  videos.forEach(video => ['play', 'pause', 'ended'].forEach(event => video.addEventListener(event, refresh)));
  return bar;
}

trajectoryTasks.forEach(([task, label]) => {
  const cards = trajectoryVideos.filter(item => item[1] === task).map(([id, , title, caption]) => {
    const analysis = byId(id);
    const robot = byId(id.replace('fig9-sync-', 'fig9-robot-'));
    const a = robot || analysis;
    if (!a) return null;
    used.add(a.id);
    if (analysis) used.add(analysis.id);
    return videoCard(a, { title, caption, label: robot ? '1x recorded speed' : 'Trajectory analysis',
      muted: true, ariaLabel: `${task}: ${title}`,
      className: `video-card robot-card${title === 'IDP' ? ' robot-card--ours' : ''}`, headingFirst: true,
      analysisAsset: robot ? analysis : undefined });
  }).filter(Boolean);
  if (!cards.length) return;
  const key = task.toLowerCase();
  const tab = el('button', 'segment', label);
  tab.type = 'button';
  tab.id = `tab-${key}`;
  tab.setAttribute('role', 'tab');
  tab.setAttribute('aria-controls', `panel-${key}`);
  const panel = el('div', 'trajectory-task-group');
  panel.id = `panel-${key}`;
  panel.setAttribute('role', 'tabpanel');
  panel.setAttribute('aria-labelledby', tab.id);
  const grid = el('div', 'video-grid three');
  grid.append(...cards);
  panel.append(comparisonControls(grid), grid);
  tabs.push(tab); panels.push(panel); tabList.append(tab);
});
function selectTask(index, focus) {
  tabs.forEach((tab, i) => {
    const selected = i === index;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    panels[i].hidden = !selected;
    if (!selected) panels[i].querySelectorAll('video').forEach(v => v.pause());
  });
  if (focus) tabs[index].focus();
}
tabs.forEach((tab, i) => {
  tab.addEventListener('click', () => selectTask(i));
  tab.addEventListener('keydown', e => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    selectTask((i + (e.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length, true);
  });
});
if (tabs.length) {
  trajectoryRoot.replaceChildren(...(tabs.length > 1 ? [tabList] : []), ...panels);
  selectTask(0);
}

const sensingComparisons = [
  ['sensor-camera-s1', 'Visible obstacle', 'Depth sensing, camera-driven avoidance, and proximity-driven avoidance with an unobstructed view.'],
  ['sensor-camera-s2', 'Camera occlusion', 'The robot blocks the approaching obstacle from the depth camera; link-mounted sensing supports avoidance.'],
  ['sensor-camera-s3', 'Transparent glass', 'Depth sensing misses the glass in this comparison, while proximity input supports avoidance.'],
];
const sensingRoot = document.getElementById('sensing-comparisons');
if (sensingRoot) {
  const selector = el('div', 'segmented');
  selector.setAttribute('role', 'tablist');
  selector.setAttribute('aria-label', 'Sensing scenario');
  const scenarioTabs = [];
  const scenarioPanels = [];
  sensingComparisons.forEach(([id, title, caption]) => {
    const asset = byId(id);
    if (!asset) return;
    used.add(asset.id);
    const tab = el('button', 'segment', title);
    tab.type = 'button';
    tab.id = `tab-${id}`;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', `panel-${id}`);
    const panel = el('div', 'sensing-scenario');
    panel.id = `panel-${id}`;
    panel.setAttribute('role', 'tabpanel');
    panel.setAttribute('aria-labelledby', tab.id);
    panel.append(videoCard(asset, { title, caption, muted: true,
      ariaLabel: `Sensing: ${title}`, className: 'video-card sensor-video' }));
    selector.append(tab);
    scenarioTabs.push(tab);
    scenarioPanels.push(panel);
  });
  const selectScenario = (index, focus = false) => {
    scenarioTabs.forEach((tab, i) => {
      const selected = i === index;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      scenarioPanels[i].hidden = !selected;
      if (!selected) scenarioPanels[i].querySelectorAll('video').forEach(video => video.pause());
    });
    if (focus) scenarioTabs[index].focus();
  };
  scenarioTabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectScenario(i));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      selectScenario((i + (event.key === 'ArrowRight' ? 1 : scenarioTabs.length - 1)) % scenarioTabs.length, true);
    });
  });
  sensingRoot.replaceChildren(selector, ...scenarioPanels);
  if (scenarioTabs.length) selectScenario(0);
}

const proximityVideos = [
  ['notion-proximity-close-approach', 'Close-proximity interaction',
    'External view of a person approaching the sensorized robot during policy execution.'],
  ['notion-proximity-task-interaction', 'Proximity interaction during task execution',
    'External view of close human interaction while the robot continues the task sequence.'],
  ['notion-lpb-avoidance-diagnostic', 'LPB avoidance diagnostic',
    'Recorded observations, trajectories and runtime plots for qualitative inspection.'],
  ['notion-lpb-rollout-diagnostic-a', 'LPB rollout diagnostic A',
    'Runtime visualization from one recorded inference run.'],
  ['notion-lpb-rollout-diagnostic-b', 'LPB rollout diagnostic B',
    'Runtime visualization from a second recorded inference run.']
];
const proximityRoot = document.getElementById('proximity-videos');
if (proximityRoot) {
  const externalGrid = el('div', 'video-grid two');
  const diagnosticGrid = el('div', 'video-grid diagnostic-grid');
  proximityVideos.forEach(([id, title, caption], index) => {
    const asset = byId(id);
    if (!asset) return;
    used.add(asset.id);
    const card = videoCard(asset, {
      title,
      caption,
      label: index < 2 ? 'External recording' : 'Runtime diagnostic',
      muted: true,
      preload: 'none',
      ariaLabel: title,
      className: index < 2 ? 'video-card robot-card' : 'video-card diagnostic-card',
    });
    (index < 2 ? externalGrid : diagnosticGrid).append(card);
  });
  const details = el('details', 'analysis-disclosure');
  details.append(el('summary', '', 'Inspect observation and guidance plots'), diagnosticGrid);
  details.addEventListener('toggle', () => {
    if (!details.open) details.querySelectorAll('video').forEach(video => video.pause());
  });
  proximityRoot.replaceChildren(externalGrid, details);
}

document.addEventListener('play', e => {
  if (e.target.tagName !== 'VIDEO') return;
  const isTraj = e.target.closest('.trajectory-task-group');
  document.querySelectorAll('video').forEach(v => {
    if (v === e.target) return;
    if (isTraj && v.closest('.trajectory-task-group') === isTraj) return;
    v.pause();
  });
}, true);
document.querySelectorAll('details').forEach(details => {
  details.addEventListener('toggle', () => {
    if (!details.open) details.querySelectorAll('video').forEach(video => video.pause());
  });
});

function card(item) {
  const a = byId(item.id);
  if (!a) return null;
  const cleanAsset = {
    ...a,
    title: item.title || a.title,
    caption: item.caption || a.caption
  };
  const article = el('article', 'asset-card');
  const button = el('button', 'asset-cover');
  button.type = 'button';
  button.setAttribute('aria-label', `Open ${cleanAsset.title}`);
  if (cleanAsset.thumbnail) {
    const img = new Image(); img.src = cleanAsset.thumbnail; img.alt = cleanAsset.title; img.loading = 'lazy'; img.decoding = 'async';
    button.append(img);
  } else {
    button.append(el('span', 'filetype', cleanAsset.src.split('.').pop().toUpperCase()));
  }
  if (cleanAsset.kind === 'video') {
    const mark = el('span', 'play-mark');
    mark.setAttribute('aria-hidden', 'true');
    mark.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13l10.5-6.5z"/></svg>';
    button.append(mark);
  }
  button.addEventListener('click', () => openMedia(cleanAsset));
  const info = el('div', 'asset-info');
  const link = el('a', '', 'Download ↓');
  link.href = cleanAsset.src;
  link.download = '';
  info.append(el('h3', '', cleanAsset.title), el('p', '', cleanAsset.caption), link);
  article.append(button, info);
  return article;
}

document.querySelectorAll('a[href="#replay"], a[href="replay.html"], #replay, #replay-shell').forEach(node => node.remove());

const supplementaryItems = [
  {
    id: 'idp-research-montage',
    title: 'Multi-view research montage',
    caption: 'Robot trials, expert demonstrations, and corrective data collection across multiple recordings.'
  },
  {
    id: 'obstacle-interaction-full',
    title: 'Full obstacle-interaction rollout',
    caption: 'A complete external-camera recording of task execution with repeated obstacle approaches.'
  }
];
const extras = supplementaryItems
  .filter(item => !used.has(item.id))
  .map(card)
  .filter(Boolean);

const assetsRoot = document.getElementById('assets');
if (assetsRoot) {
  assetsRoot.replaceChildren(...extras);
}
