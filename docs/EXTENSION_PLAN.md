# Plan de extensión a K=128 — versión 0.1

Estado: **plan, no ejecución**. Nada de lo que sigue se ha medido bajo registro.
Este documento existe para que la decisión de extender la rejilla se tome con el
costo a la vista, y para resolver en papel el problema del segundo registro
antes de mover código.

## Por qué

[RQ3](RESEARCH_CHARTER.md) pregunta cómo cambian las comparaciones con N, K, G y
la política de punto cero. La campaña registrada barrió **N** y midió un solo
grupo de 32 elementos: de los tres factores, se contestó uno. El protocolo
define la matriz principal como K en {32,128,512}, así que la rejilla ejecutada
es un subconjunto declarado, no la que el diseño pide.

Hay un segundo motivo, menos obvio. Con G=32, K=32 da **exactamente un grupo**
por fila, y el manifiesto lo dice: `group_stride_exercised_in_initial_grid` es
`false`. El parámetro `group_stride` del perfil ZS se transporta pero nunca
actúa, y `test_group_stride_is_inactive_for_one_group` existe para dejarlo
constando. Con K=128 hay **cuatro grupos** por fila y ese parámetro entra en
juego por primera vez. La extensión no agranda el experimento: estrena una
dimensión del diseño.

## Señal preliminar — no es evidencia

Una sonda fuera del repositorio generó y ejecutó casos con el layout parcheado
a mano para que K=128 quepa. **No cuenta como resultado**: una sola semilla, solo
Icarus, sin comprobar las salidas contra el inventario, y con un layout que no
existe en ninguna política congelada.

Lo que sí hace creíble al arnés es que reproduce la campaña registrada en K=32
ciclo a ciclo: D 43/149/581 y B3 43/217/745 para N=1/4/16, idénticos a la
evidencia firmada en `CAMPAIGN_STATE.json`.

Con esa salvedad, el cociente B3/D bajo punto cero variable por fila:

| N | K=32 | K=128 |
|---|---|---|
| 1 | 1.00 | 1.00 |
| 4 | 1.46 | 1.31 |
| 16 | 1.28 | 1.12 |

La ventaja **se estrecha también al crecer K**. La lectura tentativa es que con
cuatro grupos por fila el producto punto crece cuatro veces mientras la
corrección por grupo cuesta lo mismo, así que la corrección pesa menos en el
total y absorberla rinde menos. Si la campaña lo confirma, H2 tendría un segundo
eje de apoyo y el mapa de condiciones ganaría una frontera que hoy no tiene.

Si no lo confirma, también es resultado. Por eso se mide antes de escribirlo.

## Costo de máquina

Medido sobre una sonda de las doce configuraciones variante × N, y validado
contra la corrida real: el modelo predice 53 min para la campaña K=32 y la
observada fue ~55.

| paso | costo |
|---|---|
| campaña, 4560 casos (K=32 y K=128) | ~2 h 15 |
| verificación de kernels, dos pasadas | ~52 min |
| medición re-fijada, dos pasadas | ~7 min |
| piloto | ~5 min |
| materialización del inventario | ~3 min |
| **total** | **~3 h 20** |

Icarus domina: Verilator resuelve cada caso en centésimas de segundo y el
toolchain en ~20 ms. Los casos K=128 cuestan 1.84× los de K=32 en promedio
ponderado, y B1 se lleva el 79% de los ciclos totales.

K=512 **no** entra en este plan. Con N=16 los pesos solos piden 8192 bytes
contra una memoria de datos de 4096, así que es un cambio de modelo de memoria,
no de layout, y toca D10.

## Qué cambia

Archivos que se tocan:

- `../benchmarks/tensors.py` — bases derivadas de K en vez de constantes, y la
  guarda de activaciones contra pesos que falta ([D44](DECISIONS.md))
- `../benchmarks/campaign.json` — `grid.K`, política v3, 4560 casos planificados
- `../scripts/verify_kernels.py` — hoy fija `K = G = 32` como constante de módulo
- `../tests/benchmarks/test_campaign.py` — fija 2280 casos
- `../tests/benchmarks/test_layout_limits.py` — su prueba del defecto fallará al
  añadirse la guarda, que es exactamente para lo que se escribió
- `../scripts/freeze_policies.py`, `../scripts/check_project.py`, este documento,
  `DECISIONS.md`, los estados y el artículo

Archivos que **no** cambian:

- `../benchmarks/kernels.py` ya genera las cuatro variantes en K=128 sin tocarlo
- `../scripts/check_campaign.py` ya valida contra `PROTOCOL_K = (32, 128, 512)`

## El problema del segundo registro

`design_fingerprint()` cubre `grid` y `optimization`. Cambiar K y versionar la
política mueve los dos, así que `amend()` se niega por construcción: esto es un
**registro nuevo**, no una enmienda. Y ahí está la dificultad real, que no es de
cómputo.

Un registro escrito hoy no puede pretender ser previo a la observación de los
resultados K=32: ya están medidos, publicados en el artículo y leídos. Volver a
correr `record_preregistration.py` sobre el archivo existente destruiría el
único registro que sí fue previo a medir.

La forma honesta es **conservar el registro actual intacto y escribir un segundo
registro** que declare explícitamente qué estaba ya observado cuando se redactó.
Sus hipótesis sobre K sí serían genuinamente previas, porque K no se ha medido
bajo registro; sus afirmaciones sobre N no lo serían, y debe decirlo.

Eso exigía tres cosas del mecanismo. **Las tres están hechas** (2026-09-11):

1. `record_preregistration.py --extend "<razón>"` escribe
   `docs/PREREGISTRATION_<n>.json` sin tocar el registro anterior.
2. Cada eslabón fija los **bytes** del anterior en `extends.sha256`, así que
   reescribir un registro previo rompe el enlace de forma visible. La extensión
   declara en `already_observed` qué campaña y qué piloto ya estaban medidos,
   releídos de su propia evidencia y no reescritos de memoria.
3. `check_project.py` recorre la cadena: comprueba la secuencia, el enlace por
   hash, que la huella de diseño **sí se movió** —si no, es enmienda— y que la
   evidencia declarada como ya observada coincide con su archivo. Solo el último
   registro debe corresponder a los archivos en disco; los anteriores describen
   su propio momento y los sostiene la cadena.

Extensión y enmienda son afirmaciones opuestas sobre el mismo hecho: una dice
que el diseño se movió, la otra que no. Cada camino rechaza el caso del otro, y
`tests/benchmarks/test_registration_chain.py` lo comprueba con ocho pruebas. Dos
mutaciones inyectadas al mecanismo las hacen fallar, que es la única forma de
saber que pueden.

## Orden propuesto

1. ~~Extender el mecanismo de registro y comprobarlo.~~ **Hecho.**
2. Versionar la política a v3 con su razón, arreglar el layout y cerrar D44.
3. Registrar la extensión, con las hipótesis sobre K y su posterioridad
   declarada.
4. Materializar inventario, congelar, verificar kernels, medir.
5. Escribir resultados, confirmen o no la señal preliminar.

Los pasos 1 a 3 no consumen simulación y son reversibles. El paso 4 es el que
cuesta las tres horas y veinte.
