/* Drawings for the all-days volatility strategy dashboard. Every number comes from a dataset. */
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
const T0 = 'Test years 2016 to Oct 2024', TW = 'Walk-forward year';
const VK = ['strat', 'noreduce', 'nofilter', 'prev', 'bench', 'raw'];
const VC = {strat: C[0], noreduce: C[1], nofilter: C[2], prev: C[4] || C[1], bench: C[3] || MUTED, raw: MUTED};
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


function mark(e, ds, field, where, text) { e.setAttribute('data-source', ds); e.setAttribute('data-field', field); e.setAttribute('data-where', where); e.textContent = text; }
const sumRow = (k, src) => rows('summary')?.find((r) => r.key === k && r.source === src);
const mcChosen = (k, src, acc = '50K') => rows('montecarlo')?.find((r) => r.key === k && r.days_from === src && r.account === acc && +r.chosen === 1);
function drawSum(name, k, col, fmt) { dash.draw(name, (e) => { const r = sumRow(k, T0); r ? mark(e, 'summary', col, 'id=' + r.id, fmt(num(r[col]))) : (e.textContent = '—'); }); }
drawSum('t-total', 'strat', 'total', (v) => fUsd(v)); drawSum('t-sharpe', 'strat', 'sharpe', (v) => fNum(v, 2)); 
drawSum('t-bench-sharpe', 'bench', 'sharpe', (v) => fNum(v, 2));
dash.draw('t-bench-p30', (e) => { const r = mcChosen('bench', T0); r ? mark(e, 'montecarlo', 'pass_30d', 'id=' + r.id, fPct(num(r.pass_30d))) : (e.textContent = '—'); });
function drawMc(name, src, col) { dash.draw(name, (e) => { const r = mcChosen('strat', src); r ? mark(e, 'montecarlo', col, 'id=' + r.id, fPct(num(r[col]))) : (e.textContent = '—'); }); }
drawMc('t-p30', T0, 'pass_30d'); drawMc('t-p30wf', TW, 'pass_30d'); drawMc('t-c30wf', TW, 'control_pass_30d');
dash.draw('t-crit', (e) => { const r = rows('criteria')?.find((d) => d.id === 'all'); r ? mark(e, 'criteria', 'evidence', 'id=all', r.evidence.replace(' met', '')) : (e.textContent = '—'); });

/* ================= criteria ================= */
dash.draw('crit-body', (tb) => {
  const c = rows('criteria'); if (!c) return tb.replaceChildren();
  fillTable(tb, c, (tr, r) => { tr.setAttribute('data-key', r.id); td(tr, r.criterion); td(tr, r.result, 'nq-l ' + (r.result === 'PASS' ? 'nq-pass' : 'nq-fail')); td(tr, r.evidence, 'nq-wrap'); });
});
dash.draw('caution', (e) => {
  const s = sumRow('strat', TW), m = mcChosen('strat', TW), raw = sumRow('raw', TW);
  if (!s || !m || !raw) { e.textContent = '—'; return; }
  const beat = num(m.pass_30d) > num(m.control_pass_30d);
  e.textContent = 'Walk-forward year, the fairer read: the strategy made ' + fUsd(num(s.total)) + ' per baseline set (Sharpe ' + fNum(num(s.sharpe), 2) + ', t ' + fNum(num(s.t), 2) + ') against ' + fUsd(num(raw.total)) + ' for the unfiltered rule on all days. One year cannot confirm an edge at that t. In the simulated Combine it ' + (beat ? 'passed more often than' : 'did not pass more often than') + ' the coin-flip control.';
});

/* ================= comparison ================= */
function cmpBars(name, col, fmt, label) {
  dash.draw(name, (host) => {
    const s = rows('summary'); if (!s) return dash0(host);
    const src = sel('#cmp-source', T0); const list = VK.map((k) => s.find((r) => r.key === k && r.source === src)).filter(Boolean);
    hbar(host, {rows: list.map((r) => ({name: r.variant, value: num(r[col]), color: VC[r.key], tip: [[label, fmt(num(r[col]))]]})), ref: 0, domain: d3.extent([0].concat(list.map((r) => num(r[col])))).map((v, i) => v * 1.12 + (i ? 1e-9 : -1e-9)), fmt, label});
  });
}
function hbar(host, o) {
  host.replaceChildren();
  const width = Math.max(260, host.clientWidth), rowH = 26, h = o.rows.length * rowH + 28;
  const svg = d3.select(host).append('svg').attr('viewBox', `0 0 ${width} ${h}`).attr('height', h).attr('role', 'img').attr('aria-label', o.label);
  const CW = 6.6, left = Math.min(width * 0.5, d3.max(o.rows, (r) => r.name.length) * CW + 14);
  const x = d3.scaleLinear().domain(o.domain).range([left, width - 60]);
  svg.append('line').attr('x1', x(o.ref)).attr('x2', x(o.ref)).attr('y1', 0).attr('y2', h - 22).style('stroke', AXIS);
  const t = tip(host);
  const g = svg.append('g').selectAll('g').data(o.rows).join('g').attr('transform', (d, i) => `translate(0,${i * rowH})`);
  g.append('text').attr('x', left - 8).attr('y', rowH / 2).attr('dy', '0.32em').attr('text-anchor', 'end').text((d) => (d.name.length * CW + 10 > left ? d.name.slice(0, Math.floor((left - 10) / CW) - 1) + '…' : d.name));
  g.append('rect').attr('x', (d) => Math.min(x(o.ref), x(d.value))).attr('width', (d) => Math.max(1, Math.abs(x(d.value) - x(o.ref)))).attr('y', 5).attr('height', rowH - 10).attr('rx', 3).style('fill', (d) => d.color);
  g.append('text').attr('x', (d) => Math.max(x(o.ref), x(d.value)) + 6).attr('y', rowH / 2).attr('dy', '0.32em').text((d) => o.fmt(d.value));
  g.append('rect').attr('x', 0).attr('width', width).attr('y', 0).attr('height', rowH).style('fill', 'transparent')
    .on('pointermove', (ev, d) => { const p = d3.pointer(ev, host); t.show(p[0], p[1], d.name, d.tip); }).on('pointerleave', () => t.hide());
}
cmpBars('cmp-sharpe', 'sharpe', (v) => fNum(v, 2), 'Sharpe ratio'); cmpBars('cmp-dd', 'drawdown', (v) => fUsd(v), 'Worst drawdown');
dash.draw('summary-body', (tb) => {
  const s = rows('summary'); if (!s) return tb.replaceChildren();
  const src = sel('#cmp-source', T0);
  fillTable(tb, VK.map((k) => s.find((r) => r.key === k && r.source === src)).filter(Boolean), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.variant); td(tr, fNum(g('traded_days'), 0)); td(tr, fNum(g('trades'), 0)); td(tr, fUsd(g('total')), signClass(g('total'))); td(tr, fUsd(g('per_traded_day'), 2), signClass(g('per_traded_day'))); td(tr, fUsd(g('std_day')));
    td(tr, fNum(g('sharpe'), 2)); td(tr, fNum(g('t'), 2)); td(tr, fUsd(g('drawdown'))); td(tr, fNum(g('profit_over_drawdown'), 2)); td(tr, fPct(g('win_days'))); td(tr, fUsd(g('per_trade'), 2), signClass(g('per_trade'))); td(tr, fPct(g('win_trades')));
    td(tr, fUsd(g('worst_day'))); td(tr, fUsd(g('best_day'))); td(tr, fPct(g('avg_size'), 0));
  });
});

/* ================= P&L ================= */
const NAME = {strat: 'The strategy', noreduce: 'Same, no size reduction', nofilter: 'Same, no filter', prev: 'Without low-volatility days (previous version)', bench: 'All days, filter everywhere, fixed size', raw: 'All days, unfiltered, fixed size'};
dash.draw('equity', (host) => {
  const d = rows('daily'); if (!d) return dash0(host);
  const pre = sel('#eq-cost', '1') === '2' ? 'eq2x_' : 'eq_';
  lineChart(host, {dates: d.map((r) => parseDay(r.date)), series: VK.map((k) => ({name: NAME[k], color: k === 'strat' ? 'var(--color-fg)' : VC[k], width: k === 'strat' ? 2.4 : 1.4, dashed: k === 'raw', values: d.map((r) => num(r[pre + k]))})), fmt: fK, zero: true, height: 340, shadeLabel: true, shadeFrom: parseDay(WF_START), label: 'Cumulative profit of one baseline set, the strategy and its alternatives'});
});
dash.draw('drawdown', (host) => {
  const d = rows('daily'); if (!d) return dash0(host);
  lineChart(host, {dates: d.map((r) => parseDay(r.date)), series: ['strat', 'raw'].map((k) => ({name: NAME[k], color: k === 'strat' ? C[0] : MUTED, dashed: k === 'raw', values: d.map((r) => num(r['dd_' + k]))})), fmt: fK, zero: true, height: 200, shadeFrom: parseDay(WF_START), label: 'Drawdown of the strategy and the unfiltered rule'});
});
dash.draw('sizeline', (host) => {
  const d = rows('daily'); if (!d) return dash0(host);
  lineChart(host, {dates: d.map((r) => parseDay(r.date)), series: [{name: 'Size, share of baseline', color: C[0], width: 1, values: d.map((r) => num(r.size))}], fmt: (v) => fPct(v, 0), zero: true, height: 180, shadeFrom: parseDay(WF_START), label: 'Size held each day as a share of the baseline'});
});
dash.draw('monthly', (host) => {
  const m = rows('monthly'); if (!m) return dash0(host);
  barChart(host, {cats: m.map((r) => r.id), groups: [{name: 'Profit', signed: true, color: C[0], values: m.map((r) => num(r.pnl))}], fmt: fK, height: 260, label: 'Profit of one baseline set by month'});
});
dash.draw('yearly-body', (tb) => {
  const y = rows('yearly'); if (!y) return tb.replaceChildren();
  fillTable(tb, y, (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.year); td(tr, r.period === 'dev' ? 'test year' : 'walk-forward', 'nq-l'); td(tr, fNum(g('traded_days'), 0)); td(tr, fNum(g('trades'), 0)); td(tr, fUsd(g('pnl_strat')), signClass(g('pnl_strat'))); td(tr, fNum(g('sharpe_strat'), 2));
    ['noreduce', 'nofilter', 'prev', 'bench', 'raw'].forEach((k) => td(tr, fUsd(g('pnl_' + k)), signClass(g('pnl_' + k))));
    td(tr, fPct(g('avg_size_high'), 0)); td(tr, fUsd(g('worst_day'))); td(tr, fUsd(g('best_day')));
  });
});

/* ================= parts ================= */
dash.draw('env-body', (tb) => {
  const e = rows('environments'); if (!e) return tb.replaceChildren();
  const src = sel('#env-source', T0);
  fillTable(tb, e.filter((r) => r.source === src), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.env); td(tr, fNum(g('days'), 0)); td(tr, fNum(g('trades'), 0)); td(tr, fPct(g('avg_size'), 0)); td(tr, fPct(g('min_size'), 0)); td(tr, fUsd(g('total')), signClass(g('total'))); td(tr, fUsd(g('per_day'), 2), signClass(g('per_day'))); td(tr, fUsd(g('std_day')));
    td(tr, fNum(g('sharpe'), 2)); td(tr, fNum(g('t'), 2)); td(tr, fUsd(g('per_trade'), 2), signClass(g('per_trade'))); td(tr, fPct(g('win_trades'))); td(tr, fUsd(g('unfiltered_full_size_total')), signClass(g('unfiltered_full_size_total'))); td(tr, fUsd(g('unfiltered_full_size_std')));
  });
});
function sizingBars(name, a, b, label) {
  dash.draw(name, (host) => {
    const z = rows('sizing'); if (!z) return dash0(host);
    const d = z.filter((r) => r.period === 'dev').sort((p, q) => num(p.order) - num(q.order));
    barChart(host, {cats: d.map((r) => r.bucket), groups: [{name: 'Reduced size', color: C[0], values: d.map((r) => num(r[a]))}, {name: 'Full baseline size', color: MUTED, values: d.map((r) => num(r[b]))}], fmt: (v) => fUsd(v), height: 250, label,
      extra: (i) => [['Days', fNum(num(d[i].days), 0)], ['Average size', fPct(num(d[i].avg_size), 0)]]});
  });
}
sizingBars('sizing-std', 'std_day', 'std_day_full', 'Daily swing on high-volatility days by volatility ratio');
sizingBars('sizing-mean', 'per_day', 'per_day_full', 'Average profit per day on high-volatility days by volatility ratio');
dash.draw('sizing-body', (tb) => {
  const z = rows('sizing'); if (!z) return tb.replaceChildren();
  fillTable(tb, z.slice().sort((p, q) => (p.period < q.period ? -1 : p.period > q.period ? 1 : num(p.order) - num(q.order))), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.bucket); td(tr, SAMPLE[r.period], 'nq-l'); td(tr, fNum(g('days'), 0)); td(tr, fPct(g('avg_size'), 0)); td(tr, fUsd(g('per_day'), 2), signClass(g('per_day'))); td(tr, fUsd(g('per_day_full'), 2), signClass(g('per_day_full'))); td(tr, fUsd(g('std_day'))); td(tr, fUsd(g('std_day_full'))); td(tr, fUsd(g('total')), signClass(g('total'))); td(tr, fUsd(g('total_full')), signClass(g('total_full')));
  });
});

/* ================= statistics ================= */
dash.draw('kpi-body', (tb) => {
  const k = rows('kpis'); if (!k) return tb.replaceChildren();
  tb.replaceChildren(); let grp = null;
  k.forEach((r) => {
    if (r.group !== grp) { grp = r.group; const g = el('tr', {class: 'nq-group'}); g.append(el('td', {colspan: 7}, grp)); tb.append(g); }
    const tr = el('tr'); td(tr, r.metric);
    ['dev', 'dev_2x', 'wf', 'dev_noreduce', 'dev_bench', 'dev_raw'].forEach((c) => td(tr, byUnit(num(r[c]), r.unit, r.metric)));
    tb.append(tr);
  });
});
dash.draw('hist', (host) => {
  const h = rows('histograms'); if (!h) return dash0(host);
  const p = sel('#hist-period', 'dev');
  const a = h.filter((r) => r.period === p && r.key === 'raw'), b = h.filter((r) => r.period === p && r.key === 'strat');
  barChart(host, {cats: a.map((r) => fUsd(num(r.lo))), groups: [{name: 'All days, unfiltered, fixed size', color: MUTED, values: a.map((r) => num(r.share))}, {name: 'The strategy', color: C[0], values: b.map((r) => num(r.share))}], fmt: (v) => fPct(v, 0), height: 300, label: 'Distribution of the daily result',
    tipTitle: (d, i) => fUsd(num(a[i].lo)) + ' to ' + fUsd(num(a[i].hi)), extra: (i) => [['Days, unfiltered', fNum(num(a[i].count), 0)], ['Days, strategy', fNum(num(b[i]?.count), 0)]]});
});

/* ================= breakdowns ================= */
let bdDim = 'Environment';
const GROUPS = ['Test years', 'Walk-forward year'];
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
  barChart(host, {cats, groups: GROUPS.map((g, i) => ({name: g, color: C[i], values: pick(g, 'avg_usd')})), fmt: (v) => fUsd(v, Math.abs(v) < 100 ? 2 : 0), height: 300, label: 'Average result per trade by ' + bdDim,
    extra: (i) => [['Trades, test years', fNum(pick(GROUPS[0], 'n')[i], 0)], ['Trades, walk-forward', fNum(pick(GROUPS[1], 'n')[i], 0)]]});
});
dash.draw('bd-body', (tb) => {
  const b = bdRows(); if (!b) return tb.replaceChildren();
  fillTable(tb, b.slice().sort((a, c) => GROUPS.indexOf(a.group) - GROUPS.indexOf(c.group) || num(a.order) - num(c.order)), (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.bucket); td(tr, r.group, 'nq-l'); td(tr, fNum(num(r.n), 0)); td(tr, fPct(num(r.win_rate))); td(tr, fUsd(num(r.avg_usd), 2), signClass(num(r.avg_usd))); td(tr, fUsd(num(r.total_usd)), signClass(num(r.total_usd))); td(tr, fNum(num(r.profit_factor), 2)); td(tr, fNum(num(r.t), 2));
  });
});

/* ================= Monte Carlo ================= */
function mcRows() { const m = rows('montecarlo'); if (!m) return null; const a = sel('#mc-account', '50K'), s = sel('#mc-source', T0); return m.filter((r) => r.account === a && r.days_from === s); }
function mcChart(name, col, label, ylabel) {
  dash.draw(name, (host) => {
    const m = mcRows(); if (!m) return dash0(host);
    const xs = Array.from(new Set(m.map((r) => num(r.contracts)))).sort((a, b) => a - b);
    const series = VK.map((k) => ({name: NAME[k], color: k === 'strat' ? 'var(--color-fg)' : VC[k], width: k === 'strat' ? 2.6 : 1.6, dashed: k === 'raw', pts: m.filter((r) => r.key === k).map((r) => ({x: num(r.contracts), y: num(r[col]), extra: [['Control', fPct(num(r[col === 'pass' ? 'control_pass' : 'control_pass_30d']))]]}))}));
    series.push({name: 'Coin-flip control for the strategy', color: 'var(--color-fg)', width: 1, dashed: true, pts: m.filter((r) => r.key === 'strat').map((r) => ({x: num(r.contracts), y: num(r[col === 'pass' ? 'control_pass' : 'control_pass_30d'])}))});
    xyChart(host, {series, fmt: (v) => fPct(v, 0), log: true, xticks: xs, xlabel: 'Baseline MNQ', ylabel, label});
  });
}
mcChart('mc-pass30', 'pass_30d', 'Pass within 30 trading days by baseline size', 'Pass within 30 days');
mcChart('mc-pass', 'pass', 'Pass with no time limit by baseline size', 'Pass, no limit');
dash.draw('mc-variants-body', (tb) => {
  const m = mcRows(); if (!m) return tb.replaceChildren();
  fillTable(tb, VK.map((k) => m.find((r) => r.key === k && +r.chosen === 1)).filter(Boolean), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.variant); td(tr, r.contracts); td(tr, fPct(g('pass_30d'))); td(tr, fPct(g('control_pass_30d'))); td(tr, fPct(g('pass'))); td(tr, fPct(g('control_pass'))); td(tr, fPct(g('breach'))); td(tr, fNum(g('median_days_to_pass'), 0));
    td(tr, fPct(g('payout_rate_standard'))); td(tr, fPct(g('payout_rate_consistency'))); td(tr, fUsd(g('fees_per_account'))); td(tr, fSigned(g('profit_per_account')), signClass(g('profit_per_account'))); td(tr, fSigned(g('profit_per_account_30d')), signClass(g('profit_per_account_30d'))); td(tr, fNum(g('ben_score_30d'), 3));
  });
});
dash.draw('mc-sizes-body', (tb) => {
  const m = mcRows(); if (!m) return tb.replaceChildren();
  fillTable(tb, m.filter((r) => r.key === 'strat').sort((a, b) => num(a.contracts) - num(b.contracts)), (tr, r) => {
    tr.setAttribute('data-key', r.id); const g = (c) => num(r[c]);
    td(tr, r.contracts); td(tr, fUsd(g('daily_std_usd'))); td(tr, fNum(g('std_over_limit'), 2)); td(tr, fPct(g('pass_30d'))); td(tr, fPct(g('control_pass_30d'))); td(tr, fPct(g('pass'))); td(tr, fPct(g('breach'))); td(tr, fNum(g('median_days_to_pass'), 0));
    td(tr, fPct(g('payout_rate_standard'))); td(tr, fUsd(g('payout_usd_standard'))); td(tr, fNum(g('xfa_days_to_first_payout'), 0)); td(tr, fSigned(g('profit_per_account')), signClass(g('profit_per_account'))); td(tr, fSigned(g('profit_per_account_30d')), signClass(g('profit_per_account_30d')));
  });
});

/* ================= controls ================= */
const on = (q, names) => document.querySelectorAll(q).forEach((s) => s.addEventListener('change', () => names.forEach((n) => dash.draw(n))));
on('#cmp-source', ['cmp-sharpe', 'cmp-dd', 'summary-body']); on('#eq-cost', ['equity']); on('#env-source', ['env-body']); on('#hist-period', ['hist']);
on('#mc-account, #mc-source', ['mc-pass30', 'mc-pass', 'mc-variants-body', 'mc-sizes-body']);
