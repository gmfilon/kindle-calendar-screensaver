# Validación física pendiente

La sonda inicial y la prueba visual desde la biblioteca ya se ejecutaron.
Ver [observaciones de hardware](hardware-observations.md) para su alcance.
Los ensayos que ejecutan jailbreak, cambian pantalla, programan RTC o habilitan arranque requieren aprobación
explícita. Registrar versión del firmware, modelo, hashes de binarios, estado de
anuncios/PIN, reloj, zona, batería y resultado en cada ensayo. No usar serial completo.

## Criterios previos

* Shell funcional, copia de datos personales y recuperación normal conocida.
* No hay otro proyecto que escriba RTC/screensaver durante la prueba.
* Comportamiento stock registrado y restauración de renderizadores ya comprobada.
* Batería suficiente y prueba supervisada para las primeras modificaciones.
* Mantener salida/errores por eventos; un logger de polling puede falsear el consumo.
* En modelos con anuncios, registrar `ad_screensaver`, comprobar que no sobrescribe
  la imagen y que se restaura al detener. Upstream no confirma ese caso en hardware.

## Secuencia y aceptación

| ID | Ensayo | Evidencia para aprobar |
| --- | --- | --- |
| H01 | Sonda de lectura y observación de eventos | ABI, panel, propiedades/eventos y utilidades reales registrados |
| H02 | Una imagen estática apaisada, sin calendario/RTC | Fecha a izquierda y grilla a derecha; PNG girado 270° sin giro extra; apoyo sobre borde largo con botón a izquierda; lector/PIN intactos y reversión stock |
| H03 | Suspensión stock real sin USB | Logs/contadores muestran entrada y salida; imagen estática no es prueba |
| H04 | Alarma breve supervisada desde suspensión | Se despierta sin botón, USB ni red; registrar delta solicitado y latencia |
| H05 | Retorno tras tarea | powerd vuelve a suspender; ningún proceso fuerza Active permanentemente |
| H06 | Calendario durante reposo y desbloqueo concurrente | No dibuja sobre libro/PIN; stock no sobrescribe el calendario |
| H07 | Medianoche Buenos Aires, Wi-Fi apagado, USB retirado | Día anterior antes de 00:00 y nuevo después; despertar y resuspensión registrados |
| H08 | Reboot / salida abrupta / SIGKILL | Restaura Amazon o reinicia una única instancia segura; ninguna pantalla bloqueada |
| H09 | Imagen faltante/corrupta y fallo render | Falla acotada, registra error, restaura stock y permite suspender |
| H10 | Fin de mes/año/bisiesto | Selección correcta con reloj controlado en simulación; no alterar fecha Kindle sin acuerdo |
| H11 | Lectura atravesando medianoche | No interrumpe lectura; al suspender muestra el día actual |
| H12 | Reloj corregido y despertar días después | Recupera fecha actual y reprograma; no reproduce días omitidos |
| H13 | Desinstalación y nuevo reboot | Reposo, lectura, PIN y funcionalidad stock normales |

En H04 medir primero una alarma de pocos minutos, no esperar hasta medianoche
para descubrir que el RTC no funciona. Un retorno 0 de LIPC no aprueba H04.
`readyToSuspend` no garantiza que se haya alcanzado el estado profundo; observar
la transición y el siguiente despertar con instrumentación del dispositivo.
La primera captura debe evitar mantener USB conectado o una sesión interactiva
que impida la suspensión. Definir instrumentación de bajo impacto según H01.
En el PW6 objetivo, las solicitudes de 180 s a `rtcWakeup` y `rtcWakeup2`
devolvieron éxito, pero el reloj no produjo un despertar en ninguna de las
dos pruebas. En la segunda, powerd registró un objetivo a 3589 s al suspender.
Repetir H04 sólo con instrumentación adicional de la selección de alarma o
con un cambio de procedimiento respaldado por evidencia.

El modelo de software no incorpora la latencia física del panel o despertar.
Objetivo inicial: mostrar el nuevo día dentro de 60 s de medianoche sin intervención;
registrar la latencia real y ajustar la anticipación del RTC. El requisito original
de medianoche se considera pendiente hasta demostrarlo, no satisfecho por el margen.

## Autonomía

Comparar al menos 72 h stock y 72 h calendario con condiciones equivalentes:
mismo Wi-Fi apagado, iluminación, temperatura, batería inicial, reposo y uso.
Anotar porcentaje/voltaje al inicio/final, número de despertares, duración activa
y eventos de suspensión. El porcentaje es grueso y no lineal; no inferir mAh exactos.
Si no suspende o despierta reiteradamente, detener y restaurar stock antes de
prolongar la prueba. No prometer una penalización energética hasta medirla.

## Informe mínimo

```text
Ensayo:
Fecha local / UTC:
Modelo y firmware:
Revisiones y SHA-256:
Estado inicial / USB / Wi-Fi / PIN / anuncios:
Acción autorizada:
Alarmas y eventos observados:
Resultado de pantalla / latencia / suspensión:
Lectura normal y reversión:
PASS / FAIL / INCONCLUSO:
Logs adjuntos (sin identificadores personales):
```

Para dar soporte al dispositivo objetivo deben aprobar H01–H13 y una comparación
de autonomía. Sólo después retirar la marca experimental, fijar el perfil del
hardware y publicar un instalador de integración con reversión probada.
