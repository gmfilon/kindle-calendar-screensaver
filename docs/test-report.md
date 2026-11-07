# Resultados de desarrollo

Fecha: 6 de noviembre de 2026, Buenos Aires. Entorno: macOS ARM64,
Python 3.9.6 y Pillow 11.3.0 dentro de `.venv`.

## Ejecutado

`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`

**22 pruebas aprobadas en la revisión 0.2.0.** Incluyen:

* Los 4800 meses de un ciclo gregoriano completo de 400 años: días completos,
  orden y alineación de lunes a domingo; excepciones de bisiestos seculares.
* Cambio de año, 29 de febrero, medianoche local respecto de UTC, rechazo de hora
  sin zona y cálculo desde el reloj actual.
* PNG en grises, dimensiones, área del día resaltado, salida idéntica en dos
  generaciones locales, cobertura e integridad; rechazo de rutas fuera del bundle.
* Staging, desinstalación, archivos ajenos conservados, destinos prohibidos,
  fallo de copia sin instalación parcial y ZIP reproducible/desactivado.
* Modelo de scheduler: RTC sólo en ventana de suspensión, fallos acotados,
  paso de año, saltos de reloj, días omitidos, reboot y no dibujar leyendo.
* Script POSIX real con backend simulado: elección de fecha, rollback del reloj,
  checksum, fecha ausente, exclusión mutua, liberación de lock, desbloqueo durante
  reintento, tres intentos, timeout y confirmación sólo al terminar.

En macOS las pruebas usan adaptadores Python para `flock` y `timeout`, ausentes
en el host. El lock usa `fcntl.flock` real del kernel. Reloj y backend están
simulados; no se ejecuta LIPC ni se accede a pantalla. `sha256sum` es nativo.
Esto no comprueba el BusyBox ni los binarios reales del Kindle.

También se ejecutaron:

```sh
sh -n device/calendar-worker.sh device/probe.sh
PYTHONPATH=src .venv/bin/python tools/simulate.py
```

Revisión visual del PNG de 1272×1696 del 6 de noviembre de 2026: textos completos,
grilla alineada lunes-domingo, fecha grande y día 6 resaltado sin recortes.
La revisión 0.1.1 elimina la fecha redundante y centra el día de la semana en
76 px y negrita sobre el espacio de los dos renglones anteriores.
La revisión 0.2.0 cambia el diseño predeterminado a 1696×1272: fecha a la izquierda
y grilla a la derecha. Se comprueban los giros 90°/270° mediante inversión exacta
de píxeles y la verificación del manifiesto de una exportación girada.
La exportación predeterminada queda fijada en 270° horarios y tamaño nativo
1272×1696. Se comprueba que girar físicamente el dispositivo con su parte inferior
hacia la izquierda recupera exactamente el diseño horizontal legible.

## Pendiente o no ejecutado

* GitHub Actions tiene matriz Linux/Python 3.9 y 3.12 con herramientas nativas.
  Este informe registra las pruebas locales; los resultados remotos se consultan
  en la pestaña Actions del repositorio.
* Docker está instalado pero su daemon no está en ejecución; no se reporta una
  ejecución Linux local como aprobada.
* Ninguna prueba de framebuffer, LIPC, RTC, suspensión, arranque, PIN, OTA,
  recuperación o batería fue ejecutada sobre un Kindle.
* Las pruebas del modelo no validan `powerd` ni el binario externo KindleCron.

El protocolo [hardware-validation.md](hardware-validation.md) contiene los criterios
pendientes antes de habilitar la integración o afirmar compatibilidad completa.

## Revisión 0.3.0

28 pruebas locales aprobadas. Las seis nuevas pruebas de la vista previa verifican
render único con tiempo de inspección y redibujado, recuperación tras error de
render, rechazo de checksum incorrecto, rechazo de geometría inesperada, exigencia
de soporte de imágenes y rechazo antes de dibujar si falla el redibujado de la UI.
FBInk y X11 están simulados en estas pruebas; no son resultados de pantalla física.

El diagnóstico de lectura sí se ejecutó en el Kindle y su informe completo se
recuperó por USB. Los hallazgos constan en
[hardware-observations.md](hardware-observations.md). La imagen almacenada en el
dispositivo coincide por SHA-256 con el PNG del repositorio. La prueba visual de
25 segundos y las pruebas de suspensión/RTC permanecen pendientes.
