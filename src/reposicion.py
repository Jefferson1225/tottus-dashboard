"""Política de revisión y reposición de inventario."""

import math

import numpy as np
import pandas as pd


def calcular_reposicion(demanda, inventario, corte, plazo=3, revision=7, seguridad=2,
                       variacion=0, retraso=0, cambio_stock=0):
    """Sugiere reponer al alcanzar el punto de reorden, sin modificar las fuentes.

    Supone pedidos en tránsito y reservas iguales a cero. Los parámetros
    son supuestos comunes a la selección, no políticas verificadas de Tottus.
    """
    for nombre, valor in [('plazo', plazo), ('revision', revision), ('seguridad', seguridad), ('retraso', retraso)]:
        if not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
            raise ValueError(f'{nombre} debe ser un número finito no negativo.')
    if revision <= 0:
        raise ValueError('El periodo de revisión debe ser mayor que cero.')
    for nombre, valor in [('variacion', variacion), ('cambio_stock', cambio_stock)]:
        if not isinstance(valor, (int, float)) or not math.isfinite(valor) or not -100 <= valor <= 1000:
            raise ValueError(f'{nombre} debe estar entre -100 y 1000 %.')

    foto = inventario[inventario['fecha_corte'].eq(pd.Timestamp(corte))][['producto_id', 'stock_actual']]
    resultado = demanda.merge(foto, on='producto_id', how='left', validate='one_to_one').copy()
    resultado['demanda_escenario'] = resultado['demanda_diaria'] * (1 + variacion / 100)
    resultado['stock_evaluado'] = np.floor(resultado['stock_actual'].astype(float) * (1 + cambio_stock / 100))
    d = resultado['demanda_escenario']
    tiempo = plazo + retraso
    resultado['stock_seguridad'] = np.ceil(d * seguridad)
    resultado['punto_reorden'] = np.ceil(d * tiempo + resultado['stock_seguridad'])
    resultado['stock_objetivo'] = np.ceil(d * (tiempo + revision) + resultado['stock_seguridad'])
    resultado['cobertura_dias'] = resultado['stock_evaluado'] / d.where(d.gt(0))
    evaluable = d.notna() & resultado['stock_evaluado'].notna()
    activar = evaluable & resultado['stock_evaluado'].le(resultado['punto_reorden'])
    resultado['cantidad_sugerida'] = 0.
    resultado.loc[activar, 'cantidad_sugerida'] = (
        resultado.loc[activar, 'stock_objetivo'] - resultado.loc[activar, 'stock_evaluado']).clip(lower=0)
    resultado.loc[~evaluable, 'cantidad_sugerida'] = np.nan

    resultado['prioridad'] = 'Baja'
    resultado.loc[activar, 'prioridad'] = 'Media'
    resultado.loc[evaluable & resultado['stock_evaluado'].le(d * tiempo), 'prioridad'] = 'Alta'
    resultado.loc[evaluable & d.eq(0), 'prioridad'] = 'Sin demanda reciente'
    resultado.loc[evaluable & d.eq(0) & resultado['demanda_diaria'].gt(0), 'prioridad'] = 'Demanda simulada nula'
    resultado.loc[~evaluable, 'prioridad'] = 'No evaluable'

    motivos = []
    for fila in resultado.to_dict('records'):
        if pd.isna(fila['demanda_diaria']):
            motivo = 'Histórico diario incompleto; revisar los registros antes de recomendar.'
        elif pd.isna(fila['stock_evaluado']):
            motivo = 'No hay inventario del producto en el corte seleccionado.'
        elif fila['demanda_escenario'] == 0 and fila['demanda_diaria'] > 0:
            motivo = 'La variación del escenario reduce la demanda estimada a cero; el histórico sí registra ventas. Propuesta 0 bajo ese supuesto.'
        elif fila['demanda_escenario'] == 0:
            motivo = 'Ventas nulas en toda la ventana; propuesta 0 bajo este supuesto. Revisar demanda no atendida.'
        elif fila['cantidad_sugerida'] > 0:
            motivo = (f'Stock {fila["stock_evaluado"]:.0f} ≤ punto de reorden {fila["punto_reorden"]:.0f}. '
                      f'Objetivo {fila["stock_objetivo"]:.0f} − stock {fila["stock_evaluado"]:.0f} '
                      f'= {fila["cantidad_sugerida"]:.0f} unidades.')
        else:
            motivo = (f'Stock {fila["stock_evaluado"]:.0f} por encima del punto de reorden '
                      f'{fila["punto_reorden"]:.0f}; no se activa reposición.')
        motivos.append(motivo)
    resultado['explicacion'] = motivos
    return resultado
