"""Indicadores descriptivos: no contiene modelos predictivos ni interfaz."""

import pandas as pd


ORDEN_ESTADOS = ['Sin stock', 'Bajo mínimo', 'En nivel mínimo', 'Disponible', 'Sin datos']


def preparar_resumen(productos, ventas, inventario, fecha_corte, inicio, fin):
    """Integra un corte de stock con ventas agregadas de un periodo.

    Un producto sin registro de ventas conserva un valor desconocido.
    No se confunde la falta de inventario con stock cero.
    """
    periodo = ventas[ventas['fecha'].between(pd.Timestamp(inicio), pd.Timestamp(fin))]
    totales = periodo.groupby('producto_id', as_index=False)['unidades_vendidas'].sum()
    corte = inventario[inventario['fecha_corte'].eq(pd.Timestamp(fecha_corte))]
    resumen = productos.merge(totales, on='producto_id', how='left', validate='one_to_one')
    resumen = resumen.merge(corte, on='producto_id', how='left', validate='one_to_one')
    for columna in ['unidades_vendidas', 'stock_actual', 'stock_minimo']:
        resumen[columna] = resumen[columna].astype('Int64')

    resumen['estado'] = 'Disponible'
    resumen.loc[resumen['stock_actual'].eq(resumen['stock_minimo']).fillna(False), 'estado'] = 'En nivel mínimo'
    resumen.loc[resumen['stock_actual'].lt(resumen['stock_minimo']).fillna(False), 'estado'] = 'Bajo mínimo'
    resumen.loc[resumen['stock_actual'].eq(0).fillna(False), 'estado'] = 'Sin stock'
    resumen.loc[resumen['stock_actual'].isna(), 'estado'] = 'Sin datos'
    resumen['faltante_minimo'] = (resumen['stock_minimo'] - resumen['stock_actual']).clip(lower=0)
    resumen['estado'] = pd.Categorical(resumen['estado'], categories=ORDEN_ESTADOS, ordered=True)
    return resumen.sort_values(['estado', 'nombre']).reset_index(drop=True)


def indicadores(resumen):
    """Los contadores de stock cero y bajo mínimo pueden coincidir."""
    return {
        'productos': len(resumen),
        'unidades': int(resumen['unidades_vendidas'].sum()),
        'sin_stock': int(resumen['stock_actual'].eq(0).sum()),
        'bajo_minimo': int(resumen['stock_actual'].lt(resumen['stock_minimo']).sum()),
        'sin_inventario': int(resumen['stock_actual'].isna().sum()),
    }
