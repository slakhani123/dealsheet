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
