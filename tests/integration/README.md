# M3a — interfaz inmediata e integración en Kuntur

Estado: integración experimental verificada, 2026-09-08.
La [especificación ISA v0.1](../../isa/SPEC.md) fija operandos, encoding y límites;
[INTEGRATION_STATE.json](../../docs/INTEGRATION_STATE.json) fija la evidencia.
No es todavía la variante D completa de los experimentos. Esta batería se
ejecuta con `ENABLE_MUL=0` y `ENABLE_XQDOT4=0`; la [batería escalar](../scalar/README.md) verifica
MUL sola y con XQDot4Zi. M3a se repitió sobre el RTL ampliado y se fijó la
evidencia nueva sin borrar las ejecuciones ni las copias de fuentes anteriores.

## Reproducir

Desde la raíz de investigación:

```sh
make core-test         # regresión completa, extensión desactivada por defecto
make integration-test # pruebas específicas, activada y desactivada
make check            # hashes y coherencia; no vuelve a simular
```

Requiere Python 3 en Linux, Icarus/vvp, Verilator, make/C++ y GNU binutils
`riscv64-linux-gnu-{as,ld,objcopy,nm}`. No se instalan dependencias ni se usa FPGA.
El [runner](../../scripts/verify_integration.py) exige evidencias M1/M2 vigentes.
Una nueva ejecución no reemplaza automáticamente la evidencia seleccionada.

Para ensamblar, añadir `isa/` al include path de GNU as y usar:

```asm
.include "xqdot4zi.inc"
# x1: ocho U4; x2: cuatro S8; z=8; mitad baja de los pesos
xqdot4zi x3, x1, x2, 8, 0
```

Es un macro de una instrucción de 32 bits, no un nuevo mnemónico integrado
en GCC/binutils. No permite pasar un GPR como z. Para compilar el core con
`ENABLE_XQDOT4Z=1` se debe incluir `rtl/xqdot4z.v` de la raíz junto al RTL
de `kuntur/rtl/`. El runner lo hace explícitamente; con 0 no se instancia
esa unidad ni se requiere añadirla a los comandos históricos del clon.

## Qué se comprobó

| Grupo | Alcance |
|---|---|
| Codificación GNU frente a Python | 1024 palabras: 32 combinaciones z/h × 32 distribuciones de GPR |
| Decodificador Python | 1024 combinaciones de funct7/funct3, legales y reservadas |
| Política RTL activada/desactivada | 32 768 estímulos: 1024 combinaciones × 32 distribuciones de GPR |
| Validación del software | 9 rechazos del encoder y 4 errores de inmediato del macro GNU |
| Pipeline | 25 programas, cada uno en Icarus y Verilator |
| Campaña numérica integrada | 32 casos z/h + 512 entradas aleatorias en ambas mitades = 1056 operaciones |
| Controles de sensibilidad | Dos mutaciones detectadas por comparación de retiro/writeback en Icarus |

La semilla de M3a es 20260910. Hay operaciones adicionales en los programas
dirigidos; 1056 es la cuenta de la campaña numérica, no la suma de toda la batería.
No se afirma exhaustividad de todos los registros/operandos ni del espacio de 32
bits de instrucciones. Las 32 distribuciones no son las 32³ ternas de registros.

[oracle.py](oracle.py) interpreta los bytes ensamblados de un subconjunto
explícito: LUI, ADDI, ADD/SUB, LW/SW, cuatro branches, JAL/JALR, EBREAK,
C.NOP/C.ADDI/C.LI y XQDot4Zi. También ofrece MUL mediante `mul_enabled`,
apagada por defecto y usada por la batería escalar. XQDot4 se modela con
`packed_enabled=False` por defecto para la [batería B3](../packed_integration/README.md).
Rechaza instrucciones
de prueba no modeladas.
No usa el encoder para reconocer la instrucción: verifica los campos por
separado. La aritmética XQDot4Z usa la referencia congelada de M1.
No es un simulador ISA completo ni una comparación con Spike/Sail.

Cada programa inicializa sus GPR mediante 31 ADDI reales; sus retiros también
se comprueban. La RAM de datos se inicializa a cero explícitamente en el banco,
no por reset del hardware. La IMEM del banco tiene 32 KiB, con 256 B de DMEM:
son parámetros de prueba y no cambian los tamaños predeterminados del core.

Se comparan, en orden, PC de cada retiro, destino y dato de writeback,
stores y valores, causa/PC de parada y los 31 GPR finales. También se comparan
los operandos y metadatos efectivos de cada ejecución XQDot4Zi. Un store,
retiro o escritura extra es un fallo, aunque coincida la firma final de memoria.
La cuenta de stalls load-use se exige por programa.

Los casos dirigidos incluyen:

- Forwarding M y W para ambos operandos y lectura normal del banco.
- QDot→QDot, QDot→ADD/SW/branch/JALR; load→pesos, activaciones o ambas fuentes.
- rd=rs1, rd=rs2, fuentes iguales, lecturas de x0 y descarte del destino x0.
- Saltos tomados/no tomados, instrucciones custom legales e ilegales descartadas.
- Instrucción de 32 bits en dirección PC mod 4 = 2, mezclada con C.
- Drenaje de una operación anterior a un fallo; rechazo si está desactivada
  y de cinco bits reservados representativos en el pipeline.
- Reset asíncrono cuando la operación entra en E: cancelación de controles,
  ausencia de escritura del resultado y conservación de los GPR ya escritos.

El reset también cancela las dos instrucciones anteriores todavía en M/W;
en ese caso son NOP explícitos. La expectativa excluye esos retiros, tal como
fija el contrato de reset, y reinicia en EBREAK. No se afirma reset de registros
ni precisión arquitectónica de traps a partir de ese control.

Las dos mutaciones temporales evitan el forwarding de pesos o fuerzan h=0.
Ambas compilan y terminan la simulación; el comparador detecta los resultados
incorrectos. No se usan para la implementación válida ni se compilan por glob.

## Evidencia, lint y límites

`results/<fecha-UTC>/` conserva ensamblador, ELF, binario, imagen de memoria,
expectativas, logs, versiones, semilla, hashes y copias exactas de todas las
fuentes verificadas. Los temporales de compilación se eliminan al terminar.
Los programas están hechos para verificar, no para medir aceleración.

La primera ejecución `20260908T181509420002Z` pasó los 25 programas; la
ejecución anteriormente fijada `20260908T181809095468Z` añade la comprobación exhaustiva
de campos del decoder Python y los dos controles de mutación, también aprobados.
La repetición `20260908T223636748518Z` pasó con las mismas fuentes, herramientas,
conteos y controles que la ejecución fijada. Se compararon los hashes de todos
los binarios, imágenes de memoria y expectativas: coinciden. El binario de
la campaña numérica también se comparó byte a byte. Tras incorporar MUL,
la regresión `20260908T230805734088Z` vuelve a pasar con MUL apagada;
esa evidencia se conserva. Tras integrar B3, `20260909T041316148935Z` es
la evidencia actual fijada para M3a, con MUL y B3 apagadas, sobre las nuevas
fuentes compartidas. El encoding y la unidad aritmética D no cambiaron.

El lint del core se ejecuta con la extensión apagada y encendida. Conserva
solo las excepciones heredadas `VARHIDDEN` y `UNUSEDSIGNAL`; no usa `-Wno-fatal`.
Esto se distingue del lint estricto sin excepciones de la unidad M2.
El banco registra eventos funcionales; no se infiere frecuencia del `#5`
usado para generar reloj. No hay síntesis, FPGA, evaluación de ZR, benchmark
pareado ni prueba formal. Los mismos programas y oráculo se usan en ambos
simuladores, por lo que no son verificaciones independientes del contrato.
