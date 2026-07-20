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
- Completed/drawn → `Completed Deals`.

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
  does not expand ranges. Known quirk (do not "fix" without being asked): Declined Deals
  total row sums H5:H19 only.

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
