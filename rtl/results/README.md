# Evidencia de M2

Cada subdirectorio UTC corresponde a `make rtl-test`. `summary.json` registra
éxito o fallo, fuentes, referencia M1, herramientas, semillas, comandos,
conteos y hashes de artefactos. La ejecución seleccionada para el proyecto
se fija deliberadamente en [RTL_STATE.json](../../docs/RTL_STATE.json).
Repetir los tests no cambia automáticamente esa selección.

`vectors.txt.gz` conserva los estímulos y expectativas completos. Gzip usa
mtime cero y no incluye el nombre del archivo; el conjunto es reproducible
con la misma referencia y semilla. Las rutas temporales, timestamps y tiempos
de compilación pueden variar y no son métricas del procesador.

Los `control_*.txt` y `mutant_*.v` contienen errores deliberados. Sus logs de
fallo son controles positivos del detector, no errores del RTL publicado.
Nunca se deben incluir los mutantes en una compilación del diseño.

La ejecución `20260908T174500010623Z` falló en el banco de pruebas: después de
comparar todos los vectores, Icarus devolvió cero al consumir el espacio final
del archivo y el banco lo clasificó como registro malformado. Se corrigió la
detección de EOF, conservando el rechazo de registros parciales y la cuenta
exacta. No se modificó la aritmética para ajustarla al oráculo.

La ejecución `20260908T174612788781Z` pasó todas las comparaciones aritméticas
en ambos simuladores, pero falló el control de clasificación del archivo
truncado: Verilator lo detectó por cuenta incorrecta, no por registro parcial.
Se sustituyó la lectura por tokens por lectura y validación de líneas completas,
y se añadieron controles de registro parcial sobrante y columna adicional.
Así, EOF no puede ocultar un registro incompleto tras la cantidad esperada.

La ejecución `20260908T174825647724Z` expuso otra diferencia del lector:
pedir un sexto campo opcional a `$sscanf` no devolvía la misma cuenta en
Verilator e Icarus al alcanzar el final. La versión final valida los 31 bytes
del formato exportado (anchos, separadores y dígitos) antes de leer exactamente
cinco campos. No depende de solicitar conversiones adicionales hasta EOF.

Las ejecuciones `20260908T175106508019Z` y `20260908T175331000302Z` pasaron
la batería final con las mismas fuentes, referencia, herramientas, conteos y
controles. Sus archivos `vectors.txt.gz` se compararon byte a byte y coinciden:
SHA-256 `ca0b47f041fa31054286fdd850dda316b40a7ff6ae02f1b1a7b7fc1225d299f0`.
La primera está fijada como evidencia M2. Los tres intentos previos fallidos
se conservan para documentar la depuración del banco, no como pruebas aprobadas.

Estos artefactos verifican una unidad aislada. No prueban integración ISA,
síntesis, equivalencia formal, FPGA ni aceleración.
