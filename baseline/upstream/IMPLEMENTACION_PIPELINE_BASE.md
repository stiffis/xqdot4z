# Implementacion del Pipeline Base en `week13`

## Objetivo

Este documento explica, fase por fase, como se construyo el procesador **pipeline base sin hazard handling** en `week13/Src files/Src files/`, que decisiones se tomaron, por que se tomaron, que archivos se modificaron y como se valido cada etapa del desarrollo.

La meta funcional del proyecto fue llegar al conjunto de instrucciones pedido en el curso a partir de una base `single-cycle`, siguiendo la figura 7.51 de **Harris & Harris, RISC-V Edition**.

## Punto de partida

Se partio de dos referencias ya existentes en el repo:

- `week12/Src files/Src files/`: base `single-cycle`
- `week10/Src files/Src files/`: extensiones previas del grupo (`lui`, `xor/xori`, fixes de modulos parametrizados)

### Por que se eligio `week12` como base principal

Se eligio `week12` como base estructural porque:

- era una implementacion `single-cycle` limpia y estable
- separaba bien `controller` y `datapath`
- ya seguia el estilo del curso/profesor
- servia mejor para mapear el cambio de arquitectura hacia pipeline

### Por que no se uso `week10` como base completa

`week10` tenia mejoras utiles, pero no convenia usarlo entero como punto de partida porque:

- mezclaba extensiones funcionales con la base estructural
- `lui` reutilizaba una codificacion de ALU que luego chocaba con shifts
- la prioridad inicial era construir **pipeline base**, no agregar todas las instrucciones a la vez

Por eso la estrategia fue:

- usar `week12` como base estructural
- traer de `week10` solo ideas utiles, cuando hicieran falta

## Fase 1: Crear la arquitectura pipeline base

### Meta de la fase

Convertir el `single-cycle` a un **pipeline de 5 etapas**:

1. IF
2. ID
3. EX
4. MEM
5. WB

sin implementar todavia:

- forwarding
- stalls
- flush
- hazard unit

### Archivos base creados en `week13`

- `top.v`
- `riscvpipe.v`
- `controller.v`
- `datapath.v`
- modulos auxiliares (`alu.v`, `maindec.v`, `aludec.v`, `extend.v`, `flopr.v`, `mux2.v`, `mux3.v`, etc.)

### Decision de arquitectura

Se decidio pipelinear por separado:

- **datos** en `datapath.v`
- **senales de control** en `controller.v`

#### Por que

Porque eso sigue mejor la figura 7.51 del libro:

- el `datapath` mueve y registra valores entre etapas
- el `controller` decodifica en D y arrastra las senales a E/M/W

Si se hubiera dejado el `controller` como uno puramente `single-cycle`, el pipeline iba a quedar menos claro y mas dificil de extender.

### Registros de etapa agregados

En `datapath.v` se agregaron registros entre etapas:

- `IF/ID`
- `ID/EX`
- `EX/MEM`
- `MEM/WB`

#### Que datos se arrastran

- instruccion (`InstrD`)
- `PC`
- `PC+4`
- operandos leidos del `regfile`
- inmediato extendido
- registro destino `rd`
- resultados de ALU
- datos leidos de memoria

#### Por que

Porque en pipeline una instruccion ya no hace todo en un ciclo. Cada etapa necesita guardar lo que produjo para la siguiente etapa.

### Pipeline de control

En `controller.v` se hizo que el control viaje por etapas:

- `ImmSrcD`
- `ALUControlE`
- `ALUSrcE`
- `MemWriteM`
- `ResultSrcW`
- `RegWriteW`

#### Por que

Porque la senal no siempre se usa en el mismo ciclo en que se decodifica.

Ejemplo:

- `MemWrite` se sabe al decodificar
- pero se usa recien en MEM

### Burbujas seguras

En `maindec.v` se cambio el `default` para que produzca una instruccion tipo `nop/bubble` segura en vez de valores `x`.

#### Por que

En pipeline, sobre todo al reset, aparecen registros de etapa con contenido transitorio. Si el decoder devolvia `x`, todo el pipeline quedaba contaminado con valores indeterminados. Con controles en cero, una burbuja no escribe memoria ni registros y se comporta como `nop`.

## Fase 2: Definir un subset minimo de prueba

### Meta de la fase

No probar todo el ISA de golpe. Primero validar que la estructura pipeline base funcionaba.

### Primer subset elegido

- `add`
- `addi`
- `lw`
- `sw`

### Por que se eligio ese subset

Porque cubre las rutas mas importantes del datapath:

- ALU tipo R
- ALU tipo I
- acceso a memoria de lectura
- acceso a memoria de escritura
- writeback

Sin introducir todavia control hazards ni nuevas rutas complejas.

### Como se probaron

Se creo:

- `riscvtest_base.txt`
- `testbench_base.v`

#### Decision importante: usar `NOP`s entre dependencias

Se insertaron `NOP`s entre instrucciones dependientes.

##### Por que

Porque todavia no existia hazard unit ni forwarding. La idea era validar el pipeline base, no mezclar errores de arquitectura con dependencias de datos.

### Resultado

El subset base paso correctamente.

## Fase 3: Extender la ALU basica ya soportada

### Instrucciones agregadas/probadas

- `and`
- `or`
- `andi`
- `ori`
- `slt`
- `slti`

### Por que este fue el siguiente paso

Porque estas instrucciones:

- no cambian el flujo de control
- no necesitan nuevas rutas de `PC`
- reutilizan el mismo datapath base

### Archivos de prueba

- `riscvtest_base.txt`
- `testbench_base.v`

Se fueron ampliando para incluir estos casos.

### Que se valido

- decode de instrucciones R-type e I-type ALU
- generacion correcta de inmediatos I-type
- writeback correcto desde ALU
- comparacion `slt/slti`

## Fase 4: Agregar `xor` y `xori`

### Meta

Traer una extension ya trabajada antes en `week10`.

### Archivos tocados

- `aludec.v`

### Cambio realizado

Se agrego el caso:

```verilog
3'b100 -> XOR/XORI
```

### Por que solo hubo que tocar `aludec.v`

Porque:

- `maindec` ya distinguia R-type vs I-type ALU
- `extend` ya armaba inmediato I-type
- `alu.v` ya tenia implementado `a ^ b`
- el datapath ya tenia la ruta correcta para registro-registro y registro-inmediato

Entonces el unico problema real era que el decoder de ALU no estaba pidiendo la operacion correcta.

### Prueba separada

Se agregaron:

- `riscvtest_xor.txt`
- `testbench_xor.v`

### Resultado

La prueba paso correctamente.

## Fase 5: Agregar `beq` y `jal` como control-flow basico

### Meta

Validar el camino de control del `PC` antes de entrar a la parte mas grande de hazards.

### Por que no se hizo con flush desde el inicio

Porque todavia no se estaba implementando hazard handling. En vez de eso, se usaron programas con `NOP`s protectores para que las instrucciones que ya estaban en el pipeline al resolverse el salto fueran inofensivas.

### Archivos de prueba

- `riscvtest_ctrl.txt`
- `testbench_ctrl.v`

### Que se valido

- `beq` tomado correctamente
- `jal` actualizando el `PC`
- `jal` escribiendo `PC+4` en el registro link

### Decision de prueba

Se usaron instrucciones "daninas" despues del branch/jump para verificar que el flujo correcto no terminara ejecutandolas cuando no correspondia, siempre dentro del supuesto de `NOP`s protectores.

## Fase 6: Implementar `lui`

### Meta

Soportar el inmediato de tipo U usando el datapath ya existente, sin agregar una ruta nueva de writeback.

### Estrategia elegida

Seguir el enfoque de `week10`:

```text
ImmExt -> SrcB -> ALU(pass B) -> ALUResult -> WB
```

### Archivos tocados

- `maindec.v`
- `aludec.v`
- `extend.v`
- `datapath.v`
- `alu.v`

### Que se hizo

#### `maindec.v`

- se agrego el opcode de `lui`
- se uso `ALUOp = 11`
- `ALUSrc = 1`
- `ResultSrc = 00`

#### `aludec.v`

- se agrego una operacion especial de `ALUControl` para `lui`

#### `extend.v`

- se agrego `op` como entrada
- `ImmSrc = 11` se hizo compartido entre `jal` y `lui`
- si `op == lui`, se construye `{instr[31:12], 12'b0}`

#### `datapath.v`

- solo se paso `InstrD[6:0]` a `extend`

#### `alu.v`

- la operacion de `lui` devuelve `b`

### Decision importante

Esta solucion era minimalista y valida, pero temporalmente piso una codificacion que antes estaba asociada a `sll`. Eso nos obligo a replantear despues la codificacion de la ALU.

### Prueba separada

- `riscvtest_lui.txt`
- `testbench_lui.v`

### Resultado

`lui` paso correctamente.

## Fase 7: Redisenar `ALUControl` y agregar la familia de shifts

### Problema previo

Con `ALUControl` de 3 bits ya no habia codigos limpios para:

- `add`
- `sub`
- `and`
- `or`
- `xor`
- `slt`
- `lui`
- `sll`
- `srl`
- `sra`

### Decision

Ampliar `ALUControl` de **3 bits a 4 bits**.

### Por que

Porque era la forma mas limpia de:

- mantener `lui`
- recuperar `sll`
- agregar `srl`
- agregar `sra`

sin seguir reciclando codigos incompatibles.

### Archivos tocados

- `riscvpipe.v`
- `controller.v`
- `datapath.v`
- `aludec.v`
- `alu.v`

### Nueva codificacion

- `0000` -> add
- `0001` -> sub
- `0010` -> and
- `0011` -> or
- `0100` -> xor
- `0101` -> slt
- `0110` -> lui (pass B)
- `0111` -> sll / slli
- `1000` -> srl / srli
- `1001` -> sra / srai

### Instrucciones agregadas

- `sll`
- `slli`
- `srl`
- `srli`
- `sra`
- `srai`

### Como se decodificaron

#### `aludec.v`

- `funct3 = 001` -> `sll/slli`
- `funct3 = 101` y `funct7b5 = 0` -> `srl/srli`
- `funct3 = 101` y `funct7b5 = 1` -> `sra/srai`

### Prueba separada

- `riscvtest_shift.txt`
- `testbench_shift.v`

### Resultado

La familia de shifts paso correctamente.

### Revalidacion

Despues de ampliar `ALUControl` se reejecutaron todos los testbenches previos para comprobar que no hubiera regresiones. Todos siguieron pasando.

## Fase 8: Extender la familia de branches

### Instrucciones agregadas

- `bne`
- `blt`
- `bge`

### Meta

Ampliar la logica de branch en `E` sin redisenar el pipeline.

### Estrategia elegida

- `beq` y `bne` usan **resta** y la señal `ZeroE`
- `blt` y `bge` reutilizan `slt`, usando el bit 0 del resultado de ALU en `E`

### Archivos tocados

- `riscvpipe.v`
- `controller.v`
- `datapath.v`
- `maindec.v` (comentario aclaratorio)
- `aludec.v`

### Cambios clave

#### `controller.v`

- se pipelineo `funct3D` hasta `funct3E`
- se redefinio `PCSrcE` segun la familia exacta de branch:
  - `beq` -> `ZeroE`
  - `bne` -> `~ZeroE`
  - `blt` -> `CondBitE`
  - `bge` -> `~CondBitE`

#### `datapath.v`

- se expuso `CondBitE = ALUResultE[0]`

#### `aludec.v`

- si `ALUOp = 01` y `funct3` es de `blt/bge`, se usa `slt`
- si es `beq/bne`, se usa resta

### Prueba separada

- `riscvtest_branch3.txt`
- `testbench_branch3.v`

### Resultado

La familia de branches restante paso correctamente.

## Fase 9: Implementar `jalr`

### Meta

Soportar el ultimo cambio de control faltante:

```text
rd = PC + 4
PC = (rs1 + imm) & ~1
```

### Dificultad

`jalr` no usa el mismo target que `jal` o los branches.

- `jal` usa `PCE + ImmExtE`
- `jalr` usa `ALUResultE` como target, con el bit 0 forzado a 0

### Estrategia elegida

No se rehizo el mux del `PC`. En vez de eso, se redefinio que significa `PCTargetE`:

- para `jal` y branches: `PCE + ImmExtE`
- para `jalr`: `{ALUResultE[31:1], 1'b0}`

### Archivos tocados

- `maindec.v`
- `controller.v`
- `datapath.v`
- `riscvpipe.v`

### Cambios clave

#### `maindec.v`

- se agrego el opcode de `jalr`
- se agrego un bit de control nuevo: `Jalr`

#### `controller.v`

- se pipelineo `JalrD -> JalrE`
- `PCSrcE` ahora se activa tambien si `JalrE = 1`

#### `datapath.v`

- se calculo `PCBranchTargetE`
- se calculo `PCJalrTargetE`
- `PCTargetE` selecciona entre ambos segun `JalrE`

### Prueba separada

- `riscvtest_jalr.txt`
- `testbench_jalr.v`

### Resultado

`jalr` paso correctamente.

## Estado final del proyecto

### Instrucciones objetivo soportadas

Se implemento y valido todo el conjunto pedido:

- `lw`
- `addi`
- `slli`
- `xori`
- `srli`
- `srai`
- `ori`
- `andi`
- `sw`
- `add`
- `sub`
- `sll`
- `xor`
- `srl`
- `sra`
- `or`
- `and`
- `lui`
- `beq`
- `bne`
- `blt`
- `bge`
- `jalr`
- `jal`

### Extras ya funcionales

Tambien quedaron funcionando:

- `slt`
- `slti`

## Estrategia de validacion usada

En vez de un solo test gigante, se prefirio una bateria de pruebas separadas:

- `testbench_base.v`
- `testbench_ctrl.v`
- `testbench_xor.v`
- `testbench_lui.v`
- `testbench_shift.v`
- `testbench_branch3.v`
- `testbench_jalr.v`

### Por que se hizo asi

Porque aisla errores por familia funcional:

- ALU base
- control flow basico
- XOR/XORI
- LUI
- shifts
- branches adicionales
- JALR

Si un cambio rompia algo, se detectaba rapido y con contexto.

## Decisiones globales del proyecto

### 1. Primero pipeline base, luego ISA, luego hazards

Esta fue una decision central.

#### Por que

Si se intentaba hacer todo al mismo tiempo:

- cambio estructural del pipeline
- nuevas instrucciones
- hazards

iba a ser mucho mas dificil identificar por que fallaba algo.

### 2. Pruebas con `NOP`s entre dependencias

#### Por que

Mientras no existiera hazard handling, necesitabamos evitar que fallaran los tests por razones que todavia no estabamos intentando resolver.

### 3. Reusar el datapath siempre que fuera posible

#### Por que

Sigue el estilo del curso y del libro:

- cambios minimos
- control mas expresivo
- evitar agregar muxes o rutas si no son estrictamente necesarios

### 4. Hacer regresion completa despues de cambios grandes

#### Por que

Fue especialmente importante despues de:

- ampliar `ALUControl` a 4 bits
- cambiar la logica de branch
- agregar `jalr`

## Fase 10: Correccion del register file a write-first (puente hacia hazards)

### Contexto

El banco de registros que se venia usando era el generico del Cap. 5 del libro
(HDL Example 5.8): escritura en `posedge clk` y dos lecturas combinacionales.
Es correcto como componente, pero al meterlo en un pipeline tiene una
consecuencia de timing importante.

### Problema detectado

Cuando una instruccion esta en **WB** (escribiendo el regfile) y otra esta en
**D** (leyendo el mismo registro) en el **mismo ciclo** (dependencia a
distancia 3), la escritura `posedge` con asignacion non-blocking **no es
visible** para la lectura de ese ciclo: la etapa D captura el valor **viejo**.

Esto se verifico empiricamente con un testbench que escribe `x5 = 42` y
simultaneamente lee `a1 = x5` en el mismo flanco:

- regfile `posedge` (Cap. 5): la etapa EX recibe el valor **viejo** (stale).
- regfile write-first: la etapa EX recibe **42** (correcto).

Esa es la razon por la que el pipeline base necesitaba **3 NOPs** (separacion
de 4 instrucciones) y no 2 entre productor y consumidor.

### Decision y respaldo del libro

Se migro el register file a **write-first**, escribiendo en el **flanco de
bajada** (`negedge clk`). Esto es exactamente lo que indica el libro para el
procesador segmentado:

> "The register file in the pipelined processor writes on the falling edge of
> CLK so that it can write a result in the first half of a cycle and read that
> result in the second half of the cycle for use in a subsequent instruction."
> -- Harris & Harris, RISC-V Edition, Seccion 7.5.1

Es decir, el regfile generico del Cap. 5 (`posedge`) y el del pipeline del
Cap. 7 (`negedge`) son distintos a proposito. Se adopto la version del Cap. 7.

### Cambio realizado

#### `regfile.v`

- La escritura paso de `always @(posedge clk)` a `always @(negedge clk)`.
- Las lecturas siguen siendo combinacionales (sin cambios).
- Se agrego comentario citando la Seccion 7.5.1.

### Por que se hizo ahora

Es el puente natural hacia la fase de hazards. Con el regfile write-first:

- el hazard de **distancia 3** (WB->D) lo resuelve el propio banco de registros,
- por lo que el **forwarding** que viene despues solo tendra que cubrir
  **distancia 1 y 2** (logica `ForwardAE`/`ForwardBE` de dos casos del libro).

### Nota relacionada: correccion de Fig. 7.50 ya presente

El libro (Seccion 7.5.1) plantea como error de la Fig. 7.49(b) escribir el
regfile usando `RdD` (señal de Decode) en vez de `RdW` (Writeback). Este
proyecto **ya tenia** el `Rd` correctamente pipelineado
(`RdD -> RdE -> RdM -> RdW`) y el regfile usa `.a3(RdW)`, por lo que no
presenta ese bug.

### Resultado

Se reejecutaron los 7 testbenches (base, ctrl, xor, lui, shift, branch3, jalr).
**Todos siguieron pasando**: la correccion es no-destructiva (los programas con
3 NOPs siguen siendo seguros) y deja el terreno listo para forwarding y stalls.

## Lo que sigue

El objetivo del cuadro de instrucciones ya quedo completado.

El siguiente gran paso natural del proyecto ya no es ISA, sino **hazard handling**:

- forwarding
- stalls
- flush
- control hazards reales sin depender de `NOP`s protectores

## Resumen ejecutivo

El proyecto en `week13` paso por tres grandes etapas:

1. construir el pipeline base a partir de `week12`
2. ampliar el ISA objetivo por familias funcionales
3. validar cada familia con testbenches separados y regresion completa

El resultado final es un **pipeline base funcional**, alineado con la figura 7.51 del libro, que ya soporta todo el conjunto de instrucciones objetivo y esta listo para pasar a la etapa de hazards.
