"""Opt-in compatibility smoke test against the installed model libraries."""
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch


@unittest.skipUnless(os.getenv('CONTRASTA_MODEL_TEST') == '1', 'Requiere el entorno Python del pipeline')
class ModelContractTests(unittest.TestCase):
    def test_whisperx_pyannote_bridge_with_generated_audio(self):
        import torch
        import whisperx
        from pyannote.audio import Pipeline
        from pyannote.core import Annotation, Segment
        from torchcodec.decoders import AudioDecoder
        from whisperx.diarize import DiarizationPipeline

        with TemporaryDirectory() as folder:
            wav = Path(folder) / 'synthetic.wav'
            subprocess.run([
                'ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'lavfi',
                '-i', 'anullsrc=r=16000:cl=mono', '-t', '1', str(wav),
            ], check=True)
            self.assertEqual(AudioDecoder(str(wav)).get_all_samples().data.shape, (1, 16000))
            audio = whisperx.load_audio(str(wav))
        annotation = Annotation()
        annotation[Segment(0, 0.5), 'first'] = 'SPEAKER_00'
        annotation[Segment(0.4, 0.9), 'second'] = 'SPEAKER_01'
        backend = Mock()
        backend.to.return_value = backend
        backend.return_value = SimpleNamespace(speaker_diarization=annotation)
        with patch.object(Pipeline, 'from_pretrained', autospec=True, return_value=backend):
            diarization = DiarizationPipeline(device='cpu')(audio, min_speakers=2, max_speakers=2)
        self.assertEqual(list(diarization.speaker), ['SPEAKER_00', 'SPEAKER_01'])
        self.assertEqual(backend.call_args.args[0]['waveform'].shape, torch.Size([1, 16000]))
        aligned = {'segments': [{'start': 0.55, 'end': 0.8, 'text': 'Prueba',
                                'words': [{'start': 0.55, 'end': 0.8, 'word': 'Prueba'}]}]}
        result = whisperx.assign_word_speakers(diarization, aligned)
        self.assertEqual(result['segments'][0]['words'][0]['speaker'], 'SPEAKER_01')

    def test_separator_keeps_bounds_and_unassigned_channels(self):
        import soundfile
        import torch
        from speechbrain.inference.separation import SepformerSeparation
        from separation import separate_overlaps
        from pipeline import read

        with TemporaryDirectory() as folder:
            work = Path(folder)
            soundfile.write(work / 'debate.wav', torch.zeros(16000).numpy(), 16000)
            model = Mock()
            model.separate_batch.return_value = torch.zeros(1, 4000, 2)
            revision = 'a' * 40
            with patch.object(SepformerSeparation, 'from_hparams', autospec=True, return_value=model) as load:
                separate_overlaps(work, [
                    dict(start=0.25, end=0.75, speakers=['a', 'b']),
                    dict(start=0.75, end=1, speakers=['a', 'b', 'c']),
                ], revision)
            self.assertEqual(load.call_args.kwargs['fetch_config'].revision, revision)
            self.assertEqual(model.separate_batch.call_args.args[0].shape, (1, 4000))
            manifest_path, = (work / 'separation').glob('run-*/manifest.json')
            regions = read(manifest_path)['regions']
            self.assertEqual(regions[0]['start'], 0.25)
            self.assertEqual(len(regions[0]['tracks']), 2)
            self.assertEqual(regions[1]['tracks'], [])
            self.assertEqual(soundfile.info(manifest_path.parent / regions[0]['tracks'][0]).samplerate, 8000)
