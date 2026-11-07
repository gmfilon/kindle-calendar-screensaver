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
  El tamaño virtual no debe confundirse con el tamaño físico del panel. Falta
  contrastarlo con los datos de inicialización de FBInk durante la prueba visual.
* RTC `/dev/rtc0` presente, controlador `bd71828-rtc`.
* Propiedades de powerd expuestas: `rtcWakeup` (entero, escritura), `rtcWakeup2`
  (cadena, escritura), `abortSuspend` (entero, escritura) y `state` (cadena, lectura).
  Se enumeraron propiedades; todavía no se escribió ninguna alarma.
* `lipc-get-prop`, `lipc-probe`, `lipc-wait-event`, `lipc-set-prop`, `flock`,
  `sha256sum` y `timeout` disponibles.
* FBInk del entorno de jailbreak disponible en `/var/local/kmc/bin/fbink`.
* PNG de prueba recibido íntegro: el SHA-256 del dispositivo coincide con el host.

## Siguiente ensayo preparado

`device/kpm-calendar-preview/launch.sh` usa el FBInk existente para una prueba
manual de 25 segundos, con reserva de ejecución exclusiva y tiempos límite.
Verifica marcador propio, checksum, geometría, capacidad de imágenes de FBInk y
que `xrefresh` funcione antes de dibujar. Al terminar solicita el redibujado de la
interfaz; también lo intenta si falla el render. Guarda el resultado en
`kindle-calendar-check/preview.log`.

No deshabilita renderizadores de Amazon, no altera powerd, no programa RTC y no
instala arranque automático. La imagen de ensayo tiene fecha fija del 6 de
noviembre de 2026: esta prueba mide representación y orientación, no cambio de día.

La prueba visual aún no fue ejecutada. La vista se espera horizontal, con botón
de encendido a la izquierda. Una superposición o un redibujado inmediato de Amazon
se registrarán como un resultado del ensayo, sin deducir compatibilidad completa.

## Pendiente

Representación de PNG y retorno visual a Amazon, reposo con anuncios, carreras al
desbloquear, despertar RTC desde suspensión real, medianoche offline, consumo,
arranque, recuperación y desinstalación de una integración activa. La presencia de
propiedades RTC no demuestra que el hardware despierte en el estado requerido.
