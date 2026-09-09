# Auditoría inicial de kirky-arqui

**Documento histórico del estado original.** En la revisión 0.2 se creó el
clon activo, ahora llamado Kuntur (`kuntur/`), y se aplicaron correcciones; consultar
[el registro actual](../kuntur/docs/CORE_CORRECTIONS.md).
Las rutas futuras y tareas pendientes del texto siguiente describen el momento
de la auditoría inicial, no el estado corregido. Su evidencia no se sobrescribe.

Fecha: 2026-09-08. Fuente: commit `d2e62fd127d85ac33fe54c9b98cffa06970b3fd5`.
Alcance: inspección RTL, regresión histórica y sondas dirigidas de módulos.
No es una certificación de conformidad RV32IC ni una verificación formal.

## Decisión: sí usaremos tu procesador

Es una base apropiada para estudiar una extensión escalar: tiene pipeline de
cinco etapas, dos lecturas de registros, forwarding, manejo de load-use y Fetch
de instrucciones de 16/32 bits. Conocer su diseño reduce el costo de integración
y permite explicar cada cambio. No hace falta reemplazarlo por otro core.

Separaremos tres cosas:

1. `baseline/upstream/`: exportación histórica, inmutable por política y comprobada
   mediante `baseline/SHA256SUMS`. Nunca se aplican correcciones aquí.
2. Una futura base experimental normalizada en `rtl/core/`: derivada de esa
   exportación, con correcciones y adaptaciones comunes a todas las variantes.
3. Las variantes de multiplicación y producto punto: cambios experimentales,
   identificables y comparados sobre la misma base normalizada.

El directorio `/home/stiff/kirky-arqui` no fue modificado. La copia incluye los
143 archivos versionados del commit, no el historial Git ni archivos locales
sin versionar. No se creó todavía `rtl/core/` ni una implementación de XQDot4Z.

## Evidencia ejecutada

Comando desde la raíz de investigación: `make audit`.
Evidencia inicial: `audit/results/20260908T070537358477Z/summary.json`.
Entorno: Icarus Verilog 13.0; versiones completas registradas en los logs.

La batería histórica produjo **26 PASS, 0 FAIL**. Son pruebas de programas
concretos, varias basadas en escrituras esperadas a memoria. Su resultado no
cubre automáticamente todas las instrucciones, operandos ni encodings.
El runner histórico filtra advertencias y usa mensajes de texto como oráculo;
por eso se conserva como prueba de humo, no como único criterio de aceptación.

El testbench adicional `audit/tests/tb_observations.sv` produjo:

| Sonda | Entrada | Expansión/valor esperado | Observado | Interpretación |
|---|---|---|---|---|
| Control `c.addi x5,1` | `0285` | `00128293` | `00128293` | Coincide |
| Control instrucción de 32 bits | `00100293` | `00100293` | `00100293` | Coincide |
| `c.li x5,1` | `4285` | `00100293` | `00004285` | No expandida |
| `c.addi4spn x8,sp,4` | `0040` | `00410413` | `00000040` | No expandida |
| `c.addi16sp sp,16` | `6141` | `01010113` | `00010137` | Se expande como LUI |
| `c.ebreak` | `9002` | `00100073` | `000000E7` | Se expande como JALR |
| Load seguido de ADDI sin dependencia | Campos explicados abajo | `StallF=0` | `StallF=1` | Pausa espuria |
| Control load-use real | `rs1D=rdE=5` | `StallF=1` | `StallF=1` | Coincide |

Las expansiones esperadas siguen la [especificación C de RISC-V](https://docs.riscv.org/reference/isa/unpriv/c-st-ext.html).
Las sondas muestran la salida del decompresor; no afirman haber ejecutado esos
cuatro programas completos ni una excepción de breakpoint en el procesador.

La pausa espuria corresponde a `lw x5,...` seguido de `addi x6,x0,5`.
Los bits 24:20 del inmediato contienen 5, pero no son un registro fuente.
La sonda coloca esos campos en `hazardunit`, que no recibe señales `uses_rs1`
ni `uses_rs2`. Se comprueba la salida de control, no un speedup de aplicación.

## Hallazgos y prioridad

Las líneas siguientes pertenecen a la copia histórica, sin cambios.

| ID | Evidencia | Impacto y tratamiento previsto |
|---|---|---|
| A01 | `rtl/decompressor.v:28`, `:35`, `:60`, `:71`; sondas anteriores | C parcial y dos decodificaciones incorrectas. Delimitar el subconjunto; corregir casos usados antes de medir; impedir ejecución silenciosa de instrucciones excluidas. |
| A02 | `rtl/hazardunit.v:13`; sonda `false_rs2_stall` | Pausas por campos que no son fuentes. Añadir clasificación de operandos en la base común antes de comparar ciclos. |
| A03 | `rtl/maindec.v:16`, `rtl/aludec.v:20`, `rtl/controller.v:81` | No hay RV32I completo: el decoder de memoria solo mira opcode; faltan rutas dedicadas para AUIPC, comparaciones unsigned y accesos byte/halfword. Usar ensamblador y lista permitida explícita. |
| A04 | `rtl/aludec.v:21` y su interfaz parcial de funct7 | No hay MUL ni M. El encoding MUL puede seleccionar ADD con este decoder. No ejecutar código compilado con M sin implementar y verificar la operación. |
| A05 | `rtl/imem.v:4`, `rtl/dmem.v:5` | 64 palabras por memoria: 256 B. Parametrizar capacidades iguales para todas las variantes y agregar comprobaciones de rango/alineamiento. |
| A06 | `rtl/imem.v:11`, `rtl/dmem.v:7` | Lectura combinacional, sin handshake. El modelo no demuestra comportamiento de BRAM síncrona; la latencia física es una fase posterior. |
| A07 | `rtl/datapath.v:116`, `rtl/controller.v:57` | ID/EX habilitado permanentemente; no hay protocolo de unidad multiciclo. Añadir validez, retención y transferencia única antes de evaluar variantes iterativas. |
| A08 | `rtl/regfile.v:9`; interfaz de pipeline | Escritura en flanco negativo y ausencia de retiro explícito. Conservar la convención temporal al verificar y diseñar un contador de retiro que incluya stores/branches. |
| A09 | `rtl/maindec.v:24`, `rtl/decompressor.v:71` | Encodings desconocidos no generan una señal explícita de ilegalidad. Incluir rechazo en la plataforma/testbench; las excepciones arquitectónicas completas quedan fuera del mínimo inicial. |
| A10 | Árbol Git exportado | No se encontró archivo LICENSE en la raíz. Antes de publicar la derivación, resolver autorización de coautores del proyecto de curso y licencia. No asignarla unilateralmente. |

A01 y A02 tienen evidencia dinámica dirigida. A03–A10 son observaciones de
estructura o alcance: no deben presentarse como fallos descubiertos por esas
ocho sondas. Es necesario ampliar la auditoría, en particular aritmética con
overflow, saltos, límites de Fetch, reset, ilegalidad y dependencias.

## Política para evitar resultados confundidos

La aceleración principal nunca se calculará comparando una extensión corregida
con un core original que aún introduce pausas espurias. Las correcciones de
funcionalidad, memoria e instrumentación se aplican primero a una base común;
después se congelan y derivan los baselines y la propuesta.

Si se reporta el progreso frente al proyecto de curso, se identifica como
comparación histórica y se separa del efecto atribuible a la extensión.
El objetivo no es completar toda la ISA antes de investigar: es definir y
verificar el subconjunto realmente usado, y detectar cualquier salida de él.

## Reproducibilidad

`scripts/audit_core.py` verifica hashes antes y después, copia la exportación a
un directorio temporal, ejecuta la regresión y las sondas y conserva un nuevo
directorio de evidencia por ejecución. Las diferencias conocidas se registran
como `DIFFERENCE`; no se convierten en PASS de conformidad. El exit code cero
indica que la reproducción terminó y la regresión histórica pasó.

Los logs y JSON ya generados no se editan. Una corrección crea una nueva versión
del core y nuevas evidencias; el manuscrito selecciona la evidencia explícitamente.
