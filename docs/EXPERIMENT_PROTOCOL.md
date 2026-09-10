# Protocolo experimental — versión 0.6

Nota editorial 0.2: estas matrices e hipótesis se conservan como notas internas,
fuera del artículo IEEE breve. No obligan a implementar todas las alternativas.
Revisión 2026-09-09, antes de medir rendimiento: se explicitan factores de
zero-point, especialización y amenazas a la validez. Este documento sigue
siendo la fuente normativa; no se crea otro contrato reducido en benchmarks.
El [manifiesto inicial](../benchmarks/campaign.json) concreta una selección
de casos, no redefine la frontera, métricas ni política de codegen de aquí.
Revisión 0.3, 2026-09-09: se selecciona la regla aritmética acotada de B1,
se hace explícita su congelación y se separan los fines de las semillas.
No se han escrito kernels de rendimiento ni ejecutado el piloto.
Revisión 0.4, 2026-09-09: se seleccionan y congelan las cinco políticas
comunes de codegen —desenrollado, recorrido, registros, reutilización de la
corrección y planificación— con sus consecuencias declaradas. Seleccionarlas
no desbloquea la campaña; los demás bloqueadores siguen vigentes.
Revisión 0.5, 2026-09-09: se fijan y verifican los eventos de medición y los
contadores en el testbench, con oráculo estructural, controles negativos y
mutaciones. Siguen sin existir kernels de las variantes ni mediciones.
Revisión 0.6, 2026-09-09: la política común pasa a `shared_tile_resident_skeleton_v2`
por contradicción interna e inviabilidad en K=128/512; el recorrido de filas se
deriva del ISA y aparece `required_row_bodies`. El comprobador gana invariantes
cruzados entre campos congelados.
El core corregido Kuntur está en `kuntur/`; aún no están completos los
comparadores B2/B3/D con sus kernels y fronteras de medida.

Actualización M3a: existe una integración inmediata `xqdot4zi`, con interfaz
en `isa/SPEC.md` y verificación en `docs/INTEGRATION_STATE.json`. No incluye
MUL en esa batería ni resuelve ZR, por lo que no se identifica aún como la variante D
completa. Su ejecución en E es funcional, sin evidencia de timing físico.

Actualización M3b parcial: MUL escalar común está implementada y verificada
con XQDot4Zi apagada/encendida. Su contrato es `isa/scalar/SPEC.md`, con
evidencia en `docs/SCALAR_STATE.json`. Ambas opciones están apagadas por
defecto. Habilitar ambas opciones no es
por sí solo un experimento D completo. No se han observado speedups ni se
han cambiado hipótesis a partir de resultados de rendimiento.

Actualización B3 aislado: `rtl/packed/xqdot4.v` implementa el producto punto
sin corrección; contrato `rtl/packed/SPEC.md` y evidencia `docs/PACKED_STATE.json`.
Los 24 fixtures matriz–vector reconstruyen resultados desde respuestas de
las unidades RTL, pero Sa, acumulación y corrección se calculan en el host.
No son ejecuciones en Kuntur ni mediciones de rendimiento. Sus dimensiones
de prueba no sustituyen la matriz experimental prospectiva de este protocolo.

Actualización de integración B3 (2026-09-09 UTC): XQDot4 es opcional e
independiente; `isa/packed/SPEC.md` y `docs/PACKED_INTEGRATION_STATE.json`
fijan el contrato y la verificación de ocho configuraciones. Cuatro pares
de fixtures N=2, K=G=8 ejecutan Sa, acumulación y corrección en Kuntur,
con resultados iguales a D. No son kernels optimizados ni pruebas ZR.
Los parámetros (MUL, XQDot4Zi, XQDot4) permiten B1=(0,0,0), B2=(1,0,0),
B3=(1,0,1) y D=(1,1,0). (1,1,1) prueba convivencia, no es D causal.
Falta cerrar kernels, memoria común y eventos de medición antes de comparar.

Actualización de kernels (2026-09-09): existen las **cuatro** variantes bajo la
política v2, con evidencia en `docs/KERNEL_STATE.json`. Cada caso corre su brazo
de titular, cuyo recorrido de filas se deriva de la codificación de la variante,
más el **gemelo estructural** en la forma contraria allí donde la codificación
admite ambas. El gemelo difiere solo en el control de bucle, así que restar el
par lo cotiza en vez de estimarlo, y contrastar ese par entre ZC y ZS separa la
bonificación de desenrollado del costo de suministrar el zero-point.

B1 y B2 comparten generador y difieren solo en la multiplicación: B2 usa `mul`,
B1 la descomposición por máscaras ya congelada. El cuerpo lo definen los
operandos, no las instrucciones, así que las cuatro emiten el mismo número de
cuerpos sobre los mismos ocho elementos. La lista blanca por variante se
comprueba decodificando el texto enlazado: **JALR queda fuera de las cuatro**,
porque un salto indirecto es la firma del despacho que la regla de
especialización declina, y así esa regla se verifica en el binario en vez de
prometerse en prosa.

Dos consecuencias arquitectónicas quedaron registradas al escribirlas. El cuerpo
de fila de B1 supera el alcance de una rama condicional, así que su arista de
retorno se expande a rama invertida sobre un salto **directo**; se permite solo
en B1 y se marca por caso, porque es el tamaño del código forzando el control y
no un despacho. Y la capacidad de instrucciones se fija en **32 768 palabras,
común a las cuatro**, dimensionada por el brazo mayor —el gemelo inline de B1 a
N=16, cerca de veinte mil palabras—; el fetch es combinacional, así que la
capacidad no cuesta ciclos y solo permite que el brazo quepa. Esto cierra la
compuerta de D10, que pedía decidirla tras generar kernels.

### Descomposición del hueco bajo ZS

Bajo ZS los brazos de titular no comparten forma de fila: D está forzada a
rectilínea y B3 recorre en bucle. El hueco crudo entre ambos mezcla, por tanto,
la corrección con el control de bucle, y **ninguna de las dos se puede leer
sola de ese número**.

El gemelo estructural lo separa sin ningún término estimado. Comparando D
contra el brazo de B3 **de la misma forma**:

```text
crudo        = B3(bucle) − D
estructural  = B3(bucle) − B3(misma forma que D)
aritmético   = B3(misma forma que D) − D
crudo        = estructural + aritmético      (comprobado, no supuesto)
```

El término estructural es lo que B3 paga por recorrer en bucle y D no paga
porque su codificación se lo impide; el aritmético es la corrección con la
estructura igualada. El runner comprueba que la suma cierra en cada caso.

El control de bucle se **cotiza**, no se modela: es la resta entre el brazo de
titular en bucle y su gemelo rectilíneo, y obedece una ley exacta que el runner
verifica. Una arista de retorno simple cuesta `3N−1` ciclos. El cuerpo de fila
de B1 supera el alcance de una rama condicional en cuanto el zero-point no es
cero, así que su arista se expande a rama sobre salto y cuesta `4N−2`. Esa
diferencia queda ligada al mismo campo que marca la expansión, de modo que no
se puede cambiar una sin la otra.

Contrapartida obligatoria: la especialización forzada de D **no es gratis**.
Se reporta junto a la descomposición como palabras de código y como
`required_row_bodies`. Un hueco de ciclos a favor de D bajo ZS y un texto varias
veces mayor son la misma decisión de interfaz vista por dos lados, y reportar
uno sin el otro sería incompleto.

Al desarrollarlos se observaron contadores de esas corridas de corrección; se
registran como tiempos de desarrollo observados, no como resultados, y no se ha
comparado ni calculado ningún speedup. Falta materializar tensores e inventario
con hashes, congelar las dos políticas y registrar la revisión previa antes de
medir: la campaña sigue bloqueada.

Estado: planificación. No existen aún mediciones de XQDot4Z.
Las configuraciones siguientes son propuestas concretas; cualquier revisión
se registra antes de comparar resultados.

## Variantes y comparabilidad

| ID | Plataforma | Uso |
|---|---|---|
| H0 | Exportación histórica intacta | Auditoría y referencia de procedencia; no baseline causal principal |
| B1 | Base normalizada, multiplicación por software | Beneficio respecto a un core sin multiplicador |
| B2 | Base normalizada + MUL escalar | Aislar procesamiento empacado/fusión frente a multiplicación disponible |
| B3 | Base normalizada + producto punto U4×S8 sin corrección | `P - z*Sa`, reutilizando Sa por grupo entre filas |
| D | Base normalizada + XQDot4Z | Producto punto con corrección fusionada |

B2, B3 y D tendrán el mismo MUL escalar para la corrección y el epílogo.
B1 aporta contexto frente a un core sin multiplicador: no responde por sí
solo RQ1 (D/B2) ni RQ2 (D/B3, central). No se dedicará una búsqueda de
algoritmos de multiplicación a maximizar su rendimiento o el speedup de D.
Añadir MUL no equivale a implementar M completo. Para aislar la corrección,
B3 y D usarán el mismo número de vías, protocolo y selección de mitades;
el resultado B3 será `sum(qw*qa)`, no una operación S4 accidentalmente distinta.
El hardware extra de D se contará en síntesis; no se forzará artificialmente
la misma frecuencia máxima. Se ofrecerá comparación a reloj común viable y,
cuando proceda, con timing alcanzado por cada diseño bajo restricciones iguales.

Correcciones del core, control de fuentes, capacidad/latencia de memoria,
instrumentación y convención de inicio/fin son comunes a B1/B2/B3/D.
El progreso H0→D se reportaría aparte y nunca como efecto puro de la extensión.

## Cargas

Kernel primario: batch uno, `D[r,g] = sum_i (qw[r,i]-z[r,g])*qa[i]`.
Primero se devuelven subtotales INT32 por grupo; no se suman grupos con escalas
distintas como si compartieran una escala. Segundo nivel: capa con escalado,
bias y requantización especificados, cuya salida se verifica por separado.

Matriz principal: K en {32,128,512}, N en {1,4,16}, G=32. N=1 representa
producto punto. Pesos U4 y activaciones S8 idénticos para todos los casos.
Sensibilidad separada: G en {8,32,128}, solo cuando divide K.
Colas K en {1,3,5,31,33,127} pertenecen primero a corrección; no se mezclan
silenciosamente en el agregado principal de rendimiento.

Semillas propuestas: enteros 20260908 a 20260917, generador y versión fijados.
Su función primaria es cobertura de entradas para corrección, no repeticiones
independientes de tiempo. Por ahora se conservan las diez y se recogerán todas
sus métricas; distinguir su función no reduce silenciosamente la rejilla.
Conservar tensores empaquetados y hashes evita depender solo del generador.
Casos dirigidos: ceros, códigos extremos, activaciones -128/127, cancelaciones
y resultados negativos. La cuantización de una red real se evaluará después.

La selección inicial del manifiesto conserva N∈{1,4,16}, con K=G=32: no se
reemplaza el barrido de H2 por una sola N. Tiene un grupo; por ello no puede
demostrar sensibilidad a variación entre grupos. Las ampliaciones de K de
la matriz principal se registrarán antes de ejecutarse. Los campos operativos
del manifiesto son la referencia de esa selección; la matriz principal
anterior sigue delimitando el alcance prospectivo, no una campaña ya realizada.

### Piloto de sensibilidad a los tensores

Después de verificar kernels y eventos de medida, el piloto del manifiesto
comparará las dos primeras semillas con N=4, K=G=32, en las cuatro variantes:
los tres controles ZC y la fase ZS=0. Esta fase mezcla z=0,1,2,3 entre filas.
Son 32 casos de la rejilla existente (64 ejecuciones si se usa cada simulador),
no una nueva dimensión ni mediciones ya realizadas. Se fijan ahora para no
seleccionar el piloto según resultados favorables. Las ejecuciones válidas
podrán reutilizarse en la campaña solo si coinciden todas sus entradas y revisiones.

Por cada par de semillas se mantendrán binario, direcciones base/disposición de datos,
z, configuración, memoria y eventos. Además de ciclos se contrastarán retiros,
traza de PC/opcodes retirados, resultados de branches, stalls y direcciones de
datos; los valores aritméticos y salidas se verifican con sus propios oráculos,
no se exige que sean iguales entre semillas. Una diferencia exige investigar
su causa, no declararla automáticamente un bug ni descartar la semilla.

Dos totales iguales no demuestran independencia respecto de todos los datos.
Reducir después semillas de rendimiento requiere una revisión explícita y
análisis de código, control, direcciones, latencias y contadores; se conserva
aparte la cobertura de corrección y el historial observado. No se elige una
semilla por el speedup que produzca. La simulación determinista tampoco implica
que distintas entradas deban tardar igual.

## Zero-point: tres regímenes que no se deben mezclar

1. ZC: constante por ejecución; campañas separadas z=0,8,15.
2. ZS: por fila/grupo, conocido antes de generar el programa. Contar código y
   especialización; todas las variantes disponen de la misma información.
3. ZR: por fila/grupo, leído en ejecución. Si D usa inmediato, registrar carga,
   despacho entre rutinas y aumento de código. Si requiere otro formato ISA,
   se trata como variante adicional con sus propios hazards y costos.

La primera etapa es una **evaluación bajo especialización estática, sin
extrapolar a ZR**. Equidad de información entre variantes dentro de ZC/ZS
no implica que ese régimen represente el uso dinámico, ni demuestra una
cota superior de la ventaja de D. H3 es una hipótesis, no una desigualdad probada.

La asimetría actual es de interfaz: B3 puede usar z en un GPR para corregir
mediante aritmética escalar; XQDot4Zi lo requiere como inmediato. No es posible
pasar directamente un GPR en ese campo. Sin embargo, seleccionar en ejecución
entre instrucciones/rutinas con los 16 inmediatos legales no exige cambiar
el encoding. Ese despacho no está implementado ni medido. Por tanto, D-ZR
no tiene todavía un kernel ni un costo definido en este proyecto, pero no
se afirma que sea imposible compilarlo sin otra ISA. B3-ZR tampoco dispone
de un kernel medido: sus cargas, reutilización de metadatos, MUL o despacho
dependen de una implementación explícita, no necesariamente de una carga
obligatoria por cada salida. Véase la [interfaz vigente](../isa/SPEC.md).

### Valores, distribución y estratos del zero-point

El manifiesto fija antes de medir los códigos, su distribución, las posiciones
fila/grupo y la regla de repetición. La selección inicial incluye:

- ZC: controles constantes separados 0, 8 y 15, ya previstos en este protocolo.
  No se presentan como una distribución representativa de una red.
- ZS: fases cíclicas que cubren los 16 códigos U4 con igual frecuencia por
  cada combinación N/K/G/semilla al considerar todas las fases. La regla
  parametrizada del manifiesto depende de fila y grupo, no de la variante.
  Las fases no se regeneran para buscar mejores resultados.
- Estratos disjuntos de salida: cero, uno, potencias de dos mayores que uno
  y demás códigos U4. Uno se separa porque puede requerir solo reutilizar Sa;
  los demás códigos tampoco se suponen inmunes a reducciones de fuerza.

El programa ZS puede mezclar estratos en una misma ejecución. El tiempo total
se reporta por configuración/fase con su histograma de z; no se atribuyen
ciclos a cada estrato proporcionalmente a su frecuencia. Un desglose de
tiempos por estrato requeriría medición explícita o campañas homogéneas
declaradas por separado. ZC y ZS no se mezclan en un speedup global.

Se emparejan pesos y activaciones entre variantes y perfiles de z para una
misma dimensión/semilla; se almacenarán tensores e histogramas efectivos.
Conocer esos tensores para verificar resultados no autoriza precomputar Sa
ni los productos/salidas en el generador del kernel. A/W son datos de entrada
opacos para optimización; solo dimensiones y metadatos declarados pueden
especializar código. Sa y las correcciones reutilizadas se calculan durante
la ejecución medida, no se insertan como respuestas precalculadas.
La distribución sintética equilibrada estudia sensibilidad, no estima la
frecuencia de zero-points de un modelo real ni garantiza peor/mejor caso.

ZR es una pregunta abierta y no bloquea validar la unidad aritmética.
No se concluirá soporte barato de zero-points dinámicos usando solo ZC.
En B3, `Sa[g]` se calcula una vez por vector/grupo y se reutiliza para N filas.
Se permite calcularla mediante XQDot4 con pesos U4 iguales a uno, además
de optimizar cargas y planificación. Los fixtures actuales comprueban esa
ruta; no se impondrá extracción/suma escalar a B3 para favorecer a D.
La corrección usa los mismos z que D. Mantener salida y overflow idénticos.

Sa depende del vector/grupo, no de la fila; puede reutilizarse entre filas.
z[r,g]·Sa[g] no se eleva incondicionalmente fuera de ese bucle cuando z
cambia. Sí puede calcularse una vez por (g,z) y reutilizarse entre filas
que comparten z, bajo una política declarada. Para ZC esto es legal incluso
sin especializar cada fila; para ZS las igualdades conocidas también pueden
aprovecharse. No depende solo de que exista un generador especializado.
El manifiesto hará explícita la política y el código/almacenamiento asociado.

Con z=0, B3 puede omitir tanto la corrección como Sa cuando ninguna salida
del grupo la necesita; esto no demuestra igualdad de ciclos o timing con D.
Con z=1 puede omitir la multiplicación, y con potencias de dos usar shifts.
No se reduce por ello toda la comparación D/B3 a shift frente a MUL: quedan
Sa, cargas, acumulación, planificación y control. Para los demás valores se
permiten reducciones de fuerza justificadas por la misma política. Las
especializaciones se aplican donde sean semánticamente válidas en B1/B2/B3/D.
D puede especializar su código y reutilizar datos, aunque no tenga un término
z·Sa separado; no se afirma que toda especialización por fila sea exclusiva de B3.

### Control del esfuerzo de optimización

Antes de escribir kernels de rendimiento se fijan en el manifiesto el
desenrollado en elementos lógicos, el recorrido de filas/grupos, la política
de asignación de registros y spills, y las reglas de especialización,
reutilización de correcciones y planificación. Estos valores quedan
seleccionados en la sección siguiente; no se eligen después de mirar speedups.
No basta con que un JSON sea válido para declarar listo el experimento: los
demás bloqueadores de ejecución siguen vigentes.

### Política común: regla seleccionada y consecuencias declaradas

La política `shared_tile_resident_skeleton_v2` sustituye a
`shared_group_resident_skeleton_v1`, que era **internamente contradictoria**:
ocho elementos lógicos por iteración implican un bucle de K, mientras que la
residencia de activaciones a escala de grupo exige nombres de registro distintos
por iteración y por tanto lo prohíbe. La contradicción sobrevivió porque el
comprobador validaba la forma del manifiesto y no la coherencia entre sus campos.

La escala de grupo además **no era implementable más allá de la forma inicial**:
las palabras de activación son K/4, es decir 32 con K=128 y 128 con K=512, contra
31 registros utilizables. Habría fallado en RQ3 con independencia de esta
revisión. Esa es la razón de fondo del cambio, no un resultado observado.

Se selecciona antes de medir a partir de la forma de los operandos y del
presupuesto de registros **sobre toda la matriz K del protocolo**, no de tiempos
ni de una búsqueda sobre kernels. No se afirma óptima. Rige por igual para las
cuatro variantes y se congela en Git —política, generador, ensamblado,
desensamblado, hash del `.text`, pruebas y revisión— antes del primer cronometraje.

1. Cuerpo: ocho elementos lógicos, exactamente una palabra de pesos empacados
   —ocho códigos U4— y dos palabras de activaciones —cuatro S8 cada una—.
   **El cuerpo lo definen los operandos, no las instrucciones que los consumen**:
   B3 y D emiten dos operaciones empacadas y dos acumulaciones, mientras B1 y B2
   expanden esos mismos ocho elementos de forma escalar. Cada variante emite un
   número entero de cuerpos sobre los mismos operandos, y la auditoría de
   desensamblado puede contarlos. No se elige por su efecto medido.
2. Recorrido de K: los cuerpos se desenrollan dentro de la fila, igual en las
   cuatro variantes. Un bucle de K costaría ~6 ciclos de control sobre un cuerpo
   de ~7 instrucciones: contaminaría más de lo que ordena.
3. Residencia y registros: la ventana de activaciones es de **dos palabras, a
   escala de cuerpo, no de grupo**. Se reservan esa ventana, el acumulador de
   fila y los punteros de recorrido, sin spills internos y con idéntica reserva
   en las cuatro. Perder la residencia de grupo cuesta dos cargas de activación
   por cuerpo, por igual en todas.
4. Recorrido de filas: **se deriva del ISA de cada variante, no se elige**. Una
   variante recorre filas en bucle salvo que su codificación no pueda expresar
   el cuerpo de fila con una sola copia de código. Bajo ZS solo D está forzada a
   especializar, porque su zero-point es un inmediato; ese piso obligatorio se
   reporta como `required_row_bodies` —bajo ZC uno en las cuatro; bajo ZS uno en
   B1, B2 y B3, y dieciséis en D— y es el costo de suministrar z. Todo cuerpo
   adicional que una variante emita por elección va a `text_bytes`, no aquí.
5. Especializaciones: se toma una especialización estáticamente válida **si y
   solo si no exige despacho**, con la misma regla en las cuatro. Con filas
   rectilíneas son gratis y se toman todas; con filas en bucle solo compensan
   cuando lo ahorrado supera el despacho. Que B3 emita un solo cuerpo pasa a ser
   derivado de la regla y no una decisión del implementador, que es lo que cierra
   la objeción de haberla lastrado.
6. Reutilización de la corrección: B3 puede izar `z*Sa` compartido **solo cuando
   el calendario declarado repite z**, nunca inspeccionando tensores ni valores
   medidos. En ZC el z es constante entre filas, así que iza una vez por caso y
   corrige con una resta por fila; en ZS cada fila tiene su z, así que paga una
   multiplicación y una resta por fila. La diferencia proviene del calendario y
   de esta política, no de la arquitectura, y es otra razón para reportar ZC y ZS
   por separado y no agregar un speedup entre regímenes.
7. Reducción de fuerza y planificación: se reduce solo sobre constantes
   declaradas estáticamente, con una única pasada común a todas las variantes y
   sin reordenamientos manuales por variante.

**Dirección declarada de esta revisión.** Sus dos correcciones se oponen en el
ratio D/B3: dar bucle de filas a los baselines lo sube, y quitar la residencia de
grupo a D y B3 por igual lo baja. Ninguna se eligió por su efecto y ambas se
reportan. La revisión se hizo después de observar contadores de corridas de
desarrollo, que se conservan; su justificación —la contradicción interna y la
inviabilidad en K=128/512— no depende de ellos.

Estas siete reglas no vuelven ejecutable la campaña. Los kernels, las
capacidades de memoria, los eventos de medición, los contadores y la
materialización de tensores siguen pendientes y bloqueados.

B3 y D compartirán un generador/esqueleto de recorrido, packing, cargas y
salidas. Las diferencias permitidas serán la operación interna y el trabajo
necesario para preparar, reutilizar y aplicar la corrección. Se revisará el
ensamblado generado; compartir una función no demuestra por sí solo que
las diferencias respeten esa regla. El desenrollado y la política de registros
serán comunes para las cuatro variantes, no cuatro decisiones manuales ocultas.

Una política común no exige instrucciones, uso efectivo de registros ni
spills idénticos: necesidades distintas pueden ser efecto de la arquitectura.
No se añaden NOPs ni cálculos inútiles para igualar código. Se documentarán
los pases de optimización y sus cambios; una exploración posterior de mejores
kernels por variante será otra campaña con espacio de búsqueda explícito,
no un reemplazo silencioso de los resultados controlados.

### B1: regla seleccionada y esfuerzo acotado

La política `bounded_masked_bit_decomposition_v1` se selecciona antes de
medir por simplicidad, rango conocido y auditabilidad; no se afirma óptima
ni que una regla única garantice neutralidad. No se implementará una búsqueda
de Booth, variantes shift-add o rutinas genéricas como subproyecto de B1.
Se fijan estos cinco aspectos en el manifiesto:

1. Formulación y operando recorrido: calcular directamente `(w-z)*a`,
   recorriendo los bits de `w-z`. B1 no factoriza Sa entre filas en esta campaña.
2. Anchos y signo: `w-z` está en [-15,15], S5; `a` es S8 extendido a RV32.
   Se aprovechan dos límites conocidos estáticamente: con z=0 el peso es U4;
   con z=8 es S4. El resto usa S5. No se inspeccionan valores de A/W para elegir ancho.
   Los pesos siguen almacenados como U4; la resta se ejecuta en el kernel,
   no se recodifican los tensores previamente.
3. Iteraciones: expansión rectilínea de los bits del ancho declarado;
   contribuciones positivas y, en S4/S5, resta del bit de signo. Sin salida
   anticipada ni bucle software de 32 iteraciones.
4. Selección: cada bit produce máscara cero o todos unos; se selecciona
   `a << bit` mediante AND y se acumula con ADD/SUB. No hay rama por bit,
   rama de signo ni tabla indexada por valores del tensor.
5. Especialización: materializar z estático, omitir `w-0` y aplicar solo las
   reducciones de ancho anteriores en la multiplicación. No cambiar de algoritmo
   por semilla, introducir atajos por valores A/W o factorizar entre filas.
   Otras decisiones de recorrido, registros y planificación siguen sujetas a
   la política común pendiente. Esta limitación de B1 se reportará, no se
   interpretará D/B1 como comparación contra el mejor software posible.

Para un operando firmado de b bits, la identidad utilizada es
`x = sum_{j=0}^{b-2} bit_j(x)*2^j - bit_{b-1}(x)*2^(b-1)`.
En U4 se suman los cuatro bits sin término negativo. Multiplicar esa identidad
por `a` da la regla de máscaras; selección y acumulación se modelan en 32 bits.
El producto exacto está en [-1920,1920]. El
[modelo ejecutable de la política](../benchmarks/b1_arithmetic.py) y sus
[pruebas](../tests/benchmarks/test_b1_arithmetic.py) comprueban las 65 536 ternas
U4/U4/S8 en el host; no validan ensamblado, ejecución en Kuntur ni ciclos.
Los cuatro o cinco pasos por producto no fijan el desenrollado del bucle de
elementos del kernel, que permanece pendiente y será común a las variantes.

La política y su materialización futura (generador, ensamblado, desensamblado,
hash del código y pruebas) deben quedar en una revisión Git anterior a la
primera medida del kernel, incluido el piloto. Este documento selecciona el
algoritmo; no finge que exista ya el binario congelado. Cualquier cambio tras
observar tiempos requiere nueva versión, motivo, conservación de observaciones
y repetición de los pares afectados; no sustituye silenciosamente el baseline.

Para z=8 también se documentará la alternativa de recodificar pesos a S4.
Cambiar esa codificación sería otra comparación, no un resultado con el mismo
formato U4. No se afirmará que todas las rutas W4A8 requieren restas de 5 bits.

## Memoria, software y frontera de medida

Propuesta para la base normalizada: memorias parametrizables, inicialmente
64 KiB de instrucciones y 64 KiB de datos, modelo combinacional documentado.
No es una modificación ya realizada. Alinear palabras y detectar rangos
inválidos; el Fetch de 32 bits que cruza media palabra exige revisar límites.

Comenzar con ensamblador controlado, revisar desensamblado y rechazar opcodes
fuera de una lista permitida. No asumir que `-march=rv32ic` restringe el
compilador al subconjunto que implementa este procesador.
Los kernels primarios usarán instrucciones de 32 bits en todas las variantes;
se desactivará compresión/relajación automática al generarlos. El soporte C
se conserva y verifica por separado. No se varía compresión como un factor
adicional en la primera comparación causal.

Medir desde la aceptación de la primera instrucción del kernel hasta el retiro
de la última instrucción que materializa su salida; la implementación de esos
eventos debe quedar fijada en el testbench. Excluir reset y carga inicial del
programa. Incluir cargas de tensores, bucles, suma Sa, corrección, dispatch y
stores de salida. Para la capa completa, incluir también el epílogo.
Reportar adicionalmente el núcleo aritmético, sin sustituir el total por él.

Registrar ciclos, instrucciones retiradas (también stores/branches), desglose
de stalls, instrucciones dinámicas, bytes de código y bytes de memoria por
nivel. Separar conteo de instrucciones de señales de escritura de registros.
Un reintento/stall no puede contarse como múltiples retiros.

### Eventos y contadores: implementación fijada

`tests/benchmarks/tb_measure.sv` concreta los eventos anteriores. Observa el
pipeline jerárquicamente y **no añade instrucciones al kernel**, de modo que se
mide el mismo texto que la variante ejecutaría sin observador. Los contadores
son eventos estructurales de este modelo, no tiempo físico.

- **Apertura:** primer flanco de bajada con `ValidD` activo y `PCD` igual a
  `BEGIN_PC`. Un paso especulativo descartado deja `ValidD` en cero y no abre
  la ventana.
- **Cierre:** retiro de `END_PC`, el store que materializa la salida. Un kernel
  con bucle retira ese PC una vez por fila y la ventana cierra en **el último**.
- **Extensión del texto:** `TEXT_END` delimita el kernel para atribuir eventos.
  En un bucle el PC de cierre no es la última instrucción del cuerpo, así que
  la atribución no puede usar el PC de cierre.
- `cycles` cuenta ambos extremos: `cierre − apertura + 1`.

Contadores por ventana: `cycles`, `retired`, `retired_kernel`,
`retired_stores`, `retired_loads`, `retired_branches`, `retired_jumps`,
`register_writes`, `stall_load_use`, `stall_fault_hold`,
`flush_taken_control`, `data_read_bytes` y `data_write_bytes`.

Tres consecuencias se declaran en lugar de descubrirse al analizar resultados:

1. **Sesgo de llenado.** Una instrucción aceptada antes de la ventana puede
   retirar dentro de ella. Por eso `retired` (todos los retiros de la ventana,
   comparable con `cycles`) se separa de `retired_kernel` (solo PCs del kernel).
   Su diferencia está acotada por la profundidad del pipeline, tres.
2. **Tomadas frente a ejecutadas.** `retired_branches` se obtiene decodificando
   el opcode del binario sobre la traza de PCs retirados, no de una señal del
   pipeline: una rama no tomada retira sin levantar `PCSrcE`. `flush_taken_control`
   cuenta solo las redirecciones efectivas. Los dos números son distintos y
   ninguno sustituye al otro.
3. **Faltas ajenas al kernel.** Todo programa termina en un EBREAK de
   diagnóstico posterior a `END_PC`; `stall_fault_hold` solo cuenta faltas
   cuyo PC cae dentro del kernel, y debe ser cero en una medición válida.

Los bytes de código son estáticos, del texto enlazado, y los calcula el runner.
Los bytes de memoria cuentan solo la interfaz de datos realmente modelada; no
se inventa tráfico de caché ni niveles inexistentes.

`scripts/verify_measurement.py` comprueba estos eventos con programas dirigidos
cuyas expectativas se derivan de la estructura del pipeline, no de una corrida:
un kernel rectilíneo de n instrucciones ocupa n+3 ciclos, un riesgo load-use
añade uno y una redirección tomada añade dos. Incluye un par diferencial que
aísla el stall, controles negativos para ventanas que no abren, no cierran o
están invertidas, y mutaciones del propio harness que deben ser detectadas.
Ambos simuladores deben coincidir exactamente.

Esto fija los eventos y contadores; **no** produce kernels ni mediciones de
las variantes. El núcleo aritmético sigue pendiente como medición adicional con
su propia frontera, no una resta estimada a partir del total ni su sustituto.

Latencia de memoria de 1/3 ciclos y variantes 1/2/4 vías se estudian después de
tener un protocolo común verificado. Un modelo de espera no equivale a BRAM
implementada ni a un sistema con cache validado.

## Análisis y resultados negativos

Para cada configuración y semilla, calcular `cycles_baseline/cycles_D`.
Publicar numerador y denominador, no solo la razón. Un valor menor que uno
significa degradación y no se excluye del informe. Especificar si un resumen
usa media geométrica de speedups y exactamente qué casos incluye.

Se conservarán separadas las dimensiones, ZC/ZS, los perfiles y las fases.
No se ponderará una mezcla de z después de observar qué favorece a D.

La simulación RTL determinista no adquiere significancia estadística al
repetir el mismo binario y tensor. Las semillas exploran entradas; las
configuraciones exploran cargas. Si no cambia el control, ciclos idénticos
son un resultado esperado. Cualquier intervalo estadístico debe identificar
su unidad de muestreo; no usar barras de error de repeticiones idénticas.
Una unidad combinacional no demuestra independencia del kernel completo.
Tampoco es requisito necesario: una unidad multiciclo con latencia fija podría
mantener esa propiedad. La condición relevante incluye el control, las
direcciones/latencia de memoria, las latencias de instrucciones y los eventos
de medida del programa completo. Ninguna variante tiene aún esa comprobación.

Tiempo físico: `cycles/f`, con timing sustentado para cada diseño. Recursos:
LUT/FF/DSP/BRAM del dispositivo y flujo concretos. No convertir ciclos o LUT
en energía; potencia/energía requieren una medición o estimación declarada.
Actualmente se dispone de Icarus y Verilator; `yosys` no fue encontrado en PATH
durante la auditoría inicial. No se instalaron herramientas ni eligió FPGA.

## Datos y trazabilidad

`results/schema.json` define los campos mínimos de futuros resultados.
No se crean filas con speedups ficticios. Cada run debe conservar:
revisión del core/protocolo, configuración, toolchain/versiones/opciones,
semilla, hashes de tensores y programa, resultados esperados/obtenidos,
logs sin editar y comando de reproducción. Un fallo se registra con su estado,
no desaparece del conjunto. Las tablas se generarán desde esos datos.

### Compromiso operativo previo a resultados

Se reportarán todos los casos enumerados por el manifiesto congelado, no
solo los que produzcan aceleración. Cada identificador tendrá estado pass,
fail, timeout o unsupported; una ausencia es una campaña incompleta, no un
caso descartado. No se asignará speedup a fallos o a implementaciones ausentes.
Las tablas conservarán el inventario completo y explicarán las exclusiones
de cada agregado, sin ocultarlas ni convertirlas en un denominador conveniente.

Antes de medir se fijarán en Git manifiesto, protocolo, generador, políticas,
instrumentación y entradas con sus hashes. Esta revisión define factores de z,
pero mantiene bloqueos explícitos para políticas e instrumentación no resueltas.
Durante el desarrollo se conservarán los números de depuración observados y
se identificarán como tales: no se afirmará que se diseñó a ciegas después de verlos.
Ya existen trazas, retiros y stalls de los fixtures M3 de verificación; esta
revisión precede a la campaña de rendimiento, no a todo conocimiento previo
del comportamiento microarquitectónico.
Toda modificación posterior del espacio de casos o del código requerirá una
nueva revisión, motivo y repetición de los pares afectados; el historial anterior
se conserva. El compromiso de reporte no autoriza publicación externa sin
resolver autoría, permisos, licencia y convocatoria.

## Amenazas a la validez

El esqueleto compartido reduce el sesgo de optimización pero no demuestra
optimalidad ni elimina la interacción software–arquitectura.

- Validez interna: asignación de registros, planificación y especialización
  pueden favorecer una implementación. Se congelan políticas, se revisan
  diferencias de código y se conserva el desglose causal de eventos, sin
  presentar esa mitigación como una prueba de optimalidad.
  B1 está condicionado a una sola regla aritmética de alcance acotado; se
  congela explícitamente antes del piloto y no reemplaza D/B2 o D/B3.
- Validez externa: ZC/ZS no resuelven ZR; la distribución sintética U4, sus
  correlaciones y repetición de z no representan necesariamente una red real.
  K=G en el arranque no evalúa variación entre grupos. Los resultados quedan
  condicionados a dimensiones, perfiles y políticas explícitas.
- Validez de medición: marcadores, retiros, ventanas y contadores pueden
  introducir sesgo o doble conteo. Requieren pruebas antes de usarse para
  explicar diferencias; hashes/enlaces no demuestran coherencia semántica.
- Validez de conclusiones: repeticiones deterministas no aportan muestras
  independientes; los ciclos no prueban frecuencia, área ni energía. Se
  conservarán resultados negativos y no se extrapolará a hardware no evaluado.
