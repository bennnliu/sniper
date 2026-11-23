/* Drawings for the volatility and contract size dashboard. Every number comes from a dataset. */
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


const sel = (id, dflt) => document.querySelector(id)?.value || dflt;
const T0 = 'Test years 2016 to Oct 2024';
const ENV = [['low', 'Low volatility'], ['mid', 'Middle volatility'], ['high', 'High volatility'], ['all', 'All days']];
const ENV_COLOR = {low: C[0], mid: C[2], high: C[1], all: MUTED};
const VARN = {logit: 'Logistic filter', none: 'Unfiltered'};
const SAMPLE = {dev: 'test years', wf: 'walk-forward'};

/* ---------- lines over a numeric x ---------- */
function xyChart(host, o) {
  host.replaceChildren();
  legend(host, o.series);
  const pts = o.series.flatMap((s) => s.pts);
  if (!pts.length) return dash0(host);
  let [ylo, yhi] = d3.extent(pts, (p) => p.y); ylo = Math.min(0, ylo); yhi = Math.max(0, yhi);
  const y0 = d3.scaleLinear().domain([ylo, yhi || 1]).nice(5);
  const f = frame(host, o.height || 270, y0.ticks(5).map(o.fmt), {label: o.label, bottom: 34});
  const xd = d3.extent(pts, (p) => p.x);
  const x = (o.log ? d3.scaleLog() : d3.scaleLinear()).domain(xd).range([f.m.left + 8, f.width - f.m.right - 10]);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  yAxis(f, y, o.fmt);
  const xt = o.xticks || x.ticks(Math.max(2, Math.floor(f.iw / 70)));
  f.svg.append('g').selectAll('text').data(xt.filter((d, i) => !o.xticks || f.iw / xt.length > 26 || i % 2 === 0)).join('text').attr('x', (d) => x(d)).attr('y', f.height - f.m.bottom + 14).attr('text-anchor', 'middle').text(o.xfmt || ((d) => d));
  f.svg.append('text').attr('x', f.m.left + f.iw / 2).attr('y', f.height - 2).attr('text-anchor', 'middle').text(o.xlabel);
  o.series.forEach((s) => {
    const p = s.pts.slice().sort((a, b) => a.x - b.x);
    f.svg.append('path').attr('d', d3.line().x((d) => x(d.x)).y((d) => y(d.y))(p)).style('fill', 'none').style('stroke', s.color).style('stroke-width', s.width || 2).style('stroke-dasharray', s.dashed ? '4 3' : null);
    f.svg.append('g').selectAll('circle').data(p).join('circle').attr('cx', (d) => x(d.x)).attr('cy', (d) => y(d.y)).attr('r', 3).style('fill', s.color).style('stroke', 'var(--color-bg)').style('stroke-width', 1.2);
  });
  const all = o.series.flatMap((s) => s.pts.map((p) => ({...p, name: s.name})));
  const del = d3.Delaunay.from(all, (d) => x(d.x), (d) => y(d.y));
  const ring = f.svg.append('circle').attr('r', 6).style('fill', 'none').style('stroke', 'var(--color-fg)').style('stroke-width', 1.5).style('display', 'none');
  const t = tip(host);
  f.svg.append('rect').attr('x', f.m.left).attr('y', f.m.top).attr('width', f.iw).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, f.svg.node()); const d = all[del.find(px, py)]; if (!d) return; ring.attr('cx', x(d.x)).attr('cy', y(d.y)).style('display', null); const p = d3.pointer(ev, host); t.show(p[0], p[1], d.name, [[o.xlabel, (o.xtip || o.xfmt || String)(d.x)], [o.ylabel, o.fmt(d.y)]].concat(d.extra || [])); })
    .on('pointerleave', () => { ring.style('display', 'none'); t.hide(); });
}

/* ================= takeaway ================= */
function envRow(src, v, e) { return rows('environments')?.find((r) => r.source === src && r.variant_key === v && r.env_key === e); }
function mark(e, ds, field, where, text) { e.setAttribute('data-source', ds); e.setAttribute('data-field', field); e.setAttribute('data-where', where); e.textContent = text; }
dash.draw('t-std-low', (e) => { const r = envRow(T0, 'logit', 'low'); r ? mark(e, 'environments', 'std_day', 'id=' + r.id, fUsd(num(r.std_day))) : (e.textContent = '—'); });
dash.draw('t-std-high', (e) => { const r = envRow(T0, 'logit', 'high'); r ? mark(e, 'environments', 'std_day', 'id=' + r.id, fUsd(num(r.std_day))) : (e.textContent = '—'); });
function chosen(key) { return rows('policies')?.find((r) => r.account === '50K' && r.source === T0 && r.variant_key === 'logit' && r.policy_key === key && +r.chosen === 1); }
dash.draw('t-risk', (e) => { const r = chosen('risk'); r ? mark(e, 'policies', 'pass_30d', 'id=' + r.id, fPct(num(r.pass_30d))) : (e.textContent = '—'); });
dash.draw('t-fixed', (e) => { const r = chosen('fixed'); r ? mark(e, 'policies', 'pass_30d', 'id=' + r.id, fPct(num(r.pass_30d))) : (e.textContent = '—'); });
dash.draw('t-slope', (e) => { const r = rows('facts')?.find((d) => d.variant_key === 'logit'); e.textContent = r ? fNum(Math.pow(2, num(r.loglog_slope)), 2) : '—'; if (r) { e.setAttribute('data-source', 'facts'); } });

/* ================= verdicts ================= */
const good = (r) => r === 'SUPPORTED' || r === 'PASS';
const SHORT = {'SUPPORTED': 'Supported', 'PARTLY SUPPORTED': 'Partly supported', 'NOT SUPPORTED': 'Not supported', 'PASS': 'Passed', 'FAIL': 'Failed'};
dash.draw('verdict-tiles', (host) => {
  const v = rows('verdicts'); if (!v) return dash0(host);
  host.replaceChildren();
  v.forEach((r) => { const t = el('div', {class: 'nq-tile'}); t.append(el('span', {class: 'nq-lab'}, r.name), el('span', {class: 'nq-val ' + (good(r.result) ? 'nq-pos' : r.result.startsWith('PARTLY') ? '' : 'nq-neg'), 'data-source': 'verdicts', 'data-field': 'result', 'data-where': 'id=' + r.id}, SHORT[r.result] || r.result)); host.append(t); });
});
dash.draw('verdict-body', (tb) => {
  const v = rows('verdicts'); if (!v) return tb.replaceChildren();
  fillTable(tb, v, (tr, r) => { tr.setAttribute('data-key', r.id); td(tr, r.name); td(tr, r.result, 'nq-l ' + (good(r.result) ? 'nq-pass' : r.result.startsWith('PARTLY') ? '' : 'nq-fail')); td(tr, r.evidence, 'nq-wrap'); });
});

/* ================= environments ================= */
function envBars(name, col, fmt, label) {
  dash.draw(name, (host) => {
    const e = rows('environments'); if (!e) return dash0(host);
    const src = sel('#env-source', T0);
    const pick = (v) => ENV.map(([k]) => { const r = e.find((d) => d.source === src && d.variant_key === v && d.env_key === k); return r ? num(r[col]) : NaN; });
    barChart(host, {cats: ENV.map((d) => d[1]), groups: [{name: 'Unfiltered', color: MUTED, values: pick('none')}, {name: 'Logistic filter', color: C[0], values: pick('logit')}], fmt, height: 240, label});
  });
}
envBars('env-std', 'std_day', (v) => fUsd(v), 'Daily swing of one set by environment');
envBars('env-mean', 'per_day', (v) => fUsd(v), 'Average profit per day by environment');
envBars('env-sharpe', 'sharpe', (v) => fNum(v, 2), 'Sharpe ratio by environment');
envBars('env-mnq', 'mnq_for_500_std', (v) => fNum(v, 1), 'MNQ for a $500 daily swing by environment');
dash.draw('env-body', (tb) => {
  const e = rows('environments'); if (!e) return tb.replaceChildren();
  const src = sel('#env-source', T0); const list = [];
  ENV.forEach(([k]) => ['none', 'logit'].forEach((v) => { const r = e.find((d) => d.source === src && d.variant_key === v && d.env_key === k); if (r) list.push(r); }));
  fillTable(tb, list, (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.env); td(tr, r.variant, 'nq-l'); td(tr, fNum(g('days'), 0)); td(tr, fNum(g('trades'), 0)); td(tr, fUsd(g('exp_move_set_usd'))); td(tr, fUsd(g('total')), signClass(g('total'))); td(tr, fUsd(g('per_day'), 2), signClass(g('per_day')));
    td(tr, fUsd(g('std_day'))); td(tr, fNum(g('std_over_exp'), 2)); td(tr, fNum(g('sharpe'), 2)); td(tr, fNum(g('t'), 2)); td(tr, fPct(g('win_days'))); td(tr, fUsd(g('per_trade'), 2), signClass(g('per_trade'))); td(tr, fPct(g('win_trades')));
    td(tr, fUsd(g('worst_day'))); td(tr, fUsd(g('p05_day'))); td(tr, fUsd(g('worst_open_loss'))); td(tr, fUsd(g('drawdown'))); td(tr, fNum(g('relative_optimal_size'), 2));
  });
});

/* ================= risk against expected move ================= */
function vbChart(name, col, fmt, label, ylabel) {
  dash.draw(name, (host) => {
    const b = rows('volbins'); if (!b) return dash0(host);
    xyChart(host, {series: ['none', 'logit'].map((v) => ({name: VARN[v], color: v === 'none' ? MUTED : C[0], dashed: v === 'none', pts: b.filter((r) => r.variant_key === v).map((r) => ({x: num(r.exp_move_set_usd), y: num(r[col]), extra: [['Days', r.first_day + ' to ' + r.last_day]]}))})),
      fmt, xfmt: fK, xtip: (v) => fUsd(v), xlabel: 'Expected daily move of one set', ylabel, label});
  });
}
vbChart('vb-std', 'std_day', (v) => fUsd(v), 'Daily swing against expected move', 'Daily swing');
vbChart('vb-sharpe', 'sharpe', (v) => fNum(v, 2), 'Sharpe ratio against expected move', 'Sharpe');
dash.draw('vb-body', (tb) => {
  const b = rows('volbins'); if (!b) return tb.replaceChildren();
  fillTable(tb, b.slice().sort((a, c) => num(a.group) - num(c.group) || (a.variant_key < c.variant_key ? 1 : -1)), (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.group); td(tr, r.variant, 'nq-l'); td(tr, fUsd(num(r.exp_lo))); td(tr, fUsd(num(r.exp_hi))); td(tr, r.first_day, 'nq-l'); td(tr, r.last_day, 'nq-l'); td(tr, fUsd(num(r.per_day), 2), signClass(num(r.per_day))); td(tr, fUsd(num(r.std_day))); td(tr, fNum(num(r.sharpe), 2)); td(tr, fNum(num(r.mnq_for_500_std), 1));
  });
});

/* ================= P&L ================= */
dash.draw('equity', (host) => {
  const d = rows('daily'); if (!d) return dash0(host);
  const v = sel('#eq-variant', 'logit'); const dates = d.map((r) => parseDay(r.date));
  const s = [['all', 'All days'], ['low', 'Low volatility'], ['mid', 'Middle volatility'], ['high', 'High volatility']].map(([k, n]) => ({name: n, color: k === 'all' ? 'var(--color-fg)' : ENV_COLOR[k], width: k === 'all' ? 2.2 : 1.5, values: d.map((r) => num(r['eq_' + v + '_' + k]))}));
  s.push({name: 'All days, constant risk', color: MUTED, dashed: true, values: d.map((r) => num(r['eq_' + v + '_scaled']))});
  lineChart(host, {dates, series: s, fmt: fK, zero: true, height: 340, shadeLabel: true, shadeFrom: parseDay(WF_START), label: 'Cumulative profit of one set by volatility environment'});
});
dash.draw('expmove', (host) => {
  const d = rows('daily'); if (!d) return dash0(host);
  lineChart(host, {dates: d.map((r) => parseDay(r.date)), series: [{name: 'Expected daily move of one set', color: C[0], values: d.map((r) => num(r.exp_move_set_usd))}], fmt: fK, zero: true, height: 200, shadeFrom: parseDay(WF_START), label: 'Expected daily move of one set over time'});
});

/* ================= sizes inside each environment ================= */
function szRows() { const m = rows('mc_env'); if (!m) return null; const a = sel('#sz-account', '50K'), s = sel('#sz-source', T0), v = sel('#sz-variant', 'logit'); return m.filter((r) => r.account === a && r.source === s && r.variant_key === v); }
function szChart(name, val, label, ylabel) {
  dash.draw(name, (host) => {
    const m = szRows(); if (!m) return dash0(host);
    const xs = Array.from(new Set(m.map((r) => num(r.contracts)))).sort((a, b) => a - b);
    xyChart(host, {series: ENV.map(([k, n]) => ({name: n, color: ENV_COLOR[k], dashed: k === 'all', pts: m.filter((r) => r.env_key === k).map((r) => ({x: num(r.contracts), y: val(r), extra: [['Control within 30 days', fPct(num(r.control_pass_30d))], ['Swing over loss limit', fNum(num(r.std_over_limit), 2)]]}))})),
      fmt: (v) => fPct(v, 0), log: true, xticks: xs, xlabel: 'MNQ when every setting is in', ylabel, label});
  });
}
szChart('sz-pass30', (r) => num(r.pass_30d), 'Pass within 30 trading days by size and environment', 'Pass within 30 days');
szChart('sz-pass', (r) => num(r.pass), 'Pass with no time limit by size and environment', 'Pass, no limit');
szChart('sz-edge', (r) => num(r.pass_30d) - num(r.control_pass_30d), 'Pass rate minus the coin control by size and environment', 'Edge over the coin');
szChart('sz-breach', (r) => num(r.breach), 'Loss limit hit by size and environment', 'Loss limit hit');
dash.draw('best-body', (tb) => {
  const b = rows('best'); if (!b) return tb.replaceChildren();
  const a = sel('#sz-account', '50K'), s = sel('#sz-source', T0), v = sel('#sz-variant', 'logit'); const list = [];
  ['pass_30d', 'pass'].forEach((o) => ENV.forEach(([k]) => { const r = b.find((d) => d.account === a && d.source === s && d.variant_key === v && d.env_key === k && d.objective_key === o); if (r) list.push(r); }));
  fillTable(tb, list, (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.env); td(tr, r.objective, 'nq-l'); td(tr, fNum(g('best_contracts'), 0)); td(tr, fPct(g('pass_30d'))); td(tr, fPct(g('control_pass_30d'))); td(tr, fPct(g('pass'))); td(tr, fPct(g('breach'))); td(tr, fNum(g('median_days_to_pass'), 0)); td(tr, fUsd(g('daily_std_usd'))); td(tr, fNum(g('std_over_limit'), 2));
  });
});
dash.draw('funded-body', (tb) => {
  const f = rows('funded'); if (!f) return tb.replaceChildren();
  const a = sel('#sz-account', '50K'); const list = [];
  ENV.forEach(([k]) => ['none', 'logit'].forEach((v) => { const r = f.find((d) => d.account === a && d.variant_key === v && d.env_key === k); if (r) list.push(r); }));
  fillTable(tb, list, (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.env); td(tr, r.variant, 'nq-l'); td(tr, r.contracts); td(tr, fPct(g('pass'))); td(tr, fPct(g('pass_30d'))); td(tr, fNum(g('median_days_to_pass'), 0)); td(tr, fPct(g('payout_rate_standard'))); td(tr, fPct(g('payout_rate_consistency'))); td(tr, fUsd(g('fees_per_account')));
    td(tr, fSigned(g('profit_per_account')), signClass(g('profit_per_account'))); td(tr, fSigned(g('profit_per_account_30d')), signClass(g('profit_per_account_30d'))); td(tr, fNum(g('ben_score'), 3));
  });
});

/* ================= sizing rules ================= */
const POL = [['fixed', C[0]], ['risk', C[1]], ['fixed_notlow', C[2]], ['fixed_high', C[3] || MUTED], ['risk_high', MUTED]];
function poRows() { const p = rows('policies'); if (!p) return null; const a = sel('#po-account', '50K'), s = sel('#po-source', T0), v = sel('#po-variant', 'logit'); return p.filter((r) => r.account === a && r.source === s && r.variant_key === v); }
function poChart(name, col, label, ylabel) {
  dash.draw(name, (host) => {
    const p = poRows(); if (!p) return dash0(host);
    xyChart(host, {series: POL.map(([k, c]) => { const g = p.filter((r) => r.policy_key === k); return {name: g[0]?.policy || k, color: c, dashed: k === 'risk_high', pts: g.map((r) => ({x: num(r.avg_contracts), y: num(r[col]), extra: [['Setting', r.parameter + ' ' + r.unit], ['Control within 30 days', fPct(num(r.control_pass_30d))]]}))}; }).filter((s) => s.pts.length),
      fmt: (v) => fPct(v, 0), log: true, xfmt: (v) => fNum(v, 0), xtip: (v) => fNum(v, 1), xlabel: 'Average MNQ on traded days', ylabel, label});
  });
}
poChart('po-pass30', 'pass_30d', 'Pass within 30 trading days by sizing rule and average size', 'Pass within 30 days');
poChart('po-pass', 'pass', 'Pass with no time limit by sizing rule and average size', 'Pass, no limit');
dash.draw('po-body', (tb) => {
  const p = poRows(); if (!p) return tb.replaceChildren();
  fillTable(tb, POL.map(([k]) => p.find((r) => r.policy_key === k && +r.chosen === 1)).filter(Boolean), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.policy); td(tr, r.parameter); td(tr, r.unit, 'nq-l'); td(tr, fNum(g('avg_contracts'), 1)); td(tr, fNum(g('min_contracts'), 0)); td(tr, fNum(g('max_contracts'), 0)); td(tr, fPct(g('pass_30d'))); td(tr, fPct(g('control_pass_30d'))); td(tr, fPct(g('pass'))); td(tr, fPct(g('breach_30d'))); td(tr, fNum(g('median_days_to_pass'), 0)); td(tr, fUsd(g('fees_per_pass_30d')));
  });
});

/* ================= filter ================= */
dash.draw('filter-chart', (host) => {
  const f = rows('filter'); if (!f) return dash0(host);
  const d = f.filter((r) => r.period === 'dev');
  const pick = (c) => ENV.map(([k]) => { const r = d.find((q) => q.env_key === k); return r ? num(r[c]) : NaN; });
  barChart(host, {cats: ENV.map((e) => e[1]), groups: [{name: 'Kept trades, test years', color: C[0], values: pick('kept_avg')}, {name: 'Skipped trades, test years', color: C[1], values: pick('skipped_avg')}], fmt: (v) => fUsd(v, 2), height: 260, label: 'Average result of kept and skipped trades by environment',
    extra: (i) => [['t of the difference', fNum(pick('diff_t')[i], 2)]]});
});
dash.draw('filter-body', (tb) => {
  const f = rows('filter'); if (!f) return tb.replaceChildren();
  fillTable(tb, f, (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.env); td(tr, SAMPLE[r.period], 'nq-l'); td(tr, fNum(g('trades'), 0)); td(tr, fPct(g('skipped_share'))); td(tr, fNum(g('auc'), 3)); td(tr, fNum(g('auc_lo'), 3)); td(tr, fNum(g('auc_hi'), 3));
    td(tr, fUsd(g('kept_avg'), 2), signClass(g('kept_avg'))); td(tr, fUsd(g('skipped_avg'), 2), signClass(g('skipped_avg'))); td(tr, fNum(g('diff_t'), 2)); td(tr, fUsd(g('total_unfiltered')), signClass(g('total_unfiltered'))); td(tr, fUsd(g('total_filtered')), signClass(g('total_filtered')));
  });
});

/* ================= controls ================= */
const on = (q, names) => document.querySelectorAll(q).forEach((s) => s.addEventListener('change', () => names.forEach((n) => dash.draw(n))));
on('#env-source', ['env-std', 'env-mean', 'env-sharpe', 'env-mnq', 'env-body']); on('#eq-variant', ['equity']);
on('#sz-account, #sz-source, #sz-variant', ['sz-pass30', 'sz-pass', 'sz-edge', 'sz-breach', 'best-body', 'funded-body']);
on('#po-account, #po-source, #po-variant', ['po-pass30', 'po-pass', 'po-body']);
