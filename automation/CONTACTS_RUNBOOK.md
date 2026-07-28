# Contact list — weekly refresh runbook

Procedure of record for refreshing `Contact_List_REL.xlsx` from Shyam's Outlook
mailbox (shyam@relfinance.co.uk). Followed by the weekly automated routine; also
usable manually ("refresh the contact list").

## Files

| File | Role |
|---|---|
| `automation/contacts_data.json` | Master data — the source of truth. Holds every contact ever harvested (including `keep:false` exclusions) plus `last_sweep_utc`. |
| `automation/build_contacts_xlsx.py` | Renders the JSON into `Contact_List_REL.xlsx`. |
| `automation/build_contacts_html.py` | Renders the same JSON into a self-contained searchable web page. |
| `Contact_List_REL.xlsx` | The shareable workbook. Generated — never hand-edit. |
| `contacts_site/index.html` | The shareable web directory. Generated — never hand-edit. |
| `.github/workflows/upload-contacts-to-sharepoint.yml` | On push, uploads the xlsx to the team SharePoint area (same credentials as the deal-sheet uploader; see `SHAREPOINT_SETUP.md`). |

Two harvest routes feed the data, and the distinction matters when reading it:

- **Direct correspondence** — the address was a sender or recipient on a real
  message. These records carry `count_from` / `count_to` above zero.
- **Named in a thread** — the address was recovered from a forwarded message
  header or a quoted signature block. REL has never emailed them from this
  mailbox, so both counts are zero. Most brokers reach Shyam as a `FW:` from
  Sumeer or Tashin, so this route accounts for a large share of the broker
  list and must not be dropped.

## Refresh procedure

1. **Checkout.** Clone/pull `slakhani123/dealsheet`, branch
   `claude/outlook-contact-list-ehxnfc` (or `main` once merged).
2. **Connector check.** If the Microsoft 365 connector is not available this
   run, report that and stop. Do not guess contact data.
3. **Incremental sweep.** Read `last_sweep_utc` from
   `automation/contacts_data.json`. Search Outlook folders **Inbox, Sent
   Items, Archive** for messages received after `last_sweep_utc` minus 2 days
   (overlap for safety), paging 25 at a time (`order=oldest`, follow
   `nextOffset`). No free-text query — enumerate everything in the window.
4. **Update the data.** For each message correspondent (sender of received
   mail; recipients of sent mail, lowercase the address):
   - Existing contact → increment `count_from` / `count_to`, update
     `last_seen`, fill any blank `job_title` / `company` / `phones` from
     signature text in the message summary.
   - New address → add a record and categorise it (see categories below) using
     the email domain, subjects, signature block, and the deals sheet
     (`Deals_Sheet_REL.xlsx`) for who is a broker / lender / borrower. Set
     `keep:false` for automated senders (no-reply, newsletters, notifications).
   - Never delete or re-categorise existing contacts during a routine refresh
     unless clear new evidence appears — manual corrections must stick. Record
     `"category_locked": true` on any contact Shyam corrects by hand, and never
     touch locked fields.
5. **Bump state.** Set `last_sweep_utc` to the sweep start time (UTC ISO).
6. **Rebuild both renderings** (install `openpyxl` first if missing):

   ```bash
   python3 automation/build_contacts_xlsx.py     # -> Contact_List_REL.xlsx
   python3 automation/build_contacts_html.py     # -> contacts_site/index.html
   ```

   The workbook is written with `fullCalcOnLoad`, so Excel evaluates the
   Summary tab's COUNTIFs on open — a headless LibreOffice recalc is not
   required (and times out in the sandbox).
7. **Commit & push** `contacts_data.json`, `Contact_List_REL.xlsx` and
   `contacts_site/index.html` with message
   `Contacts sweep <date>: +N new, M updated`. The push fires the SharePoint
   upload automatically.
8. **Republish the web directory to its existing URL** so the shared link
   keeps working — do not mint a new one:

   ```
   Artifact  file_path=contacts_site/index.html
             url=https://claude.ai/code/artifact/6ce4ca22-f49d-438e-9aa5-9ad656cfc7dd
             favicon=📇  capabilities={"downloads": true}
   ```

   Passing `url` is what targets the existing artifact from a session that did
   not publish it. Keep the favicon and capabilities as shown; omitting
   `capabilities` on a redeploy also carries the stored grant forward.
8. **Report.** If contacts were added or changed, send Shyam the xlsx with a
   short list of new contacts and their categories. If nothing changed, one
   line saying so.

## Scheduling

A weekly trigger (`Weekly REL contact list refresh`, Mondays 07:23 UTC) fires
into the original Claude session, which holds the Microsoft 365 connection. If
that session is ever lost or the connection lapses, recreate the schedule the
robust way — the same 3-minute claude.ai Routines UI setup used for the daily
deal sweep (see `ROUTINE_SETUP.md` for the general steps):

1. claude.ai → Code → Routines → New routine.
2. Schedule: weekly, Monday 08:23 UK. Environment: the one with the
   `slakhani123/dealsheet` repo. **Enable the Microsoft 365 connector** —
   routines created programmatically cannot carry it; the UI is the only way
   to attach it to a fresh-session routine.
3. Prompt — paste verbatim:

> Run the weekly REL contact-list refresh for Shyam (shyam@relfinance.co.uk).
> If slakhani123/dealsheet is not on disk, clone it; fetch and check out branch
> `claude/outlook-contact-list-ehxnfc` (or `main` if that branch is gone), pull
> latest. Read `automation/CONTACTS_RUNBOOK.md` and follow it exactly — it is
> the procedure of record. If the Microsoft 365 connector is unavailable this
> run, reply saying so and stop; never guess contact data. Otherwise: run the
> incremental sweep, update `automation/contacts_data.json`, rebuild the
> workbook with `python3 automation/build_contacts_xlsx.py` (pip install
> openpyxl if missing), commit and push both files — the push re-uploads the
> sheet to SharePoint automatically. If contacts were added or changed, send
> Shyam the updated xlsx listing new contacts by category; else reply with one
> brief line.

## Categories

Broker · Lender / Bank · Borrower / Sponsor · Investor / Family Office ·
Solicitor / Legal · Valuer / Property Professional · Accountant / Tax ·
Service Provider · Internal (REL Finance) · Personal / Other

Context for categorisation: REL Finance is a Mayfair real-estate bridging
lender. Brokers introduce deals; borrowers/sponsors take loans; other lenders
appear as competitors or refinance takeouts; solicitors handle legals; valuers
(Knight Frank, Savills, CBRE…) value collateral.

## Contact record schema (contacts_data.json)

```json
{
  "email": "jane@arcandco.com",      // key, lowercase
  "name": "Jane Smith",
  "category": "Broker",
  "company": "Arc & Co",
  "job_title": "Director",
  "phones": ["+44 7700 900000"],
  "note": "Introduced 56-60 Hallam Street deal",
  "confidence": "high",
  "keep": true,                       // false = excluded from the xlsx
  "category_locked": false,           // true = manual correction, never auto-change
  "count_from": 12,                   // emails received from them
  "count_to": 8,                      // emails sent to them
  "first_seen": "2025-03-04",
  "last_seen": "2026-07-21",
  "source": "sweep"                   // "sweep" = direct, "chase" = named in a thread
}
```

## Data conventions

Apply these when writing new records, so the two renderings stay consistent:

- **Money in notes uses `£`**, not `GBP` — the harvest sometimes transliterates
  it.
- **One company spelling per domain.** Everyone at `oaknorth.co.uk` is
  "OakNorth Bank", everyone at `arcandco.com` is "Arc & Co". Independent
  categorisation passes drift on this, so re-check it after any batch run:
  group by domain, take the spelling most records on that domain carry, and
  apply it to the rest.
- **One category per domain, normally.** A domain carrying two categories is
  usually a mistake — but not always (a bank's lending desk and its treasury
  contact genuinely differ). Flag them, don't auto-merge them.
- **Phones**: at most two per contact, deduped on the trailing nine digits so
  `+44 7700 900000` and `07700900000` do not both appear.
- **Notes** are one line about who the person is to REL or which deal they
  relate to. Never a description of where the address was found — that is what
  `source` is for. Empty is better than padding.
- **Free-mail addresses** (gmail, outlook, hotmail…) get an empty `company`
  unless a real employer is known — never the mail domain.

## Known gaps

- **`Archive` is effectively empty** — the folder exists but held one message
  across the whole mailbox. Keep sweeping it in case that changes.
- **Free-text search and `&`** — a query containing an ampersand (`Arc & Co`)
  returns noise. Search the domain stem instead (`arcandco`).
- **Deals-sheet names are often misspelled** relative to the real contact
  (`Jay Bohgal` → Jay Bhogal, `Chris Whytney` → Chris Whitney, `James Grey` →
  James Gray, `Robert Sandler` → Robert Sadler). When chasing a name that
  returns nothing, try phonetic variants and the firm name before giving up.
- **Named with no address found:** Jack Collins, Mutual Finance, Darshan
  Daswani. Fast Forward Capital is reachable via a colleague instead. Retry
  these on future sweeps rather than deleting them from this list.
