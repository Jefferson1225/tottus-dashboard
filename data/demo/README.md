# Datos simulados

Estos archivos no representan operaciones reales de Tottus.

- Ámbito: una sede ficticia de demostración.
- Catálogo: 16 productos contables de 4 categorías; no se incluyen productos vendidos por peso.
- Ventas: 83 días completos, del 01/08/2026 al 22/10/2026, por producto. Incluye ceros explícitos para un producto sin ventas.
- Inventario: saldo del historial al cierre del 22/10/2026 y mínimo por producto.
- Historial para alertas: `historial_stock.csv` simula entradas con distintos plazos, ventas atendidas y saldo diario. Los otros CSV se concilian con el historial.
- Fuente: `scripts/generar_demo.py`, con semillas fijas `20261022` y `10911`. Permite reproducir los CSV sin una API externa.
- Formato: UTF-8, separado por `;`, fechas `AAAA-MM-DD` y códigos de texto con ceros iniciales.

Controles del corte: 16 productos, 1 con stock cero y 8 con stock menor que el mínimo. El producto sin stock también está dentro de los 8 bajo mínimo; no se suman ambos contadores.
