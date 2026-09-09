# XQDot4Z — contrato numérico v0.1

Estado: contrato de la operación aislada, 2026-09-08.
Referencia ejecutable: [xqdot4z.py](xqdot4z.py).
Este documento fija semántica numérica, no encoding ISA ni microarquitectura.
Una revisión que cambie resultados, packing o entradas requiere nueva versión.

## 1. Operación

Para cuatro pesos enteros sin signo `w_i`, cuatro activaciones enteras con signo
`a_i` y un punto cero compartido `z`:

```text
d = Σ(i=0..3) (w_i - z) * a_i
```

Cada `w_i` y `z` pertenece a [0, 15]; cada `a_i` pertenece a [−128, 127].
El punto cero de las activaciones es cero. El resultado es un **subtotal exacto**,
sin saturación, redondeo, escala, bias ni acumulación con un destino anterior.
Las operaciones se realizan sobre enteros matemáticos; no se permite truncar
la resta a cuatro bits ni reinterpretar primero los pesos como S4.

La forma equivalente, que se usará como control algebraico, es:

```text
P  = Σ(i=0..3) w_i * a_i
Sa = Σ(i=0..3) a_i
d  = P - z * Sa
```

Ambas formas deben producir exactamente el mismo entero. Esta igualdad no
implica igual costo de hardware ni demuestra una ventaja de fusionarlas.

## 2. Entradas y salida de la unidad aislada

| Señal conceptual | Ancho | Interpretación |
|---|---:|---|
| `W` / `weights_word` | 32 bits | Ocho códigos U4, no ocho números S4 |
| `A` / `activations_word` | 32 bits | Cuatro bytes S8 en complemento a dos |
| `z` / `zero_point` | 4 bits | Un U4 común a los cuatro términos seleccionados |
| `h` / `half` | 1 bit | 0: mitad baja de W; 1: mitad alta de W |
| `result` | 32 bits | Complemento a dos del subtotal d, extendido con signo |

Estos son operandos conceptuales de la unidad, **no cuatro registros fuente
de una instrucción ya diseñada**. Cómo suministrar z, dónde codificar h,
el opcode, los registros ISA y el protocolo temporal siguen abiertos.
El nombre lo/hi describe dos selecciones del mismo cálculo, no dos opcodes
ya implementados.

## 3. Packing y correspondencia entre elementos

El índice cero ocupa siempre los bits menos significativos.
Todos los intervalos de bits son inclusivos.

| Término i | Peso si h=0 | Peso si h=1 | Activación, en ambos casos |
|---:|---|---|---|
| 0 | W[3:0] | W[19:16] | A[7:0] |
| 1 | W[7:4] | W[23:20] | A[15:8] |
| 2 | W[11:8] | W[27:24] | A[23:16] |
| 3 | W[15:12] | W[31:28] | A[31:24] |

Formalmente:

```text
w_i = (W >> (4 * (i + 4*h))) & 0xf
b_i = (A >> (8 * i)) & 0xff
a_i = b_i                  si b_i < 128
      b_i - 256            en caso contrario
```

Seleccionar h=1 **solo cambia los pesos**. No selecciona otros bytes de A,
no invierte los elementos ni procesa ocho productos. Para un producto punto
de ocho elementos se necesitan dos llamadas y dos grupos de activaciones;
la suma de sus resultados pertenece al software o a una operación posterior.
Los cuatro nibbles no seleccionados no pueden influir en d.

El packing define posiciones dentro de palabras, independientemente del host.
Para serializar palabras en los futuros programas se usará little-endian:

```text
W = 0x78f04a95  -> bytes en direcciones crecientes: 95 4a f0 78
A = 0x02ff7f80  -> bytes en direcciones crecientes: 80 7f ff 02
```

Una representación hexadecimal escrita de izquierda a derecha no es el orden
de los elementos: los primeros pesos del ejemplo son 5, 9, 10, 4.
Serializar una palabra no equivale a ejecutar una carga de memoria.

## 4. Rangos y anchos

Los siguientes rangos se derivan del dominio legal de entradas:

| Cantidad | Rango | Mínimo de bits con signo suficiente |
|---|---|---:|
| `w_i-z` | [−15, 15] | 5 |
| Un producto `(w_i-z)*a_i` | [−1920, 1920] | 12 |
| Suma de dos productos | [−3840, 3840] | 13 |
| Subtotal de cuatro productos d | [−7680, 7680] | 14 |
| `Sa` | [−512, 508] | 10 |
| `P` y `z*Sa`, individualmente | [−7680, 7620] | 14 |

Justificación: `|w_i-z| ≤ 15` y `|a_i| ≤ 128`, por tanto cada producto tiene
valor absoluto como máximo 1920, y cuatro productos como máximo 7680.
Ambos extremos del subtotal son alcanzables con un z compartido:
pesos 15, activaciones −128, z=0 dan −7680; pesos 0, activaciones −128, z=15
dan +7680. Por eso no basta S13, cuyo máximo es 4095; S14 sí basta.

Un multiplicador genérico S5×S8 puede producir una señal de **13 bits**.
Que 12 bits basten para los productos de este contrato usa el hecho de que
la resta nunca vale −16. No se debe truncar un multiplicador genérico sin
comprobar esa condición y la extensión de signo. Un primer RTL puede conservar
anchos mayores; el contrato no exige una optimización particular.

En la ruta factorizada, tratar P y z*Sa como valores independientes daría una
cota de [−15300, 15300] para la resta; S15 es una elección conservadora para
ese intermedio. La cota final menor depende de que ambos provienen de los
mismos operandos. Python evita overflow intermedio mediante enteros sin ancho fijo.

Con z=8 la diferencia está en [−8, 7] y cabe en S4, pero esa especialización
no reemplaza el dominio general de esta versión.

## 5. Representación de salida y ejemplos verificables

La API separa dos resultados:

- `qdot4z(...)` devuelve d como entero Python con signo.
- `qdot4z_bits(...)` devuelve el patrón de 32 bits como entero no negativo.

Para d negativo, el patrón es `2**32 + d`; para d no negativo, es d.
Esto **no es saturación ni overflow**. La salida de una implementación RTL
deberá tener esos mismos bits. No hay acumulador implícito.

| Caso | W | A | z | h | d | Patrón result |
|---|---|---|---:|---:|---:|---|
| Mitad baja | 00004a95 | 0102fd04 | 8 | 0 | −15 | fffffff1 |
| Mitad alta | 78f04a95 | 02ff7f80 | 8 | 1 | 1911 | 00000777 |
| Extremo negativo | 0000ffff | 80808080 | 0 | 0 | −7680 | ffffe200 |
| Extremo positivo | 00000000 | 80808080 | 15 | 0 | 7680 | 00001e00 |

W, A y result están escritos en hexadecimal; d, z y h están en decimal.
En el primer caso, los pesos centrados son [−3, 1, 2, −4], las activaciones
[4, −3, 2, 1] y los productos [−12, −3, 4, −4]: suman −15.
En el segundo son [−8, 7, 0, −1] y [−128, 127, −1, 2]:
1024 + 889 + 0 − 2 = 1911.

Los casos se mantienen en [qdot4z_examples.json](../tests/data/qdot4z_examples.json)
y se prueban automáticamente. Son ejemplos numéricos, no mediciones de hardware.
Proceden de los ejemplos ya revisados en la guía de IA; la API del proyecto
añade validación estricta y no importa ni modifica el script de esa guía.

## 6. Contrato de la API Python

Todos los escalares deben ser `int` nativos de Python; se rechazan bool,
float y strings con `TypeError`. Un entero fuera de rango produce `ValueError`.
No hay conversión implícita ni enmascarado silencioso de entradas.

- W y A se pasan como patrones U32 de 0 a `0xffffffff`, incluso cuando A
  contiene activaciones negativas. Un argumento A negativo no es un patrón U32 válido.
- `half` debe ser el entero 0 o 1, no un bool; por defecto es 0.
- `pack_weights` exige exactamente ocho U4; `pack_activations`, cuatro S8.
- `dot4` y `dot4_factored` aceptan exactamente cuatro pesos y cuatro activaciones.
- Las secuencias pueden ser listas, tuplas u otros iterables finitos.
- `encode_s32/decode_s32` son utilidades generales S32/U32: validan sus
  rangos completos, aunque el operador solo genera d en [−7680, 7680].

Esta validación detecta errores del software de prueba. No especifica
excepciones ISA, estados X/Z del Verilog ni comportamiento ante fallos físicos.

## 7. Casos de borde y límites

La operación siempre procesa cuatro términos. No hay longitud ni máscara.
Si un kernel tiene una cola más corta, puede rellenar activaciones con cero;
esos términos son neutros aunque sus pesos no sean cero. Alternativamente,
un peso igual a z también aporta cero. El kernel es responsable del relleno
y de no acceder fuera de memoria: la unidad no realiza esas cargas.

No se garantiza que acumular una cantidad arbitraria de subtotales quepa en
INT32. Esa política requiere otro contrato; tampoco se suman grupos con escalas
distintas suponiendo que representan la misma magnitud real.

Fuera de v0.1: entrenamiento, precisión de una red, escalas/epílogos,
encoding y estado ISA, latencia, handshake, reset/flush, integración en Kuntur
y mediciones de aceleración, recursos o energía.

## 8. Puerta de aceptación de M1

Ejecutar `make model-test`. La batería comprueba ejemplos, packing, todas las
65 536 ternas legales de un término en las ocho posiciones físicas de W,
productos punto completos aleatorios, identidades y rechazo de entradas inválidas.
Se conservan logs, semillas, vectores exportados, versión y hashes.

El control factorizado está escrito separadamente de la suma directa.
Además, las pruebas usan `struct`, bytes y construcción hexadecimal para
no depender únicamente del packing del propio modelo. Aun así, no son
implementaciones independientes de dos equipos ni una prueba formal.

M1 valida esta referencia numérica, **no un RTL que todavía no existe**.
No se recorre todo el espacio combinado de W, A, z y h (69 bits de entrada).
Las comprobaciones exhaustivas de un término no deben presentarse como
exhaustividad del producto punto de cuatro términos.
