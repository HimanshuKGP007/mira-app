"""mira_app/report.py - the artefact a person actually reads.

Design rule inherited from the specification: THE TABLES ARE THE REPORT. The
narration is a readability layer on top of them, and deleting it entirely must
still leave something a clinician can read and sign. That is the test of whether
the split between Module 2A and Module 2B is real, and this file is written so
the test passes: the narration appears in one block near the top, and every
figure in it also appears in a table below.

Every non-correct cell carries the timestamps that produced it, so a clinician
can play the two seconds rather than taking the row on trust. That is what makes
a score arguable, and a score nobody can argue with is a score nobody should act
on.
"""

import html
import json
from datetime import datetime, timezone

CSS = """
:root{--ink:#141519;--mut:#6b7280;--line:#e5e7eb;--bg:#fbfbfc;
--ok:#0f7b4f;--warn:#b45309;--bad:#b91c1c;--held:#6b7280;--accent:#3730a3}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:17px;margin:38px 0 12px;letter-spacing:-.01em}
h2 .n{color:var(--mut);font-weight:400;margin-right:8px}
.sub{color:var(--mut);margin:0 0 24px;font-size:14px}
.banner{border:1px solid var(--warn);background:#fffbeb;color:#78350f;
padding:14px 16px;border-radius:8px;margin:0 0 24px;font-size:14px}
.banner b{display:block;margin-bottom:3px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px}
.card .k{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--mut)}
.card .v{font-size:26px;font-weight:600;letter-spacing:-.02em;margin-top:4px}
.card .d{font-size:12px;color:var(--mut);margin-top:2px}
.narr{background:#fff;border-left:3px solid var(--accent);
border-radius:0 8px 8px 0;padding:16px 18px;margin:6px 0 0}
table{width:100%;border-collapse:collapse;background:#fff;
border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
th{text-align:left;font-weight:600;font-size:11px;text-transform:uppercase;
letter-spacing:.06em;color:var(--mut);padding:9px 12px;border-bottom:1px solid var(--line)}
td{padding:8px 12px;border-bottom:1px solid #f3f4f6}
tr:last-child td{border-bottom:0}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.tag{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;
font-weight:600;letter-spacing:.02em}
.t-correct{background:#dcfce7;color:var(--ok)}
.t-substitution,.t-assimilation{background:#fee2e2;color:var(--bad)}
.t-omission,.t-addition{background:#ffedd5;color:var(--warn)}
.t-distortion{background:#fef9c3;color:#854d0e}
.t-held{background:#f3f4f6;color:var(--held)}
.t-excused{background:#e0e7ff;color:var(--accent)}
.note{color:var(--mut);font-size:13px;margin:8px 0 0}
.flag{border:1px solid var(--line);background:#fff;border-radius:8px;
padding:11px 14px;margin-bottom:8px;font-size:14px}
.flag .k{font-size:11px;text-transform:uppercase;letter-spacing:.06em;
color:var(--mut);margin-bottom:3px}
footer{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);
color:var(--mut);font-size:12px}
footer code{font-size:11px}
"""


def _esc(x):
    return html.escape(str(x)) if x is not None else ""


def _tag(t):
    return f'<span class="tag t-{_esc(t)}">{_esc(t)}</span>'


def _pct(r):
    if not r or not r.get("reportable"):
        return "not reportable"
    return f"{r['pct']:.1f}%"


def render(analysis, narration=None, title="Mira speech report"):
    a = analysis
    acc = a["accuracy"]
    out = [f"<!doctype html><meta charset=utf-8><title>{_esc(title)}</title>",
           f"<style>{CSS}</style><div class=wrap>"]

    out.append(f"<h1>{_esc(title)}</h1>")
    out.append(f'<p class=sub>{a["n_items"]} items, {a["n_phonemes"]} sounds. '
               f'Protocol {_esc(a["protocol"]["id"])} '
               f'{_esc(a["protocol"]["version"])}. '
               f'Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.</p>')

    # The limitation cannot be separated from the numbers it limits, so it goes
    # above them rather than in a footnote nobody reaches.
    if a.get("uncalibrated"):
        out.append(
            '<div class=banner><b>Preview mode. Not for clinical use.</b>'
            'These figures come from an uncalibrated preview scorer, not the '
            'validated model. No disordered speech and no child speech has been '
            'used in building any part of this system. The pipeline is shown to '
            'work; the numbers are not evidence of anything about this speaker.'
            '</div>')

    # --- headline figures ---------------------------------------------------
    out.append('<div class=cards>')
    for k, r, d in [("Consonants correct", acc["pcc"], "PCC"),
                    ("Vowels correct", acc["pvc"], "PVC"),
                    ("Coverage", acc["coverage"], "sounds measured")]:
        n = f'{r["n"]} of {r["d"]}' if r.get("reportable") else d
        out.append(f'<div class=card><div class=k>{_esc(k)}</div>'
                   f'<div class=v>{_pct(r)}</div><div class=d>{_esc(n)}</div></div>')
    out.append('</div>')

    # --- narration ----------------------------------------------------------
    if narration and narration.get("use_narrative"):
        out.append('<h2><span class=n>1</span>Summary</h2>')
        out.append(f'<div class=narr>{_esc(narration["text"])}</div>')
        out.append(f'<p class=note>Written by the narration layer, which may only '
                   f'restate figures computed below. '
                   f'{len(narration["kept"])} of '
                   f'{len(narration["kept"]) + len(narration["dropped"])} sentences '
                   f'passed verification.</p>')
    elif narration:
        out.append('<h2><span class=n>1</span>Summary</h2>')
        out.append('<p class=note>The narration layer failed verification and was '
                   'discarded. The tables below are the complete report.</p>')

    # --- flags --------------------------------------------------------------
    if a.get("flags"):
        out.append('<h2><span class=n>2</span>Flags for review</h2>')
        for f in a["flags"]:
            out.append(f'<div class=flag><div class=k>{_esc(f["flag"])} '
                       f'&middot; {_esc(f["severity"])}</div>{_esc(f["text"])}</div>')
        out.append('<p class=note>Every flag is an observation and a request for '
                   'attention. None of them is a finding.</p>')

    # --- error breakdown ----------------------------------------------------
    out.append('<h2><span class=n>3</span>What happened, by sound</h2>')
    out.append('<table><tr><th>Word</th><th>Target</th><th>Produced</th>'
               '<th>Position</th><th>Result</th><th>Score</th><th>Clip</th></tr>')
    for r in a.get("records", []):
        clip = ("" if r.get("start_s") is None else
                f'{r["start_s"]:.2f}&ndash;{r["end_s"]:.2f}s')
        sc = "" if r.get("score") is None else f'{r["score"]:.2f}'
        out.append(
            f'<tr><td>{_esc(r["word"])}</td>'
            f'<td class=mono>{_esc(r["target_arpabet"])}</td>'
            f'<td class=mono>{_esc(r["produced_arpabet"] or "&mdash;")}</td>'
            f'<td>{_esc(r["position"] or "")}</td>'
            f'<td>{_tag(r["error_type"])}</td>'
            f'<td class=mono>{sc}</td><td class=mono>{clip}</td></tr>')
    out.append('</table>')
    out.append('<p class=note>Timestamps are given so any row can be checked '
               'against the recording that produced it.</p>')

    # --- processes ----------------------------------------------------------
    applied = {k: v for k, v in a["processes"].items()
               if isinstance(v, dict) and v.get("reportable")}
    out.append('<h2><span class=n>4</span>Patterns</h2>')
    if applied:
        out.append('<table><tr><th>Pattern</th><th>Rate</th><th>Occurred</th>'
                   '<th>In plain English</th></tr>')
        for k, v in sorted(applied.items(), key=lambda kv: -(kv[1]["n"] or 0)):
            out.append(f'<tr><td>{_esc(k.replace("_", " "))}</td>'
                       f'<td class=mono>{v["pct"]:.0f}%</td>'
                       f'<td class=mono>{v["n"]} of {v["d"]}</td>'
                       f'<td>{_esc(v.get("plain_english", ""))}</td></tr>')
        out.append('</table>')
        out.append('<p class=note>Each rate has its own denominator: the number of '
                   'opportunities that pattern had to occur, not the number of '
                   'sounds in the session.</p>')
    else:
        out.append('<p class=note>No pattern had enough opportunities to be '
                   'reportable.</p>')

    # --- inventory ----------------------------------------------------------
    from . import mira_module2a as m2a
    rows = m2a.grid_to_rows(a["inventory"])
    if rows:
        out.append('<h2><span class=n>5</span>Sound inventory</h2>')
        cols = ["initial", "medial", "final"]
        out.append('<table><tr><th>Sound</th>' +
                   "".join(f"<th>{c}</th>" for c in cols) + '</tr>')
        for r in rows:
            cells = []
            for c in cols:
                cell = r.get(c)
                if not cell or cell in ("not_tested", "-"):
                    cells.append('<td class=mono>&mdash;</td>')
                else:
                    cells.append(f'<td class=mono>{_esc(cell)}</td>')
            out.append(f'<tr><td class=mono>{_esc(r.get("phone", r.get("target")))}'
                       f'</td>' + "".join(cells) + '</tr>')
        out.append('</table>')

    # --- what this report cannot say ----------------------------------------
    out.append('<h2><span class=n>6</span>What this report does not say</h2>')
    out.append('<table><tr><th>Not stated</th><th>Why</th></tr>')
    for k, v in m2a.module2_prohibitions().items():
        out.append(f'<tr><td>{_esc(k.replace("_", " "))}</td><td>{_esc(v)}</td></tr>')
    out.append('</table>')
    out.append('<p class=note>These are structural. The output schema has no field '
               'for a diagnosis, a severity or a plan, and a check refuses any '
               'payload that grows one.</p>')

    out.append('<footer>Mira measures. It does not decide. '
               'Every figure above is produced by ordinary code from the sound '
               'records and can be reproduced by rerunning the same function on '
               'the same input.</footer>')
    out.append('</div>')
    return "\n".join(out)


def save(analysis, path, narration=None, title="Mira speech report"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(analysis, narration, title))
    return path


def save_json(analysis, path, narration=None):
    payload = {"analysis": analysis,
               "narration": None if not narration else
               {k: narration[k] for k in ("use_narrative", "text",
                                          "retained_ratio", "register")}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    return path
