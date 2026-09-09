# Estructura del artículo IEEE — versión 0.10

El artículo es un borrador breve, no el protocolo interno completo. Se mantienen
`paper/main_es.tex` y `paper/main_en.tex`, con bibliografía, ecuaciones y figura
compartidas o comprobadas para evitar divergencias.

| Sección | Qué escribir ahora | Qué añadir cuando exista evidencia |
|---|---|---|
| Resumen | Problema, pregunta, propuesta y estado provisional | Hallazgos reales y alcance de las conclusiones |
| I. Introducción | Motivación y operación acotada | Contribuciones precisas al cerrar la evaluación |
| II. Fundamentos y trabajo relacionado | Cuantización, factorización y antecedentes pertinentes | Comparación más completa de trabajos |
| III. Pregunta y alcance | Pregunta central, simulación primero, límites | Cambios de alcance acordados antes de medir |
| IV. Método propuesto | Base común con MUL, contrato v0.1, referencia Python, RTL e integración opcional D/B3 | Kernels comparables y método de medición efectivamente ejecutado |
| V. Resultados y discusión | Verificación M2/M3a, MUL, B3 aislado e integrado; amenazas a la validez y rendimiento pendiente | Medidas comparativas e interpretación |
| VI. Conclusiones | Marcador explícito de pendiente | Respuesta respaldada a la pregunta |
| Referencias | Solo trabajos citados | Fuentes primarias relevantes, sin rellenar por cantidad |

Los títulos pueden ajustarse a la convocatoria; IEEE no impone que toda
investigación tenga exactamente estas seis secciones. La justificación del
formato está en [IEEE_FORMAT.md](IEEE_FORMAT.md).

## Reglas de mantenimiento

- No convertir decisiones de planificación en resultados ni conclusiones.
- Mantener equivalentes pregunta, alcance, ecuaciones, citas y estado en ES/EN.
- No afirmar prioridad absoluta ni aceleración antes de evaluar.
- Las correcciones de Kuntur viven en `kuntur/docs/CORE_CORRECTIONS.md`:
  habilitan la investigación, pero no prueban el beneficio de XQDot4Z.
- No fijar todavía una convocatoria, número final de páginas, autoría,
  afiliación o licencia sin acuerdo.
- La versión extensa anterior está preservada en `docs/archive/paper-v0.1/`.
  `RESEARCH_CHARTER.md` y `EXPERIMENT_PROTOCOL.md` son notas revisables fuera del
  artículo, no una obligación de implementar todas sus alternativas.

## Trazabilidad

La auditoría original se conserva en `audit/results/20260908T070537358477Z/`.
La revisión corregida se identifica mediante `docs/CORE_STATE.json` y los
hashes de su regresión. La referencia numérica se fija en `docs/MODEL_STATE.json`.
La unidad aislada se fija en `docs/RTL_STATE.json`. Las mediciones de aceleración
siguen sin existir; M1/M2/M3a no las sustituyen. La integración inmediata se
fija en `docs/INTEGRATION_STATE.json`. Los conteos de M2/M3a se comprueban
automáticamente contra la evidencia, sin añadir al artículo todo el protocolo.
MUL se fija en `docs/SCALAR_STATE.json`; sus 49 programas también se
comprueban frente al estado indicado en ambos artículos. M3b sigue parcial.
La aritmética B3 se fija en `docs/PACKED_STATE.json`: sus 67 910 vectores se
contrastan con ambos textos. La reconstrucción de matrices es en el host;
no se presenta como kernel ejecutado en Kuntur ni como medición.
La integración B3 se fija aparte en `docs/PACKED_INTEGRATION_STATE.json`:
123 programas y cuatro pares de fixtures con ocho salidas comprobadas en
Kuntur. Se distingue de la reconstrucción anterior en el host y de los
benchmarks aún no implementados. Se permite obtener Sa con pesos iguales a uno.

La revisión 0.9 incorpora especialización estática, factores de zero-point y
amenazas a la validez como subsección, no nota al pie. La distribución y
selección de casos se concretan en `benchmarks/campaign.json`, subordinado al
único protocolo `docs/EXPERIMENT_PROTOCOL.md`. Su checker verifica cobertura
de diseño, no coherencia semántica completa ni preparación para medir.

La revisión 0.10 delimita B1 como contexto y exige congelar su regla y código
antes del piloto. D/B2 y D/B3 siguen siendo las comparaciones de las preguntas.
Se distingue cobertura por semillas de repeticiones estadísticas. La prueba
aritmética B1 en el host se documenta fuera del artículo; no se presenta como
kernel ejecutado en Kuntur ni como resultado de rendimiento.
