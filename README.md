# REL Finance — deal sheet & contact list automation

Two things live here, both built from Shyam's Outlook mailbox and both kept
current without anyone having to remember to do it.

| Deliverable | Source of truth | Rebuilt by | Refresh |
|---|---|---|---|
| `Deals_Sheet_REL.xlsx` | the workbook itself | the daily sweep | every weekday morning |
| `Contact_List_REL.xlsx` + `contacts_site/index.html` | `automation/contacts_data.json` | `automation/build_contacts_xlsx.py` and `build_contacts_html.py` | every Monday |

Both are pushed to the team's SharePoint area automatically on every commit
that changes them, by the two workflows in `.github/workflows/`.

## Deal sheet

The master copy of REL's potential and declined deals. A daily sweep reads new
deal emails, applies adds and updates, and pushes the workbook. Procedure of
record: `automation/SWEEP_RUNBOOK.md`. Scheduling: `automation/ROUTINE_SETUP.md`.
State (which email conversations have already been processed) lives in
`automation/processed_deals.json`.

## Contact list

Every counterparty REL corresponds with, categorised by the role they play in a
deal — broker, lender, borrower, solicitor, valuer, investor, accountant. Two
renderings of the same data:

- **`Contact_List_REL.xlsx`** — filterable workbook for SharePoint, with a
  summary tab and a README tab.
- **`contacts_site/index.html`** — a self-contained searchable directory page.
  Search across name, firm, email and deal note; filter by category; click any
  address or number to copy it; export the current selection as CSV. There are
  no external dependencies, so it works from a file share, an email attachment
  or a hosted URL. Published copy:
  <https://claude.ai/code/artifact/6ce4ca22-f49d-438e-9aa5-9ad656cfc7dd>
  (private until shared from the page's share menu). Republishing to that same
  URL is part of the weekly refresh.

Procedure of record: `automation/CONTACTS_RUNBOOK.md`.

## Ground rules

- **The repo is the source of truth.** Do not hand-edit either workbook in
  SharePoint — the next automated run overwrites it. Corrections go through the
  automation (or ask Claude to make them), so they land in the repo first.
- **Contact corrections stick** if they are marked `"category_locked": true` in
  `automation/contacts_data.json`; the weekly refresh leaves those records
  alone.
- **Nothing is guessed.** If the Microsoft 365 connection is unavailable on a
  scheduled run, the run reports that and changes nothing.

## Rebuilding by hand

```bash
pip install openpyxl
python3 automation/build_contacts_xlsx.py     # -> Contact_List_REL.xlsx
python3 automation/build_contacts_html.py     # -> contacts_site/index.html
```

## SharePoint upload

One Entra app registration serves both uploads. Setup, resolved values for the
RELfinance tenant, and troubleshooting: `automation/SHAREPOINT_SETUP.md`.
Until the credentials are configured the upload workflows fail with
"Missing required configuration", which is harmless — the files are still
committed to the repo.
