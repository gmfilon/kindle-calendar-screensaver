# Observaciones de la validación física

Perfil: Kindle Paperwhite 12 (PW6), firmware **5.20.1.0.2**. Estos resultados se
separan de la investigación inicial; no implican que pantalla de reposo y RTC ya
funcionen juntos. Los informes completos y los identificadores del dispositivo
se mantienen fuera del repositorio público.

## Confirmado

* Véra ejecutado por el propietario; Jobman funciona y muestra OTA deshabilitado.
* Transferencias MTP verificadas por nombre, tamaño, carpeta y almacenamiento.
  El relleno temporal fue retirado y se confirmó la recuperación del espacio.
* Diagnóstico propio ejecutado mediante `;kpm launch calendar-check`, con informe
  completo recuperado por USB. La entrada de biblioteca no apareció: su causa
  sigue pendiente. KPM ofrece una vía de ejecución comprobada en esta unidad.
* El diagnóstico corre con UID 0. Kernel `5.15.41-lab126`, arquitectura `armv7l`,
  cargador `/lib/ld-linux-armhf.so.3` y firmware exacto confirmados en el dispositivo.
* El proceso de diagnóstico observó un desfase horario `+0000`. El proyecto debe
  aplicar Buenos Aires por proceso; este dato no identifica la zona que muestra
  la interfaz de Amazon ni justifica cambiar globalmente el reloj.
* Framebuffer: `virtual_size=1272,3392`, profundidad de 8 bits, `rotate=0`.
  FBInk confirmó un área visible de 1272×1696.
* RTC `/dev/rtc0` presente, controlador `bd71828-rtc`.
* Propiedades de powerd expuestas: `rtcWakeup` (entero, escritura), `rtcWakeup2`
  (cadena, escritura), `abortSuspend` (entero, escritura) y `state` (cadena, lectura).
  La sonda inicial sólo enumeró propiedades. Los resultados de los ensayos
  posteriores de alarma se describen abajo.
* `lipc-get-prop`, `lipc-probe`, `lipc-wait-event`, `lipc-set-prop`, `flock`,
  `sha256sum` y `timeout` disponibles.
* FBInk del entorno de jailbreak disponible en `/var/local/kmc/bin/fbink`.
* PNG de prueba recibido íntegro: el SHA-256 del dispositivo coincide con el host.

## Prueba visual

El primer ensayo pasó las comprobaciones de geometría y de soporte PNG. El
FBInk 1.25.0 del Kindle terminó con un fallo de segmentación al consultar su
estado con `-e`, antes de dibujar.

`device/kpm-calendar-preview/launch.sh` usa el FBInk existente para una prueba
manual de 25 segundos, con reserva de ejecución exclusiva y tiempos límite.
Verifica marcador propio, checksum, geometría, capacidad de imágenes de FBInk y
que `xrefresh` funcione antes de dibujar. La segunda versión comprueba la
inicialización de FBInk con `-v` y entrada vacía para evitar el volcado de
estado. Al terminar solicita el redibujado de la interfaz y también lo intenta
si falla el render. Guarda el resultado en `kindle-calendar-check/preview-v2.log`.

No deshabilita renderizadores de Amazon, no altera powerd, no programa RTC y no
instala arranque automático. La imagen de ensayo tiene fecha fija del 6 de
noviembre de 2026: esta prueba mide representación y orientación, no cambio de día.

En el segundo ensayo, el usuario confirmó que vio el calendario. El registro
confirmó inicialización, refresco y solicitud de redibujado de Amazon, con
salida 0. El ensayo se hizo con el Kindle activo desde la biblioteca.

El modo `sleep` del mismo lanzador permite probar un único refresco con
la pantalla de reposo puesta. Espera `readyToSuspend` con tiempo límite,
revalida geometría y estado de powerd, dibuja una vez y sale. El sistema
conserva el control de la pantalla. Si el anuncio vuelve a dibujarse, se
registra como resultado del ensayo. El paquete local usa el nombre corto
`cal` y arranca directamente en ese modo.

En el equipo objetivo, `cal` refrescó la pantalla y terminó correctamente.
El usuario vio el calendario unos dos segundos antes de que volviera un
paisaje del sistema. La apariencia del paisaje no identifica el módulo
responsable ni confirma el estado de Special Offers.

El ensayo supervisado `ss` comprueba la lista de módulos de Blanket.
Sólo si aparece `screensaver` y no aparece `ad_screensaver`, pausa el módulo
normal durante una prueba visual y verifica su restitución al despertar o
al terminar la espera. Un marcador temporal permite que una nueva ejecución
recupere el módulo si una interrupción dejó incompleta la restitución.
No arma alarmas ni instala un servicio de arranque.

El ensayo `ss` detectó `screensaver` y no detectó `ad_screensaver` en la
lista de Blanket. Verificó la pausa del módulo, el refresco y la restitución
del módulo al recibir `outOfScreenSaver`. El usuario no vio el calendario y
observó el regreso a la biblioteca. El ensayo no establece qué provocó la
salida del reposo ni qué capa impidió ver la imagen.

El siguiente ensayo, `ss2`, añade durante un ciclo la ventana de protección
de [Custom Screensaver v0.6.0](https://github.com/chengandre/kindle-custom-screensaver/releases/tag/v0.6.0).
El lanzador valida el binario y las dependencias antes de tocar el módulo.
Sólo dibuja después de comprobar que la ventana se abrió, la cierra al
terminar y verifica la restitución de `screensaver`. El binario se obtiene
del ZIP publicado y se copia con su licencia MIT. El repositorio no lo
redistribuye. El ensayo no habilita arranque ni programa el RTC.

En el Kindle objetivo, `ss2` abrió la ventana y el calendario se mantuvo
visible durante el reposo observado. El minuto inicial con la imagen de
Amazon corresponde a la espera de `readyToSuspend` del ensayo. El registro
confirma que el auxiliar terminó al despertar. La primera comprobación de
restitución de `screensaver` falló. El usuario ejecutó el modo de recuperación
y el segundo registro confirmó la restitución, con salida 0.

`ss3` está preparado para probar el refresco al inicio de la pantalla de
reposo, usando `goingToScreenSaver` y verificando el estado antes de dibujar.
Registra la hora del evento y del refresco. La restitución permite un margen
acotado para que Blanket registre el módulo antes de darla por fallida.

`ss3` recibió el evento de entrada. Blanket aún mostraba el módulo justo
después de aceptar la descarga, así que el lanzador abortó antes de dibujar.
Al comenzar la restitución, el módulo ya se había descargado. La
restitución se confirmó en el mismo ensayo. `ss4` espera la confirmación
con un límite tanto al descargar como al recargar el módulo.

Con `ss4`, el refresco terminó cuatro segundos después del evento de entrada.
El usuario confirmó que el calendario se mantuvo visible hasta despertar el
Kindle. El registro confirmó que la ventana se cerró y `screensaver` volvió
a cargarse automáticamente. El ensayo usó la imagen fija.

El siguiente piloto, `day`, elige un PNG por la fecha local de Buenos Aires
al entrar en reposo. Verifica el hash y cancela el refresco si cambia la fecha
durante la preparación de la pantalla. La primera carpeta preparada contiene
14 fechas consecutivas. Sigue siendo un ensayo de un ciclo, sin arranque
automático ni refresco a medianoche.

En el Kindle, `day` leyó la fecha correcta, pero la búsqueda en `SHA256SUMS`
terminó con un fallo de segmentación y el lanzador salió antes de cambiar
Blanket o dibujar. El mismo flujo pasó en una simulación en macOS. Si se
retoma, el primer paso es aislar esa consulta del manifiesto en el shell
del Kindle y comprobar su sustitución con el mismo lote verificado.

## Ensayo de RTC

`device/kpm-calendar-rtc/launch.sh` espera `readyToSuspend` con el Kindle
desconectado y solicita a powerd una sola alarma a 180 segundos. Registra
eventos, tiempos y los contadores de suspensión y RTC que exponga el kernel
en `kindle-calendar-check/rtc-test-v2.log`. Un resultado positivo requiere
evidencia de suspensión y de reanudación en torno al momento de la alarma.
El ensayo no cambia la imagen de reposo ni impide que powerd suspenda.

El primer ensayo recibió `10` como carga del evento `readyToSuspend`. En
modo de un solo evento, `lipc-wait-event` devolvió la carga sin el nombre.
El primer lanzador abortó antes de solicitar la alarma. La segunda versión
espera ese evento por nombre y comprueba `powerd.state` antes de escribir.

El segundo ensayo sí obtuvo éxito al pedir `rtcWakeup 180` en
`readyToSuspend`. El kernel tenía seleccionado `deep` y contabilizó una
suspensión exitosa adicional. El proceso reanudó 423 segundos después del
pedido, con el Kindle activo y un incremento del contador del botón. El
contador de interrupciones del RTC no cambió. En este ensayo el botón
produjo la reanudación y la solicitud de powerd no produjo el despertar
esperado. La compatibilidad del RTC sigue abierta.

El lanzador actual, sin argumentos, recopila registros de energía y atributos
del RTC en `kindle-calendar-check/power-inspection.log`. El modo explícito
`trial` conserva el ensayo de una sola alarma para pruebas supervisadas.

La lectura posterior confirmó que el kernel registró la entrada y la salida
de `deep` durante el segundo ensayo y que `rtc0` está habilitado como fuente
de despertar. La alarma estaba deshabilitada al hacer la lectura posterior.
Ese estado no revela qué quedó programado justo antes de suspender. El
ejecutable de powerd contiene un segundo manejador, `rtcWakeup2`, usado por
una tarea interna de métricas.

La inspección del ejecutable de esta unidad muestra que `rtcWakeup2` recibe
`cliente:segundos` y que ambos manejadores entregan el retraso a la misma
rutina. El modo supervisado `named-trial` usa un identificador propio y la
misma demora de 180 s para comparar ambas rutas. Registra el estado del RTC
antes y después de pedir la alarma y después de reanudar.

En el ensayo con `rtcWakeup2`, la solicitud también devolvió éxito. Sin embargo,
al entrar en suspensión, powerd registró una hora de alarma a 3589 s de ese
momento. El proceso reanudó 536 s después de la solicitud. El contador de
suspensiones profundas pasó de 4 a 5, el contador del botón subió y el contador
del RTC no cambió. El registro del daemon prueba qué hora eligió, pero se emite
antes de escribir al hardware y no prueba que esa alarma futura haya quedado
armada. El ensayo no observó un despertar automático.

## Estado al pausar

Se desactivaron y verificaron los 14 lanzadores de prueba de KPM y el
diagnóstico de la biblioteca. Se conservaron como `launch.sh.disabled` en
las respectivas carpetas de paquetes y `Calendar Diagnostics.sh.disabled`
en `documents`. Permanecen las imágenes de prueba y los diagnósticos.
No se instaló un servicio residente, arranque automático ni un planificador.
El salvapantallas artístico quedó a cargo del sistema.

### Material para retomar

* `device/kpm-calendar-preview/launch.sh` conserva los modos supervisados.
  `quick-sleep` corresponde al ensayo `ss4` y `dated-sleep` al piloto `day`.
  Los lanzadores copiados al equipo fijaban ese modo por defecto.
* Ambos modos usaron `screensaver_shield` de Custom Screensaver v0.6.0, junto
  con su licencia. La procedencia y los hashes están en [sources.json](sources.json).
* `quick-sleep` usa el PNG fijo del 6 de noviembre que está en
  `preview/current`. El piloto `dated-sleep` usa una carpeta `images` junto al
  lanzador, con los PNG y `SHA256SUMS`. El lote se puede regenerar con
  `python -m kindle_calendar generate --start 2026-11-07 --end 2026-11-20 --out build/pilot-images`.
* `device/kpm-calendar-rtc/launch.sh` conserva los ensayos y la inspección de
  energía. Los dos pedidos de alarma registrados no justifican habilitar un
  planificador de producción.

## Pendiente si se retoma

Selección de fecha real en el Kindle, reposo con anuncios, carreras al
desbloquear, despertar RTC desde suspensión real, medianoche offline, consumo,
arranque, recuperación y desinstalación de una integración activa.
