#!/usr/bin/env python3
"""Work out what the dashboard needs in order to match the deal sheet.

The dashboard (REL Pipeline Desk) keeps deal FACTS in an artifact database and
the team's own columns — owner, stage, RAG, next action, notes, reviewed flag —
alongside them. The spreadsheet owns the facts; the team owns their columns.
This script enforces that split: it emits writes for the fact fields only, so a
sync can never overwrite someone's Monday review.

Usage:
    # 1. dump the current database (ArtifactData action="list", out_dir=DIR)
    # 2. python3 automation/sync_dashboard.py --db DIR/deals --out writes.json
    # 3. feed writes.json to ArtifactData action="batch"

It writes nothing itself and talks to nothing — it reads two local inputs and
prints a plan. Run it, read the summary, then apply it.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys

import openpyxl

SHEET = "Deals_Sheet_REL.xlsx"

# The two sheets do NOT share a layout, and getting this wrong reads one
# column as another rather than failing, so both are spelled out in full.
# Columns E-N agree; after that Completed Deals carries two extra columns
# (drawdown timing, PG) and pushes the rest right.
_SHARED = {
    "tranche": 5, "dealType": 6, "acqRefi": 7, "netLoan": 8, "relReturn": 9,
    "grossLoan": 10, "collateral": 11, "ltv": 12, "months": 13, "irr": 14,
}
COLS = {
    "Potential Deals": dict(
        _SHARED, dateReceived=1, property=2, assetClass=3, borrower=4,
        tsIssued=15, commitFee=16, source=17, sheetComments=18, relShare=19),
    # Completed Deals leads with the property and has a No of Units column.
    "Completed Deals": dict(
        _SHARED, dateReceived=None, property=1, assetClass=2, borrower=4,
        tsIssued=17, commitFee=18, source=19, sheetComments=20,
        introducer=21, relShare=22),
}
# Some Completed Deals rows carry a date in column A instead, which pushes the
# text columns one to the right and drops No of Units. Columns E onwards stay put.
COLS["Completed Deals+date"] = dict(
    COLS["Completed Deals"], dateReceived=1, property=2, assetClass=3, borrower=4)

# Fields the sheet owns. A sync writes these and nothing else.
#
# Deliberately absent, though a sync does set both on a deal it creates:
#   ltvBasis — an interpretation of which loan figure the LTV column used, not
#     a value the sheet states. Rewriting it every run churns rows where net
#     and gross are equal and the evidence cannot decide.
#   flags — written by the integrity check (e.g. also-in-declined). Syncing it
#     from the sheet would wipe those findings on the next run.
FACT_FIELDS = [
    "dateReceived", "property", "assetClass", "borrower", "tranche", "dealType",
    "acqRefi", "netLoan", "relReturn", "grossLoan", "collateral", "ltv",
    "months", "irr", "tsIssued", "commitFee", "source",
    "sheetComments", "sheetSection", "derivedStage", "relShare", "introducer",
]

# Fields the team owns. Never written by a sync, at any version, for any reason.
#
# "corrections" is the one that needs explaining. The board shows the sheet's
# figures, but a person who spots a wrong one can amend it there — otherwise
# the only options are to act on a number they know is wrong or to stop using
# the board. An amendment is stored as {field: value} under "corrections" and
# the board displays it in place of the sheet's own, saying so. It is a claim
# about the sheet, not a replacement for it: check_corrections() below reports
# every one still outstanding so the sweep can fix the spreadsheet, and clears
# it once the sheet agrees. A correction is therefore temporary by design.
TEAM_FIELDS = [
    "stage", "owner", "rag", "nextAction", "nextActionDue", "teamNote",
    "reviewedWeek", "updatedBy", "updatedAt", "createdBy", "origin",
    "corrections",
]

# The figures a person may amend on the board. Text fields are deliberately
# absent: a wrong property name or borrower is a different kind of problem and
# belongs in the sheet, where renaming it also re-keys the board document.
AMENDABLE = ["netLoan", "grossLoan", "collateral", "relShare", "relReturn",
             "ltv", "irr", "months"]

# Stage order, funnel order. "Completed" was replaced by the pair Drawn /
# Redeemed once it became clear the sheet was calling drawn loans completed.
STAGES = ["Enquiry", "Terms Issued", "Commitment Fee", "In Legals", "Drawn", "Redeemed"]

# Row blocks. The In Legals block sits under its header at row 7; EARLY STAGE
# under row 19. Both end before their Total row.
# Declined rows carry the same column layout as Potential Deals and, unlike
# the board's old summary of them, real funnel evidence: when the enquiry came
# in, whether terms were ever issued, whether a commitment fee was paid. That
# is what makes a conversion rate possible at all, so the sync now rebuilds the
# whole reference document rather than leaving it as a one-off hand-loaded blob.
DECLINED_BLOCK = ("Declined Deals", 5, 94)

BLOCKS = [
    ("Potential Deals", 8, 10, "live", "In Legals"),
    ("Potential Deals", 20, 56, "live", None),
    # The Completed Deals sheet carries two blocks. "Redeemed" means the money
    # came back; "Drawn" means it went out and has not. Conflating them read
    # Uxbridge and Stanmore as finished when both are still running.
    ("Completed Deals", 5, 9, "redeemed", "Redeemed"),
    ("Completed Deals", 14, 18, "drawn", "Drawn"),
]


def slug(s, limit=60):
    out = re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")[:limit].strip("-")
    return out or "deal"


def truthy(v):
    return str(v).strip().lower() in ("y", "yes", "true", "1") if v is not None else False


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def text(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def iso(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return None


def read_sheet(path):
    """Every deal the spreadsheet currently describes, as fact dicts."""
    wb = openpyxl.load_workbook(path, data_only=True)
    rows = []
    for sheet, lo, hi, section, forced_stage in BLOCKS:
        ws = wb[sheet]
        for r in range(lo, min(hi, ws.max_row) + 1):
            key = sheet
            if sheet == "Completed Deals" and isinstance(
                    ws.cell(r, 1).value, (dt.datetime, dt.date)):
                key += "+date"
            cols = COLS[key]

            def cell(field):
                c = cols.get(field)
                return ws.cell(r, c).value if c else None

            prop = text(cell("property"))
            if not prop or prop.lower() == "total":
                continue

            gross, net = num(cell("grossLoan")), num(cell("netLoan"))
            coll, ltv = num(cell("collateral")), num(cell("ltv"))
            # The LTV column mixes two definitions across rows. Record which
            # one this row used, so the board never averages figures that do
            # not mean the same thing. Whichever loan figure reproduces the
            # stated LTV more closely wins; a tie means it cannot be told
            # apart, and gross is the sheet's usual convention.
            basis = "gross"
            if ltv is not None and coll and net is not None:
                off_net = abs(ltv - net / coll)
                off_gross = abs(ltv - gross / coll) if gross is not None else None
                if off_net < 0.005 and (off_gross is None or off_net < off_gross):
                    basis = "net"

            ts, cf = truthy(cell("tsIssued")), truthy(cell("commitFee"))
            stage = forced_stage or ("Commitment Fee" if cf else "Terms Issued" if ts else "Enquiry")

            rows.append({
                "dateReceived": iso(cell("dateReceived")),
                "property": prop,
                "assetClass": text(cell("assetClass")),
                "borrower": text(cell("borrower")),
                "tranche": text(cell("tranche")),
                "dealType": text(cell("dealType")),
                "acqRefi": text(cell("acqRefi")),
                "netLoan": net, "relReturn": num(cell("relReturn")),
                "grossLoan": gross, "collateral": coll,
                "ltv": ltv, "ltvBasis": basis,
                "months": num(cell("months")), "irr": num(cell("irr")),
                "tsIssued": ts, "commitFee": cf,
                "source": text(cell("source")),
                "sheetComments": text(cell("sheetComments")),
                "sheetSection": section,
                "derivedStage": stage,
                # REL's own share of a syndicated loan. Uxbridge is £8.2m whole
                # but £2.05m REL; without this every total overstates REL money.
                "relShare": num(cell("relShare")) if "relShare" in cols else None,
                "introducer": text(cell("introducer")) if "introducer" in cols else None,
                "flags": [],
            })
    return rows


def read_declined(path):
    """The declined book, as the board's reference document.

    Kept deliberately small — property, asset class, size, why we passed — plus
    the four fields a conversion rate needs: when it arrived, whether terms went
    out, whether a fee was paid, and where it came from. 90 rows of full deal
    records would be a second copy of the spreadsheet; this is a summary that
    can answer "what do we see, and what do we write?".
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[DECLINED_BLOCK[0]]
    cols = dict(COLS["Potential Deals"], relShare=None)
    items = []
    for r in range(DECLINED_BLOCK[1], min(DECLINED_BLOCK[2], ws.max_row) + 1):
        def cell(field):
            c = cols.get(field)
            return ws.cell(r, c).value if c else None

        prop = text(cell("property"))
        if not prop or prop.lower() == "total":
            continue
        # "Broker (Arc & Co)" names the broker in the source column. Split it,
        # so the source stays one of two values and the name is still kept.
        src, introducer = text(cell("source")), None
        if src:
            m = re.match(r"^\s*(Broker|Direct)\s*\((.+)\)\s*$", src, re.I)
            if m:
                src, introducer = m.group(1).title(), m.group(2).strip()
            else:
                src = src.strip()
        items.append({
            "property": prop,
            "assetClass": text(cell("assetClass")),
            "dateReceived": iso(cell("dateReceived")),
            "grossLoan": num(cell("grossLoan")),
            "ltv": num(cell("ltv")),
            "months": num(cell("months")),
            "tsIssued": truthy(cell("tsIssued")),
            "commitFee": truthy(cell("commitFee")),
            "source": src,
            "introducer": introducer,
            "reason": text(cell("sheetComments")),
        })
    return items


def check_corrections(db, sheet_rows):
    """Figures a person amended on the board, against what the sheet now says.

    Returns (writes, outstanding). An amendment the sheet has caught up with is
    cleared — leaving it would keep showing an "amended" badge over a figure
    that no longer differs from anything. One the sheet still contradicts is
    reported, because fixing the spreadsheet is a human step this script must
    never take for itself.
    """
    by_prop = {r["property"]: r for r in sheet_rows}
    writes, outstanding = [], []
    for doc_id, d in sorted(db.items()):
        corr = d.get("corrections")
        if not isinstance(corr, list) or not corr:
            continue
        row = by_prop.get(d.get("property"))
        keep = []
        for c in corr:
            if not isinstance(c, dict) or c.get("field") not in AMENDABLE:
                continue
            field, value = c["field"], c.get("value")
            sheet_value = row.get(field) if row else None
            if same_number(sheet_value, value):
                continue                      # the sheet caught up; drop it
            keep.append(c)
            outstanding.append((d.get("property"), field, sheet_value, value,
                                c.get("by") or d.get("updatedBy")))
        if len(keep) != len(corr):
            # The whole list is rewritten, never patched key by key: it is an
            # array precisely so that withdrawing one amendment cannot half-apply.
            entry = {"op": "update", "collection": "deals", "doc_id": doc_id,
                     "data": {"corrections": keep}}
            if "version" in d:
                entry["if_version"] = d["version"]
            writes.append(entry)
    return writes, outstanding


def same_number(a, b):
    """Equal as figures, not as objects. Floats out of Excel are never exact."""
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(float(a) - float(b)) <= 1e-9 + 1e-9 * abs(float(b))
    except (TypeError, ValueError):
        return a == b


def read_db(db_dir):
    docs = {}
    if not os.path.isdir(db_dir):
        sys.exit(f"No such database dump: {db_dir}\n"
                 "Dump it first with ArtifactData action=\"list\", collection=\"deals\", out_dir=...")
    for name in sorted(os.listdir(db_dir)):
        if name.endswith(".json"):
            with open(os.path.join(db_dir, name)) as f:
                docs[name[:-5]] = json.load(f)
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default=SHEET)
    ap.add_argument("--db", required=True, help="directory of the dumped deals collection")
    ap.add_argument("--out", required=True, help="where to write the batch payload")
    ap.add_argument("--versions", help="optional JSON map of doc_id -> version, for if_version pinning")
    args = ap.parse_args()

    sheet_rows = read_sheet(args.sheet)
    declined = read_declined(args.sheet)
    db = read_db(args.db)
    versions = json.load(open(args.versions)) if args.versions else {}

    # Keep ids stable: match on the property string the sheet and board share.
    by_property = {d.get("property"): doc_id for doc_id, d in db.items() if d.get("property")}
    used = set(db)

    writes, added, changed, manual, unmatched = [], [], [], [], []

    for row in sheet_rows:
        doc_id = by_property.get(row["property"])
        if doc_id is None:
            doc_id = base = slug(row["property"])
            n = 0
            while doc_id in used:
                n += 1
                doc_id = f"{base}-{n}"
            used.add(doc_id)
            doc = dict(row)
            doc.update({f: None for f in TEAM_FIELDS})
            doc["stage"] = row["derivedStage"]
            doc["flags"] = []
            writes.append({"op": "set", "collection": "deals", "doc_id": doc_id, "data": doc})
            added.append((doc_id, row["property"]))
            continue

        current = db[doc_id]
        patch = {f: row[f] for f in FACT_FIELDS if current.get(f) != row[f]}
        if patch:
            entry = {"op": "update", "collection": "deals", "doc_id": doc_id, "data": patch}
            if doc_id in versions:
                entry["if_version"] = versions[doc_id]
            elif "version" in current:
                entry["if_version"] = current["version"]
            writes.append(entry)
            changed.append((doc_id, row["property"], sorted(patch)))

    # Anything on the board the sheet no longer describes. Never deleted here:
    # a hand-added deal legitimately lives only on the board, and a swept deal
    # that vanished from the sheet is a question for a human, not a delete.
    sheet_props = {r["property"] for r in sheet_rows}
    for doc_id, d in db.items():
        if d.get("property") in sheet_props:
            continue
        (manual if d.get("origin") == "manual" else unmatched).append((doc_id, d.get("property")))

    # The declined book is one document, rewritten whole: it is a summary of a
    # sheet nobody edits from the board, so there is nothing of the team's in
    # it to preserve.
    writes.append({"op": "set", "collection": "reference", "doc_id": "declined",
                   "data": {"count": len(declined), "items": declined}})

    corr_writes, outstanding = check_corrections(db, sheet_rows)
    writes.extend(corr_writes)

    with open(args.out, "w") as f:
        json.dump(writes, f, indent=2)

    print(f"{len(sheet_rows)} deals in the sheet, {len(db)} on the board")
    print(f"\n{len(added)} to add:")
    for doc_id, prop in added:
        print(f"  + {prop}  [{doc_id}]")
    print(f"\n{len(changed)} with changed facts:")
    for doc_id, prop, fields in changed:
        print(f"  ~ {prop}  [{doc_id}]  {', '.join(fields)}")
    if manual:
        print(f"\n{len(manual)} added by hand on the board, not in the sheet "
              "(put them in the sheet so the sweep tracks them):")
        for doc_id, prop in manual:
            print(f"  · {prop}  [{doc_id}]")
    if unmatched:
        print(f"\n{len(unmatched)} on the board but no longer in the sheet — "
              "check before doing anything; nothing is deleted automatically:")
        for doc_id, prop in unmatched:
            print(f"  ? {prop}  [{doc_id}]")
    print(f"\n{len(declined)} declined deals in the reference document "
          f"({sum(1 for d in declined if d['tsIssued'])} reached terms, "
          f"{sum(1 for d in declined if d['dateReceived'])} dated)")
    if outstanding:
        print(f"\n{len(outstanding)} figure(s) amended on the board that the sheet "
              "still contradicts — FIX THE SHEET, then the amendment clears itself:")
        for prop, field, sheet_value, board_value, by in outstanding:
            print(f"  ! {prop}  {field}: sheet says {sheet_value}, "
                  f"{by or 'someone'} says {board_value}")
    if corr_writes:
        print(f"\n{len(corr_writes)} amendment(s) the sheet has caught up with, "
              "being cleared")
    print(f"\n{len(writes)} writes -> {args.out}"
          + ("  (apply in chunks of 50)" if len(writes) > 50 else ""))


if __name__ == "__main__":
    main()
