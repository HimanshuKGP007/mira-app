"""mira_app/server.py - the browser interface.

    python -m mira_app serve --synthetic     UI demo, no model download
    python -m mira_app serve                 real, downloads the model once
    python -m mira_app serve --bundle out/   real and calibrated

One page. It shows a word, records it, scores it, and builds the report when the
session ends. Deliberately plain: the point of this interface is to put the
measurement chain in front of a person quickly, not to be the product's design.

WHY THE AUDIO IS DECODED SERVER SIDE
------------------------------------
The browser records webm/opus. Rather than depending on ffmpeg, the page decodes
to raw PCM with the Web Audio API and posts float samples as JSON. Slower over
the wire and it removes an install step that breaks on half of all machines.

SESSION STATE IS IN MEMORY AND SINGLE USER. This is a demo server. It has no
authentication, no storage, no consent capture and no access control, and none of
those are optional for anything involving a real patient. Do not put it on a
public address.
"""

import io
import json

import numpy as np

from . import protocol as proto
from . import report as rpt
from . import session as sess

PAGE = """<!doctype html><meta charset=utf-8><title>Mira</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{--ink:#141519;--mut:#6b7280;--line:#e5e7eb;--accent:#3730a3;--bad:#b91c1c;--ok:#0f7b4f}
*{box-sizing:border-box}
body{margin:0;background:#fbfbfc;color:var(--ink);
font:16px/1.5 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:680px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:22px;margin:0 0 2px;letter-spacing:-.02em}
.sub{color:var(--mut);font-size:13px;margin:0 0 20px}
.banner{border:1px solid #b45309;background:#fffbeb;color:#78350f;padding:11px 14px;
border-radius:8px;font-size:13px;margin-bottom:20px}
.stage{background:#fff;border:1px solid var(--line);border-radius:12px;
padding:36px 24px;text-align:center}
.word{font-size:52px;font-weight:600;letter-spacing:-.03em;margin:6px 0 4px}
.phones{font-family:ui-monospace,Menlo,monospace;color:var(--mut);font-size:14px}
.prog{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.08em}
button{font:inherit;font-weight:600;border:0;border-radius:99px;padding:13px 30px;
cursor:pointer;background:var(--accent);color:#fff;margin-top:22px}
button.rec{background:var(--bad)}
button:disabled{background:#d1d5db;cursor:default}
button.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
.hint{color:var(--mut);font-size:13px;margin-top:12px;min-height:20px}
.results{margin-top:20px}
.row{display:flex;gap:10px;align-items:center;background:#fff;border:1px solid var(--line);
border-radius:8px;padding:9px 13px;margin-bottom:6px;font-size:14px}
.row .w{font-weight:600;min-width:82px}
.row .d{color:var(--mut);font-size:13px;flex:1}
.pill{font-size:11px;font-weight:600;padding:1px 8px;border-radius:99px}
.p-ok{background:#dcfce7;color:var(--ok)}.p-err{background:#fee2e2;color:var(--bad)}
.p-held{background:#f3f4f6;color:var(--mut)}
.bar{display:flex;gap:8px;margin-top:18px}
a.dl{display:inline-block;margin-top:16px;color:var(--accent);font-weight:600}
</style>
<div class=wrap>
<h1>Mira</h1><p class=sub id=mode>loading</p>
<div class=banner id=banner></div>
<div class=stage>
  <div class=prog id=prog></div>
  <div class=word id=word>ready</div>
  <div class=phones id=phones></div>
  <button id=btn>Start</button>
  <div class=hint id=hint>Say the word once, clearly, then stop.</div>
</div>
<div class=bar>
  <button class=ghost id=finish disabled>Finish and build report</button>
  <button class=ghost id=reset>Reset</button>
</div>
<div class=results id=results></div>
<div id=link></div>
</div>
<script>
let words=[],i=-1,rec=null,chunks=[],recording=false,results=[],started=false;
const $=x=>document.getElementById(x);

fetch('/api/info').then(r=>r.json()).then(d=>{
  words=d.words;
  $('mode').textContent=d.mode+' mode \\u00b7 '+d.decoder+' \\u00b7 '+d.protocol;
  $('banner').textContent=d.banner;
  if(!d.uncalibrated)$('banner').style.display='none';
});

async function setup(){
  const s=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,
    echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
  rec=new MediaRecorder(s);
  rec.ondataavailable=e=>chunks.push(e.data);
  rec.onstop=async()=>{
    const blob=new Blob(chunks,{type:rec.mimeType});chunks=[];
    const buf=await blob.arrayBuffer();
    const ctx=new (window.AudioContext||window.webkitAudioContext)({sampleRate:16000});
    const dec=await ctx.decodeAudioData(buf);
    const pcm=Array.from(dec.getChannelData(0));
    $('hint').textContent='scoring\\u2026';
    const r=await fetch('/api/score',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({word:words[i],sr:dec.sampleRate,audio:pcm})});
    show(await r.json()); next();
  };
}

function show(r){
  results.push(r);
  const cls=r.status!=='scored'?'p-held':(r.n_errors?'p-err':'p-ok');
  const label=r.status!=='scored'?'held':(r.n_errors?r.n_errors+' to review':'clear');
  const div=document.createElement('div');div.className='row';
  div.innerHTML='<span class=w>'+r.word+'</span>'+
    '<span class="pill '+cls+'">'+label+'</span>'+
    '<span class=d>'+(r.detail||'')+'</span>';
  $('results').prepend(div);
  $('finish').disabled=false;
}

function next(){
  i++;
  if(i>=words.length){$('word').textContent='done';$('phones').textContent='';
    $('btn').disabled=true;$('hint').textContent='Build the report below.';return;}
  $('prog').textContent='item '+(i+1)+' of '+words.length;
  $('word').textContent=words[i];
  fetch('/api/item?word='+words[i]).then(r=>r.json())
    .then(d=>$('phones').textContent=d.phones.join(' \\u00b7 '));
  $('btn').textContent='Record';$('btn').className='';
  $('hint').textContent='Say the word once, clearly, then stop.';
}

$('btn').onclick=async()=>{
  if(!started){await setup();started=true;next();return;}
  if(!recording){chunks=[];rec.start();recording=true;
    $('btn').textContent='Stop';$('btn').className='rec';
    $('hint').textContent='recording\\u2026';}
  else{rec.stop();recording=false;$('btn').disabled=true;
    setTimeout(()=>{$('btn').disabled=false;},400);}
};

$('finish').onclick=async()=>{
  $('finish').disabled=true;$('finish').textContent='building\\u2026';
  const r=await fetch('/api/report',{method:'POST'});const d=await r.json();
  $('link').innerHTML='<a class=dl href="/report" target=_blank>Open the report</a>'+
    '<div class=sub>consonants correct '+d.pcc+'% \\u00b7 '+d.n+' sounds measured</div>';
  $('finish').textContent='Finish and build report';
};
$('reset').onclick=()=>fetch('/api/reset',{method:'POST'}).then(()=>location.reload());
</script>
"""


# A speaker who stops fricatives and glides liquids: the textbook pattern, and
# the one every phonological process table is built to detect. Used only by the
# synthetic decoder in UI-demo mode.
DEMO_SUBSTITUTIONS = {"s": "t", "z": "d", "\u0283": "s", "\u03b8": "t",
                      "\u00f0": "d", "\u0279": "w"}


def build_app(engine):
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse

    app = FastAPI(title="Mira")
    state = {"responses": [], "html": None}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE

    @app.get("/api/info")
    def info():
        r = engine.readiness()
        return {
            "mode": r["mode"], "decoder": r["decoder"],
            "protocol": r["protocol"], "uncalibrated": r["uncalibrated"],
            "words": [w for w, _, _ in proto.WORDS],
            "banner": ("Preview mode. Scores come from an uncalibrated scorer and "
                       "no disordered or child speech was used in building any "
                       "part of this. Not for clinical use."),
        }

    @app.get("/api/item")
    def item(word: str):
        try:
            return proto.get_item(word)
        except KeyError as e:
            return JSONResponse({"error": str(e)}, status_code=404)

    @app.post("/api/score")
    async def score(request: Request):
        body = await request.json()
        audio = np.asarray(body["audio"], dtype=np.float32)
        sr = int(body.get("sr", 16000))
        if sr != 16000:
            # The page asks for 16 kHz and browsers do not always obey. Resample
            # rather than measuring at the wrong rate, which would shift every
            # formant and every duration without any visible symptom.
            n = int(round(audio.size * 16000 / sr))
            audio = np.interp(np.linspace(0, audio.size - 1, n),
                              np.arange(audio.size), audio).astype(np.float32)
            sr = 16000
        # The synthetic decoder fabricates frames from a phone sequence rather
        # than listening, so in UI-demo mode the microphone audio is discarded
        # and a scripted production is used instead. Stated here rather than
        # hidden, because a demo whose numbers look real is worse than no demo.
        if type(engine.decoder).__name__ == "SyntheticDecoder":
            item = proto.get_item(body["word"])
            ipas = [engine.arp_to_ipa[a] for a in item["phones"]]
            engine.decoder.set_production([DEMO_SUBSTITUTIONS.get(i, i)
                                           for i in ipas])

        r = engine.score(audio, sr, body["word"], capture_context="home")
        state["responses"].append(r)

        errs = [p for p in r["phones"]
                if p.get("error_type") not in (None, "correct", "excused")]
        detail = ""
        if r["status"] != "scored":
            detail = r["quality_gate"].get("reason") or "held at the gate"
        elif errs:
            detail = ", ".join(
                f"{p['target']} as {p['produced'] or 'unclear'}" for p in errs[:3])
        return {"word": r["prompt_word"], "status": r["status"],
                "n_errors": len(errs), "detail": detail,
                "n_phones": len(r["phones"])}

    @app.post("/api/report")
    def build_report():
        if not state["responses"]:
            return JSONResponse({"error": "nothing recorded yet"}, status_code=400)
        a = sess.analyse(state["responses"],
                         uncalibrated=engine.readiness()["uncalibrated"])
        n = sess.narrate(a)
        state["html"] = rpt.render(a, n)
        return {"pcc": round(a["accuracy"]["pcc"]["pct"] or 0, 1),
                "n": a["accuracy"]["coverage"]["n"]}

    @app.get("/report", response_class=HTMLResponse)
    def get_report():
        return state["html"] or "<p>No report yet. Record some words first.</p>"

    @app.post("/api/reset")
    def reset():
        state["responses"].clear()
        state["html"] = None
        return {"ok": True}

    return app


def run(host="127.0.0.1", port=8000, bundle=None, synthetic=False):
    from .score import MiraEngine
    if synthetic:
        from .acoustics import SyntheticDecoder, default_vocab_symbols
        print("SYNTHETIC decoder: the UI works, the scores are fabricated from")
        print("the target phones. Use this to look at the interface, nothing else.")
        engine = MiraEngine(SyntheticDecoder(default_vocab_symbols()))
    else:
        from .acoustics import Wav2Vec2Decoder
        print("loading the acoustic model, this downloads about 1 GB the first time")
        b = None
        if bundle:
            from .bundle_loader import load_bundle
            b = load_bundle(bundle)
        engine = MiraEngine(Wav2Vec2Decoder(), bundle=b)

    r = engine.readiness()
    print(f"\nmode: {r['mode']}   decoder: {r['decoder']}")
    if r["uncalibrated"]:
        print("Uncalibrated. Every number this produces is a demonstration.")
    print(f"\n  http://{host}:{port}\n")

    import uvicorn
    uvicorn.run(build_app(engine), host=host, port=port, log_level="warning")
