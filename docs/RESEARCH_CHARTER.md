# Acta de investigación — versión 0.1

Nota editorial 0.2: este documento se conserva como planificación interna.
Sus alternativas e hitos son revisables, no resultados ni compromisos cerrados.
El artículo IEEE breve se desarrolla en `paper/main_es.tex` y `paper/main_en.tex`.

Fecha de formulación: 2026-09-08. Estado: protocolo prospectivo, revisable.
Título de trabajo: **Productos punto U4×S8 con corrección de zero-point en un
pipeline RV32: diseño y evaluación de XQDot4Z**.

## Problema y pregunta principal

Empacar pesos a cuatro bits ahorra almacenamiento, pero utilizarlos en un core
escalar requiere extracción y aritmética de signo/corrección. Una operación
fusionada puede ahorrar instrucciones, pero añade hardware y puede prolongar
la latencia o el período de reloj. Además, la corrección admite una forma
factorizada que reutiliza la suma de activaciones entre filas.

**¿En qué condiciones una operación escalar de cuatro productos U4×S8 con
corrección de zero-point fusionada reduce el costo de ejecutar productos punto
y matriz–vector en un pipeline RV32, frente a multiplicación escalar y producto
punto empacado con corrección factorizada, considerando reutilización de
activaciones y costo de suministrar el zero-point?**

En simulación, “costo” significa principalmente ciclos del kernel completo,
con desglose de instrucciones y código. Recursos y tiempo físico son resultados
condicionados a disponer de síntesis/timing comparable; energía requiere otra
metodología. No se mezclan esas magnitudes en una promesa de “eficiencia”.

## Subpreguntas y criterios

- **RQ1, procesamiento empacado:** diferencia entre D y B2 con datos iguales.
- **RQ2, corrección fusionada (central):** diferencia entre D y B3, permitiendo
  que B3 calcule `Sa` una vez por grupo y reutilice entre N filas.
- **RQ3, sensibilidad:** cómo cambian RQ1/RQ2 con N, K, G y política de zero-point.
- **RQ4, extensión posterior:** compromiso de recursos y tiempo para una unidad
  paralela, de dos vías e iterativa, bajo idéntico dispositivo y restricciones.

**H1:** D reduce ciclos respecto de B2 en el kernel primario predefinido. Se
contrasta por caso; resultados iguales o peores se conservan y se discuten.
**H2:** el beneficio relativo D/B3 disminuye al aumentar N si B3 amortiza `Sa`;
se buscará esa tendencia sin forzar monotonicidad ni ocultar contraejemplos.
**H3:** suministrar zero-points variables puede desplazar o eliminar una ventaja
observada con constantes; se comparan regímenes explícitos, no se asume gratis.
H1–H3 son expectativas de trabajo, no hallazgos ni pruebas de significancia.

Ejecutados el piloto y la campaña, H2 se sostiene donde tiene sentido: la
ventaja de D sobre B3 se estrecha al crecer N y se anula con z=0, donde B3 elide
la corrección. Bajo ZS parte del hueco es estructural y se descuenta. H1 y H3 no
cambian: H1 se contrasta por caso y H3 sigue sin evidencia, porque el régimen ZR
no es expresable con esta interfaz. **Las hipótesis no se han editado desde su
formulación**, y el preregistro lo comprueba por hash.

La revisión del [protocolo 0.7](EXPERIMENT_PROTOCOL.md) trata valores,
distribución y repetición de z como factores, separa especialización estática
de ZR y declara amenazas a la validez. H3 no implica una cota superior de
ventaja. El [manifiesto inicial](../benchmarks/campaign.json) conserva el
barrido N y ya fija las políticas comunes de codegen, pero sigue en diseño:
faltan kernels, memoria común, instrumentación y eventos de medida.
B1 es contexto, no la respuesta a RQ1/RQ2: se selecciona una sola regla
aritmética acotada, sin búsqueda de rendimiento, y se exige congelar su
implementación antes de medir. Las semillas cubren entradas; no son
repeticiones estadísticas. El piloto por variante sigue pendiente.

## Objetivo general y objetivos específicos

Determinar experimentalmente el alcance útil y las limitaciones de XQDot4Z
sobre Kuntur, una derivación verificable de kirky-arqui.

1. Congelar y auditar la plataforma; fijar un contrato numérico independiente.
2. Validar unidad e integración con oráculos enteros y pruebas de control.
3. Implementar baselines que separen multiplicación, packing y corrección.
4. Medir kernels reproducibles, publicar todos los casos y analizar sensibilidad.
5. Preparar síntesis y FPGA sin confundir simulación con evidencia física.

## Alcance mínimo

- Kuntur: un core in-order RV32 derivado de kirky-arqui; soporte C documentado.
- Pesos U4, activaciones S8 con zero-point cero, grupos de pesos con zero-point U4.
- Cuatro términos por operación, selección de mitad baja/alta, resultado INT32.
- Batch uno; productos punto y matriz–vector densos pequeños.
- Primera etapa sin FPGA: corrección y ciclos RTL; capa con epílogo como hito posterior.

Fuera del mínimo: entrenar LLM, ejecutar un LLM completo, desarrollar una NPU,
RVV, MMU, sistema operativo, soporte íntegro de RV32IC/M y medición de energía.
Una red pequeña y FPGA son extensiones posteriores, no requisitos para validar
el subtotal entero. No se promete novedad absoluta ni publicación garantizada.

## Contribuciones candidatas

Un contrato y una implementación reproducibles; una comparación controlada que
aísle el zero-point; y un mapa de condiciones donde la fusión ayuda o no ayuda.
La contribución definitiva se redactará después de medir y ampliar antecedentes.
Un resultado negativo bien explicado también responde la pregunta.

## Hitos y puertas de aceptación

| Hito | Entregable | Condición para avanzar |
|---|---|---|
| M0 | Protocolo, auditoría, snapshot y artículo inicial | Evidencias trazables y alcance explícito; realizado en esta versión |
| M1 | Contrato v0.1 y referencia Python: realizado | Packing, signo, límites, selector y ejemplos comprobados; evidencia en `docs/MODEL_STATE.json`. No valida RTL |
| M2 | RTL aislado y testbench: realizado | 556 734 comparaciones por simulador, ocho controles por simulador y cuatro mutaciones detectadas; evidencia en `docs/RTL_STATE.json`. No valida integración ni rendimiento |
| M3a | Interfaz inmediata e integración opcional: realizado | 25 programas en dos simuladores, encoding, retiro/writeback, stores, hazards, flush, reset y mutaciones; `docs/INTEGRATION_STATE.json` |
| M3b | Base común y comparadores: realizado | Las cuatro variantes tienen kernels verificados bajo la política común v2, con 24 acuerdos a cuatro bandas en dos simuladores y lista blanca de opcodes por variante; evidencia en `docs/KERNEL_STATE.json`. Eventos de medida y contadores fijados y verificados con oráculo estructural (`docs/MEASUREMENT_STATE.json`) |
| M4 | B1/B2/B3/D y kernels: realizado | Inventario de 2280 casos materializado y recomputable, políticas congeladas y revisión previa registrada; campaña completa con 2280/2280 en `pass`, costos por caso y ningún caso ausente. Sin speedup agregado ni rejilla reducida. `docs/CAMPAIGN_STATE.json`, `docs/PILOT_STATE.json` |
| M5 | Resultados y análisis: realizado | Artículo ES/EN con la comparación central por régimen y fase, la descomposición del hueco bajo ZS, el costo en tamaño de código y tres límites explícitos. Cifras ancladas por macro y comprobadas contra la evidencia |
| M6 | Síntesis/FPGA | Herramientas, dispositivo y restricciones acordados; evidencia física separada |

M1/M2 se desarrollaron sin modificar el core. M3a añade la instrucción sin
convertirla en la variante D completa del protocolo. No se inicia la comparación
causal M4 hasta cerrar los problemas que afecten a los kernels de M3b.

## Gestión de cambios

Las decisiones abiertas están en `DECISIONS.md`. Se permite revisar hipótesis y
factores, registrando fecha, motivo y si se observaron resultados antes del
cambio. Este es un protocolo versionado local, no una preregistración externa.
Cada tabla del artículo debe citar un artefacto o decir “pendiente”; no se usan
valores de ejemplo como resultados. Autoría, afiliación, licencia y venue se
acuerdan con las personas involucradas antes de difundir públicamente.
