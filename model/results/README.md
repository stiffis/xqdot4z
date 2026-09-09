# Evidencia de la referencia numérica

Cada ejecución de `make model-test` crea un directorio UTC independiente:

- `summary.json`: estado, versión de contrato, versiones de entorno, semillas,
  conteos completados y hashes de fuentes y artefactos.
- `unittest.log`: resultados completos de los tests.
- `vectors.txt`: muestra reproducible de 2068 vectores para un testbench futuro.
- `vectors.jsonl`: los mismos vectores con nombres y resultados con signo.

La muestra contiene cuatro ejemplos, 16 marcadores de posición/signo y
2048 operaciones aleatorias (1024 pares W/A, cada uno probado con ambos h).
**No contiene las 524 288 inserciones de la batería exhaustiva**; estas se
regeneran y comprueban al ejecutar los tests.

## Formato para RTL

Cada línea de `vectors.txt` tiene cinco columnas hexadecimales, sin prefijo 0x
ni cabecera, compatibles con una lectura `%h %h %h %h %h`:

```text
weights_word  activations_word  zero_point  half  expected_u32
00004a95      0102fd04          8           0     fffffff1
```

La primera línea anterior explica las columnas; **no aparece en el archivo**.
W/A/result tienen ocho dígitos, z y h uno. El resultado negativo se representa
en complemento a dos; JSONL incluye además `expected_signed` en decimal.

La versión de contrato se registra en summary.json. Los vectores son datos,
no instrucciones ISA. Un testbench RTL deberá registrar su propio resultado:
compararlo con estos valores no convierte retroactivamente esta ejecución
Python en una verificación de hardware.

Los archivos de cada ejecución se conservan sin editar. La evidencia vigente
se fija en [MODEL_STATE.json](../../docs/MODEL_STATE.json). Un cambio de semántica
requiere nueva versión de contrato y nueva ejecución; un cambio de tests o
documentación normativa también exige volver a verificar los hashes.
