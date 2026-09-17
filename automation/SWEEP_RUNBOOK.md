# REL Deal Sheet — Daily Email Sweep Runbook

Purpose: every weekday morning, scan Shyam's Outlook mailbox (shyam@relfinance.co.uk,
Microsoft 365 connector) for new or updated lending deals and reflect them in
`Deals_Sheet_REL.xlsx`. This file is the procedure of record for the automated sweep.

## 0. Setup

1. Working branch: `claude/deal-sheet-auto-populate-svgr0b` on `slakhani123/dealsheet`.
   If the repo is not on disk, clone it; always `git fetch origin` and check out /
   fast-forward that branch before touching the sheet.
2. `automation/processed_deals.json` holds state: the last sweep timestamp and, per
   Outlook `conversationId`, what was done (sheet row, status). Read it first.
3. Python needs `openpyxl`. Recalc needs LibreOffice **Calc**
   (`apt-get install -y --no-install-recommends libreoffice-calc` if missing — core alone cannot load xlsx).

## 1. Find candidate emails

- Search window: since `last_sweep_utc` minus 1 day of overlap (dedupe makes overlap safe).
- Primary search: `mcp__Microsoft_365__outlook_email_search` with
  `query: "term sheet OR loan OR bridge OR LTV OR facility OR deal"`, `afterDateTime`, paginate.
- Also sweep Sent Items (folderName: 'Sent Items') for outgoing term sheets/proposals.
- Deal-relevant = a specific lending opportunity: new enquiry with terms, term sheet
  issued/revised, deal declined, deal moved to legals, commitment fee received, completed.
- NOT deal-relevant: meeting logistics, valuations chatter on existing completed loans,
  newsletters, company-registration notices (unless tied to a live deal thread).
- Read full bodies via `read_resource`; read PDF term sheets / DAs attached when terms
  are not in the body (attachment URIs come from the message read).

## 2. Dedupe and classify

For each deal thread (group by conversationId / property):
- Already logged in `processed_deals.json` with no new messages → skip.
- New messages on a known deal → UPDATE the existing sheet row (terms, status, comment).
- Deal already in the sheet under another name → match on figures/address before adding
  (e.g. "Moove" = "27 Gemini Business Park" row; brokers often use codenames).
- Genuinely new → ADD a row.

Destination:
- New/negotiating deals → `Potential Deals`, EARLY STAGE / NEGOTIATING section.
- Deal moved to legals → move row to the In Legals section (top table).
- REL declined or deal died → `Declined Deals` (append after last data row; new deals that
  died go straight here).
- Loan drew down → `Completed Deals`, **DRAWN — NOT YET REDEEMED** block (rows 14-15).
- Loan repaid → `Completed Deals`, **Redeemed Loans** block (rows 5-8), and remove it
  from the drawn block. Redeemed means the money came back, nothing weaker.

> **Drawn is not completed.** The sheet used to call a drawn loan "completed", which read
> Uxbridge and Stanmore as finished while both were still running — Uxbridge is past
> maturity with a default/extension underway. Keep the two blocks distinct.
>
> **Record REL's share.** Column V on Completed Deals (S on Potential Deals) holds REL's
> own participation where a loan is syndicated. Uxbridge is £8.2m whole but £2.05m REL;
> Appold was £21.07m whole and £4.214m REL. Without it every total overstates REL money.
> The figure comes from the lending forecast workbook's per-deal tab, not the deal sheet.

## 3. Sheet conventions (match exactly)

- Columns (Potential/Declined): A Date Received (datetime, 1st of receipt month, fmt mmm-yy) ·
  B Property Address · C Asset Class · D Borrower · E Senior/Mezz/Pref · F Deal Type ·
  G 'A'/'R' (acquisition/refinance) · H Net Loan £m (gross minus arrangement fee) ·
  I REL Return £m (total interest + fees over term) · J Gross Loan £m · K Collateral Value £m
  (MV, or purchase price if no MV) · L LTV as formula `=J{r}/K{r}` (or `=H{r}/K{r}` where the
  sheet row already does that) · M Length months · N IRR (annualised return incl fees, decimal) ·
  O Term Sheet Issued Y/N · P Commitment Fee Received Y/N · Q Broker / Direct · R Comments.
- Comments: dates as DD/MM, key terms, current status, next action. Put anything uncertain
  here rather than guessing a number; use 'TBC' for unknown text fields, leave numbers blank.
- Styles: copy the cell styles of the row above when inserting (font Arial 10, existing
  number formats).
- Inserting in EARLY STAGE: `insert_rows` before the blank row above the Total row, then
  REWRITE the Total row formulas (`=SUM(H20:H{last})`, `=AVERAGE(L20:L{last})`) — openpyxl
  does not expand ranges. The same applies to the other two sheets' Total rows
  (`Completed Deals` H10:K10 over rows 5–8, `Declined Deals` H96:K96 over rows 5–94):
  extend the range whenever you append a row, or the headline understates the book.

## 4. Verify, commit, report

1. Run recalc: `python3 /root/.claude/skills/xlsx/scripts/recalc.py Deals_Sheet_REL.xlsx 120`
   — must return `status: success` with 0 errors. (If the skill path is missing, any
   LibreOffice headless recalculation that preserves formulas is acceptable.)
2. Spot-check the changed rows with `load_workbook(data_only=True)`.
3. Update `automation/processed_deals.json` (bump `last_sweep_utc`, log each conversation
   handled with row ref + one-line outcome).
4. Commit with a message listing the deals touched; `git push -u origin
   claude/deal-sheet-auto-populate-svgr0b` (retry on network errors: 2s/4s/8s/16s).
5. If anything changed: send Shyam the updated file (SendUserFile) + a short summary table
   of added/updated rows, flagging every field marked TBC. If nothing changed: one line
   saying so — no file.
   Note: pushing the sheet also triggers `.github/workflows/upload-to-sharepoint.yml`,
   which copies it to the team's SharePoint (see automation/SHAREPOINT_SETUP.md) — the
   sweep itself does nothing extra for this, but if the Action fails after setup is
   complete, mention it to Shyam.
6. If the Microsoft 365 connector is unavailable when the sweep fires, say so and stop —
   do not guess.

## 4a. The sweep MUST run from a persistent session

**A routine that spawns a fresh session cannot read the mailbox.** Confirmed 17/09/2026:
the old sweep routine (`trig_01GbjCLH7se26NeUcusmKVxi`, fresh session, Microsoft-365 listed
in its `mcp_connections`) fired daily and reported SUCCEEDED, but its sessions received only
`Bash, Write, Edit, Read, Glob, Grep, Agent` — no `mcp__Microsoft_365__*` tools at all. It
last produced a commit on 08/09 and then burned ~20 minutes and several pounds of compute
every morning doing nothing. The freshness badge on the board was telling the truth the
whole time.

The control that proves it is the contacts routine (`trig_0175MEpBodZSz5vZM47ky5jg`), which
sweeps the SAME mailbox through the SAME connector and has succeeded every week — 13/08,
17/08, 24/08, 31/08, 07/09, 14/09. Its only material difference is that it wakes an
existing interactive session instead of spawning one.

So the sweep now runs from *Daily REL sweep + dashboard sync*
(`trig_017Fe5pm522n1jUBmgnAR2Yb`, 08:00 UTC daily), bound to
`session_01QbSriq6UGNWFocVGvEFtNh`, and does both the mailbox sweep and the board sync in
one turn. If that session is ever archived, BOTH halves stop silently — re-point the
routine with `update_trigger` rather than recreating it as a fresh-session routine, which
would reintroduce exactly this bug.

## 5. The dashboard is synced separately from the sweep's own commit

The team's live board is the Artifact **REL Pipeline Desk**
(`https://claude.ai/artifact/QakzsFdHVhWZmRGwuPd98P`). It keeps deal facts in an artifact
`db`, so the spreadsheet alone does not keep it current.

**A scheduled routine cannot write to it.** This was tested on 16/09/2026 with a throwaway
routine: a routine-fired cloud session gets `Bash, Write, Edit, Read, Glob, Grep, Agent`
and no `ArtifactData` — not even `ToolSearch` to go looking for it. The routines
documentation confirms there is no setting for this: "there is no permission-mode picker
and no approval prompts during a run… what a routine can reach is determined by the
repositories you select, the environment's network access and variables, and the
connectors you include." So **do not attempt the dashboard from the daily sweep**, and do
not report the board as updated.

Instead a second routine — *Daily dashboard sync (REL pipeline)*,
`trig_017Fe5pm522n1jUBmgnAR2Yb`, daily at 09:00 UTC — wakes an existing interactive
session rather than spawning a fresh one, and a woken session keeps its own tools. It
runs `automation/sync_dashboard.py`, which needs no mailbox access: everything it syncs
is already in the spreadsheet by the time it fires.

The hour's gap after the 08:00 sweep is deliberate — the sweep has taken ~25 minutes on
its longest run, so the sync reads a branch the sweep has already pushed to. If the sweep
ever grows past that, move the sync later rather than letting the two overlap; a sync that
runs mid-sweep just reports no changes and the board sits a day behind.

> **If the board stops updating, look here first.** That routine is bound to
> `session_01QbSriq6UGNWFocVGvEFtNh`. Archiving or deleting that session leaves the
> routine firing into nothing, silently. Re-point it with `update_trigger`, or create a
> replacement bound to a current session.

### What the sync may and may not write

`sync_dashboard.py` enforces this, but the rule matters more than the script:

- **The sheet owns** `dateReceived`, `property`, `assetClass`, `borrower`, `tranche`,
  `dealType`, `acqRefi`, `netLoan`, `relReturn`, `grossLoan`, `collateral`, `ltv`,
  `months`, `irr`, `tsIssued`, `commitFee`, `source`, `sheetComments`, `sheetSection`
  and `derivedStage`.
- **The team owns** `stage`, `owner`, `rag`, `nextAction`, `nextActionDue`, `teamNote`,
  `reviewedWeek`, `updatedBy`, `updatedAt`, `createdBy` and `origin`. Never write these.
  Overwriting them silently discards someone's Monday review. One field, one writer.
- `ltvBasis` and `flags` are set when a deal is first created and left alone after:
  `ltvBasis` is an inference, and `flags` is written by the integrity check, so syncing it
  from the sheet would wipe findings like `also-in-declined` on the next run.
- Pin every write to an existing document with `if_version`.
- Nothing is ever deleted. A deal on the board but not in the sheet is reported, because
  a hand-added deal legitimately lives only on the board.

Deals carrying `origin: "manual"` were typed straight into the board — phone enquiries the
mailbox never sees. They are NOT in the spreadsheet. When one turns up in the mailbox
later, add it to `Potential Deals` as normal and drop the `origin` field on its db doc so
it stops showing the "added here" badge — do not create a second row for it.
