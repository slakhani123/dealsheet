#!/usr/bin/env python3
"""Render automation/contacts_data.json into a shareable single-file web directory.

    python3 automation/build_contacts_html.py [output.html]

Output defaults to contacts_site/index.html. The page is fully self-contained
(no external requests) so it can be published as an Artifact, emailed, or
dropped on SharePoint and opened straight from the browser.
"""

import html
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "automation", "contacts_data.json")
DEFAULT_OUT = os.path.join(ROOT, "contacts_site", "index.html")

# Everything firm-specific lives in contacts_data.json's "config" block, so the
# same code renders any mailbox owner's directory.
DEFAULT_CONFIG = {
    "owner_name": "",
    "owner_first_name": "",
    "owner_email": "",
    "org_name": "",
    "org_locale": "",
    "org_blurb": ("Every counterparty this firm has corresponded with, drawn "
                  "automatically from the mailbox and sorted by the role they "
                  "play in a deal — who brings it, who funds it, who borrows, "
                  "who signs it off."),
}

CATEGORY_ORDER = [
    "Broker",
    "Lender / Bank",
    "Borrower / Sponsor",
    "Investor / Family Office",
    "Solicitor / Legal",
    "Valuer / Property Professional",
    "Accountant / Tax",
    "Service Provider",
    "Internal",
    "Personal / Other",
]

# Short blurb shown under each category heading — says what the group *is* to
# REL, not just what it is called.
CATEGORY_BLURB = {
    "Broker": "Intermediaries introducing deal flow.",
    "Lender / Bank": "Competing lenders, co-lenders and refinance takeouts.",
    "Borrower / Sponsor": "Counterparties borrowing against property.",
    "Investor / Family Office": "Capital partners and shareholder side.",
    "Solicitor / Legal": "Firms running legals on facilities.",
    "Valuer / Property Professional": "Valuation, agency and building surveying.",
    "Accountant / Tax": "Audit, accounts and tax advisory.",
    "Service Provider": "Software, data, insurance and other suppliers.",
    "Internal": "The team here.",
    "Personal / Other": "Everything not yet placed.",
}

CATEGORY_KEY = {c: "c%d" % i for i, c in enumerate(CATEGORY_ORDER)}

# light, dark
CATEGORY_HUE = {
    "Broker": ("#B4632B", "#E09359"),
    "Lender / Bank": ("#2F6F8F", "#63A8C7"),
    "Borrower / Sponsor": ("#4A7C48", "#84B77F"),
    "Investor / Family Office": ("#7A6AA8", "#A79AD0"),
    "Solicitor / Legal": ("#5F6B8C", "#96A2C4"),
    "Valuer / Property Professional": ("#2D7D74", "#6BB8AE"),
    "Accountant / Tax": ("#A44B62", "#D3899E"),
    "Service Provider": ("#7C848C", "#A2ACB6"),
    "Internal": ("#9A6B22", "#D9AB58"),
    "Personal / Other": ("#6E7680", "#98A1AB"),
}

CSS = """
*, *::before, *::after { box-sizing: border-box; }

:root {
  --ground:    #EDEFF1;
  --surface:   #FFFFFF;
  --ink:       #151A20;
  --muted:     #5C6773;
  --faint:     #8B96A2;
  --hairline:  #D5DAE0;
  --hairline-strong: #B9C1CA;
  --accent:    #9A6B22;
  --accent-soft: rgba(154, 107, 34, 0.12);
  --bar-in:    #2F6F8F;
  --bar-out:   #9A6B22;
  --shadow:    0 1px 2px rgba(21, 26, 32, 0.06), 0 8px 24px rgba(21, 26, 32, 0.05);
__CAT_LIGHT__
}

@media (prefers-color-scheme: dark) {
  :root { __DARK_TOKENS__ }
}
:root[data-theme="dark"] { __DARK_TOKENS__ }
:root[data-theme="light"] {
  --ground: #EDEFF1; --surface: #FFFFFF; --ink: #151A20; --muted: #5C6773;
  --faint: #8B96A2; --hairline: #D5DAE0; --hairline-strong: #B9C1CA;
  --accent: #9A6B22; --accent-soft: rgba(154, 107, 34, 0.12);
  --bar-in: #2F6F8F; --bar-out: #9A6B22;
  --shadow: 0 1px 2px rgba(21, 26, 32, 0.06), 0 8px 24px rgba(21, 26, 32, 0.05);
__CAT_LIGHT__
}

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--ground);
  color: var(--ink);
  font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system,
               BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  font-feature-settings: 'kern' 1;
}

.wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px; }

/* ---------- masthead ---------- */

.masthead { padding: 56px 0 0; }
.masthead .wrap { display: flex; flex-direction: column; gap: 14px; }

.eyebrow {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--accent);
}

h1 {
  margin: 0;
  font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino,
               'Book Antiqua', 'URW Palladio L', Georgia, serif;
  font-size: clamp(34px, 5.2vw, 52px);
  font-weight: 600;
  letter-spacing: -0.015em;
  line-height: 1.04;
  text-wrap: balance;
}

.standfirst {
  margin: 0;
  max-width: 62ch;
  color: var(--muted);
  font-size: 16px;
}

.tally {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 12px 0 0;
  border-top: 1px solid var(--hairline-strong);
  border-bottom: 1px solid var(--hairline);
}
.tally > div {
  padding: 14px 26px 14px 0;
  margin-right: 26px;
  border-right: 1px solid var(--hairline);
}
.tally > div:last-child { border-right: 0; margin-right: 0; padding-right: 0; }
.tally dt {
  margin: 0 0 3px;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--faint);
}
.tally dd {
  margin: 0;
  font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', 'Segoe UI Mono',
               'Roboto Mono', Menlo, Consolas, monospace;
  font-size: 22px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
.tally dd small { font-size: 12px; color: var(--muted); letter-spacing: 0; }

/* ---------- command bar ---------- */

.commandbar {
  position: sticky;
  top: 0;
  z-index: 20;
  margin-top: 26px;
  background: color-mix(in srgb, var(--ground) 88%, transparent);
  backdrop-filter: saturate(1.4) blur(10px);
  border-bottom: 1px solid var(--hairline);
}
.commandbar .wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 14px;
  padding-bottom: 14px;
}

.searchrow { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }

.searchfield { position: relative; flex: 1 1 300px; min-width: 220px; }
.searchfield input {
  width: 100%;
  padding: 10px 82px 10px 13px;
  font: inherit;
  font-size: 15px;
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  border-radius: 3px;
}
.searchfield input::placeholder { color: var(--faint); }
.searchfield input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
  border-color: var(--accent);
}
.searchfield kbd {
  position: absolute;
  right: 10px; top: 50%; transform: translateY(-50%);
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 10.5px;
  color: var(--faint);
  border: 1px solid var(--hairline);
  border-radius: 3px;
  padding: 2px 6px;
  pointer-events: none;
}

.btn {
  font: inherit;
  font-size: 13px;
  padding: 9px 14px;
  color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  border-radius: 3px;
  cursor: pointer;
  white-space: nowrap;
}
.btn:hover { border-color: var(--accent); color: var(--accent); }
.btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

select.btn { padding-right: 10px; }

.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  font: inherit;
  font-size: 12.5px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 11px 5px 9px;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--hairline-strong);
  border-radius: 999px;
  cursor: pointer;
}
.chip::before {
  content: "";
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--chip-hue, var(--faint));
  flex: none;
}
.chip:hover { color: var(--ink); border-color: var(--chip-hue, var(--accent)); }
.chip:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.chip[aria-pressed="true"] {
  color: var(--ink);
  border-color: var(--chip-hue, var(--accent));
  background: color-mix(in srgb, var(--chip-hue, var(--accent)) 14%, transparent);
  font-weight: 600;
}
.chip b {
  font-variant-numeric: tabular-nums;
  font-weight: inherit;
  color: var(--faint);
}
.chip[aria-pressed="true"] b { color: inherit; }

/* ---------- directory ---------- */

main { padding: 8px 0 80px; }

.group { margin-top: 40px; }
.group-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--group-hue, var(--hairline-strong));
}
.group-head h2 {
  margin: 0;
  font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino,
               'Book Antiqua', 'URW Palladio L', Georgia, serif;
  font-size: 23px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--group-hue, var(--ink));
}
.group-head .count {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--faint);
}
.group-head .blurb { margin: 0; margin-left: auto; font-size: 13px; color: var(--muted); }

.rows { border-bottom: 1px solid var(--hairline); }

.row {
  display: grid;
  grid-template-columns: minmax(170px, 1.35fr) minmax(130px, 1.1fr) minmax(200px, 1.5fr) 148px 120px;
  gap: 16px;
  align-items: start;
  padding: 13px 12px 13px 14px;
  border-bottom: 1px solid var(--hairline);
  border-left: 3px solid var(--group-hue, transparent);
  background: var(--surface);
}
.row:hover { background: color-mix(in srgb, var(--group-hue, var(--accent)) 5%, var(--surface)); }

.who { min-width: 0; }
.who .name { font-weight: 600; letter-spacing: -0.005em; }
.who .title { font-size: 12.5px; color: var(--muted); }
.who .note {
  margin: 5px 0 0;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--muted);
  border-left: 2px solid var(--hairline);
  padding-left: 8px;
}

.org { min-width: 0; font-size: 13.5px; }
.org .unknown { color: var(--faint); font-style: italic; }

.contactcol { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.mono {
  font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', 'Segoe UI Mono',
               'Roboto Mono', Menlo, Consolas, monospace;
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}
.copy {
  font: inherit;
  font-family: ui-monospace, 'SF Mono', 'Cascadia Mono', 'Segoe UI Mono',
               'Roboto Mono', Menlo, Consolas, monospace;
  font-size: 12.5px;
  text-align: left;
  padding: 1px 4px 1px 0;
  color: var(--ink);
  background: none;
  border: 0;
  border-bottom: 1px dotted var(--hairline-strong);
  cursor: pointer;
  overflow-wrap: anywhere;
}
.copy:hover { color: var(--accent); border-bottom-color: var(--accent); }
.copy:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.phone { color: var(--muted); }

.activity { display: flex; flex-direction: column; gap: 5px; }
.bar {
  display: flex;
  height: 5px;
  background: var(--hairline);
  border-radius: 2px;
  overflow: hidden;
}
.bar i { display: block; height: 100%; }
.bar .in  { background: var(--bar-in); }
.bar .out { background: var(--bar-out); }
.legend {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  display: flex;
  gap: 9px;
}
.legend .swatch-in  { color: var(--bar-in); }
.legend .swatch-out { color: var(--bar-out); }

.indirect {
  font-size: 11.5px;
  color: var(--faint);
  font-style: italic;
  border-left: 2px solid var(--hairline-strong);
  padding-left: 7px;
}
.row-indirect .name { font-weight: 500; }

.dates {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
  color: var(--muted);
  text-align: right;
}
.dates .last { color: var(--ink); }
.dates .first { color: var(--faint); }

.empty {
  margin-top: 48px;
  padding: 34px;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--hairline-strong);
  border-radius: 3px;
}

/* ---------- footer + toast ---------- */

footer {
  border-top: 1px solid var(--hairline);
  padding: 26px 0 60px;
  font-size: 12.5px;
  color: var(--muted);
}
footer .wrap { display: flex; flex-direction: column; gap: 7px; }
footer strong { color: var(--ink); font-weight: 600; }

/* ---------- composer ---------- */

.btn-accent { border-color: var(--accent); color: var(--accent); font-weight: 600; }
.btn-accent:hover { background: var(--accent-soft); }
.btn-sm { font-size: 12px; padding: 5px 10px; }

.sheet {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(10, 14, 18, 0.5);
  padding: 0;
}
.sheet[hidden] { display: none; }

.sheet-panel {
  display: flex;
  flex-direction: column;
  width: min(760px, 100%);
  max-height: 92vh;
  background: var(--surface);
  border: 1px solid var(--hairline-strong);
  border-bottom: 0;
  border-radius: 4px 4px 0 0;
  box-shadow: var(--shadow);
}
@media (min-width: 700px) {
  .sheet { align-items: center; padding: 24px; }
  .sheet-panel { border-bottom: 1px solid var(--hairline-strong); border-radius: 4px; }
}

.sheet-head, .sheet-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  flex: none;
}
.sheet-head { border-bottom: 1px solid var(--hairline); }
.sheet-foot { border-top: 1px solid var(--hairline); flex-wrap: wrap; }
.sheet-head h2 {
  margin: 0;
  margin-right: auto;
  font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino,
               'Book Antiqua', Georgia, serif;
  font-size: 20px;
  font-weight: 600;
}
.sheet-foot .btn-accent { margin-left: auto; }

.sheet-body {
  overflow-y: auto;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sheet-note { margin: 0; font-size: 13px; color: var(--muted); }
.sheet-note strong { color: var(--ink); }

.fld { display: flex; flex-direction: column; gap: 5px; }
.fld > span {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--faint);
}
.fld > span em { font-weight: 400; letter-spacing: 0; text-transform: none; }
.fld > span code {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11px;
  color: var(--accent);
}
.fld input, .fld textarea {
  font: inherit;
  font-size: 14px;
  padding: 9px 11px;
  color: var(--ink);
  background: var(--ground);
  border: 1px solid var(--hairline-strong);
  border-radius: 3px;
  resize: vertical;
}
.fld input:focus-visible, .fld textarea:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.cmp-optrow { display: flex; flex-wrap: wrap; gap: 14px; }
.chk { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted); }
.chk input { accent-color: var(--accent); }

.cmp-preview { border: 1px solid var(--hairline); border-radius: 3px; }
.cmp-preview-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--muted);
  background: var(--ground);
  border-bottom: 1px solid var(--hairline);
}
.cmp-preview-head strong { color: var(--ink); }
.cmp-preview-head .btn { margin-left: auto; }
.cmp-preview-body { padding: 12px 14px; max-height: 240px; overflow-y: auto; }
#cmp-render {
  font-size: 13.5px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
#cmp-render .subj {
  font-weight: 600;
  padding-bottom: 7px;
  margin-bottom: 9px;
  border-bottom: 1px solid var(--hairline);
  white-space: normal;
}
#cmp-render .optout {
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--hairline);
  font-size: 12px;
  color: var(--muted);
}
.cmp-excluded { margin: 0; font-size: 12.5px; color: var(--muted); }

#toast {
  position: fixed;
  left: 50%;
  bottom: 26px;
  transform: translate(-50%, 14px);
  background: var(--ink);
  color: var(--ground);
  font-size: 13px;
  padding: 9px 16px;
  border-radius: 3px;
  box-shadow: var(--shadow);
  opacity: 0;
  pointer-events: none;
  transition: opacity .18s ease, transform .18s ease;
  z-index: 60;
}
#toast.show { opacity: 1; transform: translate(-50%, 0); }

@media (prefers-reduced-motion: reduce) {
  #toast { transition: none; }
}

@media (max-width: 880px) {
  .row { grid-template-columns: 1fr 1fr; gap: 10px; }
  .contactcol { grid-column: 1 / -1; }
  .activity { grid-column: 1 / 2; }
  .dates { grid-column: 2 / 3; text-align: left; }
  .group-head .blurb { margin-left: 0; flex-basis: 100%; }
}
@media (max-width: 560px) {
  .wrap { padding: 0 16px; }
  .row { grid-template-columns: 1fr; }
  .dates, .activity { grid-column: auto; }
  .tally > div { padding-right: 18px; margin-right: 18px; }
}
"""

JS = """
const BYCAT = new Map(DATA.categories.map(c => [c.key, c]));
const state = { q: '', cats: new Set(), sort: 'activity' };

const maxTotal = Math.max(1, ...DATA.contacts.map(c => c.i + c.o));
const logmax = Math.log(maxTotal + 1);

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g,
  m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));

function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 1900);
}

async function copy(text, label) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e2) { toast('Copy blocked by the browser'); ta.remove(); return; }
    ta.remove();
  }
  toast(label);
}

function visible() {
  const q = state.q.trim().toLowerCase();
  const terms = q ? q.split(/\\s+/) : [];
  return DATA.contacts.filter(c => {
    if (state.cats.size && !state.cats.has(c.k)) return false;
    if (!terms.length) return true;
    const hay = c.hay;
    return terms.every(t => hay.includes(t));
  });
}

function sortRows(rows) {
  const by = state.sort;
  const copy = rows.slice();
  if (by === 'name') copy.sort((a, b) => a.n.localeCompare(b.n));
  else if (by === 'recent') copy.sort((a, b) => (b.ls || '').localeCompare(a.ls || '') || (b.i + b.o) - (a.i + a.o));
  else copy.sort((a, b) => (b.i + b.o) - (a.i + a.o) || a.n.localeCompare(b.n));
  return copy;
}

function rowHTML(c) {
  const total = c.i + c.o;
  const width = total ? Math.max(4, (Math.log(total + 1) / logmax) * 100) : 0;
  const inPct = total ? (c.i / total) * 100 : 0;
  const outPct = total ? (c.o / total) * 100 : 0;
  const phone = c.p && c.p.length
    ? `<button class="copy phone" data-copy="${esc(c.p[0])}" data-label="Phone copied">${esc(c.p[0])}</button>`
    : '';
  // No direct correspondence: the address came out of a forwarded thread, so
  // an empty bar would read as "no data" rather than "never emailed directly".
  const activity = total
    ? `<div class="bar" style="width:${width.toFixed(1)}%" role="img"
            aria-label="${c.i} received, ${c.o} sent">
         <i class="in" style="width:${inPct.toFixed(1)}%"></i><i class="out" style="width:${outPct.toFixed(1)}%"></i>
       </div>
       <div class="legend"><span class="swatch-in">${c.i} in</span><span class="swatch-out">${c.o} out</span></div>`
    : `<div class="indirect" title="Address found in a forwarded thread, not in direct correspondence">Never emailed directly</div>`;
  return `<div class="row${total ? '' : ' row-indirect'}">
    <div class="who">
      <div class="name">${esc(c.n)}</div>
      ${c.t ? `<div class="title">${esc(c.t)}</div>` : ''}
      ${c.note ? `<p class="note">${esc(c.note)}</p>` : ''}
    </div>
    <div class="org">${c.co ? esc(c.co) : '<span class="unknown">Company unknown</span>'}</div>
    <div class="contactcol">
      <button class="copy" data-copy="${esc(c.e)}" data-label="Email address copied">${esc(c.e)}</button>
      ${phone}
    </div>
    <div class="activity">${activity}</div>
    <div class="dates">
      <div class="last">${esc(c.ls || '—')}</div>
      <div class="first">${total ? 'since ' : 'seen '}${esc(c.fs || '—')}</div>
    </div>
  </div>`;
}

function render() {
  const rows = visible();
  const host = document.getElementById('directory');
  const counts = new Map();
  for (const c of DATA.contacts) counts.set(c.k, (counts.get(c.k) || 0) + 1);

  // chip counts reflect the search term, not the category filter itself
  const q = state.q.trim().toLowerCase();
  const terms = q ? q.split(/\\s+/) : [];
  const searchCounts = new Map();
  for (const c of DATA.contacts) {
    if (terms.length && !terms.every(t => c.hay.includes(t))) continue;
    searchCounts.set(c.k, (searchCounts.get(c.k) || 0) + 1);
  }
  for (const btn of document.querySelectorAll('.chip')) {
    const k = btn.dataset.cat;
    btn.querySelector('b').textContent = searchCounts.get(k) || 0;
  }

  if (!rows.length) {
    host.innerHTML = `<div class="wrap"><p class="empty">No contacts match that search.</p></div>`;
    document.getElementById('shown').textContent = '0';
    return;
  }

  const groups = new Map();
  for (const c of rows) {
    if (!groups.has(c.k)) groups.set(c.k, []);
    groups.get(c.k).push(c);
  }

  let out = '<div class="wrap">';
  for (const cat of DATA.categories) {
    const list = groups.get(cat.key);
    if (!list) continue;
    out += `<section class="group" style="--group-hue:var(--hue-${cat.key})">
      <div class="group-head">
        <h2>${esc(cat.label)}</h2>
        <span class="count">${list.length} of ${counts.get(cat.key) || 0}</span>
        <p class="blurb">${esc(cat.blurb)}</p>
      </div>
      <div class="rows">${sortRows(list).map(rowHTML).join('')}</div>
    </section>`;
  }
  out += '</div>';
  host.innerHTML = out;
  document.getElementById('shown').textContent = String(rows.length);
}

document.addEventListener('click', e => {
  const c = e.target.closest('.copy');
  if (c) { copy(c.dataset.copy, c.dataset.label); return; }
  const chip = e.target.closest('.chip');
  if (chip) {
    const k = chip.dataset.cat;
    if (state.cats.has(k)) state.cats.delete(k); else state.cats.add(k);
    chip.setAttribute('aria-pressed', state.cats.has(k) ? 'true' : 'false');
    render();
  }
});

document.getElementById('search').addEventListener('input', e => {
  state.q = e.target.value;
  render();
});

document.getElementById('sort').addEventListener('change', e => {
  state.sort = e.target.value;
  render();
});

document.getElementById('clear').addEventListener('click', () => {
  state.q = '';
  state.cats.clear();
  document.getElementById('search').value = '';
  for (const b of document.querySelectorAll('.chip')) b.setAttribute('aria-pressed', 'false');
  render();
});

document.getElementById('copyall').addEventListener('click', () => {
  const rows = visible();
  if (!rows.length) { toast('Nothing to copy'); return; }
  copy(rows.map(c => c.e).join('; '), `${rows.length} email addresses copied`);
});

document.addEventListener('keydown', e => {
  const s = document.getElementById('search');
  if (e.key === '/' && document.activeElement !== s) { e.preventDefault(); s.focus(); s.select(); }
  else if (e.key === 'Escape' && document.activeElement === s) { s.value = ''; state.q = ''; render(); s.blur(); }
});

// Download the current selection as a spreadsheet-ready file. Only offered
// when the viewer's runtime grants saves.
const dl = document.getElementById('download');
if (window.claude && window.claude.downloads) {
  dl.hidden = false;
  const cell = v => {
    const s = String(v == null ? '' : v);
    return /[",\\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const csv = rows => [
    ['Name', 'Category', 'Company', 'Job title', 'Email', 'Phone',
     'First seen', 'Last seen', 'Emails in', 'Emails out', 'How found', 'Notes'],
    ...rows.map(c => [
      c.n, BYCAT.get(c.k).label, c.co, c.t, c.e, (c.p || []).join(' / '),
      c.fs, c.ls, c.i, c.o,
      (c.i + c.o) ? 'Direct correspondence' : 'Named in a thread', c.note,
    ]),
  ].map(r => r.map(cell).join(',')).join('\\r\\n');

  dl.addEventListener('click', async () => {
    const rows = visible();
    if (!rows.length) { toast('Nothing to download'); return; }
    const body = '\\ufeff' + csv(rows);          // BOM so Excel reads UTF-8
    const stem = 'REL-contacts-' + DATA.refreshed;
    try {
      await window.claude.downloads.save({ filename: stem + '.csv', data: body });
      toast(`${rows.length} contacts downloaded`);
    } catch (err) {
      const code = err && err.code;
      if (code === 'declined') return;
      if (code === 'extension_not_enabled') {
        try {
          await window.claude.downloads.save({ filename: stem + '.txt', data: body });
          toast(`${rows.length} contacts downloaded as a .txt — rename to .csv to open in Excel`);
          return;
        } catch (err2) {
          if (err2 && err2.code === 'declined') return;
        }
      }
      if (code === 'rate_limited') { toast('Another download is already open'); return; }
      if (code === 'too_large') { toast('Too much to download — narrow the filter first'); return; }
      dl.hidden = true;
      toast('Downloads are unavailable here — use Copy shown emails instead');
    }
  });
}

// ---------- composer ----------
// This page never sends. It assembles the mail and hands it to Outlook, so a
// human always presses the button — and recipients always go in Bcc.

const cmp = {
  el: document.getElementById('composer'),
  subject: document.getElementById('cmp-subject'),
  body: document.getElementById('cmp-body'),
  skipDne: document.getElementById('cmp-skipdne'),
  skipInternal: document.getElementById('cmp-skipinternal'),
  sig: document.getElementById('cmp-sig'),
  idx: 0,
};

const INTERNAL_KEY = (DATA.categories.find(c => /^Internal/.test(c.label)) || {}).key;
const OPT_OUT = 'Reply with "unsubscribe" and I will take you off this list.';

function audience() {
  return visible().filter(c => {
    if (cmp.skipDne.checked && c.dne) return false;
    if (cmp.skipInternal.checked && c.k === INTERNAL_KEY) return false;
    return true;
  });
}

function firstNameOf(c) {
  const n = (c.n || '').trim();
  if (!n || n.includes('@')) return 'there';
  return n.split(/\\s+/)[0];
}

function merge(text, c) {
  return String(text || '')
    .replace(/\\{\\{\\s*first\\s*\\}\\}/gi, firstNameOf(c))
    .replace(/\\{\\{\\s*name\\s*\\}\\}/gi, c.n || '')
    .replace(/\\{\\{\\s*company\\s*\\}\\}/gi, c.co || 'your firm');
}

function cmpRender() {
  const list = audience();
  document.getElementById('cmp-count').textContent = String(list.length);
  const excluded = visible().length - list.length;
  document.getElementById('cmp-excluded').textContent = excluded
    ? `${excluded} of the ${visible().length} shown contacts excluded by the filters above.`
    : '';

  if (!list.length) {
    document.getElementById('cmp-who').textContent = '—';
    document.getElementById('cmp-render').textContent = 'No recipients.';
    return;
  }
  if (cmp.idx >= list.length) cmp.idx = 0;
  const c = list[cmp.idx];
  document.getElementById('cmp-who').textContent =
    `${c.n}${c.co ? ' · ' + c.co : ''} · ${c.e}`;
  const out = document.getElementById('cmp-render');
  out.textContent = '';
  const s = document.createElement('div');
  s.className = 'subj';
  s.textContent = merge(cmp.subject.value, c) || '(no subject)';
  const b = document.createElement('div');
  b.textContent = merge(cmp.body.value, c) || '(no message yet)';
  out.append(s, b);
  if (cmp.sig.checked) {
    const o = document.createElement('div');
    o.className = 'optout';
    o.textContent = OPT_OUT;
    out.append(o);
  }
}

function bodyFor(c) {
  let t = merge(cmp.body.value, c);
  if (cmp.sig.checked) t += '\\n\\n' + OPT_OUT;
  return t;
}

function openComposer() {
  cmp.idx = 0;
  cmp.el.hidden = false;
  cmpRender();
  cmp.subject.focus();
}
function closeComposer() { cmp.el.hidden = true; }

document.getElementById('compose').addEventListener('click', openComposer);
document.getElementById('cmp-close').addEventListener('click', closeComposer);
cmp.el.addEventListener('click', e => { if (e.target === cmp.el) closeComposer(); });
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && !cmp.el.hidden) closeComposer();
});
for (const id of ['cmp-subject', 'cmp-body', 'cmp-skipdne', 'cmp-skipinternal', 'cmp-sig']) {
  document.getElementById(id).addEventListener('input', cmpRender);
  document.getElementById(id).addEventListener('change', cmpRender);
}
document.getElementById('cmp-cycle').addEventListener('click', () => {
  cmp.idx += 1;
  cmpRender();
});

document.getElementById('cmp-bcc').addEventListener('click', () => {
  const list = audience();
  if (!list.length) { toast('No recipients'); return; }
  copy(list.map(c => c.e).join('; '), `${list.length} addresses copied — paste into Bcc`);
});

document.getElementById('cmp-text').addEventListener('click', () => {
  const list = audience();
  if (!list.length) { toast('No recipients'); return; }
  // One generic copy: merge fields resolve per-recipient only in the CSV, so a
  // single pasted body uses neutral wording rather than one person's name.
  const generic = { n: '', co: '', e: '' };
  const subj = merge(cmp.subject.value, generic);
  copy(subj + '\\n\\n' + bodyFor(generic),
       'Subject and body copied — merge fields left generic');
});

document.getElementById('cmp-mailto').addEventListener('click', () => {
  const list = audience();
  if (!list.length) { toast('No recipients'); return; }
  const generic = { n: '', co: '', e: '' };
  const url = 'mailto:?bcc=' + encodeURIComponent(list.map(c => c.e).join(';'))
    + '&subject=' + encodeURIComponent(merge(cmp.subject.value, generic))
    + '&body=' + encodeURIComponent(bodyFor(generic));
  // Long recipient lists blow past what a mailto: URL can carry; fall back to
  // the clipboard rather than silently opening a truncated draft.
  if (url.length > 1800) {
    copy(list.map(c => c.e).join('; '),
         `${list.length} addresses is too many for a mailto link — Bcc list copied instead`);
    return;
  }
  window.location.href = url;
});

const cmpMerge = document.getElementById('cmp-merge');
if (window.claude && window.claude.downloads) {
  cmpMerge.hidden = false;
  cmpMerge.addEventListener('click', async () => {
    const list = audience();
    if (!list.length) { toast('No recipients'); return; }
    const cell = v => {
      const s = String(v == null ? '' : v);
      return /[",\\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    const rows = [['Name', 'First name', 'Company', 'Email', 'Subject', 'Body'],
      ...list.map(c => [c.n, firstNameOf(c), c.co, c.e,
                        merge(cmp.subject.value, c), bodyFor(c)])];
    const body = '\\ufeff' + rows.map(r => r.map(cell).join(',')).join('\\r\\n');
    const stem = 'REL-campaign-' + DATA.refreshed;
    try {
      await window.claude.downloads.save({ filename: stem + '.csv', data: body });
      toast(`${list.length} personalised rows downloaded`);
    } catch (err) {
      const code = err && err.code;
      if (code === 'declined') return;
      if (code === 'extension_not_enabled') {
        try {
          await window.claude.downloads.save({ filename: stem + '.txt', data: body });
          toast('Downloaded as .txt — rename to .csv for Outlook mail merge');
          return;
        } catch (e2) { if (e2 && e2.code === 'declined') return; }
      }
      cmpMerge.hidden = true;
      toast('Downloads unavailable here — use Copy Bcc list instead');
    }
  });
}

render();
"""


def build(payload, out_path):
    cfg = {**DEFAULT_CONFIG, **(payload.get("config") or {})}
    org = cfg["org_name"] or "Contact"
    internal_label = f"Internal ({org})" if cfg["org_name"] else "Internal"
    label_of = {c: (internal_label if c == "Internal" else c) for c in CATEGORY_ORDER}

    contacts = [c for c in payload["contacts"] if c.get("keep", True)]
    refreshed = (payload.get("last_sweep_utc") or "")[:10] or date.today().isoformat()

    present = [c for c in CATEGORY_ORDER
               if any(x.get("category") == c for x in contacts)]
    counts = {c: sum(1 for x in contacts if x.get("category") == c) for c in present}

    slim = []
    for c in contacts:
        cat = c.get("category", "Personal / Other")
        name = c.get("name") or c["email"].split("@")[0]
        hay = " ".join(filter(None, [
            name, c.get("company", ""), c.get("job_title", ""), c["email"],
            c.get("note", ""), cat,
        ])).lower()
        slim.append({
            "n": name,
            "e": c["email"],
            "co": c.get("company", ""),
            "t": c.get("job_title", ""),
            "p": c.get("phones", []) or [],
            "k": CATEGORY_KEY[cat],
            "note": c.get("note", ""),
            "i": int(c.get("count_from", 0) or 0),
            "o": int(c.get("count_to", 0) or 0),
            "fs": c.get("first_seen", ""),
            "ls": c.get("last_seen", ""),
            "dne": bool(c.get("do_not_email")),
            "hay": hay,
        })
    slim.sort(key=lambda c: -(c["i"] + c["o"]))

    data = {
        "refreshed": refreshed,
        "owner": cfg["owner_name"],
        "ownerFirst": cfg["owner_first_name"] or cfg["owner_name"].split(" ")[0],
        "ownerEmail": cfg["owner_email"],
        "org": cfg["org_name"],
        "contacts": slim,
        "categories": [
            {"key": CATEGORY_KEY[c], "label": label_of[c],
             "blurb": CATEGORY_BLURB.get(c, "")}
            for c in present
        ],
    }

    cat_light = "\n".join(
        "  --hue-%s: %s;" % (CATEGORY_KEY[c], CATEGORY_HUE[c][0]) for c in present)
    cat_dark = " ".join(
        "--hue-%s: %s;" % (CATEGORY_KEY[c], CATEGORY_HUE[c][1]) for c in present)
    dark_tokens = (
        "--ground: #111519; --surface: #181D23; --ink: #E4E9EE; --muted: #97A2AE; "
        "--faint: #6F7B87; --hairline: #262D35; --hairline-strong: #39434D; "
        "--accent: #D9AB58; --accent-soft: rgba(217, 171, 88, 0.16); "
        "--bar-in: #63A8C7; --bar-out: #D9AB58; "
        "--shadow: 0 1px 2px rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.34); " + cat_dark
    )
    css = (CSS.replace("__CAT_LIGHT__", cat_light)
              .replace("__DARK_TOKENS__", dark_tokens))

    total = len(contacts)
    n_broker = counts.get("Broker", 0)
    n_lender = counts.get("Lender / Bank", 0)
    n_borrow = counts.get("Borrower / Sponsor", 0)
    n_phone = sum(1 for c in contacts if c.get("phones"))

    chips = "\n".join(
        '<button class="chip" type="button" data-cat="{k}" aria-pressed="false" '
        'style="--chip-hue:var(--hue-{k})">{label} <b>{n}</b></button>'.format(
            k=CATEGORY_KEY[c], label=html.escape(label_of[c]), n=counts[c])
        for c in present)

    title = f"{org} — Contact Directory" if cfg["org_name"] else "Contact Directory"
    eyebrow = " &middot; ".join(
        html.escape(x) for x in (cfg["org_name"], cfg["org_locale"]) if x)
    corrections_to = html.escape(cfg["owner_first_name"] or cfg["owner_name"] or "the list owner")
    built_from = (f"Built from the {html.escape(org)} mailbox"
                  if cfg["org_name"] else "Built from the mailbox")

    page = f"""<title>{html.escape(title)}</title>
<style>{css}</style>

<header class="masthead">
  <div class="wrap">
    <p class="eyebrow">{eyebrow}</p>
    <h1>Contact Directory</h1>
    <p class="standfirst">{html.escape(cfg["org_blurb"])}</p>
    <dl class="tally">
      <div><dt>Contacts</dt><dd>{total}</dd></div>
      <div><dt>Brokers</dt><dd>{n_broker}</dd></div>
      <div><dt>Lenders &amp; banks</dt><dd>{n_lender}</dd></div>
      <div><dt>Borrowers</dt><dd>{n_borrow}</dd></div>
      <div><dt>With a phone number</dt><dd>{n_phone}</dd></div>
      <div><dt>Last refreshed</dt><dd><small>{html.escape(refreshed)}</small></dd></div>
    </dl>
  </div>
</header>

<div class="commandbar">
  <div class="wrap">
    <div class="searchrow">
      <div class="searchfield">
        <input id="search" type="search" autocomplete="off" spellcheck="false"
               placeholder="Search name, firm, email or deal note" aria-label="Search contacts">
        <kbd>/</kbd>
      </div>
      <select id="sort" class="btn" aria-label="Sort contacts">
        <option value="activity">Most correspondence</option>
        <option value="recent">Most recent contact</option>
        <option value="name">Name A–Z</option>
      </select>
      <button id="copyall" class="btn" type="button">Copy shown emails</button>
      <button id="download" class="btn" type="button" hidden>Download shown</button>
      <button id="compose" class="btn btn-accent" type="button">Email shown…</button>
      <button id="clear" class="btn" type="button">Reset</button>
    </div>
    <div class="chips">{chips}</div>
  </div>
</div>

<main id="directory"></main>

<div id="composer" class="sheet" hidden>
  <div class="sheet-panel" role="dialog" aria-modal="true" aria-labelledby="composer-title">
    <div class="sheet-head">
      <h2 id="composer-title">Email <span id="cmp-count">0</span> contacts</h2>
      <button id="cmp-close" class="btn" type="button">Close</button>
    </div>
    <div class="sheet-body">
      <p class="sheet-note">Nothing is sent from this page. Write the mail here,
        then take it to Outlook one of three ways — the recipients always land in
        <strong>Bcc</strong> so nobody sees anyone else's address.</p>

      <label class="fld">
        <span>Subject</span>
        <input id="cmp-subject" type="text" placeholder="REL Finance — current bridging terms">
      </label>

      <label class="fld">
        <span>Message <em>— <code>{{{{first}}}}</code>, <code>{{{{name}}}}</code>,
          <code>{{{{company}}}}</code> are filled in per recipient</em></span>
        <textarea id="cmp-body" rows="9" placeholder="Hi {{{{first}}}},&#10;&#10;..."></textarea>
      </label>

      <div class="cmp-optrow">
        <label class="chk"><input id="cmp-skipdne" type="checkbox" checked>
          Skip anyone marked do-not-email</label>
        <label class="chk"><input id="cmp-skipinternal" type="checkbox" checked>
          Skip internal colleagues</label>
        <label class="chk"><input id="cmp-sig" type="checkbox" checked>
          Append opt-out line</label>
      </div>

      <div class="cmp-preview">
        <div class="cmp-preview-head">
          Preview for <strong id="cmp-who">—</strong>
          <button id="cmp-cycle" class="btn btn-sm" type="button">Next recipient</button>
        </div>
        <div class="cmp-preview-body"><div id="cmp-render"></div></div>
      </div>

      <p id="cmp-excluded" class="cmp-excluded"></p>
    </div>
    <div class="sheet-foot">
      <button id="cmp-bcc" class="btn" type="button">Copy Bcc list</button>
      <button id="cmp-text" class="btn" type="button">Copy subject &amp; body</button>
      <button id="cmp-merge" class="btn" type="button" hidden>Download mail-merge CSV</button>
      <button id="cmp-mailto" class="btn btn-accent" type="button">Open in Outlook</button>
    </div>
  </div>
</div>

<footer>
  <div class="wrap">
    <p><strong><span id="shown">{total}</span> of {total} contacts shown.</strong>
       Click any address or number to copy it. Press <kbd>/</kbd> to search.</p>
    <p>{built_from} (Inbox, Sent Items and Archive) and
       refreshed automatically every Monday. Job titles, firms and phone numbers
       are read from email signatures, so a blank field means no signature was
       found — not that the detail doesn't exist. <em>In</em> and <em>out</em>
       count messages received from and sent to that contact.</p>
    <p>Corrections go to {corrections_to} so they survive the next refresh — edits
       made to a downloaded copy will not.</p>
  </div>
</footer>

<div id="toast" role="status" aria-live="polite"></div>

<script>
const DATA = {json.dumps(data, separators=(",", ":"))};
{JS}
</script>
"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write(page)
    print(f"Wrote {out_path}: {total} contacts, {len(present)} categories, "
          f"{len(page):,} bytes")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    with open(DATA) as f:
        payload = json.load(f)
    build(payload, out)


if __name__ == "__main__":
    main()
