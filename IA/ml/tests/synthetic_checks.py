import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
"""Contrôle de cohérence : CV par blocs sur la baseline + attaques SYNTHÉTIQUES (pas des données réelles)."""
import pandas as pd, numpy as np
from resilience_ml.model import AnomalyModel
X = pd.read_csv(os.path.join(os.path.dirname(__file__),'..','data','features_baseline.csv'), index_col=0); X=X[X.http_rps>=1]
blk=(X.index-X.index.min())//600; out=[]
for b in sorted(blk.unique()):
    s=AnomalyModel().fit(X[blk!=b]).score(X[blk==b]); out.append(s)
    print(b, int(s.anomaly.sum()), len(s), s.top_features[s.anomaly==1].head(2).tolist())
s=pd.concat(out); print(f'FP hors échantillon : {s.anomaly.sum()}/{len(s)} = {s.anomaly.mean():.1%}')
m=AnomalyModel.load(os.path.join(os.path.dirname(__file__),'..','models','baseline.joblib')); base=X.iloc[100:120].copy()
def show(name,a):
    s=m.score(a); print(f'{name:<40} détecté {s.anomaly.mean():>4.0%}  pca {s.pca_ratio.mean():5.2f}  env {s.envelope_score.mean():5.2f} | {s.top_features.iloc[0]}')
VOL=['http_rps','http_rps_donations','http_rps_2xx','log_waf_lines','log_waf_2xx','log_api_lines','c_security_waf_net_rx_bps','c_app_api_net_rx_bps']
for k in [1.5,2,3,20]:
    a=base.copy(); a[VOL]*=k; show(f'[synth] charge x{k}',a)
a=base.copy(); a['http_rps_5xx']=2.0; show('[synth] 5xx 2 req/s',a)
a=base.copy(); a[['http_rps','http_rps_2xx','http_rps_donations','donations_succeeded_rps','donations_failed_rps']]=0.2; show('[synth] effondrement trafic légitime',a)
a=base.copy(); a['log_waf_lines']*=10; a['log_waf_4xx']=a['log_waf_lines']*0.9; a['log_waf_uniq_paths']=40; show('[synth] scan/flood bloqué par le WAF (403)',a)
lo=X.quantile(0.02); hi=X.quantile(0.98); a=base.copy()
for c in ['http_rps','http_rps_2xx','http_rps_donations','log_waf_lines','log_waf_2xx','log_api_lines']: a[c]=lo[c]
for c in ['c_app_api_cpu','c_app_db_net_rx_bps','c_app_db_net_tx_bps','http_latency_avg_s','c_app_api_net_rx_bps']: a[c]=hi[c]
show('[synth] combo incohérente dans les plages',a)
