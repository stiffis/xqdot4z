# Protocolo experimental — versión 0.1

Nota editorial 0.2: estas matrices e hipótesis se conservan como notas internas,
fuera del artículo IEEE breve. No obligan a implementar todas las alternativas.
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

## Zero-point: tres regímenes que no se deben mezclar

1. ZC: constante por ejecución; campañas separadas z=0,8,15.
2. ZS: por fila/grupo, conocido antes de generar el programa. Contar código y
   especialización; todas las variantes disponen de la misma información.
3. ZR: por fila/grupo, leído en ejecución. Si D usa inmediato, registrar carga,
   despacho entre rutinas y aumento de código. Si requiere otro formato ISA,
   se trata como variante adicional con sus propios hazards y costos.

ZR es una pregunta abierta y no bloquea validar la unidad aritmética.
No se concluirá soporte barato de zero-points dinámicos usando solo ZC.
En B3, `Sa[g]` se calcula una vez por vector/grupo y se reutiliza para N filas.
Se permite calcularla mediante XQDot4 con pesos U4 iguales a uno, además
de optimizar cargas y planificación. Los fixtures actuales comprueban esa
ruta; no se impondrá extracción/suma escalar a B3 para favorecer a D.
La corrección usa los mismos z que D. Mantener salida y overflow idénticos.

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

Latencia de memoria de 1/3 ciclos y variantes 1/2/4 vías se estudian después de
tener un protocolo común verificado. Un modelo de espera no equivale a BRAM
implementada ni a un sistema con cache validado.

## Análisis y resultados negativos

Para cada configuración y semilla, calcular `cycles_baseline/cycles_D`.
Publicar numerador y denominador, no solo la razón. Un valor menor que uno
significa degradación y no se excluye del informe. Especificar si un resumen
usa media geométrica de speedups y exactamente qué casos incluye.

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
