# Viabilidad — Paperwhite 12 / 5.20.1.0.2

Consulta realizada el 6 de noviembre de 2026, hora de Buenos Aires. Investigación
remota y lectura de código primario; ningún Kindle fue conectado o modificado.
Los enlaces `main`, `master` y `latest` pueden cambiar; el registro
[sources.json](sources.json) identifica las revisiones y hashes consultados.

## Conclusión

**Viable como prototipo; integración de bajo consumo aún experimental para esta
combinación exacta.** No existe evidencia obtenida aquí de una solución completa
probada en PW6 / 5.20.1.0.2. El bloqueo real es comprobar el comportamiento físico
de suspensión, despertar y control del screensaver. El desarrollo local puede
avanzar sin resolver ese bloqueo.

| Capacidad | Evidencia | Resultado |
| --- | --- | --- |
| Jailbreak exacto | Selector oficial Véra, entrada PW6 | Soporte declarado para 5.20.1.0.2; no ejecutado |
| Sustitución de reposo | Custom Screensaver: matriz PW6 | Probada por upstream con otros firmwares; pendiente en el objetivo |
| Control de framebuffer | FBInk reconoce PW6/Bellatrix4/MTK | Soporte en código; binario/rotación/refresco por validar |
| Despertar desde suspensión | KindleCron y código powerd | Probado upstream en otros modelos, no en PW6 |
| Calendario y selección offline | Implementación local | Probados; no dependen del dispositivo |
| Autonomía y retorno a suspensión | Requiere medidas físicas | No medidos; no se promete duración de batería |

## Jailbreak

La [guía Véra](https://kindlemodding.org/jailbreaking/Vera/) pide seleccionar modelo
y firmware. El [selector primario](https://github.com/KindleModding/kindlemodding.github.io/blob/e2326a755725a0e034911618160350a02eaf61b7/static/vera/index.html)
incluye expresamente PW6, nombre Paperwhite 12th gen, panel 1272×1696 y versión
5.20.1.0.2. Es evidencia más fuerte que el reporte comunitario citado en el pedido.
No prueba que esta unidad concreta termine el procedimiento sin fallos. La regla
de probar versiones vecinas de la guía sólo cubre otro intervalo: no extrapolarla
al firmware objetivo. Reconfirmar la información del dispositivo antes de actuar.

La [descripción general del proyecto](https://kindlemodding.org/jailbreaking/)
explica que el jailbreak habilita código externo sin sustituir el sistema de
lectura y que no se puede asumir un downgrade sin jailbreak previo. No planificar
un downgrade como recuperación. Toda ejecución de jailbreak queda fuera de esta
entrega y necesita aprobación explícita.

## Pantalla de reposo y FBInk

[Custom Screensaver v0.6.0](https://github.com/chengandre/kindle-custom-screensaver/releases/tag/v0.6.0)
es la referencia preferida para conservar el lector Amazon. Su
[README](https://github.com/chengandre/kindle-custom-screensaver/blob/c73cf75c47c0cc55a31464ce597f0b83a793ee52/README.md)
declara `kindlehf`, firmware desde 5.16.3 y pruebas PW6 en 5.18.6, 5.19.5 y 5.19.6;
no incluye PW6/5.20.1.0.2. El soporte de Colorsoft/5.20.1 no confirma nuestro caso.
Requiere un daemon y auxiliares de pantalla; no arranca automáticamente tras reboot.

Su [daemon](https://github.com/chengandre/kindle-custom-screensaver/blob/c73cf75c47c0cc55a31464ce597f0b83a793ee52/src/scripts/custom_ss_daemon.sh)
escucha eventos de reposo/desbloqueo, deshabilita renderizadores Amazon mediante
helpers, levanta un shield y restaura renderizadores al salir. Por tanto, copiar
un PNG al framebuffer no reproduce su manejo del screensaver. Tampoco basta
copiar 365 imágenes a su carpeta: las rota, no las selecciona por fecha. No se
integra sin resolver primero propiedad de pantalla, PIN y orden de eventos.

[FBInk](https://github.com/NiLuJe/FBInk) maneja imágenes y refrescos E Ink. Su
[identificación de dispositivos](https://github.com/NiLuJe/FBInk/blob/886f25f13368859ad8a899b88d04c26e19cda32e/fbink_device_id.c)
reconoce PW6 como Sangria/Bellatrix4 y MTK. Usar una compilación `kindlehf`
comprobada; no asumir que un binario antiguo o `eips` sirve. FBInk no administra
el reposo Amazon ni resuelve por sí solo las carreras con sus renderizadores.

## powerd, RTC y KindleCron

[KindleCron](https://github.com/lennardollesch/KindleCron) documenta pruebas en KT4
5.13.6 y PW4 5.17.1.0.3. La versión publicada consultada es
[v0.2.0](https://github.com/lennardollesch/KindleCron/releases/tag/v0.2.0).
Su [implementación](https://github.com/lennardollesch/KindleCron/blob/v0.2.0/kron/daemon.go)
escribe `rtcWakeup` de `com.lab126.powerd` durante `readyToSuspend`, atiende eventos
LIPC y mantiene brevemente despierto al equipo mientras hay trabajo. Su daemon
permanece residente, pero no implica CPU permanentemente activa. No es un cron
convencional. El subcomando `setup` crea un enlace en `/usr/bin`: evitarlo y usar
ruta absoluta. No ejecutamos ningún setter ni instalamos su binario.

En PW6 aún hay que confirmar propiedades disponibles, unidades, ventana aceptada,
despertar real desde suspensión, alarmas competidoras y retorno al mismo estado.
Que exista `/dev/rtc` o un setter devuelva éxito no demuestra despertar. No escribir
`/sys/class/rtc/.../wakealarm` ni forzar `/sys/power/state`: podrían competir con
Amazon. El screensaver visible tampoco demuestra suspensión profunda.

## Otras referencias

[Kindle Dynamic Calendar](https://github.com/ikeee/kindle-dynamic-calendar)
documenta PW1/5.6.1.1, `linkss`, KUAL, `eips` y un keeper cron por minuto. Es útil
como referencia del flujo con imágenes precalculadas, pero no es una base
compatible demostrada para PW6. No se adopta su keeper ni su stack legacy.

[KOReader](https://github.com/koreader/koreader) queda fuera del alcance: no se
necesita otro lector para producir imágenes y no hay razón técnica verificada
para instalarlo en esta fase.

## Riesgos y decisiones

| Riesgo | Decisión / prueba necesaria |
| --- | --- |
| Firmware o jailbreak incompatible | Confirmar modelo y versión; no downgrade ni firmware automático |
| Amazon sobrescribe el calendario | Un solo propietario de pantalla; probar eventos, shield y PIN |
| RTC no despierta o alarma es reemplazada | Ensayo breve supervisado, luego medianoche offline sin USB |
| CPU queda despierta | Tareas con timeout; medir suspensión y batería frente a un control |
| Fallo del daemon deja renderizadores apagados | Watchdog por supervisor, restauración probada antes de autostart |
| Pérdida de energía o de estado | Imágenes inmutables, checksum, lock del kernel, fecha del reloj en cada evento |
| RTC pierde la fecha | Detectar fecha fuera de cobertura; corrección manual de reloj si fuera necesario |
| Cambio de reglas de Argentina | Host usa IANA; revisar `ART3` antes de habilitar el runtime |
| Se agotan las imágenes | Generar varios años y documentar cobertura; no mostrar otra fecha como actual |
| Actualización Amazon rompe hooks | Deshabilitar integración antes de actualizar; repetir validación completa |

La copia del almacenamiento de usuario no es una imagen de recuperación del
sistema. No hay aquí un método de rescate de bootloader validado para esta unidad:
eso descarta modificaciones de particiones y experimentos irreversibles.
