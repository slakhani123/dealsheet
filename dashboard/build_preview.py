#!/usr/bin/env python3
"""Wrap rel-pipeline.html the way the publisher does, so it can be opened locally.

    python3 dashboard/build_preview.py <db-dump-dir> [out-dir]

<db-dump-dir> is a directory holding `deals/*.json` and `reference/*.json`, as
written by ArtifactData action="list" with out_dir set. Produces _preview.html
and _preview-dark.html in <out-dir> (default: the dump directory).

Two things this reproduces that a bare file:// open does not: the publish
skeleton's head, and a `window.claude` that resolves the `db` capability. What
it deliberately does NOT reproduce is the sandbox — so drive it with Playwright
and listen for `dialog` events, because prompt(), confirm() and alert() work
here and are silently dead in the published page.
"""
import json, os, glob, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1].rstrip("/")
    out = sys.argv[2] if len(sys.argv) > 2 else root

    deals = {os.path.basename(p)[:-5]: json.load(open(p))
             for p in sorted(glob.glob(os.path.join(root, "deals", "*.json")))}
    if not deals:
        sys.exit(f"No deals/*.json under {root} — dump the database first with "
                 'ArtifactData action="list", collection="deals", out_dir=...')

    def ref(name, fallback):
        path = os.path.join(root, "reference", name + ".json")
        return json.load(open(path)) if os.path.exists(path) else fallback

    docs = {
        "meta/state": {"lastSweep": "2026-09-08"},
        "reference/declined": ref("declined", {"count": 0, "items": []}),
        "reference/integrity": ref("integrity", None),
    }
    stub = """<script>
var DEALS=%s, DOCS=%s;
function snapDoc(d){return {exists:!!d, data:function(){return d}}}
window.claude={use:function(n){ if(n!=="db") return Promise.resolve(null);
  return Promise.resolve({ doc:function(p){ return {
      onSnapshot:function(cb){ setTimeout(function(){cb(snapDoc(DOCS[p]))},20) },
      update:function(){return Promise.resolve()},set:function(){return Promise.resolve()},
      delete:function(){return Promise.resolve()} } },
    collection:function(){ return { onSnapshot:function(cb){ setTimeout(function(){
        cb({docs:Object.keys(DEALS).map(function(k){return {id:k,data:function(){return DEALS[k]}}})}) },30) },
      doc:function(){ return {set:function(){return Promise.resolve()},
        update:function(){return Promise.resolve()}} } } } }); }};
</script>""" % (json.dumps(deals), json.dumps(docs))

    body = open(os.path.join(HERE, "rel-pipeline.html")).read()
    head = ('<!doctype html><html%s><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>body{margin:0;font:14px system-ui}[hidden]{display:none!important}</style>')
    os.makedirs(out, exist_ok=True)
    for name, attr in (("_preview.html", ""), ("_preview-dark.html", ' data-theme="dark"')):
        with open(os.path.join(out, name), "w") as f:
            f.write((head % attr) + stub + "</head><body>" + body + "</body></html>")
    print(f"{out}/_preview.html and _preview-dark.html rebuilt "
          f"({len(deals)} deals, {docs['reference/declined'].get('count', 0)} declined)")


if __name__ == "__main__":
    main()
