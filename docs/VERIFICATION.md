# Validación

La ventana principal en Ubuntu/KDE cargó la paleta EVA-01 y su caché RGBA real; se comprobó la biblioteca en español y el visualizador. La skin tiene 15 hojas BMP con dimensiones idénticas a las del skin integrado de Spotifast, ZIP íntegro y 24 colores de visualizador.

Las pruebas automatizadas Linux cubren conservación de ajustes ajenos, restauración sin deshacer cambios posteriores, reinstalación y cambio de tema, ausencia de escrituras en simulación, rechazo de ajustes inválidos, descarga con hash incorrecto sin cambiar el perfil, copias de recursos homónimos y rutas XDG/con espacios.

La CI ejecuta pruebas en Ubuntu 24.04 y Windows PowerShell 5.1. También instala con descarga real verificada en perfiles temporales y ejecuta `spotifast --version`. El resultado y logs se consultan en la pestaña Actions del repositorio.

Las pruebas no inician sesión en Spotify ni reproducen audio. La reproducción completa y el render del modo compacto en una sesión autenticada Windows no se han comprobado. No se ha compilado el código Rust vendorizado, pues no se ha modificado y el despliegue utiliza los binarios oficiales.

Verificación inicial del instalador Linux (0.13.0): ocho regresiones aprobadas y despliegue real aislado con descarga oficial, hash correcto y acceso validado por `desktop-file-validate`. Windows se verifica en el runner de Actions.

Actualización del 16/10/2026: binario oficial 0.13.3 verificado por SHA256 e instalado en EVA-01 Audio y en el motor extraído de Nightshift. Ambos informan `spotifast 0.13.3`; la configuración permanece idéntica durante la sustitución y se conserva copia de la versión anterior. La consulta local del reproductor funciona después del reinicio. Los 333 archivos del snapshot coinciden con el árbol Git oficial del commit registrado en `eva/release-lock.json`.

Las 15 regresiones locales pasan: ocho del instalador Linux y siete de Nightshift, incluyendo protocolo de estado, comandos serializados, cierre y sliders con teclado. La CI incorpora estas últimas con Qt en modo offscreen. Nightshift se ha abierto en la sesión KDE real; no se automatizan órdenes de reproducción sobre la cuenta personal.


## Actualización 0.14.2 — 28/10/2026

El snapshot de 353 archivos coincide con los blobs y modos del árbol Git oficial `3bc6bb48e2f83e63780e2b0f10b40bda17c5eed5` (v0.14.2). Los cuatro hashes de Linux y Windows x86_64/ARM64 en release-lock.json coinciden con checksums.txt y los digests de la release oficial. Los recursos EVA, los instaladores y el código de Nightshift se conservan.

Ocho regresiones del instalador Linux y siete de Nightshift correctas; Bash y revisión de espacios correctos. La CI verifica Windows PowerShell 5.1 y el binario Windows x86_64 además de Linux. Consultar Actions para el resultado del commit publicado. No se recompila ni modifica el motor Rust oficial incluido.

En KDE real, AppImage y runtime Nightshift 0.14.2 comprobados, con arranque real del reproductor, CLI local y MPRIS. Preferencias y recursos anteriores conservados, sin reproducir música durante la prueba. No se ha probado audio autenticado Windows ni hardware ARM64.
