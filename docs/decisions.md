# Decisiones de ingeniería

1. **Mantener Amazon.** No sustituir firmware ni lector; el cambio sólo debe
   poseer la pantalla durante reposo y devolverla al desbloquear.
2. **Precálculo en host.** Python/Pillow/fuentes en computadora; PNG diarios en
   dispositivo. Sin dependencias de red ni servicios externos en la primera versión.
3. **Energía por eventos.** Favorecer suspensión profunda y RTC. Un daemon bloqueado
   en eventos puede ser necesario: no confundir residente con permanentemente activo.
4. **Un único scheduler.** KindleCron es candidato a validar; no instalar un segundo
   cron, keeper o escritor directo de RTC. Evitar su `setup` sobre `/usr/bin`.
5. **Propiedad de pantalla explícita.** FBInk dibuja, pero no coordina con Amazon.
   La integración necesita un puente sincronizado y reversión de renderizadores.
6. **No suponer compatibilidad.** El soporte declarado del jailbreak exacto no
   acredita pantalla/RTC/autonomía. La entrega actual permanece desactivada.
7. **Fallos acotados y estado derivado.** Tres renders, timeout por comando, lock
   del kernel, checksums y fecha desde reloj. Ningún reintento infinito que quite sueño.
8. **Distribución inicial desde checkout.** Herramientas de desarrollo ejecutadas
   con `PYTHONPATH=src`; no se publica un wheel incompleto ni un instalador privilegiado.
9. **Reversión antes de arranque.** No habilitar servicios persistentes hasta probar
   recuperación de fallos abruptos y stock después de reboot.

Las decisiones 3–5 se revisarán si el diagnóstico real demuestra otro mecanismo
más simple con el mismo nivel de suspensión, conservación del lector y reversión.
