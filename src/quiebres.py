"""Alertas de stock cero al siguiente cierre y validación cronológica."""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

VARIABLES = ['stock_cierre', 'unidades_vendidas', 'venta_media_7d', 'dias_sin_stock_7d', 'dia_semana']


def construir_observaciones(historial, corte):
    """Calcula variables al cierre de cada día y etiqueta solo días consecutivos."""
    tabla = historial.loc[historial['fecha'].le(pd.Timestamp(corte))].sort_values(
        ['producto_id', 'fecha']).reset_index(drop=True)
    grupos = tabla.groupby('producto_id', sort=False)
    tabla['venta_media_7d'] = grupos['unidades_vendidas'].transform(lambda s: s.rolling(7).mean())
    tabla['dias_sin_stock_7d'] = tabla['stock_cierre'].eq(0).groupby(
        tabla['producto_id']).transform(lambda s: s.rolling(7).sum())
    tabla['dia_semana'] = tabla['fecha'].dt.day_of_week
    consecutivo = grupos['fecha'].shift(-1).sub(tabla['fecha']).eq(pd.Timedelta(days=1))
    tabla['quiebre'] = grupos['stock_cierre'].shift(-1).eq(0).where(consecutivo).astype('Int64')
    completos = tabla['fecha'].sub(grupos['fecha'].shift(6)).eq(pd.Timedelta(days=6))
    return tabla.loc[completos].reset_index(drop=True)


def _modelos():
    return {
        'Árbol CART': DecisionTreeClassifier(max_depth=4, min_samples_leaf=8,
                                            class_weight='balanced', random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=80, max_depth=7, min_samples_leaf=5,
                                               class_weight='balanced', random_state=42, n_jobs=1),
        'SVM (RBF)': make_pipeline(StandardScaler(), SVC(class_weight='balanced', cache_size=64)),
    }


def _puntaje(modelo, x):
    if hasattr(modelo, 'predict_proba'):
        return modelo.predict_proba(x)[:, 1]
    # Transformación monótona del margen, para usar la misma escala del umbral.
    margen = modelo.decision_function(x)
    return 1 / (1 + np.exp(-np.clip(margen, -700, 700)))


def evaluar_quiebres(historial, corte):
    """Devuelve predicciones fuera de muestra, alertas del corte y fechas de cada bloque."""
    tabla = construir_observaciones(historial, corte)
    etiquetas = tabla.dropna(subset=['quiebre'])
    if etiquetas.empty or etiquetas['fecha'].nunique() < 42:
        raise ValueError('Se necesitan al menos 42 fechas con etiqueta y una ventana diaria completa por producto.')
    fechas = pd.date_range(end=etiquetas['fecha'].max(), periods=42)
    predicciones, bloques, actuales = [], [], []
    for bloque, (_, indices) in enumerate(TimeSeriesSplit(n_splits=3, test_size=7, gap=1).split(fechas), 1):
        inicio, fin = fechas[indices[0]], fechas[indices[-1]]
        entrenamiento = etiquetas[etiquetas['fecha'] + pd.Timedelta(days=1) < inicio]
        evaluacion = etiquetas[etiquetas['fecha'].between(inicio, fin)]
        if entrenamiento['quiebre'].nunique() != 2 or evaluacion.empty:
            raise ValueError('Cada bloque necesita historial previo con y sin quiebre, y registros posteriores para evaluar.')
        bloques.append({'bloque': bloque, 'inicio_evaluacion': inicio, 'fin_evaluacion': fin,
                        'ultima_etiqueta_entrenamiento': entrenamiento['fecha'].max() + pd.Timedelta(days=1),
                        'registros': len(evaluacion), 'quiebres': int(evaluacion['quiebre'].sum())})
        for nombre, modelo in _modelos().items():
            modelo.fit(entrenamiento[VARIABLES], entrenamiento['quiebre'])
            predicciones.append(evaluacion[['fecha', 'producto_id', 'quiebre']].assign(
                modelo=nombre, puntaje=_puntaje(modelo, evaluacion[VARIABLES]), bloque=bloque))
    evaluados = pd.concat(predicciones, ignore_index=True)
    if evaluados['quiebre'].nunique() != 2:
        raise ValueError('El periodo evaluado necesita registros con y sin quiebre para comparar los modelos.')
    hoy = tabla[tabla['fecha'].eq(pd.Timestamp(corte))]
    for nombre, modelo in _modelos().items():
        if hoy.empty:
            break
        modelo.fit(etiquetas[VARIABLES], etiquetas['quiebre'])
        actuales.append(hoy[['fecha', 'producto_id', 'stock_cierre']].assign(
            modelo=nombre, puntaje=_puntaje(modelo, hoy[VARIABLES])))
    columnas = ['fecha', 'producto_id', 'stock_cierre', 'modelo', 'puntaje']
    return evaluados, (pd.concat(actuales, ignore_index=True) if actuales else pd.DataFrame(columns=columnas)), pd.DataFrame(bloques)


def medir_alertas(observado, puntajes, umbral):
    tn, fp, fn, tp = confusion_matrix(observado, np.asarray(puntajes) >= umbral, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn) if tp + fn else 0.
    return {'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp, 'precision': precision, 'recall': recall,
            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.,
            'roc_auc': roc_auc_score(observado, puntajes), 'ap': average_precision_score(observado, puntajes)}
