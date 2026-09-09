# Protocolo experimental — versión 0.2

Nota editorial 0.2: estas matrices e hipótesis se conservan como notas internas,
fuera del artículo IEEE breve. No obligan a implementar todas las alternativas.
Revisión 2026-09-09, antes de medir rendimiento: se explicitan factores de
zero-point, especialización y amenazas a la validez. Este documento sigue
siendo la fuente normativa; no se crea otro contrato reducido en benchmarks.
El [manifiesto inicial](../benchmarks/campaign.json) concreta una selección
de casos, no redefine la frontera, métricas ni política de codegen de aquí.
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
Conservar tensores empaquetados y hashes evita depender solo del generador.
Casos dirigidos: ceros, códigos extremos, activaciones -128/127, cancelaciones
y resultados negativos. La cuantización de una red real se evaluará después.

La selección inicial del manifiesto conserva N∈{1,4,16}, con K=G=32: no se
reemplaza el barrido de H2 por una sola N. Tiene un grupo; por ello no puede
demostrar sensibilidad a variación entre grupos. Las ampliaciones de K de
la matriz principal se registrarán antes de ejecutarse. Los campos operativos
del manifiesto son la referencia de esa selección; la matriz principal
anterior sigue delimitando el alcance prospectivo, no una campaña ya realizada.

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

Antes de escribir kernels de rendimiento se fijarán en el manifiesto el
desenrollado en elementos lógicos, el recorrido de filas/grupos, la política
de asignación de registros y spills, y las reglas de especialización,
reutilización de correcciones y planificación. Los campos aún pendientes
bloquean la ejecución de la campaña; no se elegirá su valor después de mirar
speedups. No basta con que un JSON sea válido para declarar listo el experimento.

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

La futura nota de instrumentación concretará señales, flancos y aceptación
de inicio/fin en el testbench, y sus pruebas dirigidas. No repetirá este
contrato como otra fuente normativa. Deberá distinguir total de retiros e
histograma dinámico por opcode, pausas load-use, penalizaciones de redirección
y llenado/vaciado; no sumar eventos solapados como ciclos independientes.
Para memoria distinguirá capacidad/huella de bytes transferidos y contará
solo interfaces/niveles realmente modelados, sin inventar tráfico de caché.
El núcleo aritmético será una medición adicional con su propia frontera,
no una resta estimada a partir del total ni su sustituto.

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
