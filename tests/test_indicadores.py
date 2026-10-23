import unittest

import pandas as pd

from src.indicadores import indicadores, preparar_resumen


class IndicadoresTests(unittest.TestCase):
    def setUp(self):
        self.productos = pd.DataFrame({
            'producto_id': ['001', '002', '003'],
            'nombre': ['Arroz', 'Agua', 'Jabon'],
            'categoria': ['Abarrotes', 'Bebidas', 'Limpieza'],
        })
        self.ventas = pd.DataFrame({
            'producto_id': ['001', '001', '002'],
            'fecha': pd.to_datetime(['2026-10-01', '2026-10-02', '2026-10-02']),
            'unidades_vendidas': [2, 3, 4],
        })
        self.inventario = pd.DataFrame({
            'producto_id': ['001', '002', '001'],
            'fecha_corte': pd.to_datetime(['2026-10-02', '2026-10-02', '2026-10-01']),
            'stock_actual': [0, 10, 100],
            'stock_minimo': [5, 10, 5],
        })

    def resumen(self, inicio='2026-10-01', fin='2026-10-02'):
        return preparar_resumen(self.productos, self.ventas, self.inventario,
                                pd.Timestamp('2026-10-02'), pd.Timestamp(inicio), pd.Timestamp(fin))

    def test_no_multiplica_stock_y_conserva_productos_sin_datos(self):
        resumen = self.resumen().set_index('producto_id')
        self.assertEqual(len(resumen), 3)
        self.assertEqual(resumen.loc['001', 'unidades_vendidas'], 5)
        self.assertEqual(resumen.loc['001', 'stock_actual'], 0)
        self.assertEqual(resumen.loc['002', 'estado'], 'En nivel mínimo')
        self.assertTrue(pd.isna(resumen.loc['003', 'stock_actual']))
        self.assertEqual(resumen.loc['003', 'estado'], 'Sin datos')
        self.assertTrue(pd.isna(resumen.loc['003', 'unidades_vendidas']))

    def test_totales_manuales_y_umbrales(self):
        self.assertEqual(indicadores(self.resumen()), {
            'productos': 3, 'unidades': 9, 'sin_stock': 1,
            'bajo_minimo': 1, 'sin_inventario': 1,
        })

    def test_periodo_de_ventas_no_cambia_stock(self):
        resumen = self.resumen('2026-10-02', '2026-10-02')
        self.assertEqual(indicadores(resumen)['unidades'], 7)
        self.assertEqual(indicadores(resumen)['sin_stock'], 1)

    def test_filtro_sin_productos(self):
        self.productos = self.productos.iloc[0:0]
        resumen = self.resumen()
        self.assertTrue(resumen.empty)
        self.assertEqual(indicadores(resumen)['productos'], 0)


if __name__ == '__main__':
    unittest.main()
