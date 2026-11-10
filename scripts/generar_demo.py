"""Genera ventas atendidas y existencias para una sede simulada de Lima."""

from math import ceil
from pathlib import Path

import numpy as np
import pandas as pd

DATOS = Path(__file__).resolve().parents[1] / 'data' / 'demo'
INICIO, FIN = '2025-01-01', '2026-11-09'
SEMILLA = 20261110

# Cada tupla va de enero a diciembre y multiplica la demanda base de cada ficha.
ESTACIONALIDAD = {
    'Agua': (1.48, 1.55, 1.38, 1.12, .94, .83, .82, .84, .91, 1.02, 1.14, 1.34),
    'Helado': (1.95, 2.10, 1.68, 1.22, .81, .57, .52, .57, .67, .91, 1.14, 1.60),
    'Frutas congeladas': (1.28, 1.36, 1.24, 1.08, .96, .89, .87, .90, .94, 1.02, 1.11, 1.21),
    'Mayonesa': (1.08, 1.06, 1.01, 1., 1., 1., 1.04, 1., 1., 1., 1.05, 1.22),
}
ESTABLE = (1.,) * 12

# Plazos y lotes para la simulación de la tienda. Los parámetros del panel se ajustan aparte.
ABASTECIMIENTO = {
    'Abarrotes': (2, 5, 12),
    'Bebidas': (1, 4, 6),
    'Lácteos': (1, 3, 6),
    'Panadería': (1, 2, 4),
    'Helados': (2, 5, 6),
    'Congelados': (2, 5, 6),
    'Limpieza': (2, 5, 6),
    'Cuidado personal': (2, 6, 6),
}


def simular_producto(producto, fechas):
    """Recibe pedidos antes de vender y limita la venta al stock disponible."""
    codigo = producto.producto_id
    azar = np.random.default_rng(np.random.SeedSequence([SEMILLA, int(codigo)]))
    base = producto.demanda_base_simulada
    temporada = ESTACIONALIDAD.get(producto.familia, ESTABLE)
    plazo_min, plazo_max, lote = ABASTECIMIENTO[producto.categoria]
    dias_minimo = plazo_max * azar.uniform(.50, .93)
    dias_objetivo = dias_minimo + azar.uniform(3.2, 6.4)
    stock = ceil(base * temporada[fechas[0].month - 1] * dias_objetivo * azar.uniform(.65, 1.2))
    llegada, pedido = -1, 0
    ventas, inventario, historial = [], [], []

    for dia, fecha in enumerate(fechas):
        if dia == llegada:
            stock += pedido
            llegada, pedido = -1, 0

        referencia = base * temporada[fecha.month - 1] * (1 + .035 * (fecha.year - fechas[0].year))
        fin_semana = 1.23 if fecha.day_of_week >= 5 else 1.
        impulso = azar.uniform(1.25, 1.60) if azar.random() < .05 else 1.
        demanda = int(azar.poisson(referencia * fin_semana * impulso * azar.gamma(12, 1 / 12)))
        atendidas = min(stock, demanda)
        stock -= atendidas

        fecha_iso = fecha.date().isoformat()
        minimo = ceil(referencia * dias_minimo)
        ventas.append((fecha_iso, codigo, atendidas))
        historial.append((fecha_iso, codigo, atendidas, stock))
        if fecha.is_month_end or dia == len(fechas) - 1:
            inventario.append((fecha_iso, codigo, stock, minimo))

        if llegada == -1 and stock <= minimo:
            demora = int(azar.integers(plazo_min, plazo_max + 1))
            if azar.random() < .10:
                demora += int(azar.integers(1, 3))
            llegada = dia + demora
            pedido = max(lote, ceil((referencia * dias_objetivo - stock) / lote) * lote)

    return ventas, inventario, historial


def generar(destino=DATOS):
    catalogo = pd.read_csv(DATOS / 'catalogo_referencia.csv', sep=';', dtype={'producto_id': str})
    fechas = pd.date_range(INICIO, FIN)
    productos = catalogo[['producto_id', 'nombre', 'categoria']]
    ventas, inventario, historial = [], [], []
    for producto in catalogo.itertuples(index=False):
        venta_sku, cortes_sku, historial_sku = simular_producto(producto, fechas)
        ventas.extend(venta_sku)
        inventario.extend(cortes_sku)
        historial.extend(historial_sku)

    columnas_ventas = ['fecha', 'producto_id', 'unidades_vendidas']
    tablas = {
        'productos': productos,
        'ventas': pd.DataFrame(ventas, columns=columnas_ventas),
        'inventario': pd.DataFrame(inventario, columns=['fecha_corte', 'producto_id', 'stock_actual', 'stock_minimo']),
        'historial_stock': pd.DataFrame(historial, columns=[*columnas_ventas, 'stock_cierre']),
    }
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, tabla in tablas.items():
        tabla.to_csv(destino / f'{nombre}.csv', sep=';', index=False, encoding='utf-8', lineterminator='\n')
    print(f'{len(productos)} productos, {len(fechas)} días y {len(ventas)} registros de ventas. {destino}')


if __name__ == '__main__':
    generar()
