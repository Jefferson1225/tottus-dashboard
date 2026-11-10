# Catálogo de referencia, ventas e inventario

Usamos 150 presentaciones del catálogo público de Tottus Perú, consultado el 10 de noviembre de 2026. En `catalogo_referencia.csv` guardamos el código de la ficha, nombre, marca, enlace y fecha de consulta. Organizamos los artículos en ocho categorías y familias para analizarlos. Una unidad corresponde a la presentación publicada, por ejemplo una botella, una bolsa o un sixpack.

## Fuentes y supuestos

- **Catálogo.** Seleccionamos referencias de [arroz](https://www.tottus.com.pe/tottus-pe/lista/CATG16815/Arroz), [abarrotes](https://www.tottus.com.pe/tottus-pe/lista/CATG16066/Abarrotes), [menestras](https://www.tottus.com.pe/tottus-pe/lista/CATG17707/Menestras), [mayonesa](https://www.tottus.com.pe/tottus-pe/lista/CATG17636/Mayonesa), [agua](https://www.tottus.com.pe/tottus-pe/lista/CATG16846/Aguas), [lácteos](https://www.tottus.com.pe/tottus-pe/lista/CATG16061/Lacteos), [pan](https://www.tottus.com.pe/tottus-pe/lista/CATG43004/Pan-de-Molde-y-Otros), [helados y congelados](https://www.tottus.com.pe/tottus-pe/lista/CATG16062/Productos-Congelados), [limpieza](https://www.tottus.com.pe/tottus-pe/lista/CATG16051/Limpieza) y [cuidado personal](https://www.tottus.com.pe/tottus-pe/lista/CATG16072/Cuidado-Personal).
- **Compra habitual.** La canasta alimentaria del INEI incluye productos como arroz y aceite vegetal. La usamos para darles un perfil de consumo continuo. Las unidades diarias por presentación son supuestos propios y están en `demanda_base_simulada`. [Metodología de medición del INEI](https://www1.inei.gob.pe/descargar/encuestas/documentos/enaho_pobreza_medicionpobreza.pdf/).
- **Temporada en Lima.** Usamos el patrón de temperaturas de Lima para dar mayor peso a los helados y al agua entre diciembre y marzo. La mayonesa se mantiene relativamente estable, con un repunte pequeño en diciembre que asignamos en la simulación. Los multiplicadores representan nuestras hipótesis de compra. [Temperaturas normales de Lima Oeste, SENAMHI](https://www.senamhi.gob.pe/main.php?dp=lima&p=pronostico-detalle).

El catálogo es una selección de fichas públicas en una fecha. Las ventas, los mínimos y el inventario de 2025–2026 corresponden a una sede simulada de Lima. Aplicamos el mismo surtido durante todo el historial para poder comparar periodos.

## Cómo generamos los movimientos

1. Partimos de las unidades diarias de referencia para cada presentación. Ajustamos ese valor por mes, fin de semana, variación diaria y aumentos ocasionales de demanda.
2. Sumamos los pedidos que llegan ese día. Las unidades vendidas quedan limitadas por el stock disponible, así que una venta baja puede deberse a poca demanda o a falta de inventario.
3. Registramos el saldo al cierre. Cuando alcanza el mínimo, pedimos lotes con plazos distintos según la categoría y posibles demoras. Esta regla genera el historial. El panel de reposición calcula sus propias sugerencias con los parámetros elegidos.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `catalogo_referencia.csv` | 150 fichas con fuentes y demanda base simulada. |
| `productos.csv` | Catálogo en el formato de carga del dashboard. |
| `ventas.csv` | 101 700 registros de unidades vendidas, del 01/01/2025 al 09/11/2026. |
| `inventario.csv` | Stock al cierre y mínimo por producto en 23 fechas. |
| `historial_stock.csv` | Las mismas ventas diarias y el stock al cierre para los modelos de quiebre. |

`scripts/generar_demo.py` regenera los cuatro CSV operativos a partir del catálogo guardado, con semilla fija y sin conexión a internet. Todos usan UTF-8, separador `;` y fechas `AAAA-MM-DD`.
