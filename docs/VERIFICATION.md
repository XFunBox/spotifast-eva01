# Validación

La ventana principal en Ubuntu/KDE cargó la paleta EVA-01 y su caché RGBA real; se comprobó la biblioteca en español y el visualizador. La skin tiene 15 hojas BMP con dimensiones idénticas a las del skin integrado de Spotifast, ZIP íntegro y 24 colores de visualizador.

Las pruebas automatizadas Linux cubren conservación de ajustes ajenos, restauración sin deshacer cambios posteriores, reinstalación y cambio de tema, ausencia de escrituras en simulación, rechazo de ajustes inválidos, descarga con hash incorrecto sin cambiar el perfil, copias de recursos homónimos y rutas XDG/con espacios.

La CI ejecuta pruebas en Ubuntu 24.04 y Windows PowerShell 5.1. También instala con descarga real verificada en perfiles temporales y ejecuta `spotifast --version`. El resultado y logs se consultan en la pestaña Actions del repositorio.

Las pruebas no inician sesión en Spotify ni reproducen audio. La reproducción completa y el render del modo compacto en una sesión autenticada Windows no se han comprobado. No se ha compilado el código Rust vendorizado, pues no se ha modificado y el despliegue utiliza los binarios oficiales.

Verificación local del instalador Linux: ocho regresiones aprobadas y despliegue real aislado con descarga oficial, hash correcto, `spotifast 0.13.0` y acceso validado por `desktop-file-validate`. Windows se verifica en el runner de Actions.
