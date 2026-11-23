/* Drawings for the losing-trade filter dashboard. Every number comes from a dataset. */
const C = dash.colors;
const OK = 'var(--color-ok)', BAD = 'var(--color-bad)', MUTED = 'var(--cds-chart-muted, var(--color-fg-muted))';
const GRID = 'var(--cds-chart-grid, var(--color-border-line))', AXIS = 'var(--cds-chart-axis, var(--color-border-line))', REF = 'var(--cds-chart-reference, var(--color-fg-muted))';
// Topstep Combine rule constants (topstep_rules.yaml, verified 22 Nov 2026): profit target and Maximum Loss Limit
const RULE = {'50K': {target: 3000, mll: 2000}, '100K': {target: 6000, mll: 3000}, '150K': {target: 9000, mll: 4500}};
const WF_START = '2024-11-01';
const PERIOD = {dev: 'Development', wf: 'Walk-forward', 'dev + wf': 'Both'};

const num = (v) => (v === null || v === undefined || v === '' ? NaN : +v);
const usd0 = d3.format('$,.0f'), usd2 = d3.format('$,.2f');
const fUsd = (v, d = 0) => (isFinite(v) ? (v < 0 ? '−' : '') + (d ? usd2 : usd0)(Math.abs(v)) : '—');
const fSigned = (v) => (isFinite(v) ? (v < 0 ? '−' : '+') + usd0(Math.abs(v)) : '—');
const fPct = (v, d = 1) => (isFinite(v) ? d3.format('.' + d + '%')(v) : '—');
const fNum = (v, d = 2) => (isFinite(v) ? d3.format(',.' + d + 'f')(v).replace('-', '−') : '—');
const fK = (v) => (isFinite(v) ? (v < 0 ? '−' : '') + (Math.abs(v) >= 1000 ? d3.format('$,.3~s')(Math.abs(v)).replace('k', 'k') : usd0(Math.abs(v))) : '—');
const byUnit = (v, unit, metric) => {
  if (unit === '$') return fUsd(v, Math.abs(v) < 100 ? 2 : 0);
  if (unit === '%') return fPct(v);
  if (unit === 'n') return fNum(v, 0);
  return fNum(v, 2);
};
const rows = (id) => { const g = dash.data(id); return g.status === 'ok' ? g.data : null; };
const dash0 = (el) => { el.replaceChildren(document.createTextNode('—')); };
const signClass = (v) => (v > 0 ? 'nq-pos' : v < 0 ? 'nq-neg' : '');
const parseDay = d3.utcParse('%Y-%m-%d'), fDay = d3.utcFormat('%-d %b %Y');

function el(tag, attrs, text) {
  const e = document.createElement(tag);
  if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  return e;
}
function legend(host, items) {
  const l = el('div', {class: 'nq-legend'});
  items.forEach((it) => { const s = el('span'); const i = el('i'); i.style.background = it.color; if (it.dashed) { i.style.background = 'none'; i.style.borderTop = '2px dashed ' + it.color; i.style.height = '0'; } s.append(i, document.createTextNode(it.name)); l.append(s); });
  host.append(l);
}
function tip(host) {
  const t = el('div', {class: 'nq-tip'}); t.hidden = true; host.append(t);
  return {
    show(x, y, title, lines) {
      t.replaceChildren(); const b = el('b', null, title); t.append(b);
      lines.forEach(([k, v]) => { const d = el('div'); d.append(el('span', null, k), el('span', null, v)); t.append(d); });
      t.hidden = false;
      const w = t.offsetWidth, hw = host.clientWidth;
      t.style.left = Math.max(0, Math.min(hw - w, x + 12 + w > hw ? x - w - 12 : x + 12)) + 'px';
      t.style.top = Math.max(0, y - 10) + 'px';
    },
    hide() { t.hidden = true; },
  };
}
function frame(host, height, yTicksText, opts = {}) {
  const width = Math.max(260, host.clientWidth);
  const svg = d3.select(host).append('svg').attr('viewBox', `0 0 ${width} ${height}`).attr('height', height).attr('role', 'img').attr('aria-label', opts.label || 'Chart');
  // measure the widest y tick label as drawn
  const probe = svg.append('text').text(yTicksText.reduce((a, b) => (a.length >= b.length ? a : b), ''));
  const left = Math.ceil(probe.node().getComputedTextLength() || 40) + 10; probe.remove();
  const m = {top: 8, right: opts.right ?? 14, bottom: opts.bottom ?? 22, left};
  return {svg, width, height, m, iw: width - m.left - m.right, ih: height - m.top - m.bottom};
}
function yAxis(f, y, fmt, n = 5) {
  const ticks = y.ticks(n);
  const g = f.svg.append('g');
  g.selectAll('line').data(ticks).join('line').attr('x1', f.m.left).attr('x2', f.width - f.m.right).attr('y1', (d) => y(d)).attr('y2', (d) => y(d)).style('stroke', (d) => (d === 0 ? AXIS : GRID)).style('stroke-width', 1);
  g.selectAll('text').data(ticks).join('text').attr('x', f.m.left - 6).attr('y', (d) => y(d)).attr('dy', '0.32em').attr('text-anchor', 'end').text(fmt);
}
function xTimeAxis(f, x) {
  const n = Math.max(2, Math.floor(f.iw / 70));
  f.svg.append('g').selectAll('text').data(x.ticks(n)).join('text').attr('x', (d) => x(d)).attr('y', f.height - 6).attr('text-anchor', 'middle').text(d3.utcFormat('%Y'));
}

/* ---------- time-series line chart with crosshair ---------- */
function lineChart(host, o) {
  host.replaceChildren();
  if (o.series.length > 1) legend(host, o.series);
  const all = o.series.flatMap((s) => s.values).filter(isFinite);
  let [lo, hi] = d3.extent(all); if (o.zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  const y0 = d3.scaleLinear().domain([lo, hi]).nice(5);
  const f = frame(host, o.height || 300, y0.ticks(5).map(o.fmt), {label: o.label});
  const x = d3.scaleUtc().domain(d3.extent(o.dates)).range([f.m.left, f.width - f.m.right]);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  if (o.shadeFrom) {
    const x0 = x(o.shadeFrom);
    f.svg.append('rect').attr('x', x0).attr('y', f.m.top).attr('width', f.width - f.m.right - x0).attr('height', f.ih).style('fill', MUTED).style('opacity', 0.13);
    if (o.shadeLabel) f.svg.append('text').attr('x', x0 - 4).attr('y', f.m.top + 10).attr('text-anchor', 'end').text('out-of-sample →');
  }
  yAxis(f, y, o.fmt); xTimeAxis(f, x);
  o.series.forEach((s) => {
    const line = d3.line().defined((d) => isFinite(d)).x((d, i) => x(o.dates[i])).y((d) => y(d));
    if (o.area) {
      const area = d3.area().defined((d) => isFinite(d)).x((d, i) => x(o.dates[i])).y0(y(0)).y1((d) => y(d));
      f.svg.append('path').attr('d', area(s.values)).style('fill', s.color).style('opacity', 0.18).style('stroke', 'none');
    }
    f.svg.append('path').attr('d', line(s.values)).style('fill', 'none').style('stroke', s.color).style('stroke-width', s.width || 1.6).style('stroke-dasharray', s.dashed ? '4 3' : null).style('stroke-linejoin', 'round');
  });
  const cross = f.svg.append('line').attr('y1', f.m.top).attr('y2', f.height - f.m.bottom).style('stroke', REF).style('stroke-width', 1).style('display', 'none');
  const t = tip(host), bis = d3.bisector((d) => d).center;
  f.svg.append('rect').attr('x', f.m.left).attr('y', f.m.top).attr('width', f.iw).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev) => {
      const [px] = d3.pointer(ev, f.svg.node());
      const i = bis(o.dates, x.invert(px)); const sx = x(o.dates[i]) * (host.clientWidth / f.width);
      cross.attr('x1', x(o.dates[i])).attr('x2', x(o.dates[i])).style('display', null);
      t.show(sx, d3.pointer(ev, host)[1], fDay(o.dates[i]), o.series.map((s) => [s.name, o.fmt(s.values[i])]));
    }).on('pointerleave', () => { cross.style('display', 'none'); t.hide(); });
}

/* ---------- categorical bar chart (vertical), optional two groups ---------- */
function barChart(host, o) {
  host.replaceChildren();
  if (o.groups.length > 1) legend(host, o.groups);
  const vals = o.groups.flatMap((g) => g.values).filter(isFinite);
  const y0 = d3.scaleLinear().domain([Math.min(0, d3.min(vals) ?? 0), Math.max(0, d3.max(vals) ?? 1)]).nice(4);
  const longest = d3.max(o.cats, (c) => String(c).length) || 1;
  const width0 = Math.max(260, host.clientWidth);
  const slot = (width0 - 60) / o.cats.length;
  const rotate = longest * 7.4 > slot;
  const f = frame(host, o.height || 260, y0.ticks(4).map(o.fmt), {label: o.label, bottom: rotate ? Math.min(150, longest * 4.6 + 16) : 22});
  const x = d3.scaleBand().domain(o.cats).range([f.m.left, f.width - f.m.right]).paddingInner(0.25).paddingOuter(0.1);
  const xg = d3.scaleBand().domain(d3.range(o.groups.length)).range([0, x.bandwidth()]).paddingInner(0.08);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  yAxis(f, y, o.fmt, 4);
  const every = Math.max(1, Math.ceil((o.cats.length * 15) / (width0 - 60)));
  const lab = f.svg.append('g').selectAll('text').data(o.cats.filter((d, i) => i % every === 0)).join('text').text((d) => d);
  if (rotate) lab.attr('transform', (d) => `translate(${x(d) + x.bandwidth() / 2 + 4},${f.height - f.m.bottom + 10}) rotate(-38)`).attr('text-anchor', 'end');
  else lab.attr('x', (d) => x(d) + x.bandwidth() / 2).attr('y', f.height - 6).attr('text-anchor', 'middle');
  const t = tip(host);
  o.groups.forEach((g, gi) => {
    f.svg.append('g').selectAll('rect').data(o.cats).join('rect')
      .attr('x', (d) => x(d) + xg(gi)).attr('width', Math.max(1, xg.bandwidth()))
      .attr('y', (d, i) => (isFinite(g.values[i]) ? Math.min(y(0), y(g.values[i])) : y(0)))
      .attr('height', (d, i) => (isFinite(g.values[i]) ? Math.max(0.5, Math.abs(y(g.values[i]) - y(0))) : 0))
      .attr('rx', Math.min(3, xg.bandwidth() / 3))
      .style('fill', (d, i) => (g.signed ? (g.values[i] >= 0 ? OK : BAD) : g.color)).style('opacity', g.opacity ?? 1);
  });
  f.svg.append('g').selectAll('rect').data(o.cats).join('rect').attr('x', (d) => x(d)).attr('width', x.bandwidth()).attr('y', f.m.top).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev, d) => { const i = o.cats.indexOf(d); const p = d3.pointer(ev, host); t.show(p[0], p[1], o.tipTitle ? o.tipTitle(d, i) : String(d), o.groups.map((g) => [g.name, o.fmt(g.values[i])]).concat(o.extra ? o.extra(i) : [])); })
    .on('pointerleave', () => t.hide());
}

/* ---------- scatter ---------- */
function scatter(host, o) {
  host.replaceChildren();
  legend(host, o.groups.map((g) => ({name: g.name, color: g.color})));
  const xs = d3.scaleLinear().domain(o.xdom), ys0 = d3.scaleLinear().domain(o.ydom);
  const f = frame(host, 300, ys0.ticks(5).map(o.fmt), {label: o.label, bottom: 34});
  const x = xs.range([f.m.left, f.width - f.m.right]).clamp(true), y = ys0.range([f.height - f.m.bottom, f.m.top]).clamp(true);
  yAxis(f, y, o.fmt);
  const n = Math.max(2, Math.floor(f.iw / 80));
  f.svg.append('g').selectAll('text').data(x.ticks(n)).join('text').attr('x', (d) => x(d)).attr('y', f.height - f.m.bottom + 14).attr('text-anchor', 'middle').text(o.fmt);
  f.svg.append('text').attr('x', f.m.left + f.iw / 2).attr('y', f.height - 2).attr('text-anchor', 'middle').text(o.xlabel);
  const pts = o.groups.flatMap((g) => g.points.map((p) => ({...p, color: g.color, group: g.name})));
  f.svg.append('g').selectAll('circle').data(pts).join('circle').attr('cx', (d) => x(d.x)).attr('cy', (d) => y(d.y)).attr('r', 2.6).style('fill', (d) => d.color).style('opacity', 0.45);
  const del = d3.Delaunay.from(pts, (d) => x(d.x), (d) => y(d.y));
  const ring = f.svg.append('circle').attr('r', 5).style('fill', 'none').style('stroke', 'var(--color-fg)').style('stroke-width', 1.5).style('display', 'none');
  const t = tip(host);
  f.svg.append('rect').attr('x', f.m.left).attr('y', f.m.top).attr('width', f.iw).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, f.svg.node()); const d = pts[del.find(px, py)]; if (!d) return; ring.attr('cx', x(d.x)).attr('cy', y(d.y)).style('display', null); const p = d3.pointer(ev, host); t.show(p[0], p[1], fDay(parseDay(d.date)) + ', ' + d.side + ', ' + d.group, [[o.xlabel, o.fmt(d.x)], ['Result', o.fmt(d.y)], ['Minutes held', fNum(d.minutes, 0)]]); })
    .on('pointerleave', () => { ring.style('display', 'none'); t.hide(); });
}

/* ---------- small helpers for tables ---------- */
function td(tr, text, cls) { const c = el('td', cls ? {class: cls} : null, text); tr.append(c); return c; }
function fillTable(tbody, list, make) {
  tbody.replaceChildren();
  list.forEach((r) => { const tr = el('tr'); make(tr, r); tbody.append(tr); });
}


/* ---------- horizontal bars around a reference value ---------- */
function hbar(host, o) {
  host.replaceChildren();
  const width = Math.max(260, host.clientWidth), rowH = 22, h = o.rows.length * rowH + 30;
  const svg = d3.select(host).append('svg').attr('viewBox', `0 0 ${width} ${h}`).attr('height', h).attr('role', 'img').attr('aria-label', o.label);
  const CW = 6.6, left = Math.min(width * 0.5, d3.max(o.rows, (r) => r.name.length) * CW + 14);
  const x = d3.scaleLinear().domain(o.domain).range([left, width - 44]);
  const ticks = x.ticks(5);
  svg.append('g').selectAll('line').data(ticks).join('line').attr('x1', (d) => x(d)).attr('x2', (d) => x(d)).attr('y1', 0).attr('y2', h - 22).style('stroke', (d) => (d === o.ref ? AXIS : GRID));
  svg.append('g').selectAll('text').data(ticks).join('text').attr('x', (d) => x(d)).attr('y', h - 6).attr('text-anchor', 'middle').text(o.fmt);
  const t = tip(host);
  const g = svg.append('g').selectAll('g').data(o.rows).join('g').attr('transform', (d, i) => `translate(0,${i * rowH})`);
  g.append('text').attr('x', left - 8).attr('y', rowH / 2).attr('dy', '0.32em').attr('text-anchor', 'end').text((d) => (d.name.length * CW + 10 > left ? d.name.slice(0, Math.floor((left - 10) / CW) - 1) + '…' : d.name));
  g.append('rect').attr('x', (d) => Math.min(x(o.ref), x(d.value))).attr('width', (d) => Math.max(1, Math.abs(x(d.value) - x(o.ref)))).attr('y', 4).attr('height', rowH - 8).attr('rx', 3).style('fill', (d) => d.color);
  g.filter((d) => isFinite(d.lo)).append('line').attr('x1', (d) => x(d.lo)).attr('x2', (d) => x(d.hi)).attr('y1', rowH / 2).attr('y2', rowH / 2).style('stroke', 'var(--color-fg)').style('stroke-width', 1.2);
  g.append('text').attr('x', width - 40).attr('y', rowH / 2).attr('dy', '0.32em').text((d) => o.fmt(d.value));
  g.append('rect').attr('x', 0).attr('width', width).attr('y', 0).attr('height', rowH).style('fill', 'transparent')
    .on('pointermove', (ev, d) => { const p = d3.pointer(ev, host); t.show(p[0], p[1], d.name, d.tip); }).on('pointerleave', () => t.hide());
}
const sel = (id, dflt) => document.querySelector(id)?.value || dflt;
const SAMPLE = {dev: 'test years', wf: 'walk-forward'};
const MODEL_ORDER = ['none', 'cnn', 'mlp', 'boosted', 'logistic'];
const MODEL_NAME = {none: 'Unfiltered', cnn: 'Convolutional network (primary)', mlp: 'Neural network on the table', boosted: 'Boosted trees', logistic: 'Logistic regression'};
const MODEL_COLOR = {none: MUTED, cnn: C[0], mlp: C[3] || C[0], boosted: C[1], logistic: C[2]};

/* ================= takeaway ================= */
function one(ds, keycol, key, col) { const r = rows(ds)?.find((d) => d[keycol] === key); return r ? r[col] : undefined; }
dash.draw('t-skip', (e) => { const v = num(one('models', 'key', 'cnn', 'dev_skipped_avg')); e.textContent = isFinite(v) ? fUsd(v, 2) : '—'; });
dash.draw('t-base', (e) => { const v = num(one('models', 'key', 'cnn', 'dev_total_unfiltered')); e.textContent = isFinite(v) ? fUsd(v) : '—'; });
dash.draw('t-filt', (e) => { const v = num(one('models', 'key', 'cnn', 'dev_total_filtered')); e.textContent = isFinite(v) ? fUsd(v) : '—'; });
dash.draw('t-log-t', (e) => { const v = num(one('models', 'key', 'logistic', 'dev_diff_t')); e.textContent = isFinite(v) ? fNum(v, 2) : '—'; });
dash.draw('t-cnn-n', (e) => { const v = one('criteria', 'id', 'cnn|all', 'evidence'); e.textContent = v ? v.replace(' passed', '') : '—'; });
dash.draw('t-log-n', (e) => { const v = one('criteria', 'id', 'logistic|all', 'evidence'); e.textContent = v ? v.replace(' passed', '') : '—'; });

/* ================= verdict ================= */
dash.draw('verdict-tiles', (host) => {
  const c = rows('criteria'); if (!c) return dash0(host);
  host.replaceChildren();
  ['cnn', 'mlp', 'boosted', 'logistic'].forEach((k) => {
    const r = c.find((d) => d.id === k + '|all'); if (!r) return;
    const t = el('div', {class: 'nq-tile'});
    t.append(el('span', {class: 'nq-lab'}, r.model), el('span', {class: 'nq-val ' + (r.result === 'ADOPT' ? 'nq-pos' : 'nq-neg'), 'data-source': 'criteria', 'data-field': 'result', 'data-where': 'id=' + r.id}, r.result === 'ADOPT' ? 'Meets all six' : 'Rejected'),
      el('span', {class: 'nq-sub', 'data-source': 'criteria', 'data-field': 'evidence', 'data-where': 'id=' + r.id}, r.evidence), el('span', {class: 'nq-sub'}, k === 'cnn' ? 'the model the hypothesis is about' : 'comparison model'));
    host.append(t);
  });
});
dash.draw('crit-body', (tb) => {
  const c = rows('criteria'); if (!c) return tb.replaceChildren();
  const k = sel('#crit-model', 'cnn');
  fillTable(tb, c.filter((r) => r.key === k), (tr, r) => { tr.setAttribute('data-key', r.id); td(tr, r.criterion); td(tr, r.result, 'nq-l ' + (r.result === 'PASS' || r.result === 'ADOPT' ? 'nq-pass' : 'nq-fail')); td(tr, r.evidence, 'nq-wrap'); });
});

/* ================= winners and losers ================= */
dash.draw('wl-chart', (host) => {
  const w = rows('winlose'); if (!w) return dash0(host);
  const pre = w.filter((r) => r.kind === 'Known at entry').slice(0, 12), post = w.filter((r) => r.kind !== 'Known at entry');
  const list = post.concat(pre).map((r) => ({name: r.feature + (r.kind === 'Known at entry' ? '' : ' (after entry)'), value: num(r.auc), lo: num(r.auc_lo), hi: num(r.auc_hi), color: r.kind === 'Known at entry' ? C[0] : C[1],
    tip: [['AUC', fNum(num(r.auc), 3)], ['95% interval', fNum(num(r.auc_lo), 3) + ' to ' + fNum(num(r.auc_hi), 3)], ['Winners, mean', fNum(num(r.winners_mean), 3)], ['Losers, mean', fNum(num(r.losers_mean), 3)]]}));
  hbar(host, {rows: list, ref: 0.5, domain: [0.4, 0.9], fmt: (v) => fNum(v, 2), label: 'How well each feature alone separates winners from losers'});
  const l = el('div', {class: 'nq-legend'}); [['Known only after entry', C[1]], ['Known at entry, twelve strongest', C[0]]].forEach(([n, c]) => { const s = el('span'); const i = el('i'); i.style.background = c; s.append(i, document.createTextNode(n)); l.append(s); }); host.prepend(l);
});
dash.draw('wl-body', (tb) => {
  const w = rows('winlose'); if (!w) return tb.replaceChildren();
  fillTable(tb, w, (tr, r) => { td(tr, r.feature); td(tr, r.kind, 'nq-l'); td(tr, fNum(num(r.winners_mean), 3)); td(tr, fNum(num(r.losers_mean), 3)); td(tr, fNum(num(r.std_diff), 2)); td(tr, fNum(num(r.auc), 3)); td(tr, fNum(num(r.auc_lo), 3)); td(tr, fNum(num(r.auc_hi), 3)); });
});

/* ================= models ================= */
dash.draw('models-body', (tb) => {
  const m = rows('models'); if (!m) return tb.replaceChildren();
  const p = sel('#model-period', 'dev');
  const order = ['cnn', 'mlp', 'boosted', 'logistic'];
  fillTable(tb, order.map((k) => m.find((r) => r.key === k)).filter(Boolean), (tr, r) => {
    const g = (c) => num(r[p + '_' + c]);
    td(tr, r.model); td(tr, fNum(g('auc'), 3)); td(tr, fNum(g('auc_lo'), 3) + ' to ' + fNum(g('auc_hi'), 3)); td(tr, fPct(g('skipped_share')));
    td(tr, fUsd(g('kept_avg'), 2), signClass(g('kept_avg'))); td(tr, fUsd(g('skipped_avg'), 2), signClass(g('skipped_avg'))); td(tr, fNum(g('diff_t'), 2));
    td(tr, fUsd(g('total_unfiltered'))); td(tr, fUsd(g('total_filtered')), signClass(g('total_filtered') - g('total_unfiltered'))); td(tr, fNum(g('sharpe_unfiltered'), 2)); td(tr, fNum(g('sharpe_filtered'), 2));
    td(tr, fPct(g('random_pctile'), 0)); td(tr, fUsd(g('dd_unfiltered'))); td(tr, fUsd(g('dd_filtered'))); td(tr, fPct(g('winners_kept'))); td(tr, fPct(g('losers_skipped')));
  });
});
dash.draw('fifths', (host) => {
  const s = rows('score_fifths'); if (!s) return dash0(host);
  const k = sel('#fifth-model', 'cnn');
  const pick = (p) => s.filter((r) => r.key === k && r.period === p).sort((a, b) => num(a.order) - num(b.order));
  const dv = pick('dev'), wf = pick('wf');
  barChart(host, {cats: dv.map((r) => r.fifth), groups: [{name: 'Test years 2016 to Oct 2024', color: C[0], values: dv.map((r) => num(r.avg_usd))}, {name: 'Walk-forward year', color: C[1], values: wf.map((r) => num(r.avg_usd))}], fmt: (v) => fUsd(v, Math.abs(v) < 100 ? 2 : 0), height: 280, label: 'Average result per trade by fifth of model score',
    extra: (i) => [['Winners, test years', fPct(num(dv[i].win_rate))], ['Winners, walk-forward', fPct(num(wf[i]?.win_rate))], ['Trades, test years', fNum(num(dv[i].n), 0)]]});
});
dash.draw('weights', (host) => {
  const w = rows('logistic_weights'); if (!w) return dash0(host);
  const list = w.slice(0, 14).map((r) => ({name: r.feature, value: num(r.weight), color: num(r.weight) >= 0 ? OK : BAD, tip: [['Weight', fNum(num(r.weight), 3)]]}));
  const mx = d3.max(list, (r) => Math.abs(r.value)) || 1;
  hbar(host, {rows: list, ref: 0, domain: [-mx * 1.1, mx * 1.1], fmt: (v) => fNum(v, 2), label: 'Largest logistic regression weights'});
});

/* ================= P&L ================= */
function dailyCols() { const d = rows('daily'); if (!d) return null; return {d, dates: d.map((r) => parseDay(r.date))}; }
dash.draw('equity', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  const pre = sel('#eq-cost', '1') === '2' ? 'equity2x_' : 'equity_';
  lineChart(host, {dates: g.dates, series: MODEL_ORDER.map((k) => ({name: MODEL_NAME[k], color: MODEL_COLOR[k], values: g.d.map((r) => num(r[pre + k])), width: k === 'none' ? 2.2 : 1.5, dashed: k === 'none'})), fmt: fK, zero: true, height: 340, shadeLabel: true, shadeFrom: parseDay(WF_START), label: 'Cumulative profit of one set, unfiltered and with each filter'});
});
dash.draw('drawdown', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  lineChart(host, {dates: g.dates, series: ['none', 'cnn', 'logistic'].map((k) => ({name: MODEL_NAME[k], color: MODEL_COLOR[k], values: g.d.map((r) => num(r['drawdown_' + k])), dashed: k === 'none'})), fmt: fK, zero: true, height: 200, shadeFrom: parseDay(WF_START), label: 'Drawdown, unfiltered and filtered'});
});
dash.draw('yearly-body', (tb) => {
  const y = rows('yearly'); if (!y) return tb.replaceChildren();
  fillTable(tb, y, (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.year); td(tr, r.period === 'dev' ? 'test year' : 'walk-forward', 'nq-l'); td(tr, fNum(num(r.days), 0)); td(tr, fNum(num(r.trades), 0));
    ['none', 'cnn', 'mlp', 'boosted', 'logistic'].forEach((k) => td(tr, fUsd(num(r['pnl_' + k])), signClass(num(r['pnl_' + k]))));
    td(tr, fNum(num(r.auc_cnn), 3)); td(tr, fNum(num(r.auc_boosted), 3));
  });
});
dash.draw('kpi-body', (tb) => {
  const k = rows('kpis'); if (!k) return tb.replaceChildren();
  tb.replaceChildren(); let grp = null;
  k.forEach((r) => {
    if (r.group !== grp) { grp = r.group; const g = el('tr', {class: 'nq-group'}); g.append(el('td', {colspan: 7}, grp)); tb.append(g); }
    const tr = el('tr'); td(tr, r.metric);
    ['dev_base', 'dev_filter', 'dev_base_2x', 'dev_filter_2x', 'wf_base', 'wf_filter'].forEach((c) => td(tr, byUnit(num(r[c]), r.unit, r.metric)));
    tb.append(tr);
  });
});
dash.draw('hist', (host) => {
  const h = rows('histograms'); if (!h) return dash0(host);
  const p = sel('#hist-period', 'dev');
  const a = h.filter((r) => r.period === p && r.variant === 'Unfiltered'), b = h.filter((r) => r.period === p && r.variant !== 'Unfiltered');
  barChart(host, {cats: a.map((r) => fUsd(num(r.lo))), groups: [{name: 'Unfiltered', color: MUTED, values: a.map((r) => num(r.share))}, {name: 'Convolutional network filter', color: C[0], values: b.map((r) => num(r.share))}], fmt: (v) => fPct(v, 0), height: 300, label: 'Distribution of the daily result',
    tipTitle: (d, i) => fUsd(num(a[i].lo)) + ' to ' + fUsd(num(a[i].hi)), extra: (i) => [['Days, unfiltered', fNum(num(a[i].count), 0)], ['Days, filtered', fNum(num(b[i]?.count), 0)]]});
});

/* ================= kept and skipped ================= */
let bdDim = 'Winners and losers';
const GROUPS = ['Kept, test years', 'Skipped, test years', 'Kept, walk-forward', 'Skipped, walk-forward'];
dash.draw('bd-dim', (s) => {
  const b = rows('breakdowns'); const dims = b ? Array.from(new Set(b.map((r) => r.dimension))) : [];
  s.replaceChildren(...dims.map((d) => new Option(d))); if (dims.includes(bdDim)) s.value = bdDim;
  s.onchange = () => { bdDim = s.value; dash.draw('bd-chart'); dash.draw('bd-body'); };
});
function bdRows() { const b = rows('breakdowns'); if (!b) return null; return b.filter((r) => r.dimension === bdDim).sort((a, c) => num(a.order) - num(c.order)); }
dash.draw('bd-chart', (host) => {
  const b = bdRows(); if (!b) return dash0(host);
  const cats = Array.from(new Set(b.map((r) => r.bucket)));
  const pick = (g, c) => cats.map((k) => { const r = b.find((d) => d.bucket === k && d.group === g); return r ? num(r[c]) : NaN; });
  barChart(host, {cats, groups: [{name: 'Kept, test years', color: C[0], values: pick(GROUPS[0], 'avg_usd')}, {name: 'Skipped, test years', color: C[1], values: pick(GROUPS[1], 'avg_usd')}], fmt: (v) => fUsd(v, Math.abs(v) < 100 ? 2 : 0), height: 300, label: 'Average result of kept and skipped trades by ' + bdDim,
    extra: (i) => [['Kept, count', fNum(pick(GROUPS[0], 'n')[i], 0)], ['Skipped, count', fNum(pick(GROUPS[1], 'n')[i], 0)]]});
});
dash.draw('bd-body', (tb) => {
  const b = bdRows(); if (!b) return tb.replaceChildren();
  fillTable(tb, b.slice().sort((a, c) => GROUPS.indexOf(a.group) - GROUPS.indexOf(c.group) || num(a.order) - num(c.order)), (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.bucket); td(tr, r.group, 'nq-l'); td(tr, fNum(num(r.n), 0)); td(tr, fPct(num(r.win_rate))); td(tr, fUsd(num(r.avg_usd), 2), signClass(num(r.avg_usd))); td(tr, fUsd(num(r.total_usd)), signClass(num(r.total_usd))); td(tr, fNum(num(r.profit_factor), 2)); td(tr, fNum(num(r.t), 2));
  });
});

/* ================= Monte Carlo ================= */
const mcSel = () => ({account: sel('#mc-account', '50K'), source: sel('#mc-source', 'Test years 2016 to Oct 2024 (out-of-fold)')});
function mcAll() { const m = rows('montecarlo'); if (!m) return null; const s = mcSel(); return m.filter((r) => r.account === s.account && r.days_from === s.source); }
dash.draw('mc-variants-body', (tb) => {
  const m = mcAll(); if (!m) return tb.replaceChildren();
  fillTable(tb, MODEL_ORDER.map((k) => m.find((r) => r.key === k && +r.base === 1)).filter(Boolean), (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.variant); td(tr, r.contracts); td(tr, fPct(num(r.pass))); td(tr, fPct(num(r.pass_30d))); td(tr, fPct(num(r.control_pass_30d))); td(tr, fPct(num(r.breach))); td(tr, fNum(num(r.median_days_to_pass), 0));
    td(tr, fPct(num(r.payout_rate_standard))); td(tr, fPct(num(r.payout_rate_consistency))); td(tr, fUsd(num(r.fees_per_account)));
    td(tr, fSigned(num(r.profit_per_account)), signClass(num(r.profit_per_account))); td(tr, fSigned(num(r.profit_per_account_30d)), signClass(num(r.profit_per_account_30d))); td(tr, fNum(num(r.ben_score), 3));
  });
});
function mcCurve(name, col, label) {
  dash.draw(name, (host) => {
    const m = mcAll(); if (!m) return dash0(host);
    host.replaceChildren();
    const keys = ['none', 'cnn', 'boosted'];
    const series = keys.map((k) => ({name: MODEL_NAME[k], color: MODEL_COLOR[k], dashed: k === 'none', pts: m.filter((r) => r.key === k).sort((a, b) => num(a.contracts) - num(b.contracts))}));
    legend(host, series);
    const xs = series[0].pts.map((r) => num(r.contracts));
    const y0 = d3.scaleLinear().domain([0, d3.max(series.flatMap((s) => s.pts.map((r) => num(r[col])))) || 1]).nice(5);
    const fmt = (v) => fPct(v, 0);
    const f = frame(host, 280, y0.ticks(5).map(fmt), {label, bottom: 34});
    const x = d3.scalePoint().domain(xs).range([f.m.left + 14, f.width - f.m.right - 14]);
    const y = y0.range([f.height - f.m.bottom, f.m.top]);
    yAxis(f, y, fmt);
    f.svg.append('g').selectAll('text').data(xs).join('text').attr('x', (d) => x(d)).attr('y', f.height - f.m.bottom + 14).attr('text-anchor', 'middle').text((d) => d);
    f.svg.append('text').attr('x', f.m.left + f.iw / 2).attr('y', f.height - 2).attr('text-anchor', 'middle').text('MNQ when every setting is in');
    series.forEach((s) => {
      f.svg.append('path').attr('d', d3.line().x((r) => x(num(r.contracts))).y((r) => y(num(r[col])))(s.pts)).style('fill', 'none').style('stroke', s.color).style('stroke-width', 2).style('stroke-dasharray', s.dashed ? '4 3' : null);
      f.svg.append('g').selectAll('circle').data(s.pts).join('circle').attr('cx', (r) => x(num(r.contracts))).attr('cy', (r) => y(num(r[col]))).attr('r', 3.5).style('fill', s.color).style('stroke', 'var(--color-bg)').style('stroke-width', 1.5);
    });
    const t = tip(host);
    f.svg.append('g').selectAll('rect').data(xs).join('rect').attr('x', (d) => x(d) - x.step() / 2).attr('width', x.step()).attr('y', f.m.top).attr('height', f.ih).style('fill', 'transparent')
      .on('pointermove', (ev, d) => { const p = d3.pointer(ev, host); t.show(p[0], p[1], d + ' MNQ', series.map((s) => { const r = s.pts.find((q) => num(q.contracts) === d); return [s.name, r ? fPct(num(r[col])) : '—']; })); })
      .on('pointerleave', () => t.hide());
  });
}
mcCurve('mc-pass', 'pass', 'Pass rate with no time limit by size');
mcCurve('mc-pass30', 'pass_30d', 'Pass rate within 30 trading days by size');

/* ================= controls ================= */
const on = (q, names) => document.querySelectorAll(q).forEach((s) => s.addEventListener('change', () => names.forEach((n) => dash.draw(n))));
on('#crit-model', ['crit-body']); on('#model-period', ['models-body']); on('#fifth-model', ['fifths']); on('#eq-cost', ['equity']); on('#hist-period', ['hist']);
on('#mc-account, #mc-source', ['mc-variants-body', 'mc-pass', 'mc-pass30']);
