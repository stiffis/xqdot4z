# MUL escalar común — contrato de implementación v0.1

Alcance M3b parcial: una instrucción estándar, no una extensión nueva.
`ENABLE_MUL=0` por defecto; independiente de `ENABLE_XQDOT4Z`.

## Semántica y encoding

`mul rd, rs1, rs2`: `x[rd] = (x[rs1] * x[rs2]) mod 2^32`.
Operandos y destino son GPR de 32 bits; `x0` sigue siendo cero. Se lee el
valor previo de las fuentes cuando el destino coincide con ellas. No hay
acumulación, saturación, flags, excepción por overflow ni estado adicional.
Las interpretaciones signed y unsigned dan los mismos 32 bits bajos.

Encoding estándar: opcode `0110011`, funct7 `0000001`, funct3 `000`.
Los tres campos se verifican completos. Apagada, MUL provoca el diagnóstico
de instrucción no soportada; no debe ejecutarse como ADD. Los otros siete
funct3 con funct7=1 siguen rechazados, incluso con MUL activada.

Referencia normativa: [RISC-V ISA v20260120, M 2.0, operaciones de
multiplicación y Zmmul](https://docs.riscv.org/reference/isa/v20260120/unpriv/m-st-ext.html),
consultada el 2026-09-08. **No se implementa M completo ni Zmmul**:
faltan, entre otras, MULH, MULHU y MULHSU. Usar `-march=rv32imc` únicamente
para ensamblar fixtures controlados no certifica ese conjunto en Kuntur.

## Microarquitectura y comparación futura

`scalar_mul.v` es combinacional; se conecta a ambas fuentes después del
forwarding. El bit de selección viaja D→E y se borra con flush/reset. El
resultado sigue E→M→W y las rutas de forwarding existentes. Se conserva el
stall de load-use; no se incorpora una espera específica de MUL.

Esta elección define un prototipo funcional, no una frecuencia alcanzable.
Una implementación iterativa o un registro adicional cambiarían el protocolo
y exigirían revalidación común antes de comparar resultados. B2, B3 y D
deberán usar exactamente esta misma configuración de MUL (o su sustitución
común); B1 permanecerá sin hardware de multiplicación.

Las memorias y el banco de registros no cambian. Los bancos de prueba usan
32 KiB de instrucciones y 256 B de datos, iguales para las cuatro
combinaciones de parámetros; no son las capacidades finales de benchmarks.
El circuito admite las configuraciones (MUL, XQDot4Zi)=(0,0),(0,1),(1,0),(1,1).
La configuración (1,1) comprueba convivencia, no certifica la variante D
completa: B3, los kernels, las fronteras de medida y ZR siguen pendientes.
