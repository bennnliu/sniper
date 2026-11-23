/* Drawings for the NQ breakout ensemble dashboard. Every number comes from a dataset. */
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

/* ================= headline sentence ================= */
function kpi(metric, col) { const k = rows('kpis'); if (!k) return NaN; const r = k.find((d) => d.metric === metric); return r ? num(r[col]) : NaN; }
function sentence(name, metric, col, fmt) { dash.draw(name, (e) => { const v = kpi(metric, col); e.textContent = isFinite(v) ? fmt(v) : '—'; }); }
sentence('t-dev-total', 'Total net profit', 'dev', fUsd);
sentence('t-wf-total', 'Total net profit', 'wf', fUsd);
sentence('t-dev-sharpe', 'Sharpe ratio, annualised, all days', 'dev', (v) => fNum(v, 2));
sentence('t-wf-sharpe', 'Sharpe ratio, annualised, all days', 'wf', (v) => fNum(v, 2));
sentence('t-wf-best', 'Best day', 'wf', fUsd);
sentence('w-dev-std', 'Standard deviation of a day, all days', 'dev', fUsd);
sentence('w-wf-std', 'Standard deviation of a day, all days', 'wf', fUsd);

dash.draw('tiles', (host) => {
  const k = rows('kpis'), c = rows('checks');
  if (!k || !c) return dash0(host);
  host.replaceChildren();
  const T = [
    ['Net profit', 'Total net profit', fUsd],
    ['Sharpe ratio', 'Sharpe ratio, annualised, all days', (v) => fNum(v, 2)],
    ['Net profit per trade, one MNQ', 'Net profit per trade', (v) => fUsd(v, 2)],
    ['Winning days', 'Winning days, share of traded days', fPct],
    ['Days at $150 or more', 'Days at $150 or more, share of all days', fPct],
    ['Worst drawdown', 'Worst drawdown', fUsd],
    ['Worst day', 'Worst day', fUsd],
  ];
  T.forEach(([lab, metric, fmt]) => {
    const t = el('div', {class: 'nq-tile'});
    t.append(el('span', {class: 'nq-lab'}, lab));
    t.append(el('span', {class: 'nq-val', 'data-source': 'kpis', 'data-field': 'dev', 'data-where': 'metric=' + metric}, fmt(kpi(metric, 'dev'))));
    t.append(el('span', {class: 'nq-sub'}, 'in-sample, 2010 to Oct 2024'));
    const s = el('span', {class: 'nq-sub'});
    s.append(el('span', {'data-source': 'kpis', 'data-field': 'wf', 'data-where': 'metric=' + metric}, fmt(kpi(metric, 'wf'))), document.createTextNode(' out-of-sample year'));
    t.append(s); host.append(t);
  });
  const d = c.find((r) => r.check === 'Deflated Sharpe ratio, development');
  if (d) {
    const t = el('div', {class: 'nq-tile'});
    t.append(el('span', {class: 'nq-lab'}, 'Deflated Sharpe ratio'), el('span', {class: 'nq-val', 'data-source': 'checks', 'data-field': 'value', 'data-where': 'check=Deflated Sharpe ratio, development'}, fNum(num(d.value), 2)), el('span', {class: 'nq-sub'}, 'bar to promote is 0.95'), el('span', {class: 'nq-sub'}, 'after 191 trials'));
    host.append(t);
  }
});

/* ================= P&L over time ================= */
let eqView = 'cost';
function dailyCols() { const d = rows('daily'); if (!d) return null; return {d, dates: d.map((r) => parseDay(r.date))}; }
dash.draw('equity', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  const col = (c) => g.d.map((r) => num(r[c]));
  const series = eqView === 'cost'
    ? [{name: 'Net of costs', color: C[0], values: col('equity'), width: 2}, {name: 'At double cost', color: C[1], values: col('equity_2x')}, {name: 'Gross, before costs', color: MUTED, values: col('equity_gross'), dashed: true}]
    : [{name: 'Long trades, net', color: C[0], values: col('equity_long')}, {name: 'Short trades, net', color: C[1], values: col('equity_short')}];
  lineChart(host, {dates: g.dates, series, fmt: fK, zero: true, height: 340, shadeLabel: true, shadeFrom: parseDay(WF_START), label: 'Cumulative profit of one set over time'});
});
dash.draw('drawdown', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  lineChart(host, {dates: g.dates, series: [{name: 'Drawdown', color: BAD, values: g.d.map((r) => num(r.drawdown))}], fmt: fK, zero: true, area: true, height: 190, shadeFrom: parseDay(WF_START), label: 'Drawdown from the previous equity high'});
});
dash.draw('rolling', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  lineChart(host, {dates: g.dates, series: [{name: 'Sharpe, trailing 250 days', color: C[0], values: g.d.map((r) => num(r.sharpe_250d))}], fmt: (v) => fNum(v, 1), zero: true, height: 190, shadeFrom: parseDay(WF_START), label: 'Rolling Sharpe ratio'});
});
dash.draw('rollstd', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  lineChart(host, {dates: g.dates, series: [{name: 'Std of a day, trailing 60 days', color: C[0], values: g.d.map((r) => num(r.std_60d))}], fmt: fK, zero: true, height: 190, shadeFrom: parseDay(WF_START), label: 'Rolling standard deviation of the daily result'});
});
dash.draw('dailybars', (host) => {
  const g = dailyCols(); if (!g) return dash0(host);
  host.replaceChildren();
  const v = g.d.map((r) => num(r.pnl));
  const y0 = d3.scaleLinear().domain(d3.extent(v)).nice(4);
  const f = frame(host, 200, y0.ticks(4).map(fK), {label: 'Net result of each trading day'});
  const x = d3.scaleUtc().domain(d3.extent(g.dates)).range([f.m.left, f.width - f.m.right]);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  yAxis(f, y, fK, 4); xTimeAxis(f, x);
  f.svg.append('g').selectAll('line').data(v).join('line').attr('x1', (d, i) => x(g.dates[i])).attr('x2', (d, i) => x(g.dates[i])).attr('y1', y(0)).attr('y2', (d) => y(d)).style('stroke', (d) => (d >= 0 ? OK : BAD)).style('stroke-width', 1).style('opacity', 0.75);
  const t = tip(host), bis = d3.bisector((d) => d).center;
  f.svg.append('rect').attr('x', f.m.left).attr('y', f.m.top).attr('width', f.iw).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev) => { const [px] = d3.pointer(ev, f.svg.node()); const i = bis(g.dates, x.invert(px)); const r = g.d[i]; const p = d3.pointer(ev, host); t.show(p[0], p[1], fDay(g.dates[i]), [['Result', fUsd(num(r.pnl))], ['Trades', r.trades], ['Worst open loss', fUsd(num(r.worst_open))], ['Volatility', r.regime]]); })
    .on('pointerleave', () => t.hide());
});

/* ================= years ================= */
dash.draw('yearly-body', (tb) => {
  const y = rows('yearly'); if (!y) return tb.replaceChildren();
  fillTable(tb, y, (tr, r) => {
    td(tr, r.year); td(tr, r.period === 'dev' ? 'in-sample' : r.period === 'wf' ? 'out-of-sample' : 'both', 'nq-l');
    td(tr, fUsd(num(r.pnl)), signClass(num(r.pnl))); td(tr, fUsd(num(r.pnl_2x)), signClass(num(r.pnl_2x))); td(tr, fNum(num(r.sharpe), 2));
    td(tr, fUsd(num(r.per_day))); td(tr, fUsd(num(r.std_day))); td(tr, fPct(num(r.win_days))); td(tr, fPct(num(r.days_150)));
    td(tr, fUsd(num(r.worst_day))); td(tr, fUsd(num(r.best_day))); td(tr, fUsd(num(r.worst_drawdown))); td(tr, fNum(num(r.trades), 0)); td(tr, fNum(num(r.avg_nq_price), 0));
  });
});
dash.draw('heat', (host) => {
  const m = rows('monthly'); if (!m) return dash0(host);
  host.replaceChildren();
  const mx = d3.max(m, (r) => Math.abs(num(r.pnl))) || 1;
  const names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const t = el('table', {class: 'nq-heat', 'aria-label': 'Net profit by month in thousands of dollars'}); const h = el('tr'); h.append(el('th', null, 'Year')); names.forEach((n) => h.append(el('th', null, n)));
  const th = el('thead'); th.append(h); t.append(th); const tb = el('tbody');
  d3.groups(m, (r) => r.year).forEach(([yr, list]) => {
    const tr = el('tr'); tr.append(el('td', null, yr));
    for (let k = 1; k <= 12; k++) {
      const r = list.find((d) => +d.month === k); const c = el('td');
      if (r) { const v = num(r.pnl); c.textContent = fNum(v / 1000, 1); c.style.background = `color-mix(in srgb, ${v >= 0 ? OK : BAD} ${Math.round(Math.sqrt(Math.abs(v) / mx) * 70)}%, transparent)`; if (r.period === 'wf') c.style.outline = '1px dashed var(--color-fg-muted)'; c.style.outlineOffset = '-2px'; }
      tr.append(c);
    }
    tb.append(tr);
  });
  t.append(tb); host.append(t);
  host.append(el('div', {class: 'nq-cap'}, 'Dashed cells are the out-of-sample year.'));
});

/* ================= all statistics ================= */
dash.draw('kpi-body', (tb) => {
  const k = rows('kpis'); if (!k) return tb.replaceChildren();
  tb.replaceChildren(); let grp = null;
  k.forEach((r) => {
    if (r.group !== grp) { grp = r.group; const g = el('tr', {class: 'nq-group'}); const c = el('td', {colspan: 5}, grp); g.append(c); tb.append(g); }
    const tr = el('tr'); td(tr, r.metric);
    ['dev', 'dev_2x', 'wf', 'wf_2x'].forEach((c) => td(tr, byUnit(num(r[c]), r.unit, r.metric)));
    tb.append(tr);
  });
});

/* ================= distributions ================= */
dash.draw('hist', (host) => {
  const h = rows('histograms'); if (!h) return dash0(host);
  const what = document.querySelector('#hist-what')?.value || 'Daily result, traded days ($, one set)';
  const dv = h.filter((r) => r.what === what && r.period === 'dev'), wf = h.filter((r) => r.what === what && r.period === 'wf');
  const isMin = what === 'Minutes held'; const f1 = isMin ? (v) => fNum(v, 0) : (v) => fUsd(v);
  barChart(host, {cats: dv.map((r) => f1(num(r.lo))), groups: [{name: 'Development (in-sample)', color: C[0], values: dv.map((r) => num(r.share))}, {name: 'Walk-forward year (out-of-sample)', color: C[1], values: wf.map((r) => num(r.share))}],
    fmt: (v) => fPct(v, 1), height: 300, label: what, tipTitle: (d, i) => f1(num(dv[i].lo)) + ' to ' + f1(num(dv[i].hi)), extra: (i) => [['Count, development', fNum(num(dv[i].count), 0)], ['Count, walk-forward', fNum(num(wf[i]?.count), 0)]]});
});

/* ================= breakdowns ================= */
let bdDim = 'How the trade ended';
dash.draw('bd-dim', (sel) => {
  const b = rows('breakdowns');
  const dims = b ? Array.from(new Set(b.map((r) => r.dimension))) : [];
  sel.replaceChildren(...dims.map((d) => new Option(d)));
  if (dims.includes(bdDim)) sel.value = bdDim;
  sel.onchange = () => { bdDim = sel.value; dash.draw('bd-chart'); dash.draw('bd-body'); };
});
function bdRows() { const b = rows('breakdowns'); if (!b) return null; return b.filter((r) => r.dimension === bdDim).sort((a, c) => num(a.order) - num(c.order)); }
dash.draw('bd-chart', (host) => {
  const b = bdRows(); if (!b) return dash0(host);
  const cats = Array.from(new Set(b.map((r) => r.bucket)));
  const pick = (p, c) => cats.map((k) => { const r = b.find((d) => d.bucket === k && d.period === p); return r ? num(r[c]) : NaN; });
  barChart(host, {cats, groups: [{name: 'Development (in-sample)', color: C[0], values: pick('dev', 'avg_usd')}, {name: 'Walk-forward year (out-of-sample)', color: C[1], values: pick('wf', 'avg_usd')}], fmt: (v) => fUsd(v, Math.abs(v) < 100 ? 2 : 0), height: 300, label: 'Average result by ' + bdDim,
    extra: (i) => [['Count, development', fNum(pick('dev', 'n')[i], 0)], ['Count, walk-forward', fNum(pick('wf', 'n')[i], 0)], ['Winners, development', fPct(pick('dev', 'win_rate')[i])]]});
});
dash.draw('bd-body', (tb) => {
  const b = bdRows(); if (!b) return tb.replaceChildren();
  fillTable(tb, b.slice().sort((a, c) => (a.period < c.period ? -1 : a.period > c.period ? 1 : num(a.order) - num(c.order))), (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.bucket); td(tr, r.period === 'dev' ? 'in-sample' : 'out-of-sample', 'nq-l'); td(tr, fNum(num(r.n), 0)); td(tr, fPct(num(r.win_rate)));
    td(tr, fUsd(num(r.avg_usd), 2), signClass(num(r.avg_usd))); td(tr, fUsd(num(r.total_usd)), signClass(num(r.total_usd))); td(tr, fNum(num(r.profit_factor), 2)); td(tr, fNum(num(r.t), 2));
  });
});

/* ================= intraday ================= */
function intra(name, col, fmt, label) {
  dash.draw(name, (host) => {
    const d = rows('intraday'); if (!d) return dash0(host);
    const dv = d.filter((r) => r.period === 'dev'), wf = d.filter((r) => r.period === 'wf');
    barChart(host, {cats: dv.map((r) => r.from_et), groups: [{name: 'Development (in-sample)', color: C[0], values: dv.map((r) => num(r[col]))}, {name: 'Walk-forward year (out-of-sample)', color: C[1], values: wf.map((r) => num(r[col]))}], fmt, height: 230, label, tipTitle: (c) => 'Half hour from ' + c});
  });
}
intra('intra-pnl', 'gross_per_day', (v) => fUsd(v, Math.abs(v) < 100 ? 2 : 0), 'Gross profit per day by half hour');
intra('intra-pos', 'avg_contracts', (v) => fNum(v, 1), 'Average MNQ held by half hour');

/* ================= excursions ================= */
function exc(name, col, xlabel, xdom) {
  dash.draw(name, (host) => {
    const d = rows('trade_sample'); if (!d) return dash0(host);
    const mk = (p) => d.filter((r) => r.period === p).map((r) => ({x: num(r[col]), y: num(r.net), date: r.date, side: r.side, minutes: num(r.minutes)}));
    scatter(host, {groups: [{name: 'Development (in-sample)', color: C[0], points: mk('dev')}, {name: 'Walk-forward year (out-of-sample)', color: C[1], points: mk('wf')}], xdom, ydom: [-300, 600], fmt: (v) => fUsd(v), xlabel, label: 'Trade result against ' + xlabel.toLowerCase()});
  });
}
exc('mae', 'worst_open', 'Worst open loss', [-400, 0]);
exc('mfe', 'best_open', 'Best open gain', [0, 800]);
dash.draw('extreme-body', (tb) => {
  const d = rows('extreme_days'); if (!d) return tb.replaceChildren();
  fillTable(tb, d, (tr, r) => { td(tr, r.date); td(tr, r.kind, 'nq-l'); td(tr, r.period === 'dev' ? 'in-sample' : 'out-of-sample', 'nq-l'); td(tr, fUsd(num(r.pnl)), signClass(num(r.pnl))); td(tr, fUsd(num(r.worst_open))); td(tr, r.trades); td(tr, r.regime, 'nq-l'); });
});

/* ================= sessions ================= */
dash.draw('sess-chart', (host) => {
  const d = rows('session_curves'); if (!d) return dash0(host);
  const weeks = Array.from(new Set(d.map((r) => r.week))).sort(); const dates = weeks.map(parseDay);
  const names = {NY: 'New York', ASIA: 'Asia', LONDON: 'London'};
  const series = ['NY', 'ASIA', 'LONDON'].map((s, i) => { const m = new Map(d.filter((r) => r.session === s).map((r) => [r.week, num(r.equity)])); return {name: names[s], color: C[i], values: weeks.map((w) => (m.has(w) ? m.get(w) : NaN))}; });
  lineChart(host, {dates, series, fmt: fK, zero: true, height: 300, shadeLabel: true, shadeFrom: parseDay(WF_START), label: 'Cumulative profit of one set by session'});
});
dash.draw('sess-body', (tb) => {
  const d = rows('sessions'); if (!d) return tb.replaceChildren();
  fillTable(tb, d, (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.session); td(tr, r.regime, 'nq-l'); td(tr, r.period === 'dev' ? 'in-sample' : 'out-of-sample', 'nq-l'); td(tr, fNum(num(r.days), 0));
    td(tr, fUsd(num(r.per_day), 2), signClass(num(r.per_day))); td(tr, fUsd(num(r.total)), signClass(num(r.total))); td(tr, fNum(num(r.sharpe), 2)); td(tr, fNum(num(r.t_vol_units), 2)); td(tr, fPct(num(r.win_days))); td(tr, fUsd(num(r.std_day))); td(tr, fUsd(num(r.worst_day)));
  });
});

/* ================= Monte Carlo ================= */
const mcSel = () => ({account: document.querySelector('#mc-account')?.value || '50K', source: document.querySelector('#mc-source')?.value || 'Development, all years (in-sample)'});
function mcRows() { const m = rows('montecarlo'); if (!m) return null; const s = mcSel(); return m.filter((r) => r.account === s.account && r.days_from === s.source).sort((a, b) => num(a.contracts) - num(b.contracts)); }
dash.draw('mc-tiles', (host) => {
  const m = mcRows(); if (!m) return dash0(host);
  host.replaceChildren();
  const r = m.find((d) => +d.base === 1); if (!r) return;
  const where = 'id=' + r.id.replace(/%/g, '%25').replace(/&/g, '%26').replace(/=/g, '%3D');
  const T = [
    ['Pass rate, no time limit', 'pass', fPct, `95% interval ${fPct(num(r.pass_lo))} to ${fPct(num(r.pass_hi))}`],
    ['Pass within 30 trading days', 'pass_30d', fPct, `random control ${fPct(num(r.control_pass_30d))}`],
    ['Breach rate', 'breach', fPct, `median ${fNum(num(r.median_days_to_pass), 0)} days to pass`],
    ['Funded accounts paid at least once', num(r.payout_rate_standard) >= num(r.payout_rate_consistency) ? 'payout_rate_standard' : 'payout_rate_consistency', fPct, num(r.payout_rate_standard) >= num(r.payout_rate_consistency) ? 'standard path' : 'consistency path'],
    ['Profit per Combine account bought', 'profit_per_account', fSigned, `fees ${fUsd(num(r.fees_per_account))} per account`],
    ['Profit per account, 30-day stop', 'profit_per_account_30d', fSigned, 'stop the attempt at 30 trading days'],
  ];
  T.forEach(([lab, field, fmt, sub]) => {
    const t = el('div', {class: 'nq-tile'});
    t.append(el('span', {class: 'nq-lab'}, lab), el('span', {class: 'nq-val', 'data-source': 'montecarlo', 'data-field': field, 'data-where': where}, fmt(num(r[field]))), el('span', {class: 'nq-sub'}, sub), el('span', {class: 'nq-sub'}, `${r.contracts} MNQ, simulated`));
    host.append(t);
  });
});
dash.draw('mc-size', (host) => {
  const m = mcRows(); if (!m) return dash0(host);
  barLine(host, m, [{name: 'Pass, no time limit', color: C[0], col: 'pass'}, {name: 'Pass within 30 trading days', color: C[1], col: 'pass_30d'}, {name: 'Random control within 30 days', color: MUTED, col: 'control_pass_30d', dashed: true}], (v) => fPct(v, 0), 'Pass rate by number of MNQ');
});
function barLine(host, m, series, fmt, label) {
  host.replaceChildren(); legend(host, series);
  const xs = m.map((r) => num(r.contracts));
  const y0 = d3.scaleLinear().domain([0, d3.max(series.flatMap((s) => m.map((r) => num(r[s.col])))) || 1]).nice(5);
  const f = frame(host, 300, y0.ticks(5).map(fmt), {label, bottom: 34});
  const x = d3.scalePoint().domain(xs).range([f.m.left + 14, f.width - f.m.right - 14]);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  yAxis(f, y, fmt);
  f.svg.append('g').selectAll('text').data(xs).join('text').attr('x', (d) => x(d)).attr('y', f.height - f.m.bottom + 14).attr('text-anchor', 'middle').text((d) => d);
  f.svg.append('text').attr('x', f.m.left + f.iw / 2).attr('y', f.height - 2).attr('text-anchor', 'middle').text('MNQ held when every setting is in');
  series.forEach((s) => {
    f.svg.append('path').attr('d', d3.line().x((r) => x(num(r.contracts))).y((r) => y(num(r[s.col])))(m)).style('fill', 'none').style('stroke', s.color).style('stroke-width', 2).style('stroke-dasharray', s.dashed ? '4 3' : null);
    f.svg.append('g').selectAll('circle').data(m).join('circle').attr('cx', (r) => x(num(r.contracts))).attr('cy', (r) => y(num(r[s.col]))).attr('r', (r) => (+r.base === 1 ? 5 : 3)).style('fill', s.color).style('stroke', 'var(--color-bg)').style('stroke-width', 1.5);
  });
  const t = tip(host);
  f.svg.append('g').selectAll('rect').data(m).join('rect').attr('x', (r) => x(num(r.contracts)) - x.step() / 2).attr('width', x.step()).attr('y', f.m.top).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev, r) => { const p = d3.pointer(ev, host); t.show(p[0], p[1], r.contracts + ' MNQ', series.map((s) => [s.name, fmt(num(r[s.col]))]).concat([['Median days to pass', fNum(num(r.median_days_to_pass), 0)]])); })
    .on('pointerleave', () => t.hide());
}
dash.draw('mc-profit', (host) => {
  const m = mcRows(); if (!m) return dash0(host);
  barChart(host, {cats: m.map((r) => r.contracts), groups: [{name: 'No time limit', color: C[0], values: m.map((r) => num(r.profit_per_account))}, {name: 'Stop at 30 trading days', color: C[1], values: m.map((r) => num(r.profit_per_account_30d))}], fmt: (v) => fUsd(v), height: 300, label: 'Expected profit per Combine account by number of MNQ', tipTitle: (c) => c + ' MNQ',
    extra: (i) => [['Fees per account', fUsd(num(m[i].fees_per_account))], ['Payout per funded account', fUsd(Math.max(num(m[i].payout_usd_standard), num(m[i].payout_usd_consistency)))]]});
});
dash.draw('mc-fan', (host) => {
  const p = rows('mc_paths'); if (!p) return dash0(host);
  const s = mcSel(); host.replaceChildren();
  const src = p.some((r) => r.account === s.account && r.days_from === s.source) ? s.source : 'Development, all years (in-sample)';
  const sel = p.filter((r) => r.account === s.account && r.days_from === src);
  const band = sel.filter((r) => r.kind === 'band').sort((a, b) => num(a.day) - num(b.day));
  const paths = d3.groups(sel.filter((r) => r.kind === 'path'), (r) => r.path);
  const R = RULE[s.account];
  legend(host, [{name: 'Median attempt', color: C[0]}, {name: 'Passed', color: OK}, {name: 'Breached', color: BAD}, {name: 'Still open at day 60', color: MUTED}]);
  const lo = Math.min(-R.mll * 1.15, d3.min(band, (r) => num(r.p5))), hi = Math.max(R.target * 1.25, d3.max(band, (r) => num(r.p95)));
  const y0 = d3.scaleLinear().domain([lo, hi]).nice(6);
  const f = frame(host, 360, y0.ticks(6).map(fK), {label: 'Simulated Combine balance paths', bottom: 34, right: 70});
  const x = d3.scaleLinear().domain([0, 60]).range([f.m.left, f.width - f.m.right]);
  const y = y0.range([f.height - f.m.bottom, f.m.top]);
  yAxis(f, y, fK, 6);
  f.svg.append('g').selectAll('text').data(x.ticks(6)).join('text').attr('x', (d) => x(d)).attr('y', f.height - f.m.bottom + 14).attr('text-anchor', 'middle').text((d) => d);
  f.svg.append('text').attr('x', f.m.left + f.iw / 2).attr('y', f.height - 2).attr('text-anchor', 'middle').text('Trading day of the attempt' + (src !== s.source ? ' (development sample shown)' : ''));
  const area = (a, b) => d3.area().x((r) => x(num(r.day))).y0((r) => y(num(r[a]))).y1((r) => y(num(r[b])))(band);
  f.svg.append('path').attr('d', area('p5', 'p95')).style('fill', C[0]).style('opacity', 0.12);
  f.svg.append('path').attr('d', area('p25', 'p75')).style('fill', C[0]).style('opacity', 0.2);
  const colorOf = {pass: OK, breach: BAD, open: MUTED};
  paths.forEach(([, pts]) => { pts.sort((a, b) => num(a.day) - num(b.day)); f.svg.append('path').attr('d', d3.line().x((r) => x(num(r.day))).y((r) => y(num(r.balance)))(pts)).style('fill', 'none').style('stroke', colorOf[pts[0].outcome]).style('stroke-width', 1).style('opacity', 0.55); });
  f.svg.append('path').attr('d', d3.line().x((r) => x(num(r.day))).y((r) => y(num(r.p50)))(band)).style('fill', 'none').style('stroke', C[0]).style('stroke-width', 2.2);
  [[R.target, 'target ' + fUsd(R.target)], [-R.mll, 'loss limit ' + fUsd(-R.mll)]].forEach(([v, lab]) => {
    f.svg.append('line').attr('x1', f.m.left).attr('x2', f.width - f.m.right).attr('y1', y(v)).attr('y2', y(v)).style('stroke', REF).style('stroke-dasharray', '5 4').style('stroke-width', 1.2);
    f.svg.append('text').attr('x', f.width - f.m.right + 4).attr('y', y(v)).attr('dy', '0.32em').text(lab).style('font-size', '10px');
  });
  const cross = f.svg.append('line').attr('y1', f.m.top).attr('y2', f.height - f.m.bottom).style('stroke', REF).style('display', 'none');
  const t = tip(host);
  f.svg.append('rect').attr('x', f.m.left).attr('y', f.m.top).attr('width', f.iw).attr('height', f.ih).style('fill', 'transparent')
    .on('pointermove', (ev) => { const [px] = d3.pointer(ev, f.svg.node()); const i = Math.max(0, Math.min(60, Math.round(x.invert(px)))); const r = band[i]; if (!r) return; cross.attr('x1', x(i)).attr('x2', x(i)).style('display', null); const pp = d3.pointer(ev, host); t.show(pp[0], pp[1], 'Day ' + i, [['95th percentile', fUsd(num(r.p95))], ['75th', fUsd(num(r.p75))], ['Median', fUsd(num(r.p50))], ['25th', fUsd(num(r.p25))], ['5th', fUsd(num(r.p5))]]); })
    .on('pointerleave', () => { cross.style('display', 'none'); t.hide(); });
});
dash.draw('mc-days', (host) => {
  const d = rows('mc_days'); if (!d) return dash0(host);
  const s = mcSel();
  const src = d.some((r) => r.account === s.account && r.days_from === s.source) ? s.source : 'Development, all years (in-sample)';
  const sel = d.filter((r) => r.account === s.account && r.days_from === src);
  const P = sel.filter((r) => r.outcome === 'Passed'), B = sel.filter((r) => r.outcome === 'Breached');
  barChart(host, {cats: P.map((r) => (+r.to_day === 400 ? '121+' : r.from_day + '–' + r.to_day)), groups: [{name: 'Passed', color: OK, values: P.map((r) => num(r.share))}, {name: 'Breached', color: BAD, values: B.map((r) => num(r.share))}], fmt: (v) => fPct(v, 1), height: 230, label: 'Share of attempts ending in each span of trading days', tipTitle: (c) => 'Trading days ' + c});
});
dash.draw('mc-body', (tb) => {
  const m = mcRows(); if (!m) return tb.replaceChildren();
  fillTable(tb, m, (tr, r) => {
    tr.setAttribute('data-key', r.id);
    td(tr, r.contracts + (+r.base === 1 ? ' (one set per $50K)' : ''));
    td(tr, fPct(num(r.pass))); td(tr, fPct(num(r.pass_30d))); td(tr, fPct(num(r.control_pass_30d))); td(tr, fPct(num(r.breach))); td(tr, fNum(num(r.median_days_to_pass), 0));
    td(tr, fPct(num(r.payout_rate_standard))); td(tr, fPct(num(r.payout_rate_consistency))); td(tr, fUsd(num(r.payout_usd_standard))); td(tr, fUsd(num(r.fees_per_account)));
    td(tr, fSigned(num(r.profit_per_account)), signClass(num(r.profit_per_account))); td(tr, fSigned(num(r.profit_per_account_30d)), signClass(num(r.profit_per_account_30d))); td(tr, fNum(num(r.ben_score), 3));
  });
});

/* ================= checks ================= */
dash.draw('checks-body', (tb) => {
  const c = rows('checks'); if (!c) return tb.replaceChildren();
  fillTable(tb, c, (tr, r) => { td(tr, r.check); td(tr, fNum(num(r.value), r.unit === 'n' ? 0 : 2)); td(tr, r.note, 'nq-l'); });
});

/* ================= controls ================= */
document.querySelectorAll('#eq-view').forEach((s) => s.addEventListener('change', () => { eqView = s.value; dash.draw('equity'); }));
document.querySelectorAll('#hist-what').forEach((s) => s.addEventListener('change', () => dash.draw('hist')));
document.querySelectorAll('#mc-account, #mc-source').forEach((s) => s.addEventListener('change', () => ['mc-tiles', 'mc-size', 'mc-profit', 'mc-fan', 'mc-days', 'mc-body'].forEach((n) => dash.draw(n))));
