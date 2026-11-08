import unittest

import pandas as pd

from src.reposicion import calcular_reposicion


class ReposicionTests(unittest.TestCase):
    def setUp(self):
        self.demanda = pd.DataFrame({'producto_id': ['001', '002', '003'],
                                    'nombre': ['Arroz', 'Agua', 'Jabon'], 'categoria': ['A', 'B', 'C'],
                                    'demanda_diaria': [10., 0., float('nan')]})
        self.inventario = pd.DataFrame({'producto_id': ['001', '002', '003'],
                                       'fecha_corte': pd.to_datetime(['2026-10-22'] * 3),
                                       'stock_actual': [40, 0, 12], 'stock_minimo': [20, 0, 5]})

    def calcular(self, **opciones):
        return calcular_reposicion(self.demanda, self.inventario, '2026-10-22', **opciones).set_index('producto_id')

    def test_formula_manual_y_datos_desconocidos(self):
        resultado = self.calcular(plazo=3, revision=7, seguridad=2)
        fila = resultado.loc['001']
        self.assertEqual(fila['stock_seguridad'], 20)
        self.assertEqual(fila['punto_reorden'], 50)
        self.assertEqual(fila['stock_objetivo'], 120)
        self.assertEqual(fila['cantidad_sugerida'], 80)
        self.assertEqual(fila['prioridad'], 'Media')
        self.assertEqual(fila['cobertura_dias'], 4)
        self.assertEqual(resultado.loc['002', 'cantidad_sugerida'], 0)
        self.assertEqual(resultado.loc['002', 'prioridad'], 'Sin demanda reciente')
        self.assertTrue(pd.isna(resultado.loc['003', 'cantidad_sugerida']))

    def test_disparador_incluye_igualdad_pero_no_stock_superior(self):
        self.inventario.loc[0, 'stock_actual'] = 51
        self.assertEqual(self.calcular().loc['001', 'cantidad_sugerida'], 0)
        self.inventario.loc[0, 'stock_actual'] = 50
        self.assertEqual(self.calcular().loc['001', 'cantidad_sugerida'], 70)

    def test_escenario_cero_reproduce_base_y_no_muta_fuentes(self):
        copia = self.demanda.copy(deep=True)
        base = self.calcular()
        escenario = self.calcular(variacion=0, retraso=0, cambio_stock=0)
        pd.testing.assert_frame_equal(base, escenario)
        pd.testing.assert_frame_equal(self.demanda, copia)
        estres = self.calcular(variacion=50, retraso=2, cambio_stock=-50)
        self.assertEqual(estres.loc['001', 'stock_evaluado'], 20)
        self.assertEqual(estres.loc['001', 'cantidad_sugerida'], 190)
        self.assertEqual(estres.loc['001', 'prioridad'], 'Alta')

    def test_sin_inventario_no_recomienda_cero(self):
        self.inventario = self.inventario.iloc[1:]
        fila = self.calcular().loc['001']
        self.assertEqual(fila['prioridad'], 'No evaluable')
        self.assertTrue(pd.isna(fila['cantidad_sugerida']))

    def test_rechaza_parametros_invalidos(self):
        for opciones in [{'plazo': -1}, {'variacion': -101}, {'revision': 0}, {'seguridad': float('nan')}]:
            with self.subTest(opciones=opciones), self.assertRaises(ValueError):
                self.calcular(**opciones)

    def test_escenario_sin_demanda_no_afirma_ventas_historicas_nulas(self):
        fila = self.calcular(variacion=-100).loc['001']
        self.assertEqual(fila['prioridad'], 'Demanda simulada nula')
        self.assertIn('escenario', fila['explicacion'])
        self.assertNotIn('Ventas nulas en toda la ventana', fila['explicacion'])
        self.assertEqual(fila['cantidad_sugerida'], 0)


if __name__ == '__main__':
    unittest.main()
