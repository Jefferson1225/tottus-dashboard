import unittest

import pandas as pd

from src.datos import ErrorDatos, validar_historial
from src.quiebres import construir_observaciones, evaluar_quiebres, medir_alertas


class QuiebresTests(unittest.TestCase):
    def test_rechaza_stock_o_ventas_que_contradicen_otros_csv(self):
        fecha = pd.Timestamp('2026-10-22')
        productos = pd.DataFrame({'producto_id': ['A']})
        historial = pd.DataFrame({'fecha': [fecha], 'producto_id': ['A'],
                                  'unidades_vendidas': [2], 'stock_cierre': [9]})
        ventas = historial.drop(columns='stock_cierre')
        inventario = pd.DataFrame({'fecha_corte': [fecha], 'producto_id': ['A'], 'stock_actual': [0]})
        with self.assertRaisesRegex(ErrorDatos, 'stock'):
            validar_historial(historial, productos, ventas, inventario)
        inventario['stock_actual'] = 9
        with self.assertRaisesRegex(ErrorDatos, 'ventas'):
            validar_historial(historial, productos, ventas.assign(unidades_vendidas=3), inventario)
        validar_historial(historial, productos, ventas, inventario)

    def test_etiqueta_es_el_cierre_siguiente_y_respeta_huecos(self):
        fechas = pd.date_range('2026-10-01', periods=10)
        historial = pd.DataFrame({'fecha': fechas, 'producto_id': 'A',
                                  'unidades_vendidas': [2] * 10, 'stock_cierre': [5] * 7 + [0, 7, 2]})
        observaciones = construir_observaciones(historial, fechas[8]).set_index('fecha')
        self.assertEqual(observaciones.loc[fechas[6], 'quiebre'], 1)
        self.assertEqual(observaciones.loc[fechas[7], 'quiebre'], 0)
        self.assertTrue(pd.isna(observaciones.loc[fechas[8], 'quiebre']))
        sin_dia = construir_observaciones(historial.drop(index=7), fechas[9]).set_index('fecha')
        self.assertTrue(pd.isna(sin_dia.loc[fechas[6], 'quiebre']))
        self.assertNotIn(fechas[8], sin_dia.index)

    def test_validacion_por_fecha_y_misma_muestra_para_modelos(self):
        fechas = pd.date_range('2026-08-01', periods=70)
        historial = pd.concat([pd.DataFrame({'fecha': fechas, 'producto_id': codigo,
                                            'unidades_vendidas': 2,
                                            'stock_cierre': [(i + fase) % 5 for i in range(len(fechas))]})
                               for codigo, fase in [('A', 0), ('B', 2)]], ignore_index=True)
        evaluados, actuales, bloques = evaluar_quiebres(historial, fechas[-1])
        self.assertEqual(evaluados.groupby('modelo').size().tolist(), [42] * 3)
        self.assertTrue((bloques['ultima_etiqueta_entrenamiento'] < bloques['inicio_evaluacion']).all())
        self.assertTrue(actuales['fecha'].eq(fechas[-1]).all())
        self.assertEqual(len(actuales), 6)

    def test_umbral_cambia_falsos_negativos(self):
        observado = [0, 0, 1, 1]
        puntajes = [.1, .4, .3, .8]
        estricto = medir_alertas(observado, puntajes, .5)
        sensible = medir_alertas(observado, puntajes, .3)
        self.assertEqual((estricto['fn'], estricto['fp']), (1, 0))
        self.assertEqual((sensible['fn'], sensible['fp']), (0, 1))
        self.assertEqual(estricto['ap'], sensible['ap'])

    def test_un_historial_sin_quiebres_no_genera_predicciones(self):
        fechas = pd.date_range('2026-08-01', periods=70)
        historial = pd.DataFrame({'fecha': fechas, 'producto_id': 'A',
                                  'unidades_vendidas': 2, 'stock_cierre': 10})
        with self.assertRaisesRegex(ValueError, 'quiebre'):
            evaluar_quiebres(historial, fechas[-1])
