"""Carga y validación de los tres archivos CSV del prototipo."""

import csv
import io
from pathlib import Path
import warnings

import numpy as np
import pandas as pd


class ErrorDatos(ValueError):
    """Un archivo no cumple el contrato de datos del proyecto."""


ESQUEMAS = {
    'productos': {
        'columnas': ['producto_id', 'nombre', 'categoria'],
        'clave': ['producto_id'], 'numeros': [], 'fecha': None,
    },
    'ventas': {
        'columnas': ['fecha', 'producto_id', 'unidades_vendidas'],
        'clave': ['fecha', 'producto_id'],
        'numeros': ['unidades_vendidas'], 'fecha': 'fecha',
    },
    'inventario': {
        'columnas': ['fecha_corte', 'producto_id', 'stock_actual', 'stock_minimo'],
        'clave': ['fecha_corte', 'producto_id'],
        'numeros': ['stock_actual', 'stock_minimo'], 'fecha': 'fecha_corte',
    },
}


def cargar_csv(origen, tipo):
    """Lee una ruta o archivo binario sin perder ceros de los códigos.

    Devuelve un DataFrame validado. No corrige ni elimina registros de
    manera silenciosa. Los archivos vacíos también se reportan como error.
    """
    esquema = ESQUEMAS[tipo]
    archivo = f'{tipo}.csv'
    try:
        if hasattr(origen, 'read'):
            origen.seek(0)
            contenido = origen.read()
            if isinstance(contenido, bytes):
                contenido = contenido.decode('utf-8-sig')
        else:
            contenido = Path(origen).read_text(encoding='utf-8-sig')
        encabezado = next(csv.reader(io.StringIO(contenido), delimiter=';', strict=True), [])
        if len(encabezado) != len(set(encabezado)):
            raise ErrorDatos(f'{archivo}: hay nombres de columna duplicados en el encabezado.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', pd.errors.ParserWarning)
            tabla = pd.read_csv(io.StringIO(contenido), sep=';', dtype=str,
                                keep_default_na=False, index_col=False)
    except (OSError, UnicodeError, csv.Error, pd.errors.ParserError, pd.errors.ParserWarning,
            pd.errors.EmptyDataError) as error:
        raise ErrorDatos(f'{archivo}: no se pudo leer. Usa CSV UTF-8 separado por punto y coma.') from error

    faltantes = set(esquema['columnas']) - set(tabla.columns)
    if faltantes:
        raise ErrorDatos(f'{archivo}: faltan columnas: {", ".join(sorted(faltantes))}.')
    tabla = tabla[esquema['columnas']].copy()
    if tabla.empty:
        raise ErrorDatos(f'{archivo}: no contiene registros.')

    for columna in tabla.columns:
        tabla[columna] = tabla[columna].str.strip()
        vacios = tabla[columna].eq('')
        if vacios.any():
            fila = int(tabla.index[vacios][0]) + 2
            raise ErrorDatos(f'{archivo}: {columna} está vacío en la fila {fila}.')

    fecha = esquema['fecha']
    if fecha:
        formato = tabla[fecha].str.fullmatch(r'\d{4}-\d{2}-\d{2}')
        convertido = pd.to_datetime(tabla[fecha], format='%Y-%m-%d', errors='coerce')
        if (~formato | convertido.isna()).any():
            raise ErrorDatos(f'{archivo}: {fecha} contiene fechas inválidas; usa AAAA-MM-DD.')
        tabla[fecha] = convertido

    for columna in esquema['numeros']:
        numeros = pd.to_numeric(tabla[columna], errors='coerce')
        invalidos = numeros.isna() | ~np.isfinite(numeros) | (numeros < 0) | (numeros % 1 != 0)
        # Límite conservador para evitar pérdida de precisión al agregar.
        invalidos |= numeros > 1_000_000_000
        if invalidos.any():
            fila = int(tabla.index[invalidos][0]) + 2
            raise ErrorDatos(f'{archivo}: {columna} debe ser un entero entre 0 y 1 000 000 000 (fila {fila}).')
        tabla[columna] = numeros.astype('int64')

    if tabla.duplicated(esquema['clave']).any():
        raise ErrorDatos(f'{archivo}: hay claves duplicadas ({", ".join(esquema["clave"])}).')
    return tabla


def validar_relaciones(productos, ventas, inventario):
    """Rechaza referencias a productos ajenos al catálogo."""
    catalogo = set(productos['producto_id'])
    for nombre, tabla in [('ventas', ventas), ('inventario', inventario)]:
        ajenos = set(tabla['producto_id']) - catalogo
        if ajenos:
            muestra = ', '.join(sorted(ajenos)[:5])
            raise ErrorDatos(f'{nombre}.csv: productos que no existen en el catálogo: {muestra}.')
