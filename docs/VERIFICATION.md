# Validación

La ventana principal en Ubuntu/KDE cargó la paleta EVA-01 y su caché RGBA real; se comprobó la biblioteca en español y el visualizador. La skin tiene 15 hojas BMP con dimensiones idénticas a las del skin integrado de Spotifast, ZIP íntegro y 24 colores de visualizador.

Las pruebas automatizadas Linux cubren conservación de ajustes ajenos, restauración sin deshacer cambios posteriores, reinstalación y cambio de tema, ausencia de escrituras en simulación, rechazo de ajustes inválidos, descarga con hash incorrecto sin cambiar el perfil, copias de recursos homónimos y rutas XDG/con espacios.

La CI ejecuta pruebas en Ubuntu 24.04 y Windows PowerShell 5.1. También instala con descarga real verificada en perfiles temporales y ejecuta `spotifast --version`. El resultado y logs se consultan en la pestaña Actions del repositorio.

Las pruebas no inician sesión en Spotify ni reproducen audio. La reproducción completa y el render del modo compacto en una sesión autenticada Windows no se han comprobado. No se ha compilado el código Rust vendorizado, pues no se ha modificado y el despliegue utiliza los binarios oficiales.

Verificación inicial del instalador Linux (0.13.0): ocho regresiones aprobadas y despliegue real aislado con descarga oficial, hash correcto y acceso validado por `desktop-file-validate`. Windows se verifica en el runner de Actions.

Actualización del 16/10/2026: binario oficial 0.13.3 verificado por SHA256 e instalado en EVA-01 Audio y en el motor extraído de Nightshift. Ambos informan `spotifast 0.13.3`; la configuración permanece idéntica durante la sustitución y se conserva copia de la versión anterior. La consulta local del reproductor funciona después del reinicio. Los 333 archivos del snapshot coinciden con el árbol Git oficial del commit registrado en `eva/release-lock.json`.

Las 15 regresiones locales pasan: ocho del instalador Linux y siete de Nightshift, incluyendo protocolo de estado, comandos serializados, cierre y sliders con teclado. La CI incorpora estas últimas con Qt en modo offscreen. Nightshift se ha abierto en la sesión KDE real; no se automatizan órdenes de reproducción sobre la cuenta personal.
