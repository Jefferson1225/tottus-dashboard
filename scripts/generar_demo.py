"""Genera un conjunto reproducible de ventas e inventario simulados."""

from pathlib import Path
import random

import pandas as pd


def simular_historial(ventas):
    """Simula entradas, ventas atendidas y saldo por día para las alertas."""
    azar = random.Random(10911)
    historial = []
    for _, dias in pd.DataFrame(ventas).groupby('producto_id', sort=False):
        nivel = max(1, round(dias['unidades_vendidas'].mean()))
        stock = 4 * nivel
        llegada = None
        for indice, fila in enumerate(dias.to_dict('records')):
            if llegada == indice:
                stock += nivel * azar.randint(3, 8)
                llegada = None
            atendidas = min(stock, fila['unidades_vendidas'])
            stock -= atendidas
            historial.append({**fila, 'unidades_vendidas': atendidas, 'stock_cierre': stock})
            if llegada is None and stock <= nivel * 1.8:
                llegada = indice + azar.randint(1, 4)
    return historial


def generar():
    destino = Path(__file__).resolve().parents[1] / 'data' / 'demo'
    destino.mkdir(parents=True, exist_ok=True)
    # Nombre, categoría, demanda diaria de referencia y stock mínimo.
    filas = [
        ('Arroz extra 1 kg', 'Abarrotes', 24, 80),
        ('Aceite vegetal 1 L', 'Abarrotes', 18, 60),
        ('Azúcar rubia 1 kg', 'Abarrotes', 17, 60),
        ('Fideos tallarín 500 g', 'Abarrotes', 14, 40),
        ('Leche evaporada 400 g', 'Abarrotes', 30, 90),
        ('Agua sin gas 625 ml', 'Bebidas', 35, 100),
        ('Gaseosa cola 1.5 L', 'Bebidas', 22, 60),
        ('Néctar de durazno 1 L', 'Bebidas', 12, 40),
        ('Bebida isotónica 500 ml', 'Bebidas', 10, 35),
        ('Detergente en polvo 800 g', 'Limpieza', 11, 35),
        ('Lejía 1 L', 'Limpieza', 9, 30),
        ('Lavavajillas 750 g', 'Limpieza', 8, 25),
        ('Limpiador multiuso 900 ml', 'Limpieza', 7, 20),
        ('Jabón de tocador 90 g', 'Cuidado personal', 13, 40),
        ('Pasta dental 90 g', 'Cuidado personal', 9, 30),
        ('Champú familiar 400 ml', 'Cuidado personal', 0, 20),
    ]
    productos, solicitudes, minimos = [], [], {}
    corte = '2026-10-22'
    azar = random.Random(20261022)
    for numero, (nombre, categoria, base, minimo) in enumerate(filas, start=1):
        codigo = f'{numero:04d}'
        productos.append({'producto_id': codigo, 'nombre': nombre, 'categoria': categoria})
        minimos[codigo] = minimo
        for fecha in pd.date_range('2026-08-01', corte):
            factor = 1.25 if fecha.day_of_week >= 5 else 1.0
            tendencia = 1 + (fecha.day_of_year - 213) / 650
            unidades = max(0, round(base * factor * tendencia + azar.randint(-4, 4))) if base else 0
            solicitudes.append({'fecha': fecha.strftime('%Y-%m-%d'), 'producto_id': codigo,
                           'unidades_vendidas': unidades})
    historial = simular_historial(solicitudes)
    ventas = [{k: fila[k] for k in ('fecha', 'producto_id', 'unidades_vendidas')} for fila in historial]
    inventario = [{'fecha_corte': corte, 'producto_id': fila['producto_id'], 'stock_actual': fila['stock_cierre'],
                   'stock_minimo': minimos[fila['producto_id']]} for fila in historial if fila['fecha'] == corte]
    for nombre, registros in [('productos', productos), ('inventario', inventario), ('ventas', ventas),
                              ('historial_stock', historial)]:
        pd.DataFrame(registros).to_csv(destino / f'{nombre}.csv', sep=';', index=False, encoding='utf-8')
    print(f'Demo generada: {len(productos)} productos, {len(ventas)} registros diarios. {destino}')


if __name__ == '__main__':
    generar()
