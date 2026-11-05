#!/usr/bin/env python3
"""Build a tailored CV and cover letter (.odt) from a base pair and a JSON spec.

usage: make_application.py <job_id> <spec.json>

Spec keys:
  title                  job title used in the file names: <name> - <title> - CV.odt
  base_cv, base_letter   paths relative to the repo root (the latest approved pair)
  cv       [[snippet, new text], ...]  each snippet must match exactly one paragraph
  letter   {"replace": [[snippet, new text], ...], "body": [paragraphs]}
           body replaces everything from the "Thank you" paragraph up to "Yours sincerely"
           (applied first, so replace snippets only see the base text outside the body)

Only whole paragraphs are replaced. The contact line keeps its hyperlinks because
it is never listed; the script checks both links survive in each output.
"""
import html, json, pathlib, re, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
_PROFILE = json.load(open(ROOT / 'profile' / 'profile.json'))
NAME = _PROFILE['name']
# The email and LinkedIn hyperlinks in the base documents must survive every rewrite.
# profile.json keys: email, linkedin (the URL exactly as it appears in the base .odt).
LINKS = ('mailto:' + _PROFILE['email'], _PROFILE['linkedin'])


def esc(s):
    return html.escape(s, quote=False)


def rewrite(src, dst, fn):
    zin = zipfile.ZipFile(src)
    with zipfile.ZipFile(dst, 'w') as zout:
        for it in zin.infolist():
            d = zin.read(it.filename)
            if it.filename == 'content.xml':
                d = fn(d.decode()).encode()
            ct = zipfile.ZIP_STORED if it.filename == 'mimetype' else it.compress_type
            zout.writestr(it, d, compress_type=ct)


def replace_paras(x, pairs):
    # two passes with placeholders so a new text can never match a later snippet
    for i, (snip, _) in enumerate(pairs):
        pat = re.compile(r'(<text:p [^>]*>)(?:(?!</text:p>).)*?' + re.escape(esc(snip)) + r'(?:(?!</text:p>).)*?</text:p>', re.S)
        n = len(pat.findall(x))
        assert n == 1, f'snippet matched {n} paragraphs: {snip!r}'
        x = pat.sub(lambda m: m.group(1) + f'@@{i}@@</text:p>', x)
    for i, (_, new) in enumerate(pairs):
        x = x.replace(f'@@{i}@@', esc(new))
    return x


def check_links(path):
    x = zipfile.ZipFile(path).read('content.xml').decode()
    for l in LINKS:
        assert f'xlink:href="{l}"' in x, f'{path.name}: missing hyperlink {l}'


def main(job_id, spec_path):
    spec = json.load(open(spec_path))
    out = ROOT / 'applications' / job_id
    out.mkdir(parents=True, exist_ok=True)

    title = spec['title']
    cv_out = out / f'{NAME} - {title} - CV.odt'
    cl_out = out / f'{NAME} - {title} - Cover Letter.odt'
    for p in (cv_out, cl_out):
        if p.exists():
            sys.exit(f'refusing to overwrite {p.name}: the saved copy may hold the user\'s edits')
    rewrite(ROOT / spec['base_cv'], cv_out, lambda x: replace_paras(x, spec['cv']))

    def letter(x):
        start = min(i for i in (x.find(f'<text:p text:style-name="Text_20_body">{k}') for k in ('Thank you', 'I am applying')) if i >= 0)
        end = x.index('<text:p text:style-name="Text_20_body">Yours sincerely')
        body = ''.join(f'<text:p text:style-name="Text_20_body">{esc(b)}</text:p>' for b in spec['letter']['body'])
        x = x[:start] + body + x[end:]
        return replace_paras(x, spec['letter'].get('replace', []))

    rewrite(ROOT / spec['base_letter'], cl_out, letter)
    for p in (cv_out, cl_out):
        check_links(p)
    print('wrote', cv_out.relative_to(ROOT), cl_out.relative_to(ROOT), '(links ok)')


if __name__ == '__main__':
    main(*sys.argv[1:3])
