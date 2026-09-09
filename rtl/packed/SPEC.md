# Producto punto sin corrección — contrato B3 aritmético v0.1

Fecha: 2026-09-08. Estado de alcance: unidad aislada candidata para B3;
no es todavía una instrucción integrada ni un comparador de rendimiento.
El módulo se llama `xqdot4`. No se asigna encoding ISA en este paso.

## Operación y representación

`P = sum(i=0..3) U4(W, i+4*h) * S8(A, i)`.

Se conservan exactamente el packing y el selector del
[contrato XQDot4Z v0.1](../../model/SPEC.md): W tiene ocho pesos U4,
A cuatro activaciones S8 y h selecciona cuatro pesos bajos o altos, sin
cambiar A. La posición cero está en los bits menos significativos.
Los pesos no se reinterpretan como S4. No se resta zero-point en la unidad.

La salida es el patrón de 32 bits del subtotal entero exacto, sin acumulación
implícita ni saturación. Cada producto pertenece a [−1920,1905]; por tanto
P pertenece a **[−7680,7620]**, no al intervalo simétrico de XQDot4Z.
Ambos extremos se alcanzan con pesos 15 y activaciones −128 o 127.

No hay zero-point, CSR, memoria, reloj, reset ni estado interno como puertos.
La unidad es combinacional. No completa M3b ni define ciclos del procesador.

## Relación con D y corrección separada

Para los mismos W, A y h:

`P = XQDot4Z(W,A,0,h)`.

Para cualquier z en [0,15], `d = P - z*Sa`, con `Sa = sum(S8(A,i))`.
Sa pertenece a [−512,508] en un bloque de cuatro activaciones. La resta y
el producto por z están **fuera** de `xqdot4.v`; en B3 integrado se ejecutarán
como instrucciones y deberán contarse. No basta con comparar P contra d.

Para grupos de G activaciones, se acumulan los P de cada bloque; Sa se calcula
una vez por vector/grupo y se reutiliza entre las filas que usan esas mismas
activaciones. Los pesos y z sí pueden cambiar por fila/grupo. Reutilizar Sa
entre grupos distintos, o ignorar un cambio del vector A, sería incorrecto.
No se mezclan grupos con escalas distintas en una salida sin escalado definido.

## Estructura y comparación futura

Cuatro vías y árbol de sumas con extensión de signo, como D. Se usa la misma
convención conservadora S5×S8 → S13 → S14 → S15 → INT32: el quinto bit del
peso es siempre cero, y no existe el restador de z. El resultado también
cabría en anchos más estrechos, pero esta convención mantiene explícita la
relación estructural inicial; síntesis podrá propagar constantes y simplificar.
**No se presupone igualdad de área ni de ruta crítica** por compartir anchos.

La primera integración deberá compartir con D el protocolo temporal, dos
fuentes GPR, selector h y camino de forwarding. B3 y D usarán la misma MUL
escalar y las mismas memorias. Esas condiciones no se consideran implementadas
por verificar esta unidad aislada. El encoding, integración, kernels y
frontera de medida se resolverán antes de comparar ciclos.

La batería confronta esta unidad con una referencia de extracción por
bytes/nibbles y con la unidad D congelada. Las pruebas de matriz–vector
reconstruyen salidas desde respuestas RTL; las acumulaciones, Sa y la
corrección se hacen en el verificador, no en Kuntur. No son benchmarks.
