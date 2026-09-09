# XQDot4Zi — interfaz ISA experimental v0.1 (M3a)

Fecha: 2026-09-08. Esta es una instrucción **privada y no estandarizada**.
XQDot4Z sigue siendo el nombre de la operación; `xqdot4zi` identifica su primera
interfaz con punto cero inmediato. No se cambia el [contrato numérico v0.1](../model/SPEC.md).

## Decisión y alternativas

Se implementa primero una interfaz sin estado arquitectónico adicional:
dos registros fuente y metadatos inmediatos. Los regímenes ZC (constante) y ZS
(conocido al generar código) del protocolo pueden expresarse directamente.
ZR (leído en ejecución) **no queda resuelto**: un registro no puede sustituir
al inmediato. Despachar entre especializaciones requeriría cargar z, comprobarlo,
saltar y contar código/ciclos. No se implementa ni se considera gratis aquí.

Alternativas consideradas, no implementadas en esta revisión:

| Transporte de z | Consecuencia |
|---|---|
| Inmediato de cuatro bits, elegido | Dos lecturas GPR, sin estado adicional; exige especialización para z variable |
| Tercer registro fuente | z dinámico explícito, pero otro puerto y rutas de forwarding/hazards |
| Registro de configuración | Otra instrucción, dependencias de estado, reset/flush y futuras reglas de contexto |
| Empacar z dentro de W | Cambiaría el contrato que conserva ocho pesos U4; no es compatible sin otra interfaz |

Esta elección acota la primera integración, no demuestra cuál alternativa
será mejor ni cierra la pregunta sobre metadatos dinámicos.

## Operandos y efectos

Sintaxis del macro GNU: `xqdot4zi rd, rs1, rs2, z, h`.

```text
W = X[rs1]                    # ocho pesos U4
A = X[rs2]                    # cuatro activaciones S8
d = sum(i=0..3) (U4(W, i+4*h)-z) * S8(A, i)
X[rd] = sign_extend_32(d)      # salvo rd=x0
PC = PC + 4
```

z pertenece a [0,15], h a {0,1}. No hay acumulación con rd anterior, memoria,
CSR, escalas, saturación, flags ni excepción aritmética. Ambos operandos se
leen con los valores anteriores a la escritura; rd puede coincidir con cualquier
fuente. x0 se lee como cero y descarta escrituras, pero la instrucción se retira.
h solo cambia la mitad de W, nunca el orden de las activaciones.

## Encoding de 32 bits

| Bits | Campo | Valor |
|---|---|---|
| 31:28 | z | U4 inmediato |
| 27 | h | 0 baja, 1 alta |
| 26:25 | reservados en este prototipo | 00 obligatorio |
| 24:20 | rs2 | GPR de activaciones |
| 19:15 | rs1 | GPR de pesos |
| 14:12 | funct3 | 000 obligatorio |
| 11:7 | rd | GPR destino |
| 6:0 | opcode | 0001011, custom-0, 0x0b |

Reconocimiento: `(instr & 0x0600707f) == 0x0000000b`.
Hay 32 combinaciones z/h; los demás patrones funct7/funct3 de custom-0 se
rechazan. No se reutilizan encodings estándar reservados. El espacio custom-0
está destinado a extensiones propias en el [mapa oficial RISC-V 20260120](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv-32-64g.html).
Eso no garantiza compatibilidad con otras extensiones privadas de terceros.

El campo funct7 se construye como `(z << 3) | (h << 2)`. El
[macro](xqdot4zi.inc) usa el formato R de [GNU as .insn](https://sourceware.org/binutils/docs/as/RISC_002dV_002dFormats.html),
sin parchear el ensamblador ni anunciar soporte nativo de un compilador.
[xqdot4zi.py](xqdot4zi.py) permite codificar y decodificar con validación de rangos.
Las fuentes oficiales se consultaron el 2026-09-08; la asignación de campos z/h
y la semántica aquí descritas son decisiones de este proyecto.

## Integración temporal y configuración

`ENABLE_XQDOT4Z=0` es el valor por defecto en Kuntur. Con 1 se instancia la
unidad aritmética M2 original; no hay una segunda copia de ese RTL.
La política ISA controla legalidad y uso de ambas fuentes. Se conserva el
camino de resultado normal E→M→W y sus rutas de forwarding.

El selector, z y el bit de operación viajan en un registro D/E de seis bits,
con el mismo reset y flush que la instrucción. La aritmética usa operandos
ya reenviados y se evalúa combinacionalmente en E; no agrega una espera propia.
Un load inmediatamente anterior que produzca rs1 o rs2 debe causar el stall
normal de load-use. Un salto que descarte esta instrucción en D/F impide que
produzca efectos; no hay un registro z de configuración que deba deshacerse.

Esta microarquitectura ocupa una etapa E en el modelo funcional: **no establece
que el circuito cierre timing al reloj del core original**. Puede cambiar
la ruta crítica. No se ha sintetizado, medido frecuencia ni añadido un protocolo
multiciclo; una revisión temporal deberá verificarse y compararse por separado.

Si la extensión está desactivada o el encoding no es válido, Kuntur utiliza
su diagnóstico existente de instrucción no soportada (causa 2 en E), sin
retiro ni escritura de la instrucción. Las instrucciones anteriores pueden
drenar. No es una implementación de traps precisos, CSR o modo privilegiado.
El reset asíncrono vacía el pipeline; como antes, no borra los GPR ni memorias.

## Frontera de M3a

La verificación debe comprobar encoding contra GNU, rechazo de patrones,
operandos/resultados/PC de retiro, escrituras y memoria, dependencias,
mezcla con C, saltos, reset y configuración desactivada.
El oráculo de programas es deliberadamente pequeño, no Spike, Sail ni una
certificación RV32IC. M1/M2 se conservan sin modificaciones.

El conjunto de comparadores B1/B2/B3/D, MUL, la decisión final sobre ZR,
benchmarks de rendimiento y FPGA quedan fuera de este hito. Esta integración
no es todavía la variante D completa del protocolo experimental.
