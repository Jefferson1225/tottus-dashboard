# Metodología de demanda, reposición y alertas

Relacionamos el histórico de ventas con una política de reposición y con alertas de stock al cierre. La fuente se identifica en cada panel.

## Fecha de análisis y calidad del histórico

El corte elegido del inventario es también el cierre del histórico de los modelos. La ventana diaria predeterminada es de 28 días, incluidos sus ceros explícitos. Por producto, una fecha faltante deja la demanda desconocida; no asumimos ventas nulas, no interpolamos y no usamos registros posteriores al corte.

El periodo de la vista descriptiva es independiente: cambiar ese filtro no cambia la ventana del modelo. Cada panel indica qué periodo utiliza.

## Demanda de referencia

Usamos la media de unidades vendidas por día en la ventana completa. La tratamos como una referencia de demanda futura constante; no incorpora automáticamente promociones ni estacionalidad. Calculamos también la desviación estándar poblacional y el coeficiente de variación (CV = desviación / media). En una ventana completa de ceros asignamos CV igual a cero.

Las ventas observadas pueden ser inferiores a la demanda cuando hubo falta de stock. Sin un registro de demanda perdida, el modelo no corrige ese sesgo. Un producto sin ventas requiere revisión antes de decidir su abastecimiento.

## Evaluación temporal

Evaluamos 14 fechas de inicio por producto, con horizontes configurables de 1, 3, 7 o 14 días. El último horizonte termina en el corte. Exigimos `ventana + 14 + horizonte - 1` días consecutivos:

- **Media móvil:** promedio de la ventana anterior al inicio, multiplicado por el horizonte.
- **Ingenuo semanal:** repite los siete días anteriores al inicio hasta completar el horizonte.

Avanzamos un origen por día e incorporamos únicamente observaciones conocidas antes de cada inicio. Los horizontes pueden solaparse: cada fila compara su pronóstico acumulado con la venta acumulada correspondiente.

Informamos MAE, RMSE y WAPE sobre pares producto-fecha de inicio. MAE = promedio de errores absolutos; RMSE = raíz del promedio de errores cuadrados; WAPE = 100 × suma de errores absolutos / suma de ventas reales. WAPE queda vacío si el denominador es cero.

La ventana y el horizonte se pueden ajustar. La reposición sigue usando la media móvil; la comparación sirve para revisar su desempeño.

## Política de reposición

Definimos `d` como venta diaria de referencia, `L` como plazo de entrega, `R` como intervalo de revisión y `B` como días de seguridad. Los valores iniciales son L = 3, R = 7 y B = 2 días.

- Seguridad: `S = ceil(d × B)` unidades.
- Punto de reorden: `P = ceil(d × L + S)` unidades.
- Objetivo: `T = ceil(d × (L + R) + S)` unidades.
- Si el stock `I ≤ P`, cantidad sugerida `Q = max(T − I, 0)`; si `I > P`, `Q = 0`.
- Cobertura: `I / d` días cuando `d > 0`. Con ventas nulas no informamos una cobertura numérica.

El stock mínimo del CSV es un umbral descriptivo y no se reutiliza como si fuera el stock de seguridad calculado.

La prioridad es **alta** cuando `I ≤ d × L`; **media** cuando el inventario alcanza el punto de reorden pero supera la venta estimada durante el plazo; **baja** cuando `I > P`. Se presenta **Sin demanda reciente** para una ventana completa de ceros, **Demanda simulada nula** cuando el escenario reduce a cero una demanda base positiva, y **No evaluable** si faltan demanda o inventario. Estas categorías son reglas y no probabilidades ni eventos observados de quiebre.

Suponemos inventario disponible igual a stock actual, sin reservas ni pedidos en tránsito. El objetivo combina plazo y revisión, sujeto al punto de reorden. La política no optimiza costos, lotes, vencimientos, presupuesto o capacidad. La decisión de compra requiere revisión humana.

## Escenarios What-If

El escenario conserva los archivos y aplica tres cambios comunes a la selección:

- Demanda ajustada = `d × (1 + variación_demanda / 100)`.
- Plazo ajustado = plazo base + retraso adicional.
- Stock ajustado = `floor(I × (1 + variación_stock / 100))`.

Recalculamos seguridad, punto de reorden, objetivo y cantidades con esos valores. Con tres cambios iguales a cero, los resultados son idénticos a los de la política base. El CSV de comparación incluye los parámetros, el corte y la ventana para interpretar la propuesta.

Hay dos casos listos para comparar en el mismo corte. **Favorable** reduce la demanda un 20 % y aumenta el stock un 20 %. **Temporada alta con retraso** aumenta la demanda un 20 % y añade dos días al plazo de entrega. Ambos usan porcentajes editables.

En **Sensibilidad y meta de cobertura**, elegimos un producto. La tabla cambia la demanda de −40 % a +40 % en pasos de 20 puntos porcentuales, con el stock y los plazos de la política base. Muestra cómo cambian el punto de reorden, la prioridad y la cantidad sugerida.

La búsqueda de objetivo parte de los días que queremos cubrir. Para una meta de `k` días y demanda diaria `d`, el stock objetivo de cobertura es `ceil(d × k)`. La brecha es la diferencia positiva frente al stock actual. Esta meta usa la demanda base y corresponde únicamente a los días que pide el usuario. La propuesta general de reposición usa además sus propios parámetros de entrega, revisión y seguridad.

## Segmentación de productos

Aplicamos StandardScaler a venta diaria media y CV. K-means usa centroides e incluye inercia para el método del codo. K-medoids usa productos como centros y reduce la suma de distancias mediante intercambios. Ward agrupa por el aumento de varianza dentro de los grupos y permite explorar las uniones en el dendrograma. Exigimos tantos perfiles distintos como grupos solicitados y excluimos los históricos incompletos.

Los números de clúster no tienen significado comercial por sí solos. Ordenamos los perfiles por venta diaria media y mostramos los promedios sin estandarizar para interpretarlos. Los grupos son relativos al catálogo filtrado y pueden cambiar al modificar la selección o la ventana.

La silueta resume separación y cohesión en las variables estandarizadas, entre -1 y 1. Solo se calcula con al menos dos grupos y más observaciones que grupos. No mide exactitud predictiva ni garantiza un número óptimo de segmentos.

## Clasificación de quiebres al cierre

Las variables describen lo que se sabe al cierre: stock disponible, ventas del día, media de ventas y días sin stock en la última semana, y día de semana. La etiqueta procede del stock del cierre siguiente. Stock cero al cierre no mide cuánto duró el quiebre ni cuánta demanda quedó sin atender.

Comparamos un árbol CART de profundidad limitada, Random Forest y SVM con kernel RBF. Los modelos ponderan las clases para que el entrenamiento no dependa solo de la más frecuente. SVM ajusta su escalado dentro de cada bloque.

Tomamos hasta 84 días de historial hasta el corte, inclusive. Evaluamos tres bloques de siete días por fecha con entrenamiento expansivo dentro de esa ventana. Antes de cada bloque excluimos los registros cuya etiqueta aún no estaría disponible antes de la primera fecha evaluada. Las métricas y curvas usan las mismas observaciones para los tres modelos. Luego ajustamos cada modelo con las etiquetas disponibles en la ventana para ordenar la revisión del día siguiente.

El umbral modifica precisión, recall, F1 y la matriz de confusión. La curva precisión–recall se compara con la frecuencia de quiebres; AP resume la precisión a distintos niveles de recall. ROC-AUC y AP no dependen del umbral mostrado. Las salidas de los clasificadores no se presentan como probabilidades calibradas.

Los datos de ejemplo comparten la misma simulación de ventas e inventario. Con archivos propios, comprobamos que el historial concuerde con los otros archivos donde coinciden producto y fecha. La clasificación no altera las cantidades de reposición ni genera pedidos.

Referencias técnicas: [K-means](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html), [silueta](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html), [validación por fecha](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) y [métricas de evaluación](https://scikit-learn.org/stable/modules/model_evaluation.html).

## Correspondencia con el LRPD

| Objetivo del proyecto | Dónde se demuestra |
| --- | --- |
| OE1 · Gestionar productos, ventas e inventario | Carga y validación de CSV, filtros, inventario por producto y formatos en **Datos y alcance**. |
| OE2 · Estimar y evaluar la demanda | Demanda diaria por producto en **Reposición** y evaluación temporal en **Pronóstico y modelos**. |
| OE3 · Determinar el riesgo de quiebre | Comparación de stock, demanda y punto de reorden en **Reposición**, con prioridad por riesgo. |
| OE4 · Recomendar reposición | Cantidad sugerida, explicación por producto y descarga de la propuesta en **Reposición**. |
| OE5 · Visualizar la decisión | Indicadores y evolución de ventas en **Vista general**, stock en **Inventario** y variables de decisión en **Reposición**. |
| OE6 · Simular escenarios | Comparación de riesgo y cantidad al variar demanda, demora y stock en **Escenarios What-If**. |

Los apartados IV.3 y V.2 del LRPD se trabajan con los dos casos contrastantes, la sensibilidad a la demanda, la meta de cobertura y el recorrido del README. La adopción organizacional, el costo-beneficio y el monitoreo pertenecen al informe de factibilidad. El historial simulado permite demostrar el flujo y comparar resultados bajo los supuestos del modelo.
