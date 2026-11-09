# Diccionario de datos

Contrato utilizado por la primera implementación. Los ejemplos están en `data/demo/`; `src/datos.py` valida los archivos cargados por la aplicación.

## Convenciones

- CSV UTF-8, separador `;`, decimal con punto y fechas `AAAA-MM-DD`.
- Códigos de producto como texto, conservando ceros iniciales.
- Primera versión con una sola tienda o ámbito de inventario, declarado junto con el dataset. Si se agregan tiendas, se incorporará `tienda_id` a las claves de ventas e inventario.
- Unidades enteras para productos contables. Se utilizará un catálogo que excluya productos vendidos por peso en esta primera versión.
- El periodo de ventas disponible y su fecha de cierre deberán declararse. Una fecha ausente no significa automáticamente cero ventas.
- Los datos de ejemplo se identifican como simulados en el dashboard.

## `productos.csv`: catálogo

Grano: un producto por fila. Clave: `producto_id`.

| Campo | Tipo | Regla / significado |
| --- | --- | --- |
| `producto_id` | Texto | Obligatorio, no vacío y único. |
| `nombre` | Texto | Nombre legible obligatorio. |
| `categoria` | Texto | Categoría obligatoria para filtros y agrupaciones. |

El catálogo define los productos analizados, incluso si no tienen ventas en el periodo. No se borran por no aparecer en ventas.

## `ventas.csv`: histórico diario

Grano: unidades vendidas de un producto durante un día. Clave compuesta: `fecha`, `producto_id`.

| Campo | Tipo | Regla / significado |
| --- | --- | --- |
| `fecha` | Fecha | Obligatoria y válida; dentro del periodo declarado. |
| `producto_id` | Texto | Debe existir en el catálogo. |
| `unidades_vendidas` | Entero | Mayor o igual que cero; cero solo cuando se conoce que no hubo ventas. |

Si la fuente contiene líneas de tickets, se consolidarán a este grano antes de cargarla. Las devoluciones quedan fuera del contrato inicial y deberán tratarse explícitamente si aparecen. No se eliminarán filas duplicadas sin revisar su origen: con este contrato, una clave diaria repetida debe reportarse para corregirla.

## `inventario.csv`: fotografía del stock

Grano: un producto en una fecha de corte. Clave compuesta: `fecha_corte`, `producto_id`.

| Campo | Tipo | Regla / significado |
| --- | --- | --- |
| `fecha_corte` | Fecha | Obligatoria. El análisis inicial usará un único corte común para todo el catálogo. |
| `producto_id` | Texto | Debe existir en el catálogo. |
| `stock_actual` | Entero | Unidades disponibles, mayor o igual que cero. |
| `stock_minimo` | Entero | Umbral descriptivo de inventario, mayor o igual que cero. |

La fotografía de inventario debe cubrir el catálogo analizado. Si falta un producto, se señalará como «Sin datos», sin interpretarlo como stock cero. Un CSV con varios cortes permite seleccionar uno desde el menú lateral antes de integrar los datos.

## Parámetros del modelo

| Parámetro | Unidad | Uso posterior |
| --- | --- | --- |
| `ventana_dias` | Días | Ventana completa de ventas hasta el corte; 28 por defecto. |
| `plazo_base` | Días | Plazo de entrega común a la selección; 3 por defecto. |
| `revision_dias` | Días | Intervalo de revisión; 7 por defecto. |
| `seguridad_dias` | Días de venta | Colchón de seguridad; 2 por defecto. |
| `variacion_demanda_pct` | Porcentaje | Escenario respecto a la media; base 0 %. |
| `retraso_dias` | Días | Incremento de plazo en el escenario; base 0. |
| `cambio_stock_pct` | Porcentaje | Cambio relativo del stock en el escenario; base 0 %. |

Los plazos y días de seguridad son no negativos; la revisión debe ser mayor que cero. Las variaciones porcentuales de demanda y stock admiten disminuciones hasta -100 %. Estos parámetros se controlan en pantalla y no agregan columnas obligatorias a los tres CSV originales. Cuando se introduzcan pedidos en tránsito o reservas habrá que ampliar el modelo de inventario disponible antes de recomendar compras.

## Resultados analíticos

| Variable | Unidad / interpretación |
| --- | --- |
| `demanda_diaria` | Unidades/día; media de la ventana completa, o desconocida si faltan registros. |
| `desviacion_diaria` | Desviación poblacional de las ventas diarias. |
| `cv` | Desviación / media; 0 para una ventana completa de ceros. |
| `dias_observados` | Número de días con dato válido dentro de la ventana. |
| `historial` | Completo o descripción de días faltantes. |
| `stock_seguridad` | `ceil(demanda_escenario × seguridad_dias)`, en unidades. |
| `punto_reorden` | Umbral de la política; distinto de stock mínimo del CSV. |
| `stock_objetivo` | Cobertura objetivo al plazo + revisión, más seguridad. |
| `cobertura_dias` | Stock / demanda diaria; sin valor numérico si la demanda es cero. |
| `cantidad_sugerida` | Unidades propuestas cuando se activa el reorden; desconocida si faltan datos. |
| `prioridad` | Alta, Media, Baja, Sin demanda reciente, Demanda simulada nula o No evaluable; regla explicable. |
| `explicacion` | Razón del resultado y valores utilizados. |
| `segmento` | Perfil relativo de venta obtenido con K-means; no es una clase de riesgo. |

Para fórmulas, evaluación y supuestos, consultar [metodología](metodologia-analisis.md).

## Indicadores descriptivos de la primera versión

| Indicador | Definición |
| --- | --- |
| Productos analizados | Códigos únicos del catálogo tras filtros de producto y categoría. |
| Unidades vendidas | Suma de `unidades_vendidas` en el periodo y productos seleccionados. |
| Productos sin stock | Productos con `stock_actual = 0` en el corte elegido. |
| Productos bajo mínimo | Productos con `stock_actual < stock_minimo` en el corte elegido. |

Los dos últimos grupos pueden coincidir y no deben sumarse como si fueran categorías excluyentes. Ambos excluyen inventario desconocido e informan cuántos productos quedaron sin evaluar.

En el detalle se muestra `faltante_minimo = max(stock_minimo - stock_actual, 0)`, bajo el nombre «Brecha al mínimo». Es un indicador descriptivo y no una recomendación de compra. Los estados son «Sin stock», «Bajo mínimo», «En nivel mínimo», «Disponible» y «Sin datos»; stock cero tiene precedencia incluso cuando el mínimo es cero.

Las cantidades por fila se limitan a 1 000 000 000 unidades para evitar valores desproporcionados y pérdida de precisión. Los archivos vacíos se rechazan; los días conocidos sin ventas deben registrarse explícitamente con cero.

## Validación y manejo de errores

Antes de calcular, comprobar formato, columnas obligatorias, campos vacíos, tipos, claves repetidas y referencias al catálogo. Reportar archivo, columna y motivo del error. Detener los cálculos afectados si el dato no es válido; no descartar registros silenciosamente.

No sumar stock a través de fechas ni a través de cada fila de ventas. Agregar ventas primero y unir con el corte de inventario por producto, verificando que la unión no multiplique registros.

Para estimar la demanda exigimos continuidad de calendario por producto durante la ventana. Los días confirmados sin ventas deben venir explícitamente con cero; los días sin registro, anteriores al alta del producto o con falta de stock requieren revisión de la fuente. El modelo no completa huecos automáticamente.
