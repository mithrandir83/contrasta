# Contrasta

Plataforma abierta e independiente de verificación del discurso político en español. La versión inicial del sitio presenta el estado de la investigación. Las fichas públicas provienen exclusivamente de `data/published.json`.

## Desarrollo y pruebas

Instala Node 22 y Python 3.11. La web y las pruebas de datos funcionan sin descargar modelos ni configurar credenciales.

```bash
python validate.py
python -m unittest discover -s tests -v
cd web
npm ci
npm run dev
```

Para compilar con la ruta de GitHub Pages, ejecuta `GITHUB_REPOSITORY=mithrandir83/contrasta npm run build` desde `web/`. El HTML y los datos descargables se generan en `web/dist/`.

## Pipeline audiovisual

El lockfile de Python fija dependencias y hashes para CPython 3.11 en Linux x86-64. Instala FFmpeg en el sistema. PyTorch incluye dependencias CUDA en este lockfile. Usa `--cpu` para forzar CPU.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --require-hashes -r requirements-linux-py311.lock
CONTRASTA_MODEL_TEST=1 python -m unittest discover -s tests -v
```

La prueba de compatibilidad usa audio sintético, FFmpeg, TorchCodec y la interfaz de WhisperX con una anotación Pyannote reproducible. La inferencia completa requiere acceso a los pesos de WhisperX y del modelo de alineación, así como a [Pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1). Acepta las condiciones del modelo y proporciona `HF_TOKEN` mediante el entorno. Conserva el medio autorizado fuera del repositorio. El pipeline genera WAV mono a 16 kHz, conserva tiempos relativos al inicio de esa pista y registra el hash del medio original, el modelo y las versiones de las herramientas. En medios editados o con desfase entre las pistas de audio y vídeo, confirma el origen temporal antes de publicar.

```bash
python pipeline.py transcribe /ruta/externa/debate.mp4 --min-speakers 4 --max-speakers 7
# Escucha el audio y guarda un mapa de hablantes confirmado a partir de speakers.pending.json.
python pipeline.py label data/work/speakers.confirmed.json
python pipeline.py tracks
```

Usa un directorio de trabajo nuevo para cada medio. El valor por defecto es `data/work/`. Puedes seleccionar una carpeta externa con `CONTRASTA_WORK_DIR` antes de ejecutar los comandos. La asignación automática produce etiquetas anónimas. Los nombres se incorporan con el mapa humano y las atribuciones dudosas quedan pendientes.

`tracks` enmascara intervalos con la mezcla original. La separación acústica opcional usa [SepFormer WSJ02Mix](https://huggingface.co/speechbrain/sepformer-wsj02mix), un modelo de dos fuentes entrenado con habla en inglés. Ejecuta `python pipeline.py separate --revision SHA_COMPLETO` con una revisión de confianza del modelo. Genera dos estimaciones a 8 kHz por intervalo elegible de dos hablantes, de entre 0,2 y 15 segundos. El manifiesto conserva los límites y las etiquetas detectadas. Los canales carecen de identidad asignada y requieren escucha humana. La inferencia de separación queda pendiente de una prueba con pesos y audio autorizado representativo en español.

## Extracción y revisión editorial

`extract` envía texto de la transcripción y su contexto a la API. `verify` envía las afirmaciones para investigar fuentes. Configura `OPENAI_API_KEY` en el entorno y solo ejecuta estos pasos con permiso para compartir ese texto. Puedes seleccionar el modelo con `OPENAI_MODEL`. El uso de API puede generar costes.

```bash
python pipeline.py extract
python pipeline.py verify
python editorial.py
```

Abre `http://127.0.0.1:8765/` en el mismo equipo. Puedes escuchar el turno, consultar los turnos adyacentes y registrar el análisis, las fuentes, el veredicto y la persona responsable. Contrasta la cita con el audio original y documenta evidencia favorable y contraria. Distingue los datos disponibles en la fecha del debate de sus revisiones posteriores. Las pistas separadas son material auxiliar.

La interfaz guarda las aprobaciones humanamente confirmadas en `editorial-approved.json` dentro del directorio de trabajo. Tras la aprobación editorial explícita, incorpora las fichas aprobadas a `data/published.json` mediante un PR y vuelve a ejecutar el validador. El validador comprueba estructura y campos de revisión. La comprobación factual sigue siendo responsabilidad editorial.

## GitHub Pages

Configura GitHub Actions como origen de Pages. El workflow valida las fichas, ejecuta las pruebas y compila en PR y en `main`. Después de la revisión y la fusión, una persona autorizada puede ejecutar manualmente **Contrasta · Publicación** sobre `main`. El workflow sirve únicamente el artefacto estático. Mantén los medios, credenciales y borradores fuera de Git.
