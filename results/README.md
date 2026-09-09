# Resultados experimentales

Todavía no hay resultados de rendimiento de XQDot4Z. `schema.json` define el
formato inicial para registrarlos; no contiene mediciones ni valores de ejemplo.
La auditoría del procesador se conserva por separado en `../audit/results/`.
Las pruebas de la referencia numérica están en `../model/results/`. Son
comprobaciones de corrección del software de referencia, no mediciones de
ciclos, recursos, energía ni ejecución de una red neuronal.

La comprobación de la unidad aritmética RTL se conserva en `../rtl/results/`
y se fija en `../docs/RTL_STATE.json`. Sus comparaciones funcionales y tiempos
de ejecución del banco tampoco son mediciones de rendimiento del procesador.

La integración inmediata (M3a) se conserva en `../tests/integration/results/`
y se fija en `../docs/INTEGRATION_STATE.json`. Los programas de comprobación
no sustituyen los comparadores y kernels pendientes del protocolo experimental.

La base MUL (M3b parcial) se conserva en `../tests/scalar/results/` y se fija
en `../docs/SCALAR_STATE.json`. Sus pruebas tampoco constituyen mediciones
de aceleración ni completan B3 o los kernels de comparación.

La unidad B3 aislada se conserva en `../tests/packed/results/` y se fija
en `../docs/PACKED_STATE.json`. Sus reconstrucciones matriz–vector en el
verificador no cambian el estado de esta carpeta: aún no hay mediciones.
