"""Local editorial review of factual drafts with explicit approval."""
import argparse
import hmac
import hashlib
import io
import json
import math
import secrets
import wave
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from pipeline import ROOT, WORK, read, write
from validate import VERDICTS, validate


def drafts():
    claims_path = WORK / 'claims.json'
    claims = read(claims_path)
    researched = WORK / 'factchecks.json'
    if not researched.exists():
        return claims
    evidence = {row['id']: row for row in read(researched)}
    fields = ('turn_id', 'person', 'start', 'end', 'quote', 'claim', 'type')
    return [
        {**row, 'analysis': proposal['analysis'], 'sources': proposal['sources']}
        if (proposal := evidence.get(row['id'])) and all(row[key] == proposal.get(key) for key in fields)
        else row
        for row in claims
    ]


def draft_version(draft):
    return hashlib.sha256(json.dumps(draft, sort_keys=True).encode()).hexdigest()


def approve(draft, turn, form, people):
    if form.get('confirmed') != 'yes':
        raise ValueError('Confirma el cotejo del audio, la atribución, el contexto y las fuentes.')
    if any(draft[key] != turn[key] for key in ('person', 'start', 'end')) or draft['quote'] not in turn['text']:
        raise ValueError('La ficha ya no coincide con el turno original.')
    row = {
        key: draft[key]
        for key in ('id', 'person', 'claim', 'quote', 'topic', 'turn_id', 'start', 'end', 'type')
    }
    row.update(
        status='Revisada', verdict=form['verdict'], analysis=form['analysis'],
        sources=json.loads(form['sources']), reviewed_by=form['reviewed_by'],
        reviewed_at=form['reviewed_at'],
    )
    validate([row], people)
    return row


def audio_excerpt(path, start, end):
    excerpt = io.BytesIO()
    with wave.open(str(path), 'rb') as source, wave.open(excerpt, 'wb') as output:
        rate = source.getframerate()
        first = round(start * rate)
        last = min(source.getnframes(), round(end * rate))
        if first >= last:
            raise ValueError('Intervalo fuera del audio')
        source.setpos(first)
        output.setparams(source.getparams())
        output.writeframes(source.readframes(last - first))
    return excerpt.getvalue()


def local_handler(port):
    token = secrets.token_urlsafe()
    allowed_host = f'127.0.0.1:{port}'
    people = read(ROOT / 'data/debate.json')['participants']
    target = WORK / 'editorial-approved.json'

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, status=200, content_type='text/html; charset=utf-8'):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; media-src 'self'; form-action 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def check_host(self):
            if self.headers.get('Host') == allowed_host:
                return True
            self.send_error(403)
            return False

        def do_GET(self):
            if not self.check_host():
                return
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            selected = query.get('id', [''])[0]
            rows = drafts()
            draft = next((row for row in rows if row['id'] == selected), None)
            if url.path == '/audio' and draft:
                start, end = draft['start'], draft['end']
                if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end or end - start > 300:
                    self.send_error(400, 'Intervalo no válido')
                    return
                try:
                    clip = audio_excerpt(WORK / 'debate.wav', start, end)
                except (OSError, ValueError, EOFError, wave.Error):
                    self.send_error(404, 'Audio local no disponible')
                else:
                    self.send(clip, content_type='audio/wav')
                return
            if url.path != '/':
                self.send_error(404)
                return
            header = '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Revisión editorial · Contrasta</title><h1>Revisión editorial</h1>'
            if draft is None:
                links = ''.join(
                    f'<li><a href="?{escape(urlencode({"id": row["id"]}))}">{escape(row["person"])} · {escape(row["claim"])}</a></li>'
                    for row in rows if row['type'] == 'hecho'
                )
                self.send(header + (f'<ul>{links}</ul>' if links else '<p>No hay fichas factuales pendientes de cotejo.</p>'))
                return
            if draft['type'] != 'hecho':
                self.send_error(400, 'Solo se aprueban fichas factuales')
                return
            turns = read(WORK / 'interventions.json')
            index = next((i for i, turn in enumerate(turns) if turn['id'] == draft['turn_id']), None)
            if index is None:
                self.send_error(409, 'Turno de origen no disponible')
                return
            context = ''.join(
                f'<li>{escape(turn["person"])} · {turn["start"]:.2f} s · {escape(turn["text"])}</li>'
                for turn in turns[max(0, index - 1):index + 2]
            )
            options = ''.join(f'<option>{escape(v)}</option>' for v in sorted(VERDICTS))
            audio = escape(urlencode({'id': selected}))
            overlap = '<p>Se detectó un solapamiento de voces.</p>' if draft.get('overlap') else ''
            self.send(header + f'''
<p><a href="/">Volver a las fichas</a></p><h2>{escape(draft['claim'])}</h2>
<p>{escape(draft['person'])} · {draft['start']:.2f}–{draft['end']:.2f} s</p>
<blockquote>{escape(draft['quote'])}</blockquote>{overlap}
<audio controls preload="none" src="/audio?{audio}"></audio>
<h3>Turno y contexto de la transcripción</h3><ul>{context}</ul>
<form method="post" action="/">
<input type="hidden" name="token" value="{token}">
<input type="hidden" name="id" value="{escape(selected)}">
<input type="hidden" name="version" value="{draft_version(draft)}">
<p><label>Veredicto <select name="verdict" required><option value="">Selecciona</option>{options}</select></label></p>
<p><label>Análisis<br><textarea name="analysis" required rows="10" cols="65">{escape(draft['analysis'])}</textarea></label></p>
<p><label>Fuentes en JSON (title, url)<br><textarea name="sources" required rows="5" cols="65">{escape(json.dumps(draft['sources'], ensure_ascii=False, indent=2))}</textarea></label></p>
<p><label>Responsable <input name="reviewed_by" required></label>
<label>Fecha <input type="date" name="reviewed_at" required></label></p>
<p><label><input type="checkbox" name="confirmed" value="yes" required> He cotejado el audio, la atribución, el contexto y las fuentes.</label></p>
<button>Guardar aprobación local</button></form>''')

        def do_POST(self):
            if not self.check_host():
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.path != '/' or not 0 < length <= 100_000:
                    self.send_error(400)
                    return
                form = {key: values[0] for key, values in parse_qs(self.rfile.read(length).decode()).items()}
                if not hmac.compare_digest(form.get('token', '').encode(), token.encode()):
                    self.send_error(403)
                    return
                draft = next(row for row in drafts() if row['id'] == form['id'])
                if form['version'] != draft_version(draft):
                    raise ValueError('La ficha cambió. Vuelve a cargarla antes de revisarla.')
                turn = next(row for row in read(WORK / 'interventions.json') if row['id'] == draft['turn_id'])
                row = approve(draft, turn, form, people)
                approved = read(target) if target.exists() else []
                prior = next((item for item in approved if item['id'] == row['id']), None)
                if prior and any(prior[key] != row[key] for key in ('person', 'turn_id', 'quote', 'claim', 'start', 'end')):
                    raise ValueError('El ID ya corresponde a otra ficha aprobada.')
                approved = [item for item in approved if item['id'] != row['id']] + [row]
                validate(approved, people)
                write(target, approved)
            except (ValueError, KeyError, StopIteration, TypeError) as err:
                self.send(f'<p>{escape(str(err) or "Ficha no disponible")}</p><p><a href="/">Volver</a></p>', 400)
                return
            self.send('<p>Aprobación guardada en editorial-approved.json dentro del directorio de trabajo.</p><p><a href="/">Volver</a></p>')

    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not (WORK / 'claims.json').is_file():
        parser.error('Ejecuta primero la extracción de afirmaciones.')
    with HTTPServer(('127.0.0.1', args.port), local_handler(args.port)) as server:
        print(f'Revisión editorial en http://127.0.0.1:{args.port}/', flush=True)
        server.serve_forever()
