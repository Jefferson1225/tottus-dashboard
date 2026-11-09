import unittest

import pandas as pd

from src.demanda import estimar_demanda, evaluar_demanda


class DemandaTests(unittest.TestCase):
    def test_horizonte_acumula_observaciones_sin_ajustar_al_futuro(self):
        fechas = pd.date_range('2026-10-01', periods=17)
        ventas = pd.DataFrame({'producto_id': 'A', 'fecha': fechas,
                               'unidades_vendidas': [2] * 7 + [100] * 10})
        _, detalle, _ = evaluar_demanda(pd.DataFrame({'producto_id': ['A']}),
                                       ventas, fechas[-1], 7, 1, horizonte=10)
        self.assertEqual(detalle['real'].tolist(), [1000., 1000.])
        self.assertEqual(detalle['estimado'].tolist(), [20., 20.])
        self.assertEqual(detalle['fecha'].tolist(), [fechas[7]] * 2)

    def setUp(self):
        self.productos = pd.DataFrame({'producto_id': ['001', '002'],
                                      'nombre': ['Arroz', 'Agua'], 'categoria': ['A', 'B']})
        self.ventas = pd.DataFrame([
            {'producto_id': codigo, 'fecha': fecha, 'unidades_vendidas': valor}
            for codigo, valor in [('001', 10), ('002', 0)]
            for fecha in pd.date_range('2026-10-01', periods=42)
        ])
        self.corte = pd.Timestamp('2026-11-11')

    def test_media_y_ceros_conocidos(self):
        resultado = estimar_demanda(self.productos, self.ventas, self.corte, ventana=28).set_index('producto_id')
        self.assertEqual(resultado.loc['001', 'demanda_diaria'], 10)
        self.assertEqual(resultado.loc['002', 'demanda_diaria'], 0)
        self.assertEqual(resultado.loc['002', 'cv'], 0)

    def test_no_imputa_huecos_ni_aprovecha_ventas_futuras(self):
        self.ventas = self.ventas.drop(self.ventas[(self.ventas.producto_id == '001') &
                                                  (self.ventas.fecha == self.corte)].index)
        self.ventas.loc[len(self.ventas) + 1] = ['001', self.corte + pd.Timedelta(days=1), 99999]
        resultado = estimar_demanda(self.productos, self.ventas, self.corte, ventana=28).set_index('producto_id')
        self.assertTrue(pd.isna(resultado.loc['001', 'demanda_diaria']))
        self.assertEqual(resultado.loc['001', 'dias_observados'], 27)

    def test_backtest_constante_y_wape_indefinido_con_ceros(self):
        metricas, detalle, excluidos = evaluar_demanda(self.productos, self.ventas, self.corte, 28, 14)
        self.assertTrue(excluidos.empty)
        self.assertEqual(len(detalle), 56)  # 2 productos × 14 días × 2 métodos.
        self.assertTrue(metricas['mae'].eq(0).all())
        self.assertTrue(metricas['rmse'].eq(0).all())
        ceros, _, _ = evaluar_demanda(self.productos.iloc[1:], self.ventas, self.corte, 28, 14)
        self.assertTrue(ceros['wape_pct'].isna().all())

    def test_prediccion_no_usa_el_valor_del_dia_evaluado(self):
        objetivo = pd.Timestamp('2026-10-29')
        self.ventas.loc[(self.ventas.producto_id == '001') & (self.ventas.fecha == objetivo), 'unidades_vendidas'] = 1000
        _, detalle, _ = evaluar_demanda(self.productos, self.ventas, self.corte, 28, 14)
        dia = detalle[(detalle.producto_id == '001') & (detalle.fecha == objetivo)]
        self.assertEqual(dia['estimado'].tolist(), [10, 10])
        siguiente = detalle[(detalle.producto_id == '001') &
                             (detalle.fecha == objetivo + pd.Timedelta(days=1)) &
                             (detalle.metodo == 'Media móvil')]
        self.assertAlmostEqual(siguiente.iloc[0]['estimado'], 45.357142857)

    def test_backtest_incompleto_excluye_ambos_metodos(self):
        self.ventas = self.ventas.drop(self.ventas[(self.ventas.producto_id == '001') &
                                                  (self.ventas.fecha == self.corte)].index)
        metricas, detalle, excluidos = evaluar_demanda(self.productos, self.ventas, self.corte, 28, 14)
        self.assertEqual(excluidos['producto_id'].tolist(), ['001'])
        self.assertEqual(detalle['producto_id'].unique().tolist(), ['002'])
        self.assertTrue(metricas['observaciones'].eq(14).all())


if __name__ == '__main__':
    unittest.main()
