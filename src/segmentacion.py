"""Segmentación exploratoria de productos por comportamiento de venta."""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def segmentar_productos(demanda, grupos=3):
    """Estandariza media y variabilidad; perfila en las unidades originales."""
    if not isinstance(grupos, int) or not 2 <= grupos <= 6:
        raise ValueError('Selecciona entre 2 y 6 grupos.')
    elegibles = demanda.dropna(subset=['demanda_diaria', 'cv']).sort_values('producto_id').copy()
    variables = elegibles[['demanda_diaria', 'cv']]
    if len(elegibles) < grupos or len(variables.drop_duplicates()) < grupos:
        raise ValueError(f'Se necesitan al menos {grupos} productos con perfiles distintos e histórico completo.')

    escalados = StandardScaler().fit_transform(variables)
    etiquetas = KMeans(n_clusters=grupos, random_state=42, n_init=10).fit_predict(escalados)
    elegibles['grupo'] = etiquetas
    orden = elegibles.groupby('grupo')['demanda_diaria'].mean().sort_values().index
    nombres = {grupo: f'Grupo {posicion + 1} · ' + (
        'menor venta diaria' if posicion == 0 else 'mayor venta diaria' if posicion == grupos - 1 else 'venta intermedia')
        for posicion, grupo in enumerate(orden)}
    elegibles['segmento'] = elegibles['grupo'].map(nombres)
    perfiles = elegibles.groupby('segmento', as_index=False).agg(
        productos=('producto_id', 'count'), demanda_media=('demanda_diaria', 'mean'), cv_medio=('cv', 'mean'),
    ).sort_values('demanda_media')
    silueta = float(silhouette_score(escalados, etiquetas)) if 1 < len(set(etiquetas)) < len(elegibles) else None
    return elegibles.drop(columns='grupo'), perfiles, silueta
