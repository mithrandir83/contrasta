"""Fail closed: only reviewed, fully sourced factual checks go public."""
import json, math, datetime, urllib.parse
from pathlib import Path
VERDICTS={'Verdadero','Mayormente verdadero','Necesita contexto','Mayormente falso','Falso','Evidencia insuficiente'}
ROOT=Path(__file__).resolve().parent
def validate(rows,people):
    if not isinstance(rows,list): raise ValueError('Se esperaba una lista')
    ids=set()
    for c in rows:
        if not isinstance(c, dict): raise ValueError('Ficha inválida')
        for k in ('id','person','claim','quote','topic','analysis','turn_id','reviewed_by','reviewed_at'):
            if not isinstance(c.get(k),str) or not c[k].strip(): raise ValueError(f'Campo obligatorio: {k}')
        if c['id'] in ids: raise ValueError('ID duplicado')
        ids.add(c['id'])
        if c.get('type')!='hecho' or c.get('status')!='Revisada' or c.get('verdict') not in VERDICTS: raise ValueError('Ficha sin revisar o no factual')
        if c['person'] not in people: raise ValueError('Persona desconocida')
        date = datetime.date.fromisoformat(c['reviewed_at'])
        if date.isoformat() != c['reviewed_at']: raise ValueError('Fecha en formato incorrecto')
        times = (c.get('start'), c.get('end'))
        if any(type(t) not in (float, int) or not math.isfinite(t) for t in times) or not 0 <= times[0] < times[1]:
            raise ValueError('Intervalo no válido')
        if not isinstance(c.get('sources'), list) or not c['sources']: raise ValueError('Sin fuentes')
        for s in c['sources']:
            if not isinstance(s, dict) or any(not isinstance(s.get(k), str) or not s[k].strip() for k in ('url', 'title')):
                raise ValueError('Fuente inválida')
            u=urllib.parse.urlsplit(s['url'])
            if u.scheme not in ('http','https') or not u.hostname or not s.get('title'): raise ValueError('Fuente inválida')
    return len(rows)
if __name__=='__main__':
    rows=json.loads((ROOT/'data/published.json').read_text()); people=json.loads((ROOT/'data/debate.json').read_text())['participants']; print(f'{validate(rows,people)} fichas publicables')
