"""Demanda de referencia y evaluación diaria con orígenes temporales sucesivos."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


def _serie(ventas, codigo, corte, dias):
    corte = pd.Timestamp(corte).normalize()
    indice = pd.date_range(end=corte, periods=dias, freq='D')
    registros = ventas.loc[(ventas['producto_id'] == codigo) & ventas['fecha'].isin(indice)]
    return registros.set_index('fecha')['unidades_vendidas'].reindex(indice).astype(float)


def estimar_demanda(productos, ventas, corte, ventana=28):
    """Exige una ventana diaria completa; los huecos permanecen desconocidos."""
    if not isinstance(ventana, int) or not 7 <= ventana <= 365:
        raise ValueError('La ventana debe ser un entero entre 7 y 365 días.')
    filas = []
    for producto in productos.to_dict('records'):
        serie = _serie(ventas, producto['producto_id'], corte, ventana)
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


def evaluar_demanda(productos, ventas, corte, ventana=28, dias_prueba=14):
    """Backtest de un día adelante; cada origen usa solo el pasado disponible.

    Ambos métodos se comparan sobre los mismos productos y fechas.
    No ajusta hiperparámetros ni elige un ganador para producción.
    """
    if not isinstance(ventana, int) or not 7 <= ventana <= 365:
        raise ValueError('La ventana debe ser un entero entre 7 y 365 días.')
    if not isinstance(dias_prueba, int) or not 1 <= dias_prueba <= 90:
        raise ValueError('El periodo de evaluación debe estar entre 1 y 90 días.')
    registros, excluidos = [], []
    for codigo in productos['producto_id']:
        serie = _serie(ventas, codigo, corte, ventana + dias_prueba)
        if serie.isna().any():
            excluidos.append({'producto_id': codigo, 'motivo': 'Histórico diario incompleto para evaluar ambos métodos'})
            continue
        for posicion in range(ventana, len(serie)):
            media = float(serie.iloc[posicion - ventana:posicion].mean())
            semanal = float(serie.iloc[posicion - 7])
            for metodo, estimado in [('Media móvil', media), ('Ingenuo semanal', semanal)]:
                registros.append({'producto_id': codigo, 'fecha': serie.index[posicion],
                                  'metodo': metodo, 'real': float(serie.iloc[posicion]), 'estimado': estimado})

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
