# Contrasta

Los datos frente al discurso. MVP para el debate a cuatro del 26 de noviembre de 2026. No contiene todavía verificaciones revisadas ni transcripción real. La web inicial muestra ese estado explícitamente.

## GitHub y Codex

1. Crea un repositorio nuevo `contrasta` en GitHub (público para Pages con GitHub Free, o privado en desarrollo). Descomprime este paquete en la raíz, haz commit y push a `main`.
2. Abre https://chatgpt.com/codex y conecta el repositorio. Las reglas del proyecto están en `AGENTS.md`.
3. En GitHub, Settings → Pages → Build and deployment → Source → GitHub Actions. Ejecuta el workflow `Contrasta · Publicación` desde Actions. La URL aparecerá en el despliegue.
4. Protege `main` si tu plan lo permite y revisa los pull requests. El workflow publica cambios aprobados de `main`; no publica borradores de `data/work`.

## Web local

Node 22 recomendado. `cd web && npm install && npm run dev`. `npm run build` genera `web/dist`. Los datos públicos son descargables desde `datos.json`.

## Pipeline local (requiere prueba de integración)

Python 3.11 recomendado, FFmpeg instalado, GPU CUDA aconsejable. Obtén una copia autorizada del vídeo/audio, no la incluyas en Git. Crea un entorno virtual e instala `requirements.txt`. Acepta las condiciones de acceso de los modelos de diarización de Hugging Face y configura `HF_TOKEN`. Para extracción e investigación configura `OPENAI_API_KEY` y, si quieres, `OPENAI_MODEL` con un modelo que admita Responses y búsqueda web. El uso de API puede generar costes aparte de ChatGPT.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py transcribe /ruta/a/debate.mp4
# Revisar data/work/speakers.pending.json y guardar un mapa confirmado de turnos.
python pipeline.py label data/work/speakers.confirmed.json
python pipeline.py tracks
python pipeline.py extract
python pipeline.py verify
```

`tracks` genera pistas enmascaradas por intervalos, no separación acústica de voces simultáneas. Las zonas superpuestas requieren comprobación. Revisar íntegramente transcripción, etiquetas y posibles omisiones; el etiquetado por nombres es manual.

Los resultados de investigación son provisionales. Para publicar, revisar con el audio y las fuentes originales, documentar análisis y fecha, asignar `status: Revisada`, `reviewed_by`, `reviewed_at` (YYYY-MM-DD) y veredicto. Copiar únicamente las fichas aprobadas a `data/published.json`. Ejecutar `python validate.py` y `python -m unittest discover -s tests`. El validador comprueba estructura, no verdad material. Nunca confiar en él como sustituto de revisión.

Fuente audiovisual: [RTVE Play](https://www.rtve.es/play/videos/especiales-informativos/debate-cuatro-candidatos-elecciones-2026/17333102/). Fuente de contraste: [VerificaRTVE](https://www.rtve.es/noticias/20261126/debate-cuatro-verificacion-datos-elecciones-generales-2026/17330993.shtml). No se incluye contenido audiovisual de terceros.
