# Alcance de la licencia

El texto de [LICENSE](../LICENSE) es MIT sin modificar, porque alterar una
licencia estándar la vuelve una licencia distinta que nadie reconoce. El alcance
se explica aquí en lugar de dentro de ella.

## Qué cubre MIT

Todo el código y la evidencia del repositorio: el RTL de Kuntur y de las
unidades propuestas, los generadores, los runners de verificación, los
comprobadores, las pruebas y los artefactos de las corridas.

Incluye `baseline/upstream/`. Esa exportación es obra del mismo autor, pero está
**fijada por SHA-256** y verificada por `make baseline-check`, así que no se le
añade ningún encabezado: modificarla rompería su integridad, que es exactamente
lo que existe para garantizar. La licencia la cubre desde aquí.

## Qué no cubre

**El manuscrito** de `paper/`. Sigue siendo un borrador de trabajo, no destinado
a envío, y su licencia queda **deliberadamente diferida** hasta acordar venue.

La razón es de asimetría, no de indecisión: una licencia abierta es fácil de
añadir después e imposible de retirar una vez que alguien se apoyó en ella. Y
muchas conferencias piden cesión de derechos, que puede entrar en conflicto con
una licencia abierta publicada antes. Decidir venue primero mantiene abiertas
todas las opciones; publicarla ahora cierra algunas sin necesidad.

Lo que sí necesita ser reutilizable para que el trabajo sea reproducible es el
código, y eso está cubierto.

## Procedencia

La estructura y las convenciones de nomenclatura del pipeline se aprendieron de
Harris & Harris; **no se utilizó código del libro**. Las ideas y los métodos no
son objeto de copyright; lo es la expresión, y esta es propia. El autor es autor
único de kirky-arqui y por tanto de Kuntur, de modo que no hay coautores cuyos
permisos haga falta recabar.

Queda por verificar la política de propiedad intelectual de la universidad sobre
trabajo producido para cursos, que varía por institución. Ver D13.
