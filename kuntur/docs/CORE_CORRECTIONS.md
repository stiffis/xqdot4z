# Kuntur: correcciones de la base docente — 2026-09-08

## Procedencia y alcance

Este directorio se creó como clon Git independiente de `/home/stiff/kirky-arqui`,
creado con `git clone --no-hardlinks`. Conserva el historial y parte del commit
`d2e62fd127d85ac33fe54c9b98cffa06970b3fd5`. Las correcciones se registraron
en `research/core-corrections`, hasta `b6ddb1072c3639952daee2400901db311d4307f7`.
Desde 2026-09-09, los archivos forman parte del repositorio raíz en `main`;
el [historial anterior se conserva](../../docs/VERSION_CONTROL.md). No se hizo push.
`UPSTREAM.json` identifica el origen; el original y el snapshot histórico
`../baseline/upstream/` no reciben estas modificaciones.

El clon se renombró a **Kuntur**, con carpeta `kuntur/`, a petición del autor.
El cambio de nombre actualiza documentación, artículos, comandos y rutas
de GTKWave; no altera el RTL. Se conserva kirky-arqui como identidad del
proyecto original y no se reescriben logs ni archivos históricos para ocultarlo.
Las rutas absolutas que aparecen en regresiones anteriores corresponden a su
ubicación en el momento de ejecutarlas; una nueva regresión valida la nueva ruta.

Se conserva la microarquitectura docente de cinco etapas, sus memorias de
lectura combinacional y el banco de registros que escribe en flanco negativo.
Esta revisión corrige defectos observados, explicita las instrucciones admitidas
y añade verificación. La fase de correcciones no implementó XQDot4Z.
Después se añadió la integración opcional [M3a](../../isa/SPEC.md), registrada
por separado, y posteriormente [MUL escalar opcional](SCALAR_MUL.md) y
[XQDot4 opcional para B3](PACKED_INTEGRATION.md).
RV32I completo y M/Zmmul completos siguen fuera del soporte actual.

## Cambios, motivo y pruebas

| ID | Cambio y archivos | Justificación y evidencia |
|---|---|---|
| C01 | `rtl/decompressor.v`: C.LI, C.ADDI4SPN, C.ADDI16SP, C.EBREAK | Las dos primeras no se expandían; ADDI16SP se trataba como LUI; EBREAK como JALR. El oráculo GNU compara expansiones y los programas prueban integración. |
| C02 | `rtl/decompressor.v`: salida `illegal`, revisión de reservadas y HINTs | Una codificación comprimida excluida produce NOP interno **más la señal de ilegalidad**, nunca ejecución silenciosa. Se rechazan inmediatos reservados, LWSP/JR con rd=0, espacios RV64/FP y shamt[5] no implementado. Los HINTs estándar se permiten. Prueba: `tb_vectors.sv`. |
| C03 | `rtl/instruction_policy.v`, `controller.v` y `datapath.v`: lista explícita y controles inhibidos | Se comprueban funct3/funct7 completos: MUL ya no puede ejecutarse como ADD, ni LB/SB como LW/SW. Se separa EBREAK. Pruebas: `tb_policy_hazards.sv` y programas de ilegalidad. |
| C04 | `rtl/hazardunit.v` y conexiones: `UsesRs1D/UsesRs2D` y rdE distinto de x0 | Evita la pausa falsa de `lw x5,...; addi x6,x0,5`, sin perder el stall de dependencia real. Prueba unitaria y programa integrado: exactamente un stall load-use real. |
| C05 | `rtl/alu.v`: comparación explícita de operandos signed | La lógica previa de overflow no se activaba para SLT: podía interpretar mal la resta entre signos opuestos. Se corrigen SLT/SLTI y su uso por BLT/BGE. 10 036 pares contra enteros Python; el mismo test reproduce el fallo en la ALU histórica intacta. |
| C06 | `rtl/imem.v`, `rtl/dmem.v` y `top.v`: capacidades parametrizadas, rango y alineamiento | Se comprueba la dirección completa antes de indexar: se evita alias por truncamiento y se bloquean stores inválidos. Fetch cruza palabras cuando hace falta, pero una C final en el medio alto no lee fuera de memoria. Prueba: `tb_memory.sv` y `fetch-boundary`. |
| C07 | `rtl/datapath.v`, `riscvpipe.v` y `top.v`: validez, PC de retiro y parada de diagnóstico | Una instrucción excluida, EBREAK o fallo de Fetch alcanza E antes de detener el flujo. Un salto tomado descarta la ilegalidad especulativa de D. Se eliminan instrucciones jóvenes y se permite drenar las mayores; la instrucción que falla no se retira. Prueba: secuencias exactas de PC, stores y fault en cuatro programas. |
| C08 | `rtl/regfile.v`: inhibición de escritura física a x0 | Las lecturas arquitectónicas ya devolvían cero; ahora tampoco se altera la celda interna. Se conserva el flanco negativo y no se añade reset de registros. Prueba: `tb_regfile.sv`. |
| C09 | Validez y estado de fallo con reset asíncrono | Se usa la misma convención del pipeline original. Cada programa comprueba que reset entre flancos borra fallo y validez inmediatamente. |
| C10 | `verification/` y objetivos `verify/lint` del Makefile | Runner reproducible con códigos de salida, aserciones, logs completos, versiones y hashes. No se cambia el runner histórico ni se utiliza su filtrado como evidencia nueva. |

Ejemplo del error signed: `0x00000000 < 0x80000000` debe ser falso porque el
segundo operando representa −2³¹. El log `original-slt.stdout.log` conserva el
primer contraejemplo realmente encontrado; no se usa un fallo esperado como
si fuera una regresión aprobada de la ALU original.

## Subconjunto admitido

La fuente ejecutable de esta política es `rtl/instruction_policy.v`.

- Memoria: LW y SW de palabra alineada.
- Aritmética/lógica: ADD, SUB, SLL, SLT, XOR, SRL, SRA, OR, AND.
- Inmediatos: ADDI, SLLI, SLTI, XORI, SRLI, SRAI, ORI, ANDI.
- Control: BEQ, BNE, BLT, BGE, JAL, JALR; además LUI.
- Compresión: instrucciones enteras C de RV32 que se expanden a esas
  operaciones; C.EBREAK se expande a EBREAK y termina por diagnóstico.
- Opciones, apagadas por defecto: XQDot4Zi (`ENABLE_XQDOT4Z=1`), MUL
  escalar (`ENABLE_MUL=1`) y XQDot4 (`ENABLE_XQDOT4=1`), verificadas
  por separado y en convivencia.

No están implementados AUIPC, SLTU/SLTIU, BLTU/BGEU, accesos byte/halfword,
M completo, Zmmul completo, atomics, coma flotante, vector, CSR, ECALL, FENCE
ni arquitectura privilegiada. La única operación M opcional es MUL.
EBREAK no tiene manejador arquitectónico. No debe compilarse C genérico
suponiendo que `-march=rv32ic` certifica este subconjunto: esa opción solo
restringe al ensamblador a una ISA que sigue siendo más amplia que el core.
Los programas de verificación usan instrucciones explícitas y desactivan
relajación/compresión automática cuando necesitan controlar su ancho.

## Interfaces y semántica de diagnóstico

`top` mantiene los puertos antiguos con nombre y añade:

| Interfaz | Significado |
|---|---|
| `IMEM_WORDS`, `DMEM_WORDS` | Palabras de 32 bits; por defecto 64 cada una, es decir, **256 B + 256 B**, no 64 KiB. |
| `IMEM_FILE` | Archivo inicial de instrucciones; por defecto `riscvtest.mem`. |
| `CHECKS=1` | Diagnóstico de simulación en flanco negativo; falla con código no cero ante fallo de instrucción, memoria de datos o dirección de datos activa desconocida. |
| `Fault`, `FaultCause[1:0]`, `FaultPC` | Parada persistente hasta reset; causa local 1: acceso de Fetch, 2: instrucción excluida/ilegal, 3: breakpoint. No son CSR ni interfaz completa de traps. |
| `MemoryFault` | Acceso de datos activo, desalineado o fuera de rango. No se almacena ni se integra como excepción precisa del pipeline. |
| `RetireValid`, `RetirePC` | Instrucción válida en W, incluida store/branch/NOP. Observar una vez por flanco negativo; no es una interfaz RVFI completa. |

La parada de instrucciones bloquea Fetch/Decode y vacía instrucciones jóvenes.
Con `CHECKS=0` los tests pueden observarla y esperar el drenaje de M/W.
Con el valor predeterminado la simulación termina pronto: **no se garantiza
que el testbench alcance a observar ese drenaje después de un fatal**.

Las comprobaciones `$fatal` no forman hardware (`ifndef SYNTHESIS`).
En memoria de datos, un acceso inválido no escribe RAM y una lectura inválida
devuelve cero. **Con CHECKS=0, o en síntesis, no hay trap preciso ni parada por
ese fallo de datos**: no se debe interpretar la continuación como ejecución
arquitectónica correcta. Es una protección del modelo de simulación, no un
subsistema de excepciones listo para FPGA.

Instancias externas de submódulos deben conectar los puertos nuevos:
`decompressor.illegal`, clasificación de fuentes en `hazardunit`,
`controller.SupportedD`, `imem.access_fault`, `dmem.re/access_fault` y señales
de fallo/validez del pipeline. Las instancias posicionales antiguas requieren
adaptación; los 26 testbenches históricos de `top` usan puertos con nombre.

## Evidencia fijada

Regresión actual, tras integrar B3, con `ENABLE_XQDOT4Z=0`, `ENABLE_MUL=0`
y `ENABLE_XQDOT4=0`:
[summary.json](../verification/results/20260909T041314798425Z/summary.json).
La raíz de investigación la fija además en `docs/CORE_STATE.json`; los
hashes deben coincidir con el RTL, los bancos, el runner y los programas actuales.
La revisión anterior queda conservada con sus entradas en
[CORE_PRE_M3.json](../../docs/CORE_PRE_M3.json). Las pruebas con la extensión
activada se fijan por separado en [INTEGRATION_STATE.json](../../docs/INTEGRATION_STATE.json).
La batería nueva con MUL está en [SCALAR_STATE.json](../../docs/SCALAR_STATE.json).
La integración B3 está en [PACKED_INTEGRATION_STATE.json](../../docs/PACKED_INTEGRATION_STATE.json).

| Grupo | Resultado |
|---|---|
| Programas históricos | 26/26 PASS, sin ocultar stderr |
| Expansión C | 28 461 pares independientes ensamblados por GNU + 22 controles = 28 483 vectores |
| Comparación signed | 36 casos de borde + 10 000 pseudoaleatorios, semilla 20260908 |
| Reproducción de SLT histórico | Fallo esperado reproducido; ALU original sin cambios |
| Política y hazards | 21 casos dirigidos |
| Memoria y registros | Límites/alineamiento, accesos inválidos, x0 y flanco de escritura |
| Pipeline integrado | 21 retiros, 6 stores, 1 stall; breakpoint en PC 82 |
| MUL excluido / C ilegal | 3 / 1 retiros; cero stores jóvenes, destino conservado |
| Borde de Fetch | Retiros en PC 0, 4 y 6; fallo de acceso en PC 8 |
| Verilator | PASS con las exclusiones limitadas descritas en `verification/README.md` |

Las ejecuciones anteriores, incluso la que falló por un parámetro de simulación
no usado en lint de síntesis, se conservan como historial; no sustituyen esta
evidencia fijada. Los logs de `readmemh` pueden advertir que un programa corto
no llena toda la RAM: no se ocultan ni se presentan como memoria inicializada.

## Límites y trabajo posterior

Estos tests no recorren las 65 536 codificaciones C ni constituyen prueba formal,
verificación diferencial de todo el procesador o certificación ISA. El oráculo
GNU cubre codificación/expansión; los programas integrados cubren casos
dirigidos de ejecución. No se midieron cobertura funcional exhaustiva ni síntesis.

Permanecen pendientes: memoria síncrona/handshake, stall de Execute y unidad
multiciclo, trazas arquitectónicas completas, contadores de benchmarks,
variantes de comparación y suministro dinámico de z. La interfaz inmediata
ya se implementó; no es todavía la variante D completa del protocolo.
El banco y las RAM no se inicializan a cero por reset; el programa debe
inicializar lo que lee. Para FPGA habrá que diseñar y verificar reset,
memorias y tratamiento de errores en hardware.

No se añadió licencia ni se asignó autoría. Los permisos de publicación del
proyecto docente deben resolverse con sus participantes.

Referencia normativa de las correcciones C:
[RISC-V, extensión C v2.0, edición 20260120](https://docs.riscv.org/reference/isa/v20260120/unpriv/c-st-ext.html).
