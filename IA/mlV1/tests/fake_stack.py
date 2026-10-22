"""Faux Prometheus (:19090) + faux Loki (:13100) qui rejouent un export, pour tester detector/export."""
import json, re, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import pandas as pd
prom = pd.read_csv(sys.argv[1]); prom['L'] = prom['labels'].map(json.loads)
G = {k: g for k, g in prom.groupby('query')}
logs = [json.loads(l) for l in open(sys.argv[2])]; logs.sort(key=lambda r: r['ts_ns'])
TS = [r['ts_ns'] for r in logs]
import bisect
def match(sel, L):
    m = re.match(r'\{(\w+)(=~|=)"([^"]*)"\}', sel); k, op, v = m.groups()
    x = L.get(k)
    return x is not None and (re.fullmatch(v, x) if op == '=~' else x == v)
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == '/api/v1/query':
            g = G.get(q['query']); t = int(float(q['time'])); res = []
            if g is not None:
                for _, r in g[g.timestamp == t].iterrows():
                    if pd.notna(r.value): res.append({'metric': r.L, 'value': [t, str(r.value)]})
            return self.send({'status':'success','data':{'resultType':'vector','result':res}})
        if u.path == '/api/v1/query_range':
            g = G.get(q['query']); s, e = int(q['start']), int(q['end']); res = {}
            if g is not None:
                for _, r in g[(g.timestamp >= s) & (g.timestamp <= e)].iterrows():
                    if pd.notna(r.value): res.setdefault(json.dumps(r.L, sort_keys=True), []).append([r.timestamp, str(r.value)])
            return self.send({'status':'success','data':{'resultType':'matrix','result':[{'metric':json.loads(k),'values':v} for k,v in res.items()]}})
        if u.path == '/loki/api/v1/query_range':
            s, e, lim = int(q['start']), int(q['end']), int(q['limit'])
            i = bisect.bisect_left(TS, s); out = []; streams = {}
            while i < len(logs) and logs[i]['ts_ns'] <= e and len(out) < lim:
                r = logs[i]
                if match(q['query'], r['labels']): out.append(r); streams.setdefault(json.dumps(r['labels'], sort_keys=True), []).append([str(r['ts_ns']), r['line']])
                i += 1
            return self.send({'status':'success','data':{'resultType':'streams','result':[{'stream':json.loads(k),'values':v} for k,v in streams.items()]}})
        self.send_response(404); self.end_headers()
for port in (19090, 13100):
    threading.Thread(target=ThreadingHTTPServer(('127.0.0.1', port), H).serve_forever, daemon=True).start()
print('ready', flush=True); threading.Event().wait()
