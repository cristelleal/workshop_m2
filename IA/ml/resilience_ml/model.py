"""
Modèle de détection : deux détecteurs complémentaires entraînés UNIQUEMENT sur le système sain.

1. PCA / erreur de reconstruction (statistique SPE, contrôle statistique multivarié) :
   la PCA apprend comment les métriques bougent ENSEMBLE en régime sain (débit HTTP, logs WAF,
   CPU API, réseau DB… sont corrélés). Une fenêtre qui casse ces corrélations (ex. trafic
   faible mais CPU API et réseau DB au maximum) se reconstruit mal -> score élevé.
   Testé contre un Isolation Forest sur la baseline : l'IF ne détectait ni une charge ×3 ni une
   combinaison incohérente, la PCA détecte les deux (voir README).
2. Enveloppe par feature : distance hors de la plage [min, max] observée en baseline,
   normalisée par la dispersion saine (q95 - q05). Couvre les features constantes en baseline
   (5xx = 0, 4xx = 0, saturation DB = 0…) qui explosent pendant une attaque, et fournit
   l'explication (top features responsables) affichable dans Grafana.

Toutes les features passent par log1p : les débits et octets ont des queues lourdes, et un
DDoS se lit en ordre de grandeur (×10, ×100), pas en écart absolu.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import RobustScaler

PCA_VARIANCE = 0.95         # variance expliquée conservée
PCA_QUANTILE = 0.995        # seuil SPE = quantile 99,5 % des fenêtres saines
ENVELOPE_MIN_SCALE = 0.25   # dispersion minimale en espace log1p (évite les divisions par ~0)
ENVELOPE_THRESHOLD = 1.0    # > 1 : la feature sort de la plage saine d'au moins une dispersion
CLIP = 50.0                 # borne des valeurs standardisées (une feature folle ne masque pas les autres)


def _tx(X: pd.DataFrame) -> np.ndarray:
    v = X.to_numpy(dtype=float)
    return np.sign(v) * np.log1p(np.abs(v))


class AnomalyModel:
    def __init__(self, pca_variance: float = PCA_VARIANCE, pca_quantile: float = PCA_QUANTILE,
                 envelope_threshold: float = ENVELOPE_THRESHOLD,
                 envelope_min_scale: float = ENVELOPE_MIN_SCALE):
        self.pca_variance = pca_variance
        self.pca_quantile = pca_quantile
        self.envelope_threshold = envelope_threshold
        self.envelope_min_scale = envelope_min_scale

    def params(self) -> dict:
        return {k: getattr(self, k) for k in
                ("pca_variance", "pca_quantile", "envelope_threshold", "envelope_min_scale")}

    # ------------------------------------------------------------------ fit
    def fit(self, X: pd.DataFrame) -> "AnomalyModel":
        self.columns = list(X.columns)
        Z = _tx(X)
        self.scaler = RobustScaler(quantile_range=(5, 95)).fit(Z)
        Zs = self._std(Z)
        self.active = Zs.std(axis=0) > 1e-9          # features qui varient en baseline
        self.pca = PCA(n_components=self.pca_variance, svd_solver="full").fit(Zs[:, self.active])
        train_spe = self._spe(Zs)
        self.pca_threshold = float(np.quantile(train_spe, self.pca_quantile))

        self.lo, self.hi = Z.min(axis=0), Z.max(axis=0)
        q05, q95 = np.quantile(Z, 0.05, axis=0), np.quantile(Z, 0.95, axis=0)
        self.scale = np.maximum(q95 - q05, self.envelope_min_scale)

        self.train_stats = {
            "n_samples": int(len(X)),
            "n_features": len(self.columns),
            "n_features_varying": int(self.active.sum()),
            "pca_components": int(self.pca.n_components_),
            "pca_threshold": self.pca_threshold,
            "start": int(X.index.min()), "end": int(X.index.max()),
            **self.params(),
        }
        return self

    def _std(self, Z):
        return np.clip(np.nan_to_num(self.scaler.transform(Z)), -CLIP, CLIP)

    def _spe(self, Zs):
        A = Zs[:, self.active]
        R = A - self.pca.inverse_transform(self.pca.transform(A))
        return (R ** 2).sum(axis=1)

    # ------------------------------------------------------------------ score
    def deviations(self, X: pd.DataFrame) -> pd.DataFrame:
        Z = _tx(X.reindex(columns=self.columns, fill_value=0.0))
        dev = np.maximum.reduce([np.zeros_like(Z), Z - self.hi, self.lo - Z]) / self.scale
        return pd.DataFrame(dev, index=X.index, columns=self.columns)

    def score(self, X: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
        X = X.reindex(columns=self.columns, fill_value=0.0)
        spe = self._spe(self._std(_tx(X)))
        dev = self.deviations(X)
        out = pd.DataFrame({
            "pca_ratio": spe / self.pca_threshold,           # > 1 = corrélations saines cassées
            "envelope_score": dev.max(axis=1).to_numpy(),    # > 1 = feature hors plage saine
        }, index=X.index)
        out["anomaly"] = ((out["pca_ratio"] > 1) | (out["envelope_score"] > self.envelope_threshold)).astype(int)
        tops = []
        for i in range(len(dev)):
            row = dev.iloc[i]
            row = row[row > 0].sort_values(ascending=False).head(top_k)
            tops.append(", ".join(f"{k}={v:.1f}" for k, v in row.items()))
        out["top_features"] = tops
        return out

    # ------------------------------------------------------------------ io
    def save(self, path: str):
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "AnomalyModel":
        return joblib.load(path)
