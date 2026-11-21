# Widescreen, ventana y DSR para NFS U2/MW — investigación

**Fecha:** 2026-11-21
**Objetivo:** permitir resoluciones altas, ventana maximizada/borderless para mover entre monitores y aprovechar las resoluciones DSR de NVIDIA en Underground 2 y Most Wanted 2005.

## Conclusión

Sí existe un proyecto que ya resuelve casi todo: **ThirteenAG/WidescreenFixesPack**.

- Fix de **Most Wanted (2005)**: `nfsmw`
- Fix de **Underground 2**: `nfsu2`
- Releases actuales: 2026-11-19.
- Ambos incluyen:
  - Resolución nativa para cualquier modo que reporte el driver, incluyendo ultrawide.
  - Corrección de HUD, FOV y FMVs.
  - **Windowed Mode**: borderless, bordered, resizable o borderless fullscreen.
  - **Skip Intro**.
  - Límite/desbloqueo de FPS.
  - En U2: **NoOpticalDriveFix** (permite arrancar sin unidad óptica).
  - Opciones extra: SMAA, sombras, gamma, cámara con mouse/stick.

No es un fork del servidor ni del cliente online: es un `.asi` independiente que se carga con el ASI Loader que ya tenemos.

## Fuentes

- Release MW: <https://github.com/ThirteenAG/WidescreenFixesPack/releases/tag/nfsmw>
- Release U2: <https://github.com/ThirteenAG/WidescreenFixesPack/releases/tag/nfsu2>
- Repo: <https://github.com/ThirteenAG/WidescreenFixesPack>
- Alternativa MW (no recomendada para esto): <https://github.com/ExOptsTeam/NFSMWExOpts>
- Borderless Gaming (fallback): <https://github.com/Codeusa/Borderless-Gaming>
- DSR en el pack (issue): <https://github.com/ThirteenAG/WidescreenFixesPack/issues/374>
- Mover ventana borderless entre monitores (issue): <https://github.com/ThirteenAG/WidescreenFixesPack/issues/1291>
- PCGamingWiki MW: <https://www.pcgamingwiki.com/wiki/Need_for_Speed:_Most_Wanted>
- PCGamingWiki U2: <https://www.pcgamingwiki.com/wiki/Need_for_Speed:_Underground_2>

## Configuración relevante

### Most Wanted

`scripts/NFSMostWanted.WidescreenFix.ini`:

```ini
[MAIN]
FixHUD = 1
FixFOV = 1
Scaling = 1
HudAspectRatioConstraint = Auto

[MISC]
SkipIntro = 1
WindowedMode = 0   ; 0 = Fullscreen | 1 = Borderless | 2 = Border | 3 = Resizable Border | 4 = Borderless Fullscreen | 5 = Borderless Fullscreen Stretched
```

### Underground 2

`scripts/NFSUnderground2.WidescreenFix.ini`:

```ini
[MAIN]
FixHUD = 1
FixFOV = 1
Scaling = 0
HudAspectRatioConstraint = Auto

[MISC]
SkipIntro = 1
WindowedMode = 0   ; mismos valores que MW
NoOpticalDriveFix = 1
```

No hay una clave `Resolution` en el INI: el fix hace que el juego vea los modos que reporta el driver. La resolución se elige en las opciones de vídeo del juego.

## DSR: qué se puede y qué no

- DSR es una función del driver NVIDIA: el juego renderiza a una resolución mayor y el driver hace downsample a la resolución del monitor.
- Con el Widescreen Fix, las resoluciones DSR deberían aparecer en la lista de opciones de vídeo del juego. Hay reportes de la comunidad usando Widescreen Fix + DSR/VSR en U2 para antialiasing.
- Para que DSR haga downsample, lo normal es usar **pantalla completa** (`WindowedMode = 0`) y elegir la resolución DSR (por ejemplo, 3840x2160 en un monitor 1080p).
- En **ventana/borderless** el juego renderiza al tamaño de la ventana; una ventana 4K no entra en un monitor 1080p y el downsample de DSR no aplica igual. Por eso DSR y “ventana para mover entre monitores” son objetivos que chocan en la práctica.
- Si el modo DSR no aparece, probar:
  1. Activar DSR en NVIDIA Control Panel antes de abrir el juego.
  2. Ejecutar en fullscreen (`WindowedMode=0`).
  3. Reiniciar el juego.
  4. Revisar que el monitor esté en la resolución nativa.

## Modo ventana y multi-monitor

- `WindowedMode = 3` (resizable border) es la opción más segura para mover la ventana entre monitores y maximizarla.
- `WindowedMode = 2` (border) también sirve, pero no es resizable.
- `WindowedMode = 1` (borderless) se ve más moderno, pero el issue #1291 reporta que mover una ventana borderless con `Win+Shift+Left/Right` puede encoger el juego.
- `WindowedMode = 4` (borderless fullscreen) ocupa un monitor; es cómodo para alt-tab, pero no para mover la ventana entre monitores.
- `WindowedMode = 5` es borderless fullscreen estirado; solo si se quiere llenar el monitor sin respetar aspecto.

## Instalación propuesta

1. Descargar el ZIP del release correspondiente.
2. Extraer **solo la carpeta `scripts/`** dentro de la carpeta del juego, al lado de `SPEED2.EXE` / `speed.exe`.
3. **No sobrescribir** el `dinput8.dll` que ya tenemos: nuestro ASI Loader actual carga los `.asi` desde `scripts/`.
4. Configurar el INI:
   - `SkipIntro = 1`
   - `WindowedMode = 3` para la primera prueba multi-monitor.
   - U2: `NoOpticalDriveFix = 1`.
5. Probar:
   - Resolución nativa alta.
   - Ventana maximizada y movimiento entre monitores.
   - DSR en fullscreen con una resolución DSR.
   - Login online y sala, para confirmar que no rompe `net_u2.asi` / `net_mw.asi`.

Si el fix no carga con nuestro loader, usar el `dinput8.dll` del pack (es el mismo Ultimate ASI Loader), respaldando el actual. No usar dos loaders a la vez.

## Compatibilidad con NFS Online

- `net_u2.asi` / `net_mw.asi` parchean red; el Widescreen Fix parchea render/HUD/FOV/ventana. Son responsabilidades distintas y deberían convivir.
- El orden de carga del ASI Loader no debería importar, pero hay que probar login y sala después de instalar.
- No combinar con **NFSMW Extra Options** si ambos tocan resolución/ventana; para este objetivo alcanza con Widescreen Fix.
- Los videos de intro renombrados a `.bak` se pueden restaurar y dejar que `SkipIntro = 1` haga el trabajo. Si el fix no los salta, mantener los `.bak`.

## Plan de prueba

1. Backupear `scripts/` existente en U2/MW y los `.ini` actuales.
2. Instalar Widescreen Fix en U2 y MW.
3. Probar `WindowedMode = 3` a 1920x1080 y mover la ventana entre monitores.
4. Probar `WindowedMode = 1` borderless y comparar.
5. Probar DSR: `WindowedMode = 0`, resolución DSR, verificar que el juego la acepta y que el driver hace downsample.
6. Probar login U2/MW y creación de sala.
7. Documentar resultados y dejar un ZIP/instalador para amigos con la configuración elegida.

## Riesgos

- El fix espera versiones concretas del ejecutable; los repacks pueden no coincidir.
- DSR en ventana/borderless no es equivalente a DSR en fullscreen.
- Un `dinput8.dll` duplicado o incompatible puede impedir que carguen los `.asi`.
- Si el fix y el cliente online parchean la misma zona, podría haber crash; se detecta en la prueba de login.
- Los archivos del fix son binarios de terceros: se guardan fuera del repo, en `NFS-Online-Artifacts`, y se distribuyen con su licencia/atribución si se empaquetan.
