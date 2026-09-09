# XQDot4: integración del comparador B3 en Kuntur

M3b parcial, 2026-09-09 UTC. Esta etapa integra la unidad empacada sin
corrección; no añade otro procesador ni modifica la aritmética congelada.
El [contrato ISA](../../isa/packed/SPEC.md), la
[batería reproducible](../../tests/packed_integration/README.md) y la
[evidencia fijada](../../docs/PACKED_INTEGRATION_STATE.json) se mantienen
en la raíz de investigación.

## Cambios respecto de la base común con MUL

| Archivo | Cambio y motivo |
|---|---|
| `rtl/top.v`, `rtl/riscvpipe.v` | Propagan `ENABLE_XQDOT4=0`, independiente de las otras dos opciones |
| `rtl/instruction_policy.v` | Admite custom-1 solo habilitada, con funct3=0 y bits 31:28/26:25=0; declara ambas fuentes usadas |
| `rtl/maindec.v` | Configura escritura del resultado custom-1 por el camino normal, sujeta a la política anterior |
| `rtl/datapath.v` | Transporta operación/h en dos bits D→E con flush/reset, instancia XQDot4 sobre operandos reenviados y selecciona su resultado hacia M/W |
| `../../isa/packed/` | Contrato v0.1, encoder/decoder y macro GNU de una instrucción de 32 bits |
| `../../tests/integration/` | El banco compartido observa PEXEC y cancelación de B3; el intérprete acotado admite XQDot4 opcional y SUB |
| `../../scripts/verify_integration.py` | El sitio de mutación de forwarding se identifica por la instancia XQDot4Z; evita confundirla con los puertos homónimos de B3 |
| `../../tests/packed_integration/` | Política de ocho configuraciones y programas dirigidos, numéricos y de corrección en CPU |
| `../../scripts/verify_packed_integration.py` | Ensamblado, dos simuladores, lint, oráculo, mutaciones y archivo de evidencia |

Las fuentes de entrada son `SrcAE` y `WriteDataE`, después del forwarding
normal. No se lee un tercer GPR. El resultado usa E→M→W, incluido el
forwarding posterior a otras instrucciones. El mux de resultados no sustituye
la ALU usada para branches o JALR. No se añade espera dedicada en E.

La política rechaza XQDot4 apagada y reservadas antes de habilitar escritura.
Los saltos descartan operaciones jóvenes; el diagnóstico permite drenar
operaciones anteriores con CHECKS=0. Reset cancela los metadatos, sin borrar
GPR/RAM. Se conserva la semántica de diagnóstico, no traps arquitectónicos.

## Lo que se conserva

No cambian M1, la unidad fusionada M2, la unidad B3 aislada ni su banco,
el encoding XQDot4Zi, el multiplicador, la ALU, el banco de registros,
las memorias o la unidad de hazards. El original y los snapshots históricos
permanecen intactos. Las tres opciones tienen valor por defecto cero.
Con B3 habilitada, el build añade `rtl/packed/xqdot4.v` desde la raíz;
con D habilitada, añade también `rtl/xqdot4z.v`.

La regresión base, los 25 programas M3a y la batería MUL de 49 programas
se repitieron sobre las nuevas fuentes compartidas, con B3 deshabilitada.
Sus estados JSON apuntan a evidencia nueva; los logs y las copias anteriores
no se reescriben. La batería MUL y la nueva batería B3 se ejecutan dos veces
y se comprueban las entradas y resultados reproducibles.

## Corrección real en CPU, todavía sin benchmark

Cuatro fixtures N=2, K=G=8 tienen versiones B3=(MUL,D,B3)=(1,0,1) y
D=(1,1,0). Comparten tensores, z conocidos al generar código y stores finales.
B3 calcula Sa con dos XQDot4 de pesos iguales a uno; conserva la suma para
ambas filas y ejecuta `P - z*Sa` mediante ADD/MUL/SUB. D acumula sus cuatro
subtotales ya corregidos. Las ocho salidas deben coincidir con los tensores.

El código inicializa datos y registros explícitamente, y no está optimizado.
Sus cuentas de operaciones/stalls son controles de corrección, no speedups.
Faltan kernels comparables, frontera de medición y decisiones sobre metadatos.
No se ha realizado síntesis ni se ha demostrado frecuencia, energía o recursos.
