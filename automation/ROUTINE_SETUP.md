# Daily sweep — proper setup via the claude.ai Routines UI

## Why this file exists

The daily sweep must run **unattended with access to Shyam's Outlook**. A routine
created programmatically (from inside a chat session) cannot carry the Microsoft
365 connector — it fires without mailbox access and stops. The **only** way to
run it unattended with the connector attached is to create the routine from the
claude.ai Routines UI, where connectors attach at the routine level.

This is a one-time, ~3-minute setup. Do it once and the sweep runs every morning
on its own.

## Steps

1. Go to **claude.ai → Code → Routines** (or the Routines section of the app).
2. **New routine.**
3. **Schedule:** Daily at **09:05** UK time. (Off the top of the hour on purpose.)
4. **Environment:** pick the environment that has the `slakhani123/dealsheet`
   repo (the same one this project runs in).
5. **Connectors / Tools:** ensure **Microsoft 365 is enabled** for the routine.
   This is the whole point — do not skip it. Also leave the default coding tools
   (Bash, Read, Edit, Write, git) and file-send enabled.
6. **Prompt:** paste the block below verbatim.
7. Save, then use **Run now** to test. A green run ends with either a sheet
   update (file sent to Shyam) or the one-line "nothing new" message.

## Routine prompt (paste verbatim)

> Run the daily REL deal-sheet sweep for Shyam (shyam@relfinance.co.uk).
>
> Setup: if slakhani123/dealsheet is not already on disk, clone it. Then
> `git fetch origin` and check out branch
> `claude/deal-sheet-auto-populate-svgr0b`, pulling the latest. Read
> `automation/SWEEP_RUNBOOK.md` and follow it exactly — it is the procedure of
> record.
>
> Connector check first: if the Microsoft 365 connector is not available this
> run, reply saying so and stop without modifying the sheet. Do not guess deal
> data.
>
> Task: using Microsoft 365, sweep the mailbox (inbox and Sent Items) for deal
> emails received since the `last_sweep_utc` in
> `automation/processed_deals.json`, with 1 day of overlap. Dedupe against
> `processed_deals.json` and existing sheet rows (brokers use codenames — match
> on figures/address, not just name). Read attached term-sheet / DA PDFs when the
> terms are not in the email body. Apply adds/updates to `Deals_Sheet_REL.xlsx`
> per the runbook's column and section conventions, put anything uncertain in the
> Comments column rather than guessing a number, recalculate the workbook, verify
> the changed rows, update `processed_deals.json` (bump `last_sweep_utc` and log
> each conversation handled), then commit and push to the same branch.
>
> Report: if anything changed, send Shyam the updated .xlsx with a short summary
> table of added/updated rows, flagging every field left TBC. If nothing changed,
> reply with one brief line and send no file.

## Notes

- The prompt is fully self-contained because a routine starts a fresh session
  each morning with no memory of this conversation — everything it needs is in
  the repo.
- Pushing the sheet also fires `.github/workflows/upload-to-sharepoint.yml`,
  which copies the file to the team's shared area once the SharePoint
  credentials in `automation/SHAREPOINT_SETUP.md` are configured.
- To change the time or wording later, edit the routine in the same UI — no code
  change needed.
