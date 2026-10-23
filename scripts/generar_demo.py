"""Genera datos académicos deterministas. No representa operaciones de Tottus."""

from pathlib import Path
import random

import pandas as pd


def generar():
    destino = Path(__file__).resolve().parents[1] / 'data' / 'demo'
    destino.mkdir(parents=True, exist_ok=True)
    # nombre, categoría, venta diaria base, stock, stock mínimo.
    filas = [
        ('Arroz extra 1 kg', 'Abarrotes', 24, 0, 80),
        ('Aceite vegetal 1 L', 'Abarrotes', 18, 32, 60),
        ('Azúcar rubia 1 kg', 'Abarrotes', 17, 160, 60),
        ('Fideos tallarín 500 g', 'Abarrotes', 14, 120, 40),
        ('Leche evaporada 400 g', 'Abarrotes', 30, 45, 90),
        ('Agua sin gas 625 ml', 'Bebidas', 35, 240, 100),
        ('Gaseosa cola 1.5 L', 'Bebidas', 22, 0, 60),
        ('Néctar de durazno 1 L', 'Bebidas', 12, 80, 40),
        ('Bebida isotónica 500 ml', 'Bebidas', 10, 35, 35),
        ('Detergente en polvo 800 g', 'Limpieza', 11, 18, 35),
        ('Lejía 1 L', 'Limpieza', 9, 90, 30),
        ('Lavavajillas 750 g', 'Limpieza', 8, 70, 25),
        ('Limpiador multiuso 900 ml', 'Limpieza', 7, 60, 20),
        ('Jabón de tocador 90 g', 'Cuidado personal', 13, 0, 40),
        ('Pasta dental 90 g', 'Cuidado personal', 9, 85, 30),
        ('Champú familiar 400 ml', 'Cuidado personal', 0, 40, 20),
    ]
    productos, inventario, ventas = [], [], []
    azar = random.Random(20261022)
    for numero, (nombre, categoria, base, stock, minimo) in enumerate(filas, start=1):
        codigo = f'{numero:04d}'
        productos.append({'producto_id': codigo, 'nombre': nombre, 'categoria': categoria})
        inventario.append({'fecha_corte': '2026-10-22', 'producto_id': codigo,
                           'stock_actual': stock, 'stock_minimo': minimo})
        for fecha in pd.date_range('2026-08-01', '2026-10-22'):
            factor = 1.25 if fecha.day_of_week >= 5 else 1.0
            tendencia = 1 + (fecha.day_of_year - 213) / 650
            unidades = max(0, round(base * factor * tendencia + azar.randint(-4, 4))) if base else 0
            ventas.append({'fecha': fecha.strftime('%Y-%m-%d'), 'producto_id': codigo,
                           'unidades_vendidas': unidades})
    for nombre, registros in [('productos', productos), ('inventario', inventario), ('ventas', ventas)]:
        pd.DataFrame(registros).to_csv(destino / f'{nombre}.csv', sep=';', index=False, encoding='utf-8')
    print(f'Demo generada: {len(productos)} productos, {len(ventas)} registros diarios. {destino}')


if __name__ == '__main__':
    generar()
