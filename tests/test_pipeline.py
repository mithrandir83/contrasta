import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import pipeline
from editorial import approve


class PipelineTests(unittest.TestCase):
    def test_overlap_counts_distinct_speakers_and_splits_changes(self):
        rows = [
            dict(start=0, end=5, speaker='a'),
            dict(start=1, end=4, speaker='a'),
            dict(start=2, end=4, speaker='b'),
            dict(start=3, end=5, speaker='c'),
        ]
        self.assertEqual(pipeline.overlap_regions(rows), [
            dict(start=2, end=3, speakers=['a', 'b']),
            dict(start=3, end=4, speakers=['a', 'b', 'c']),
            dict(start=4, end=5, speakers=['a', 'c']),
        ])

    def test_extract_keeps_literal_eligible_quotes_and_deduplicates(self):
        with TemporaryDirectory() as folder, patch.object(pipeline, 'WORK', Path(folder)), patch.object(pipeline, 'client') as client:
            person = pipeline.read(pipeline.ROOT / 'data/debate.json')['participants'][0]
            pipeline.write(Path(folder) / 'interventions.json', [
                dict(id='T1', person=person, start=0, end=1, overlap=True, text='Muestra sintética.'),
            ])
            valid = dict(turn_id='T1', quote='Muestra sintética.', claim='Texto de prueba', topic='Pruebas', type='hecho')
            client.return_value.responses.create.return_value.output_text = json.dumps({
                'claims': [valid, valid, dict(valid, quote='Cadena ausente'), dict(valid, turn_id='T2')]
            })
            pipeline.extract(SimpleNamespace(model='test'))
            rows = pipeline.read(Path(folder) / 'claims.json')
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['status'], 'Pendiente de revisión')
            self.assertTrue(rows[0]['overlap'])
            self.assertEqual(rows[0]['quote'], valid['quote'])


class ApprovalTests(unittest.TestCase):
    def test_approval_requires_confirmation_matching_turn_and_valid_sources(self):
        turn = dict(person='Persona de prueba', start=1, end=2, text='Texto sintético.')
        draft = dict(id='A1', person=turn['person'], start=1, end=2, claim='Prueba',
                     type='hecho', turn_id='T1', topic='Pruebas', quote=turn['text'])
        form = dict(verdict='Evidencia insuficiente', analysis='Texto sintético',
                    reviewed_by='Prueba', reviewed_at='2026-11-27',
                    sources='[{"url":"https://example.org","title":"Prueba"}]')
        with self.assertRaises(ValueError):
            approve(draft, turn, form, [turn['person']])
        form['confirmed'] = 'yes'
        with self.assertRaises(ValueError):
            approve(draft, dict(turn, text='Otra versión'), form, [turn['person']])
        with self.assertRaises(ValueError):
            approve(draft, turn, dict(form, sources='[]'), [turn['person']])
        result = approve(draft, turn, form, [turn['person']])
        self.assertEqual(result['status'], 'Revisada')
        self.assertNotIn('status', draft)
