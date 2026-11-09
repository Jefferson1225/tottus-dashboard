"""Segmentación exploratoria de productos por comportamiento de venta."""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cut_tree, dendrogram, linkage
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances, silhouette_score
from sklearn.preprocessing import StandardScaler


METODOS = ['K-means', 'K-medoids', 'Jerárquico (Ward)']


def _preparar(demanda, grupos):
    elegibles = demanda.dropna(subset=['demanda_diaria', 'cv']).sort_values('producto_id').reset_index(drop=True)
    variables = elegibles[['demanda_diaria', 'cv']]
    if len(variables.drop_duplicates()) < grupos:
        raise ValueError(f'Se necesitan al menos {grupos} productos con perfiles distintos e histórico completo.')
    return elegibles, StandardScaler().fit_transform(variables)


def _silueta(datos, etiquetas):
    if 1 < len(set(etiquetas)) < len(datos):
        try:
            return float(silhouette_score(datos, etiquetas, sample_size=min(len(datos), 1000), random_state=42))
        except ValueError:
            # En muestras grandes un grupo muy pequeño podría quedar fuera.
            return None
    return None


def _medoides(datos, grupos):
    """PAM: inicialización voraz y búsqueda local por intercambios."""
    distancias = pairwise_distances(datos)
    candidatos = sorted(np.unique(datos, axis=0, return_index=True)[1])
    centros = []
    cercana = np.full(len(datos), np.inf)
    for _ in range(grupos):
        nuevo = min((i for i in candidatos if i not in centros),
                    key=lambda i: np.minimum(cercana, distancias[:, i]).sum())
        centros.append(nuevo)
        cercana = np.minimum(cercana, distancias[:, nuevo])
    for _ in range(50):
        costo, intercambio = cercana.sum(), None
        for posicion in range(grupos):
            otras = np.delete(centros, posicion)
            alternativa = distancias[:, otras].min(axis=1)
            for candidato in candidatos:
                if candidato in centros:
                    continue
                evaluada = np.minimum(alternativa, distancias[:, candidato])
                if evaluada.sum() < costo - 1e-10:
                    costo, intercambio = evaluada.sum(), (posicion, candidato, evaluada)
        if intercambio is None:
            break
        posicion, candidato, cercana = intercambio
        centros[posicion] = candidato
    return distancias[:, centros].argmin(axis=1), centros


def segmentar_productos(demanda, grupos=3, metodo='K-means'):
    """Estandariza media y variabilidad; perfila en las unidades originales."""
    if not isinstance(grupos, int) or not 2 <= grupos <= 6:
        raise ValueError('Selecciona entre 2 y 6 grupos.')
    elegibles, escalados = _preparar(demanda, grupos)
    representantes = None
    if metodo == 'K-means':
        etiquetas = KMeans(n_clusters=grupos, random_state=42, n_init=10).fit_predict(escalados)
    elif metodo == 'K-medoids':
        if len(elegibles) > 300:
            raise ValueError('Filtra hasta 300 productos para ejecutar K-medoids.')
        etiquetas, representantes = _medoides(escalados, grupos)
    elif metodo == 'Jerárquico (Ward)':
        if len(elegibles) > 1000:
            raise ValueError('Filtra hasta 1 000 productos para ejecutar Ward.')
        etiquetas = cut_tree(linkage(escalados, method='ward'), n_clusters=grupos).ravel()
    else:
        raise ValueError('Método de agrupamiento no disponible.')
    if representantes is None:
        representantes = []
        for grupo in np.unique(etiquetas):
            indices = np.flatnonzero(etiquetas == grupo)
            puntos = escalados[indices]
            representantes.append(indices[((puntos - puntos.mean(axis=0)) ** 2).sum(axis=1).argmin()])
    elegibles['representante'] = elegibles.index.isin(representantes)
    elegibles['grupo'] = etiquetas
    orden = elegibles.groupby('grupo')['demanda_diaria'].mean().sort_values().index
    nombres = {grupo: f'Grupo {posicion + 1} · ' + (
        'menor venta diaria' if posicion == 0 else 'mayor venta diaria' if posicion == grupos - 1 else 'venta intermedia')
        for posicion, grupo in enumerate(orden)}
    elegibles['segmento'] = elegibles['grupo'].map(nombres)
    perfiles = elegibles.groupby('segmento', as_index=False).agg(
        productos=('producto_id', 'count'), demanda_media=('demanda_diaria', 'mean'), cv_medio=('cv', 'mean'),
    ).sort_values('demanda_media')
    return elegibles.drop(columns='grupo'), perfiles, _silueta(escalados, etiquetas)


def diagnostico_kmeans(demanda):
    elegibles, datos = _preparar(demanda, 2)
    distintos = len(elegibles[['demanda_diaria', 'cv']].drop_duplicates())
    filas = []
    for k in range(1, min(6, distintos) + 1):
        modelo = KMeans(n_clusters=k, random_state=42, n_init=10).fit(datos)
        filas.append({'k': k, 'inercia': modelo.inertia_, 'silueta': _silueta(datos, modelo.labels_)})
    return pd.DataFrame(filas)


def ramas_ward(demanda):
    _, datos = _preparar(demanda, 2)
    arbol = dendrogram(linkage(datos, method='ward'), no_plot=True, truncate_mode='lastp', p=18)
    return pd.DataFrame([{'rama': i, 'orden': j, 'x': x, 'distancia': y}
                         for i, (xs, ys) in enumerate(zip(arbol['icoord'], arbol['dcoord']))
                         for j, (x, y) in enumerate(zip(xs, ys))])
