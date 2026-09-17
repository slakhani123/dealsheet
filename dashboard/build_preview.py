import json, os, glob, sys
src = sys.argv[1] if len(sys.argv)>1 else 'live3/deals'
deals={}
for p in glob.glob(src+'/*.json'):
    deals[os.path.basename(p)[:-5]]=json.load(open(p))
meta={"lastSweep":"2026-09-08"}
declined=json.load(open('dbnow/reference/declined.json'))
integrity=json.load(open('dbnow/reference/integrity.json'))
stub = """<script>
var DEALS=%s, META=%s, DECL=%s, INTEG=%s;
function snapDoc(d){return {exists:!!d, data:function(){return d}}}
window.claude={use:function(n){ if(n!=="db") return Promise.resolve(null);
  return Promise.resolve({ doc:function(p){ return {
      onSnapshot:function(cb){ var m={"meta/state":META,"reference/declined":DECL,"reference/integrity":INTEG};
        setTimeout(function(){cb(snapDoc(m[p]))},20) },
      update:function(){return Promise.resolve()},set:function(){return Promise.resolve()},delete:function(){return Promise.resolve()} } },
    collection:function(){ return { onSnapshot:function(cb){ setTimeout(function(){
        cb({docs:Object.keys(DEALS).map(function(k){return {id:k,data:function(){return DEALS[k]}}})}) },30) },
      doc:function(){ return {set:function(){return Promise.resolve()}} } } } }); }};
</script>""" % (json.dumps(deals), json.dumps(meta), json.dumps(declined), json.dumps(integrity))
body=open('rel-pipeline.html').read()
head=('<!doctype html><html%s><head><meta charset="utf-8">'
 '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
 '<style>body{margin:0;font:14px system-ui}[hidden]{display:none!important}</style>')
open('_preview.html','w').write((head%'')+stub+'</head><body>'+body+'</body></html>')
open('_preview-dark.html','w').write((head%' data-theme="dark"')+stub+'</head><body>'+body+'</body></html>')
print("preview rebuilt from rel-pipeline.html (%d deals)" % len(deals))
