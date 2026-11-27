import unittest
from validate import validate
class TestValidate(unittest.TestCase):
    def test_empty(self): self.assertEqual(validate([],[]),0)
    def test_draft(self):
        with self.assertRaises(ValueError): validate([{'id':'A1','status':'Pendiente'}],[])
    def test_review(self):
        c=dict(id='A1',person='Candidato ficticio',claim='Dato de prueba',quote='Dato de prueba',topic='Pruebas',analysis='Ejemplo sintético',turn_id='T1',reviewed_by='Prueba',reviewed_at='2026-11-27',type='hecho',status='Revisada',verdict='Verdadero',start=1,end=2,sources=[{'url':'https://example.org','title':'Ejemplo'}])
        self.assertEqual(validate([c],[c['person']]),1)
        c['sources'][0]['url']='javascript:alert(1)'
        with self.assertRaises(ValueError): validate([c],[c['person']])
