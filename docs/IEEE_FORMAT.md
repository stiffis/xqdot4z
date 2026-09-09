# Selección del formato IEEE y política bilingüe

Revisión: 2026-09-08. Versión editorial 0.2.

## Fuentes oficiales consultadas

1. [IEEE Author Center: herramientas y plantillas para conferencias](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/authoring-tools-and-templates/).
2. [IEEE Author Center: estructura de un paper de conferencia](https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/structure-your-paper/).
3. [IEEE Author Center: selector de plantillas para revistas](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/tools-for-ieee-authors/ieee-article-templates/).
4. [Manual de IEEEtran alojado por una conferencia IEEE](https://www.ewh.ieee.org/conf/ivec/2020/assets/Template_Instructions.pdf).

El enlace general de descarga en ieee.org devolvió una restricción de acceso
al navegador. No fue necesario descargar una clase por otro medio: el entorno
ya incluye `IEEEtran.cls` V1.8b y `IEEEtran.bst`, y la documentación de IEEE
Author Center permite verificar el flujo y la estructura aplicables.

## Qué significa “formato IEEE” aquí

IEEE tiene plantillas de conferencia, revista y publicaciones específicas.
No existe una estructura de quince páginas ni un límite de páginas universal
que pueda fijarse sin conocer la convocatoria.

Para este trabajo inicial de arquitectura se adopta provisionalmente
`IEEEtran` en modo **conference**, papel Letter, 10 pt y dos columnas.
Se deja a la clase el control de márgenes, fuente base, títulos y captions.
No se emplean geometry, títulos personalizados, portada, índice, encabezados
de informe ni fondos de color. Por indicación del autor, no se aplica ningún
tema visual: texto negro y diagramas vectoriales monocromos, sin rellenos de color.

El modo journal se reservaría para una revista cuya plantilla lo requiera.
No se activa `compsoc` solo porque el tema sea arquitectura: depende de las
instrucciones de la publicación. Antes de enviar se comprobarán papel,
extensión permitida, anonimato, idioma, bibliografía y validación PDF exigidos.
La compilación local no equivale a aprobación de IEEE PDF eXpress.

## Estructura actual, deliberadamente breve

Título y autores pendientes; resumen de un párrafo; cuatro términos clave;
introducción; antecedentes; pregunta y alcance; método propuesto;
resultados/discusión pendientes; conclusiones pendientes; referencias.

El resumen no contiene citas ni ecuaciones y tiene menos de 250 palabras.
El protocolo detallado, las decisiones tentativas y la auditoría del core
permanecen en documentos de trabajo, fuera del artículo. No se anticipan
conclusiones ni resultados para imitar un paper terminado.

## Español e inglés

Se mantienen dos versiones equivalentes, no dos contribuciones independientes.
Las ecuaciones, citas, figura, alcance y estado deben coincidir. La versión
española sirve para revisión del equipo; su posibilidad de envío depende de
la convocatoria. Autores, afiliación, financiación y copyright no se inventan.
Las referencias conservan los títulos y datos originales en ambos idiomas.

La versión 0.1 de quince páginas se archivó sin perder fuentes ni PDF.
Sus matrices experimentales son notas de planificación revisables, no
compromisos cerrados que obliguen a ampliar el alcance prematuramente.
