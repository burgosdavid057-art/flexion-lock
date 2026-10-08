<div align="center">

# FlexionLock

**Tu PC se bloquea cuando llevas demasiado tiempo frente a la pantalla. Para desbloquearlo: flexiones de pecho, contadas por la cámara.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose-0097A7?style=for-the-badge&logo=google&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-only-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![PyInstaller](https://img.shields.io/badge/PyInstaller-.exe-FFD43B?style=for-the-badge)

</div>

---

FlexionLock vive en la bandeja del sistema y mide cuánto tiempo usas el PC de
verdad (no cuenta los ratos sin teclado ni mouse). Cuando pasas el límite de la
sesión o el del día, aparece una pantalla de bloqueo con la cámara encendida y
un contador: haz las flexiones que te pide y el equipo se libera. Cada bloqueo
del día pide más flexiones que el anterior.

## Contenido

- [Características](#características)
- [Cómo funciona](#cómo-funciona)
- [Stack](#stack)
- [Estructura](#estructura)
- [Cómo correrlo](#cómo-correrlo)
- [Advertencias](#advertencias)
- [Autor](#autor)

## Características

- **Ícono en la bandeja** con semáforo: verde (activo), amarillo (quedan 5 minutos
  o menos de sesión, con el tiempo restante en el tooltip) y rojo (bloqueado).
- **Menú de bandeja:** Configuración, Estadísticas, Pausar/Reanudar y Salir.
- **Tiempo activo real:** consulta la última entrada del usuario en Windows cada
  5 s; si llevas más de 60 s sin tocar nada, ese tiempo no cuenta.
- **Dos límites:** por sesión y diario. Cualquiera de los dos dispara el bloqueo.
- **Flexiones progresivas:** `flexiones = base + bloqueos_de_hoy × incremento`.
- **Presets:**

  | Preset | Sesión | Diario | Flexiones base | Incremento |
  |---|---|---|---|---|
  | Suave | 60 min | 3 h | 5 | +3 |
  | Moderado (por defecto) | 45 min | 2 h | 8 | +5 |
  | Duro | 30 min | 1,5 h | 12 | +7 |
  | Personalizado | 1–480 min | 1–1440 min | 1–100 | 0–50 |

- **Detector de flexiones** con MediaPipe Pose + OpenCV: promedia el ángulo de
  ambos codos y cuenta una repetición con la máquina de estados arriba → abajo → arriba.
- **Pantalla de bloqueo** a pantalla completa con el video de la cámara y el
  conteo en vivo; avisa si la cámara no está disponible.
- **Selector de cámara** y opción **"Iniciar con Windows"**.
- **Estadísticas del día:** tiempo activo, número de bloqueos, flexiones totales
  y cuántas pedirá el próximo bloqueo.
  Se reinician solas al cambiar de fecha.

## Cómo funciona

```
UsageTracker (QThread)          cada 5 s: ¿hubo input en el último minuto?
        │  suma tiempo activo → ¿pasó el límite de sesión o diario?
        ▼
TrayApp ── lock_triggered ──►  LockManager.lock()   bloquea teclas y el Administrador de tareas
        │                      LockScreen            pantalla completa + cámara
        │                      PushUpDetector        MediaPipe cuenta flexiones
        ▼
unlock_ready ──► LockManager.unlock() → se reinicia la sesión
```

## Stack

| Pieza | Tecnología |
|---|---|
| Interfaz y bandeja | PyQt6 (`QSystemTrayIcon`, diálogos, pantalla de bloqueo) |
| Visión | OpenCV (captura) + MediaPipe Pose (puntos del cuerpo) |
| Integración con Windows | `ctypes` (hook de teclado de bajo nivel, `GetLastInputInfo`), `winreg`, pywin32 |
| Persistencia | JSON en `data/config.json` y `data/stats.json` |
| Empaquetado | PyInstaller (`build.spec`) + `app.manifest` |
| Pruebas | pytest (en `requirements.txt`) |

## Estructura

```
flexion-lock/
├── main.py              # punto de entrada (pide admin y abre la bandeja)
├── tray_app.py          # TrayApp: bandeja, menú y orquestación de señales
├── usage_tracker.py     # hilo que mide el tiempo activo y dispara los bloqueos
├── lock_manager.py      # hook de teclado, Administrador de tareas, autoarranque
├── pushup_detector.py   # hilo de cámara + MediaPipe que cuenta repeticiones
├── config_manager.py    # presets, config.json y stats.json
├── ui/
│   ├── lock_screen.py   # pantalla de bloqueo con video y contador
│   ├── config_window.py # presets, límites, cámara, inicio con Windows
│   └── stats_window.py  # estadísticas del día
├── assets/              # íconos verde / amarillo / rojo
├── data/                # config y stats (los .json no se versionan)
├── build.spec           # receta de PyInstaller → FlexionLock.exe
├── app.manifest         # pide elevación de administrador
└── requirements.txt
```

## Cómo correrlo

Requiere **Windows**, Python 3.10+ y una cámara web.

```bash
pip install -r requirements.txt
```

```bash
python main.py
```

`main.py` pide permisos de administrador al arrancar (Windows muestra el aviso de
UAC) y deja la app en la bandeja del sistema.

**Generar el ejecutable:**

```bash
pyinstaller build.spec      # → dist/FlexionLock.exe (sin consola, con assets/ y data/)
```

## Advertencias

- **Toca el registro de Windows (HKCU).** Mientras la pantalla está bloqueada
  escribe `DisableTaskMgr = 1` en
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System` y lo borra al
  desbloquear. "Iniciar con Windows" agrega o quita el valor `FlexionLock` en
  `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
- **Bloquea teclas a nivel de sistema** con un hook de teclado de bajo nivel:
  Windows, Esc, Alt+Tab y Alt+F4 dejan de responder mientras dura el bloqueo.
- **Pide permisos de administrador:** el ejecutable empaquetado usa
  `app.manifest` con `requireAdministrator`, así que Windows muestra el aviso de
  UAC al abrirlo.
- Si la app se cierra de forma abrupta en pleno bloqueo, el Administrador de
  tareas puede quedar deshabilitado. Para restaurarlo, borra el valor
  `DisableTaskMgr` de la clave anterior con `regedit`.
- La cámara solo se usa durante el bloqueo y los fotogramas se procesan en
  memoria: no se guarda ni se envía ninguna imagen.

## Autor

**David Burgos** — desarrollador full-stack + IA, Medellín.

- Portafolio: [davidburgos.dev](https://davidburgos.dev)
- GitHub: [@burgosdavid057-art](https://github.com/burgosdavid057-art)
- LinkedIn: [David Burgos](https://www.linkedin.com/in/david-burgos-ab673433a/)
