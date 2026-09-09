# Verificación de Kuntur

Desde este clon:

```sh
make verify
make lint
```

Desde la raíz de investigación: `make core-test`. Requisitos: Python 3,
Icarus Verilog/vvp, Verilator y binutils con prefijo `riscv64-linux-gnu-`
(as, ld, objcopy y nm). No se descarga ni instala nada.

`run.py` usa un directorio temporal para ensamblados, imágenes de memoria y
simulaciones. No escribe en el original ni en el snapshot. Cada ejecución
crea `results/<fecha-UTC>/`, con stdout/stderr por comando, versiones,
`summary.json` y SHA-256 de las entradas. Devuelve error si falla un comando,
una aserción, una secuencia esperada o el lint. No usar `make test` como
sustituto: se conserva por compatibilidad con el runner del curso.

## Qué comprueba

Esta regresión usa `ENABLE_XQDOT4Z=0`, `ENABLE_MUL=0` y `ENABLE_XQDOT4=0`,
sus valores por defecto, y no instancia las unidades externas.
La configuración XQDot4Zi activada tiene una [batería separada](../../tests/integration/README.md)
desde la raíz de investigación: `make integration-test`.
`make scalar-test` en esa misma raíz comprueba MUL y su convivencia con
XQDot4Zi; la regresión base conserva el caso de MUL excluida.
`make packed-integration-test` comprueba XQDot4 y las ocho combinaciones de
las tres opciones, con [evidencia propia](../../tests/packed_integration/README.md).

1. Los 26 programas originales, ejecutados de nuevo con logs sin filtrar.
2. Pares `.option rvc` / `.option norvc` ensamblados y enlazados sin
   relajación: cada par debe ocupar 2 + 4 bytes. La expansión RTL se compara
   con la instrucción de 32 bits codificada independientemente por GNU.
   Se recorren registros, inmediatos, desplazamientos, saltos y operaciones
   enteras C; se agregan controles de reservadas, HINTs y passthrough.
3. SLT frente a enteros signed de Python: bordes y aleatoriedad determinista.
   Si está disponible `../baseline/upstream/rtl/alu.v` desde la raíz del clon,
   se reproduce también el defecto original y se exige que falle ese test.
4. Política de instrucciones, usos de fuentes, hazards, memoria y banco de registros.
5. Cuatro programas con secuencia exacta de retiros, stores, pausas y diagnóstico.
   Se comprueba descarte de instrucciones ilegales/EBREAK tras saltos,
   conservación del destino y ausencia de stores posteriores a una ilegalidad.
   También se comprueba reset asíncrono del estado nuevo.
6. Lint de todo el RTL con Verilator. `-DSYNTHESIS` excluye los diagnósticos
   solo de simulación. Se exceptúan `VARHIDDEN` (nombre heredado rf de instancia
   y array) y `UNUSEDSIGNAL` (campos/controles heredados y bits constantes).
   El resto de advertencias conserva su efecto de error; no se usa `-Wno-fatal`.
   `CHECKS` participa en un generate, sin silenciar `UNUSEDPARAM` globalmente.

El PASS no certifica RV32IC completo. Los conteos describen vectores/casos,
no modelos de IA, resultados de rendimiento ni cobertura exhaustiva.
Para cambios posteriores hay que volver a ejecutar y revisar la evidencia;
un JSON viejo no demuestra el estado nuevo.

[Registro detallado de correcciones](../docs/CORE_CORRECTIONS.md).
