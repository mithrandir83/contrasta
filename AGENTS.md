# Contrasta — instrucciones para Codex

Construir una plataforma no partidista, reproducible y auditable de verificación de afirmaciones públicas en español. No inventar citas, minutos, fuentes ni conclusiones. No optimizar la selección para beneficiar o perjudicar a partidos. Aplicar los mismos criterios a todos los candidatos.

- Python procesa los medios autorizados localmente. Nunca subir audio, vídeo, tokens o archivos de trabajo al repositorio.
- `data/work/` contiene borradores y está excluido de Git. `data/published.json` es la única fuente de fichas públicas. Las afirmaciones necesitan cotejo literal con el audio, atribución y contexto revisados, evidencia verificable, conclusión y fecha de revisión. Nunca marcar como revisada una ficha por iniciativa del agente.
- Conservar marcas de tiempo del archivo original, hash, versiones de herramientas y fuentes. Detectar solapamientos y distinguir diarización de separación acústica. No atribuir nombres automáticamente solo por voz.
- Priorizar INE, Eurostat, BOE, organismos públicos y fuentes primarias. Buscar evidencia favorable y contraria. Diferenciar datos disponibles en la fecha del debate y revisiones posteriores.
- Astro produce una web estática para GitHub Pages; no usar secretos en el frontend. Mantener rutas compatibles con el subdirectorio del repositorio y accesibilidad móvil.
- Ejecutar `python validate.py`, `python -m unittest discover -s tests` y `cd web && npm install && npm run build`. No fusionar PR sin revisar. No publicar datos sin aprobación editorial explícita.
- Próximas tareas: validar compatibilidad de WhisperX y Pyannote en Python 3.11, añadir separación acústica opcional para solapamientos, interfaz local de revisión y trazabilidad de evidencias, pruebas con audio de licencia adecuada, exportación de datos y metodología detallada. Generar lockfile de npm cuando se pueda instalar y fijar dependencias probadas.
