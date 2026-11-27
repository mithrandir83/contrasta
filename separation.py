"""Produce unassigned two-source estimates for overlapping intervals."""
import re
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path

MODEL = 'speechbrain/sepformer-wsj02mix'
SAMPLE_RATE = 8000
MAX_SECONDS = 15


def separate_overlaps(work, regions, revision):
    from pipeline import write

    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Usa el SHA completo de la revisión del modelo')
    from speechbrain.inference.separation import SepformerSeparation
    from speechbrain.utils.fetching import FetchConfig
    import soundfile
    import torch

    base = work / 'separation'
    base.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='run-', dir=base))
    model = None
    results = []
    for region in regions:
        entry = {**region, 'tracks': []}
        duration = region['end'] - region['start']
        if len(region['speakers']) != 2 or duration > MAX_SECONDS or duration < 0.2:
            entry['status'] = 'Intervalo fuera de los límites del modelo'
        else:
            if model is None:
                model = SepformerSeparation.from_hparams(
                    source=MODEL, fetch_config=FetchConfig(revision=revision),
                    savedir=str(base / revision),
                    run_opts={'device': 'cpu'},
                )
            clip = output / 'input.wav'
            subprocess.run([
                'ffmpeg', '-nostdin', '-loglevel', 'error', '-y',
                '-ss', str(region['start']), '-i', str(work / 'debate.wav'),
                '-t', str(duration), '-ac', '1', '-ar', str(SAMPLE_RATE), str(clip),
            ], check=True)
            audio, sample_rate = soundfile.read(clip, dtype='float32')
            clip.unlink()
            if sample_rate != SAMPLE_RATE or audio.ndim != 1:
                raise ValueError('Se esperaba audio mono a 8 kHz')
            with torch.inference_mode():
                estimated = model.separate_batch(torch.from_numpy(audio).unsqueeze(0)).cpu()
            if not torch.isfinite(estimated).all():
                raise ValueError('La separación devolvió valores no finitos')
            peak = estimated.abs().amax()
            if peak > 1:
                estimated = estimated / peak
            if estimated.ndim != 3 or estimated.shape[0] != 1 or estimated.shape[2] != 2:
                raise ValueError('El modelo no devolvió dos canales de voz')
            for channel in range(2):
                target = output / f'{len(results):05}-{channel + 1}.wav'
                soundfile.write(target, estimated[0, :, channel].numpy(), SAMPLE_RATE)
                entry['tracks'].append(target.name)
            entry['status'] = 'Estimaciones sin atribuir, pendientes de escucha'
        results.append(entry)
    write(output / 'manifest.json', {
        'model': MODEL, 'revision': revision, 'sample_rate': SAMPLE_RATE,
        'speechbrain': version('speechbrain'), 'regions': results,
    })
    print(output / 'manifest.json')
