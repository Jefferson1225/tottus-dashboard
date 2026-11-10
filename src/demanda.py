"""Demanda de referencia y evaluación diaria con orígenes temporales sucesivos."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


def _series(ventas, codigos, corte, dias):
    corte = pd.Timestamp(corte).normalize()
    indice = pd.date_range(end=corte, periods=dias, freq='D')
    registros = ventas.loc[ventas['fecha'].isin(indice) & ventas['producto_id'].isin(codigos)].set_index('fecha')
    grupos = {codigo: serie.reindex(indice).astype(float) for codigo, serie
              in registros.groupby('producto_id', sort=False)['unidades_vendidas']}
    return grupos, pd.Series(index=indice, dtype=float)


def estimar_demanda(productos, ventas, corte, ventana=28):
    """Exige una ventana diaria completa; los huecos permanecen desconocidos."""
    if not isinstance(ventana, int) or not 7 <= ventana <= 365:
        raise ValueError('La ventana debe ser un entero entre 7 y 365 días.')
    series, vacia = _series(ventas, productos['producto_id'], corte, ventana)
    filas = []
    for producto in productos.to_dict('records'):
        serie = series.get(producto['producto_id'], vacia)
        dias = int(serie.notna().sum())
        completo = dias == ventana
        media = float(serie.mean()) if completo else np.nan
        desviacion = float(serie.std(ddof=0)) if completo else np.nan
        filas.append({**producto, 'demanda_diaria': media, 'desviacion_diaria': desviacion,
                      'cv': desviacion / media if completo and media > 0 else (0. if completo else np.nan),
                      'dias_observados': dias,
                      'historial': 'Completo' if completo else f'Faltan {ventana - dias} días en la ventana'})
    return pd.DataFrame(filas, columns=[*productos.columns, 'demanda_diaria', 'desviacion_diaria',
                                        'cv', 'dias_observados', 'historial'])


def evaluar_demanda(productos, ventas, corte, ventana=28, dias_prueba=14, horizonte=1):
    """Evalúa ventas acumuladas; cada origen usa solo el pasado disponible.

    Ambos métodos se comparan sobre los mismos productos y fechas.
    No ajusta hiperparámetros ni elige un ganador para producción.
    """
    if not isinstance(ventana, int) or not 7 <= ventana <= 365:
        raise ValueError('La ventana debe ser un entero entre 7 y 365 días.')
    if not isinstance(dias_prueba, int) or not 1 <= dias_prueba <= 90:
        raise ValueError('El periodo de evaluación debe estar entre 1 y 90 días.')
    if not isinstance(horizonte, int) or not 1 <= horizonte <= 30:
        raise ValueError('El horizonte debe estar entre 1 y 30 días.')
    series, vacia = _series(ventas, productos['producto_id'], corte, ventana + dias_prueba + horizonte - 1)
    registros, excluidos = [], []
    for codigo in productos['producto_id']:
        serie = series.get(codigo, vacia)
        if serie.isna().any():
            excluidos.append({'producto_id': codigo, 'motivo': 'Histórico diario incompleto para evaluar ambos métodos'})
            continue
        for posicion in range(ventana, ventana + dias_prueba):
            media = float(serie.iloc[posicion - ventana:posicion].mean()) * horizonte
            semana = serie.iloc[posicion - 7:posicion].to_numpy()
            semanal = float(np.resize(semana, horizonte).sum())
            real = float(serie.iloc[posicion:posicion + horizonte].sum())
            for metodo, estimado in [('Media móvil', media), ('Ingenuo semanal', semanal)]:
                registros.append({'producto_id': codigo, 'fecha': serie.index[posicion],
                                  'metodo': metodo, 'real': real, 'estimado': estimado})

    detalle = pd.DataFrame(registros, columns=['producto_id', 'fecha', 'metodo', 'real', 'estimado'])
    filas = []
    for metodo, grupo in detalle.groupby('metodo', sort=False):
        total_real = float(grupo['real'].sum())
        filas.append({'metodo': metodo, 'mae': mean_absolute_error(grupo['real'], grupo['estimado']),
                      'rmse': root_mean_squared_error(grupo['real'], grupo['estimado']),
                      'wape_pct': float((grupo['real'] - grupo['estimado']).abs().sum()) / total_real * 100 if total_real else np.nan,
                      'observaciones': len(grupo), 'productos': grupo['producto_id'].nunique()})
    metricas = pd.DataFrame(filas, columns=['metodo', 'mae', 'rmse', 'wape_pct', 'observaciones', 'productos'])
    return metricas, detalle, pd.DataFrame(excluidos, columns=['producto_id', 'motivo'])
