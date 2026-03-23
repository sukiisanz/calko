# 🎨 Calko
**Una capa de calco flotante y transparente para artistas digitales.**

Calko es una herramienta open-source y portable diseñada para facilitarte la vida a la hora de dibujar. Te permite cargar una imagen de referencia, hacerla semitransparente y bloquearla por encima de cualquier otro programa (Photoshop, Krita, Procreate, Clip Studio Paint, etc.). 

Una vez bloqueada, **los clics de tu ratón o lápiz pasarán a través de ella**, permitiéndote calcar o usarla como guía de proporciones directamente en tu lienzo.

## ✨ Características principales
* **Fondo 100% transparente:** Solo verás la imagen que vas a calcar o referenciar.
* **Modo Bloqueo (Click-through):** La ventana se vuelve "invisible" al ratón. Puedes dibujar a través de ella.
* **Herramientas integradas:** Control de opacidad, espejo horizontal/vertical, rotación precisa y filtros de color (tintes) para diferenciar la referencia de tu dibujo.
* **Sesiones guardables:** Guarda tu progreso en un archivo `.calko` y retómalo arrastrándolo a la aplicación para mantener exactamente el mismo nivel de zoom, posición y opacidad.
* **Portable:** Sin instalaciones molestas. Descarga, doble clic y a dibujar.

## 🚀 Descarga y Uso (Portable)
No necesitas instalar nada. Ve a la sección de **[Releases](../../releases)** (Lanzamientos) en la derecha de esta página y descarga la última versión para tu sistema operativo (ej. `calko.exe` para Windows).

1. Abre la aplicación.
2. Arrastra una imagen (o usa `Ctrl+O` para abrir desde el ordenador o `Ctrl+V` si tienes la imagen en el portapapeles).
3. Ajusta el tamaño, la posición, la rotación y la opacidad a tu gusto.
4. Pulsa **Tab** para bloquear y desbloquear la ventana.
5. ¡Dibuja en tu programa favorito por debajo de Calko!

> **⚠️ AVISO IMPORTANTE PARA USUARIOS DE WINDOWS (SmartScreen)**
> Como Calko es una herramienta independiente, gratuita y de código abierto (open-source), no cuenta con un "certificado digital de pago". Es muy probable que la primera vez que abras el `.exe`, Windows Defender muestre una pantalla azul diciendo *"Windows protegió su PC"*.
> 
> **Para abrirlo:** Simplemente haz clic en **"Más información"** y luego en el botón **"Ejecutar de todas formas"**. Esto solo te lo pedirá la primera vez.

## ⌨️ Atajos de Teclado
| Acción | Atajo |
| :--- | :--- |
| **Alternar Modo (Edición / Bloqueo)** | `Tab`, `F7`, `F8` |
| **Abrir imagen / sesión** | `Ctrl + O` (O arrastrar al lienzo) |
| **Pegar desde portapapeles** | `Ctrl + V` |
| **Tomar captura de pantalla** | `Ctrl + P` |
| **Guardar sesión actual (`.calko`)** | `Ctrl + S` |
| **Espejo Horizontal / Vertical** | `H` / `V` |
| **Ajustar a ventana / Zoom 100%** | `Ctrl + F` / `Ctrl + 0` |
| **Subir / Bajar opacidad** | `+` / `-` |
| **Cerrar Calko** | `Ctrl + W` |

## 🛠️ Para Desarrolladores (Ejecutar desde el código fuente)
Si prefieres correr Calko directamente desde Python o quieres contribuir al código:

1. Clona este repositorio.
2. Instala las dependencias necesarias:
   ```bash
    pip install PyQt6 qtawesome
3. Ejecuta el script principal:
   python calko.py

🤝 Contribuciones y Feedback
¡Todo feedback es bienvenido! Si encuentras un bug, tienes una idea para una nueva herramienta, o quieres adaptar el código, siéntete libre de abrir un Issue o enviar un Pull Request.
  
