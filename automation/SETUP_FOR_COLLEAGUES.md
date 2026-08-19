# Give a colleague their own contact directory

This produces, for any colleague's mailbox, exactly what Shyam has: a
categorised contact list rendered as a filterable Excel workbook **and** a
searchable web directory with an email composer, refreshed automatically every
week.

Setup is one prompt. Everything else is already in this repo.

## Before they start

| They need | Notes |
|---|---|
| Claude with the **Microsoft 365 connector** enabled | Same connector Shyam uses. Without it the run stops rather than guessing. |
| Access to `slakhani123/dealsheet` | Or a fork. The code is what makes their list identical to Shyam's. |
| ~20 minutes of Claude working in the background | The first build sweeps the whole mailbox; later refreshes take a minute. |

They do **not** need SharePoint credentials, an Entra app registration, or any
admin involvement to get the workbook and web page. Those are only for the
automatic SharePoint upload, which is optional and already configured at the
repo level.

## Step 0 — connect Claude to GitHub

**Use the browser, not the desktop app.** This is where everyone gets stuck.
The Claude desktop app runs against a **local folder** on your machine, so it
asks you to pick a directory and never offers a GitHub repository — there is
nothing to find, and no amount of connecting will make one appear there. The
weekly refresh also has to run unattended in a cloud environment, which the
desktop app cannot do: it would need your laptop awake with the app open. Web
sessions plus a Routine is the only combination where the Monday refresh
actually fires.

1. In a browser, go to claude.ai → **Settings → Connectors**.
2. Connect **GitHub**. Sign in as yourself and authorise the Claude GitHub App.
   > The authorisation screen asks which repositories to grant, and lists only
   > the repos **you own**. `slakhani123/dealsheet` will not be there. That is
   > expected — it is not a failure. Access to a repo someone else owns comes
   > from *their* app installation plus your collaborator permission.
3. Connect **Microsoft 365** while you are on the same screen — the build needs
   it and it saves a second trip.
4. Go to **claude.ai/code**, start a new session, and pick
   `slakhani123/dealsheet` from the repository selector. If it is not listed,
   type `Add the repo slakhani123/dealsheet to this session.` and Claude will
   attach it or say exactly what is missing.

**If the repo still will not attach**, in this order:

- The owner (`slakhani123`) checks `github.com/settings/installations` → Claude
  → Repository access, and confirms `dealsheet` is granted.
- Confirm you are actually a collaborator: repo → Settings → Collaborators. A
  pending invite has to be accepted from the email before anything works.
- Confirm your Claude plan includes Claude Code.

## Step 1 — the bootstrap prompt

Open Claude Code on the web (claude.ai → Code), point it at
`slakhani123/dealsheet`, and paste this **verbatim**, editing only the four
lines in the `MY DETAILS` block:

> Build me a contact directory from my Outlook mailbox, using the existing
> pipeline in this repo. Follow `automation/CONTACTS_RUNBOOK.md` for the data
> conventions and categories — it is the procedure of record.
>
> **MY DETAILS**
> - My name: `Tashin Morjaria`
> - My email: `tashin@relfinance.co.uk`
> - My firm: `REL Finance`
> - Output filename: `Contact_List_REL_Tashin.xlsx`
>
> **Branch.** Create and work on a new branch named
> `claude/contact-list-<my-first-name>`. Do not push to anyone else's branch.
>
> **Connector check first.** If the Microsoft 365 connector is unavailable,
> say so and stop. Never invent contact data.
>
> **Step 1 — sweep.** Read every message in Inbox, Sent Items and Archive from
> 2025-01-01 to today. Page 25 at a time with `order=oldest`, following
> `nextOffset` to the end of each folder; do not use a free-text query, and do
> not sample. For each message record the sender (as an inbound count) and each
> recipient (as an outbound count on my sent mail), and mine every message
> summary for signature details — job title, company, phone. Split the date
> range across several parallel subagents that each write their shard to a JSON
> file, then merge; a single pass will be slow and may run out of room.
>
> **Step 2 — chase the names that never appear as senders.** Most brokers reach
> a mailbox as a forwarded `FW:` from a colleague, so they never show up as a
> sender or recipient and a plain sweep misses them. Read
> `Deals_Sheet_REL.xlsx` in this repo, list every broker, lender, borrower and
> valuer named in it, and for each one that the sweep did not find, run a
> free-text search for their name and read the most promising message to pull
> their address out of quoted headers and signature blocks. Grab their
> colleagues on the same domain too. Never invent an address: if two searches
> find nothing, record the name under "named but no address" and move on. Note
> that names in the deals sheet are often misspelled, so try phonetic variants
> and the firm name, and that a free-text query containing `&` returns noise —
> search the domain stem instead.
>
> **Step 3 — categorise.** Put every contact in exactly one of: Broker,
> Lender / Bank, Borrower / Sponsor, Investor / Family Office, Solicitor /
> Legal, Valuer / Property Professional, Accountant / Tax, Service Provider,
> Internal, Personal / Other. Use the email domain, the signature, the subject
> lines and the deals sheet for context. Set `keep: false` on automated senders
> — newsletters, no-reply, notification robots — rather than deleting them.
> Where the evidence genuinely does not support a call, use Personal / Other,
> set `confidence` to `low`, and say so in the note; do not guess a role.
>
> **Step 4 — audit.** Independent categorisation batches drift, so review the
> assembled list for firms split across two company spellings or two categories
> on one email domain, and normalise them. This is the single most common
> defect — check it properly.
>
> **Step 5 — write and build.** Write the result to
> `automation/contacts_data.json` in the schema documented in the runbook,
> including a `config` block with my details above. Then run
> `python3 automation/build_contacts_xlsx.py` and
> `python3 automation/build_contacts_html.py` (pip install openpyxl first if
> needed). Commit and push all three files to my branch.
>
> **Step 6 — publish and send.** Publish `contacts_site/index.html` as an
> Artifact with favicon 📇 and the `downloads` capability enabled, give me the
> URL, and send me the .xlsx. Then tell me the category tally, anything you
> left at low confidence for me to correct, and any deals-sheet names you could
> not find an address for.

## Step 2 — the weekly refresh

Once the first build lands, they set up the recurring refresh themselves:

1. **claude.ai → Code → Routines → New routine.**
2. Schedule: weekly, Monday morning. Pick a minute that is not `:00`.
3. Environment: the one with the `slakhani123/dealsheet` repo.
4. **Enable the Microsoft 365 connector.** This is the whole point of using the
   Routines UI rather than asking Claude to schedule it — a routine created
   from inside a chat cannot carry the connector, and will fire without mailbox
   access.
5. Prompt — paste verbatim, editing the branch name and artifact URL:

> Scheduled weekly contact-list refresh. Follow
> `automation/CONTACTS_RUNBOOK.md` in the dealsheet repo (branch
> `claude/contact-list-<name>`) — it is the procedure of record. Incremental
> Outlook sweep since `last_sweep_utc` in `automation/contacts_data.json`
> (Inbox, Sent Items, Archive, 2-day overlap — and discard the overlap before
> incrementing any counts). Update `contacts_data.json`, respecting
> `category_locked`. Rebuild with `python3 automation/build_contacts_xlsx.py`
> and `python3 automation/build_contacts_html.py`, then commit and push. Then
> republish the web directory to its existing URL so the shared link keeps
> working — Artifact with `file_path=contacts_site/index.html`,
> `url=<their artifact URL>`, `favicon=📇`. If the Microsoft 365 connection is
> unavailable, do not guess any contact data — say the refresh could not run.
> If contacts changed, send me the updated workbook with the new contacts
> grouped by category; otherwise reply with one line.

## What each person ends up with

- Their own branch, their own `contacts_data.json`, their own workbook and web
  directory. Nobody overwrites anybody.
- The same categories, the same layout, the same weekly cadence.
- An artifact URL that is private until they share it.

## Worth considering instead: one list for the firm

Three separate directories means a broker who emails Sumeer but not Shyam
appears in one list and not the other, and each person maintains their own
corrections. If what the team actually wants is *one* view of who REL knows,
that is a different and arguably better build: sweep all three mailboxes into a
single `contacts_data.json`, keyed by email address, with per-owner counts, so
each contact shows who at REL has the relationship and how strong it is.

That needs either delegated access to each mailbox from one account
(`Mail.Read.Shared`) or each person running the sweep and the shards being
merged. It is a bigger job than this kit and worth deciding deliberately —
ask before assuming the per-person version is what the team wants long term.
