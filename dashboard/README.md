# REL Pipeline Desk — dashboard source

`rel-pipeline.html` is the source of the team's board, published at
https://claude.ai/artifact/QakzsFdHVhWZmRGwuPd98P

It had been living only in a session scratchpad, which is ephemeral — this
directory is the durable copy. **Edit it here, then publish** with the Artifact
tool using the `url` above so the link the team uses keeps working.

## Testing before you publish

The published page runs in a **sandboxed iframe**, which is stricter than a
plain browser in two ways that have already caused real bugs:

- `prompt()`, `confirm()` and `alert()` do nothing. The identity picker used
  `prompt()` and silently failed for everyone until 17/09/2026.
- Only the CSP-allowed CDNs load; everything else is blocked without an error.

`build_preview.py` wraps this file with the publish skeleton and a stub
`window.claude` so it can be opened locally:

    python3 dashboard/build_preview.py <dir of dumped deal JSON>

Dump the deal JSON first with `ArtifactData` `action="list"`,
`collection="deals"`, `out_dir=...`.

Drive the preview with Playwright and **listen for `dialog` events** — a native
dialog firing locally means a dead control in production.

## Two traps worth remembering

- `arr.map(dealRow)` passes `(element, index, array)`. `dealRow(d, reason,
  scope)` therefore received the index as `reason` and the array as `scope`,
  and no row in The book could be opened. Always wrap: `arr.map(function(d){
  return dealRow(d) })`.
- A drawn or redeemed loan is in `completed`, not `deals`. Look deals up with
  `findDeal(id)`, which searches both.

## Needs you empties as it is worked

"Mark it reviewed" has to take the row off the list, or the instruction visibly
does nothing and the list looks identical at the end of a morning as it did at
the start. `needsSplit()` divides the attention list into outstanding and
reviewed-this-week; reviewed rows move into a collapsed **Done this week**
block rather than disappearing, because the reason each was flagged has not
gone away — it has been dealt with for this week. The week key rolls over on
Monday and the whole list returns.

The headline count, the progress bar and the "All done for this week" state all
read from the outstanding half, so they agree with what is on screen.

## Two tabs

**The desk** is the working view: what needs a person, the book, the reference
tables. **Numbers** is the standing picture — exposure and concentration, the
track record, the conversion funnel, deal flow by month, asset-class mix and
why deals die. It reads the same `deals` collection plus `reference/declined`,
computes everything in the page, and is rendered lazily on first switch.

The chart colours are `--ch-1` / `--ch-2` / `--ch-3` (marks), `--ch-mute` (a
recessive mark) and `--ch-track` (the empty remainder). `--ch-mute` and
`--ch-track` must stay different: when they matched, a bar that was entirely
"passed or lost" rendered as nothing at all. Both sets were checked for
colour-blind separation against their own surface, and every bar is directly
labelled so colour is never the only thing carrying identity.

## Amending a figure

The sheet owns the figures, but a wrong one used to leave you choosing between
acting on a number you knew was wrong and not using the board. So a deal's
figures can be amended in place. An amendment is stored under `corrections` —
a team field the sweep never writes — and shown instead of the sheet's own
figure, marked, with the original struck through beside it.

    corrections: [{field: "grossLoan", value: 8.45, by: "Shyam", at: "..."}]

It is an **array**, not an object keyed by field, because an array is replaced
wholesale by every update semantic there is: withdrawing an amendment cannot
half-apply. `applyCorrections()` swaps amended values in at load and keeps the
sheet's own in `sheetFigs`, so every total, chart and row elsewhere just reads
`d.grossLoan` and gets the figure the team believes.

An amendment is a claim about the sheet, not a replacement for it.
`sync_dashboard.py` reports every one the spreadsheet still contradicts, and
drops it once the sheet agrees — so amendments are temporary by design.

Two traps in the comparison, both of which produced real bugs:

- Compare the box's **text** against what the box would show for the sheet's
  own figure, not the numbers. The form rounds — IRR 0.1469 displays as 14.7 —
  so a numeric comparison marked every untouched IRR as amended the moment
  anyone opened the form.
- Compare against the **sheet**, never against what is on screen. Typing the
  sheet's figure back in is how an amendment is withdrawn.

## Needs you must never lose a deal

Saving stamps `updatedAt`, which stops a deal being "45 days quiet" — the only
thing that listed many of them. Two consequences, both fixed and both easy to
reintroduce:

- `needsSplit()` builds **Done this week** from everything reviewed this week,
  not from the reviewed rows that still have a reason to be listed. Otherwise a
  reviewed deal left the outstanding list and never arrived in Done: it
  vanished, and the counter read "4 reviewed" above a block showing 3.
- `attention()` keeps a deal you touched this week but did not tick off, as
  "Updated, not ticked off". Without it, editing a quiet deal made its row
  disappear from under you mid-edit.
