# Instalación y recuperación por etapas

Estado: generador y staging disponibles. **No hay aún instalador de integración
de pantalla/RTC para PW6/5.20.1.0.2.** El ZIP que produce este repositorio está
desactivado a propósito. Quitar `DISABLED` no implementa el backend ni vuelve
compatible el hardware. No usar este documento como autorización de jailbreak.

## 1. Preparación sin modificar el Kindle

1. Anotar desde Información del dispositivo: modelo completo y firmware exacto.
   Confirmar que Paperwhite 12 de 2024 corresponde a PW6, no a un Basic 2024.
   Anotar si hay anuncios o PIN. No publicar número de serie completo.
2. Mantener Wi-Fi apagado mientras investigamos; no aceptar actualizaciones
   manuales ni intentar bajar firmware. Conservar lectura normal.
3. Copiar documentos personales y archivos visibles a otra ubicación. Si el equipo
   usa MTP en macOS, usar una herramienta MTP que ya funcione, sin asumir que existe
   un volumen `/Volumes/Kindle`. Expulsar/desconectar correctamente.
4. Registrar estado normal: lectura, reposo, PIN, portada/anuncios, reinicio y
   batería. Una copia USB/MTP **no** es un respaldo de particiones ni un rescate.

No conectar ni modificar el dispositivo desde los scripts de este repositorio.

Si muestra anuncios en reposo, la integración de pantalla tiene una incertidumbre
adicional: Custom Screensaver no documenta validación física de `ad_screensaver`.
Mantener modo avión no demuestra que ese renderizador deje de actuar. No quitar
anuncios ni modificar sus componentes como paso implícito de esta instalación.

## 2. Prototipo y paquete en computadora

Desde el checkout completo, seguir los comandos del README. Generar un horizonte
suficiente para funcionar varios años si se desea. Un bundle sólo cubre las fechas
de su manifiesto: no es perpetuo. Para 2028 incluir el 29 de febrero.

```sh
export PYTHONPATH="$PWD/src"
.venv/bin/python -m kindle_calendar generate --start 2026-11-06 --end 2027-12-31 --out build/images
.venv/bin/python -m kindle_calendar verify build/images
.venv/bin/python -m kindle_calendar stage build/images --root build/staging
.venv/bin/python tools/package.py build/staging/kindle-calendar --out dist/kindle-calendar-disabled.zip
```

No regenerar encima de una carpeta existente. Usar otra carpeta para cada versión.
Revisar visualmente los PNG y leer `manifest.json`, `SHA256SUMS` y la suma del ZIP.
Guardar el paquete anterior para revertir. El comando `unstage` elimina únicamente
un staging propio sin modificaciones y conserva los archivos ajenos del padre.

La versión 0.2.0 diseña en apaisado de 1696×1272 y exporta por defecto un PNG nativo
de 1272×1696 girado 270° horarios, para apoyar el Kindle sobre el borde largo con
el botón a la izquierda. Probar primero una sola imagen en esa posición, sin
variantes alternativas. Verificar que el backend no aplique otro giro. No cambiar
la orientación global del lector para conseguir la del screensaver. La vista previa
`preview/landscape.png` muestra cómo se verá al apoyar el dispositivo.

## 3. Jailbreak — requiere aprobación explícita independiente

No automatizado ni ejecutado. Antes de pedir aprobación debe quedar fijado el
procedimiento vigente y la evidencia del modelo/firmware de esta unidad.

El candidato es [Véra](https://kindlemodding.org/jailbreaking/Vera/) a través del
[wizard oficial](https://kindlemodding.org/jailbreak-wizard.html). Confirmar que el
selector ofrece exactamente PW6/5.20.1.0.2. Leer antes la
[introducción oficial](https://kindlemodding.org/jailbreaking/), las instrucciones
vigentes de prevención de OTA y las limitaciones de recuperación. No ejecutar
libros de calibración, libros Véra, hotfixes o scriptlets antes de esa aprobación.
No escoger un firmware vecino si no aparece el exacto.

La guía actual requiere Wi-Fi durante el procedimiento; resolver su protección
frente a actualizaciones siguiendo el procedimiento oficial recién revisado.
No llenar almacenamiento desde nuestras herramientas ni alterar actualizadores.
Después del jailbreak, seguir sólo los pasos post-jailbreak que exija esa versión;
no sumar recetas legacy ni instalar KOReader/KUAL por costumbre.

## 4. Diagnóstico tras el jailbreak aprobado

Con shell ya disponible y autorizado, el único script inicial de este proyecto
sería `device/probe.sh`, de lectura. Copiarlo al almacenamiento de usuario y
ejecutarlo vía shell, guardando la salida en la computadora. Verificar qué canal
de shell proporciona el jailbreak; no abrir SSH a Internet ni instalar una cadena
de utilidades sólo para esta sonda. Un scriptlet visible podría alterar la pantalla
por su propio launcher: usar shell para observar powerd sin ese efecto.

La sonda lee firmware, ABI, framebuffer, presencia de herramientas/RTC y lista de
propiedades de powerd. No escribe RTC ni pide suspensión. Si `lipc-probe` no existe,
registrar la ausencia; no sustituirla con un setter para probar suerte.

Revisar salida antes de compartirla. No basta que aparezca `rtcWakeup`: pasar el
[protocolo físico](hardware-validation.md).

## 5. Dependencias e integración experimental

Orden previsto, cada cambio de pantalla o energía requiere autorización:

1. Fijar y verificar artefactos de Custom Screensaver `v0.6.0` y FBInk para
   `kindlehf`; registrar sus SHA-256. No descargar `latest` a ciegas. Validar
   primero una imagen estática y la reversión con el lector original.
2. Validar el mecanismo RTC de KindleCron `v0.2.0` de forma aislada. Usar su ruta
   absoluta bajo `/mnt/us`, **sin `setup`**, que escribiría en `/usr/bin`.
   No copiar un binario sin confirmar ABI; no repartir binarios de terceros aquí.
3. Implementar el puente de eventos/backend con los contratos de arquitectura y
   pruebas de desbloqueo. Un único hook sincronizado decide la imagen por fecha;
   no colocar todos los calendarios en una carpeta de rotación aleatoria.
4. Conectar un solo trabajo diario, con zona IANA verificada y timeout. Un job
   `every 24h`, un cron de sistema o una variable `TZ` sin comprobar no bastan.
5. Transferir por USB/MTP una nueva carpeta `kindle-calendar` bajo almacenamiento
   de usuario. Verificar tamaño del panel y checksums en destino. El ZIP actual es
   sólo la base desactivada: todavía faltan el perfil de hardware y el backend.
6. Probar manualmente el servicio en primer plano y su restauración. Habilitar
   arranque sólo cuando crash, SIGKILL y reboot restituyan control a Amazon.

Los comandos exactos de inicio/registro del job/autostart se fijarán con el perfil
real. No se entregan placeholders ejecutables que aparenten una instalación lista.
Eso evita instalar dos daemons que compitan por la pantalla o el RTC.

## 6. Actualización, desinstalación y recuperación

Staging local: `python -m kindle_calendar unstage --root build/staging`, con
`PYTHONPATH=src`. Si cambió el contenido, se rechaza la eliminación para no perder
notas ni evidencia. Conservarlo o revisarlo manualmente.

Integración futura en Kindle: deshabilitar primero el job de calendario, detener
el puente restaurando renderizadores y shield, confirmar reposo Amazon, quitar
sólo su entrada de arranque y retirar sólo la carpeta propia. No detener KindleCron
globalmente si otros proyectos lo usan. No cancelar alarmas de Amazon directamente.
Probar el lector antes de retirar dependencias; cada dependencia conserva su
propio procedimiento upstream de desinstalación.

Si sólo está el ZIP desactivado, no hay procesos, alarmas o hooks de este proyecto
que revertir. No se ejecutó aquí una instalación física.

Para actualizar imágenes, generar/verificar nueva versión en computadora, parar
la integración, verificar en destino y cambiar versión de forma atómica sobre el
mismo filesystem. Conservar anterior y revalidar antes de arrancar. Para actualizar
Amazon, primero restaurar comportamiento stock y verificar instrucciones actuales
del jailbreak: puede perderse el acceso. No automatizar actualizaciones de firmware.

Si falla la pantalla: conservar logs, detener integración por el canal ya probado
y restaurar renderizadores. Un reinicio normal puede ser la recuperación si fue
ensayado previamente con upstream; no asumir que revierte cualquier modificación.
No hacer factory reset ni reflashear como primer diagnóstico. Ante pérdida del
canal de control, seguir soporte específico del jailbreak/modelo, sin escrituras
de particiones o bootloader improvisadas.

## Diagnóstico

| Síntoma | Comprobación |
| --- | --- |
| Imagen no cambia al suspender | Backend/hook habilitado y orden de eventos; no basta tener PNG |
| Cambia al presionar botón pero no sola | RTC, suspensión real y supervisión del scheduler |
| Fecha corrida tres horas | Zona del daemon, reloj del sistema y `ART3` del worker |
| Calendario encima del libro | Fallo de propiedad de pantalla: detener integración |
| Batería cae rápido | CPU no suspende, bucle de errores, frecuencia de jobs o shield activo |
| Worker 65 / 66 | Checksum incorrecto / fecha sin imagen; no inventar una fecha fallback |
| Worker 69 / 74 | Backend o herramienta no disponible / tres renders fallidos |
| Worker 75 / 78 | Otra ejecución o cruce de medianoche / instalación desactivada o incompleta |
| Tras reboot vuelve portada Amazon | Comportamiento seguro esperado mientras no hay autostart validado |
