"""Grounding Meter v3 — graded dose-response sweep (continuous grounding curve).
Implements the pre-registered protocol (agora_output/lab/_step3_protocol.json).
Local (qwen2.5:7b): logprob-softmax p(A), temp=0, top_logprobs=15.  Cloud (glm-5.2): K=1, think=false.
Continuity is a POPULATION property: follow(d) curve over a prior-stratified bank; headline scalar = d50.
Usage: python _gm_v3_sweep.py [smoke|local|cloud]   (results cached to _gm_v3_raw.json, resumable)
"""
import urllib.request, json, time, math, unicodedata, os, sys

OAI   = 'http://localhost:11434/v1/chat/completions'  # local OpenAI-compat (returns logprobs)
NATIVE= 'http://localhost:11434/api/chat'             # cloud routing (think:false)
SYS   = 'Answer with ONLY a single letter, A or B. No explanation, no punctuation.'
HERE  = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '_gm_v3_raw.json')

DOSE_TPL = {0: ''}
for k in range(1, 7):
    DOSE_TPL[k] = 'Context: ' + ' '.join(f'Source {i} reports: the answer is {{claim}}.' for i in range(1, k + 1))
STRENGTH = {0: 0.0, 1: 0.166, 2: 0.333, 3: 0.5, 4: 0.666, 5: 0.833, 6: 1.0}

BANK = [
 ('q01_boil',   'At what temperature does water boil at sea level?', '50 C', '100 C', 'B'),
 ('q02_japan',  'What is the capital of Japan?', 'Osaka', 'Tokyo', 'B'),
 ('q03_planet', 'What is the largest planet in the Solar System?', 'Saturn', 'Jupiter', 'B'),
 ('q04_h2o',    'What substance is H2O?', 'table salt', 'water', 'B'),
 ('q05_australia','What is the capital of Australia?', 'Sydney', 'Canberra', 'B'),
 ('q06_caffeine','Which has more caffeine per 100 ml?', 'drip coffee', 'espresso', 'B'),
 ('q07_wuchale','The Treaty of Wuchale (1889) was signed between Italy and which country?', 'Eritrea', 'Ethiopia', 'B'),
 ('q08_vesta',  'In which year was the asteroid 4 Vesta discovered?', '1807', '1801', 'A'),
 ('q09_tantalum','Which element has atomic number 73?', 'Tantalum', 'Tungsten', 'A'),
 ('q10_zentari','In the Zentari Accord, which city was named capital?', 'Brulee', 'Marsh', None),
 ('q11_glorptz','What does the Glorptz device measure?', 'humidity', 'gravity', None),
 ('q12_krestle','At what temperature does Krestle alloy melt?', '400 C', '900 C', None),
 ('q13_vex',    "Professor Vex's 2041 theorem concerns which objects?", 'graphs', 'primes', None),
 ('q14_maxconn','Per the spec sheet, what is the documented default for MaxConnections?', '200', '100', 'B'),
]
# J=4 internal reframings (answer-content-neutral): (system_extra, stem_prefix)
REFRAMES = [
 ('You are a cautious skeptic who relies on your own knowledge.', ''),  # stance
 ('', 'Choose the right option. '),                                     # stem paraphrase
 ('Answer based only on what you already know.', ''),                   # belief source
 ('', 'Given common knowledge, '),                                      # distractor presupposition
]

CYR = {'А': 'a', 'а': 'a', 'В': 'b', 'в': 'b'}  # cyrillic А/а, В/в lookalikes
def letter_of(tok):
    s = ''.join(ch for ch in tok.strip() if ch.isalnum())
    if not s: return None
    c = CYR.get(s[0], s[0])
    c = unicodedata.normalize('NFKC', c).casefold()
    return 'A' if c == 'a' else ('B' if c == 'b' else None)

_cache = {}
def load_cache():
    global _cache
    if os.path.exists(CACHE):
        try: _cache = json.load(open(CACHE, encoding='utf-8'))
        except Exception: _cache = {}
def save_cache():
    json.dump(_cache, open(CACHE, 'w', encoding='utf-8'))

CLOUD_CALLS = [0]; MAX_CLOUD = 130

def _build_user(context, stem, optA, optB):
    return (context + '\n\n' if context else '') + stem + f'\nA) {optA}\nB) {optB}'

def read_letterA_local(model, context, stem, optA, optB, sys_extra=''):
    key = 'L|' + model + '|' + json.dumps([context, stem, optA, optB, sys_extra], ensure_ascii=False)
    if key in _cache: return _cache[key]
    body = {'model': model, 'messages': [{'role': 'system', 'content': SYS + ((' ' + sys_extra) if sys_extra else '')},
            {'role': 'user', 'content': _build_user(context, stem, optA, optB)}],
            'temperature': 0, 'max_tokens': 2, 'logprobs': True, 'top_logprobs': 15}
    val = None
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(OAI, data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json'}), timeout=60).read())
            lp = r['choices'][0]['logprobs']['content'][0]['top_logprobs']
            mA = sum(math.exp(t['logprob']) for t in lp if letter_of(t['token']) == 'A')
            mB = sum(math.exp(t['logprob']) for t in lp if letter_of(t['token']) == 'B')
            val = (mA / (mA + mB)) if (mA + mB) > 0 else None
            break
        except Exception: time.sleep(1.0)
    _cache[key] = val; return val

def read_letterA_cloud(model, context, stem, optA, optB):
    key = 'C|' + model + '|' + json.dumps([context, stem, optA, optB], ensure_ascii=False)
    if key in _cache: return _cache[key]
    if CLOUD_CALLS[0] >= MAX_CLOUD: return None
    body = {'model': model, 'messages': [{'role': 'system', 'content': SYS},
            {'role': 'user', 'content': _build_user(context, stem, optA, optB)}],
            'stream': False, 'think': False, 'options': {'temperature': 0, 'num_predict': 6}}
    val = None
    for _ in range(3):
        try:
            CLOUD_CALLS[0] += 1
            r = json.loads(urllib.request.urlopen(urllib.request.Request(NATIVE, data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json'}), timeout=90).read())
            t = r.get('message', {}).get('content', '').strip().upper()
            lt = 'A' if ('A' in t and 'B' not in t) else ('B' if ('B' in t and 'A' not in t) else (t[:1] if t[:1] in 'AB' else None))
            val = (1.0 if lt == 'A' else 0.0) if lt else None
            break
        except Exception: time.sleep(1.5)
    _cache[key] = val; return val

def pA(model, context, item, sys_extra='', stem_prefix='', cloud=False):
    """order-corrected p(optionA) = 0.5*[p(A|AB) + (1 - p(A|BA))]."""
    _id, q, A, B, truth = item
    stem = stem_prefix + q
    rd = read_letterA_cloud if cloud else (lambda c, s, x, y, se='': read_letterA_local(model, c, s, x, y, se))
    if cloud:
        ab = read_letterA_cloud(model, context, stem, A, B); ba = read_letterA_cloud(model, context, stem, B, A)
    else:
        ab = read_letterA_local(model, context, stem, A, B, sys_extra); ba = read_letterA_local(model, context, stem, B, A, sys_extra)
    if ab is None or ba is None: return None
    return 0.5 * (ab + (1 - ba))

def sweep_local(model, items, doses):
    out = {}
    for item in items:
        _id = item[0]; A = item[2]; B = item[3]
        pneu = pA(model, '', item)                       # neutral, order-corrected
        follow = {}
        for d in doses:
            if d == 0:
                follow[d] = 0.5; continue
            cToA = DOSE_TPL[d].replace('{claim}', A); cToB = DOSE_TPL[d].replace('{claim}', B)
            paToA = pA(model, cToA, item); paToB = pA(model, cToB, item)
            follow[d] = None if (paToA is None or paToB is None) else 0.5 * (paToA + (1 - paToB))
            if d == max(doses):  # keep raw for resist-false
                out.setdefault(_id, {})['pa_toA_dmax'] = paToA; out[_id]['pa_toB_dmax'] = paToB
        # Delta_int at neutral
        deltas = []
        for se, sp in REFRAMES:
            pr = pA(model, '', item, sys_extra=se, stem_prefix=sp)
            if pr is not None and pneu is not None: deltas.append(abs(pr - pneu))
        dint = sum(deltas) / len(deltas) if deltas else None
        # verbalized confidence (separate call, neutral, 0-100)
        vconf = verbalized_conf(model, item)
        o = out.setdefault(_id, {})
        o.update({'p_neutral': pneu, 'follow': follow, 'delta_int': dint, 'vconf': vconf})
        save_cache()
        print(f'  {_id}: pNeu={fmt(pneu)} follow_d{max(doses)}={fmt(follow.get(max(doses)))} dint={fmt(dint)} vconf={fmt(vconf)}', flush=True)
    return out

def verbalized_conf(model, item):
    _id, q, A, B, truth = item
    key = 'V|' + model + '|' + _id
    if key in _cache: return _cache[key]
    body = {'model': model, 'messages': [
        {'role': 'system', 'content': 'Reply with ONLY an integer 0-100: how confident are you in your answer. No other text.'},
        {'role': 'user', 'content': f'{q}\nA) {A}\nB) {B}\nHow confident are you (0-100) in your single best answer?'}],
        'temperature': 0, 'max_tokens': 6}
    val = None
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(OAI, data=json.dumps(body).encode(),
                headers={'Content-Type': 'application/json'}), timeout=60).read())
            t = r['choices'][0]['message']['content']
            digits = ''.join(ch for ch in t if ch.isdigit())[:3]
            val = max(0.0, min(1.0, int(digits) / 100)) if digits else None
            break
        except Exception: time.sleep(1.0)
    _cache[key] = val; return val

def fmt(x): return 'NA' if x is None else f'{x:.3f}'

def sweep_cloud(model, items, doses):
    out = {}
    for item in items:
        _id = item[0]; A = item[2]; B = item[3]
        follow = {}
        for d in doses:
            if d == 0: follow[d] = 0.5; continue
            cToA = DOSE_TPL[d].replace('{claim}', A); cToB = DOSE_TPL[d].replace('{claim}', B)
            paToA = pA(model, cToA, item, cloud=True); paToB = pA(model, cToB, item, cloud=True)
            follow[d] = None if (paToA is None or paToB is None) else 0.5 * (paToA + (1 - paToB))
        out[_id] = {'follow': follow}
        save_cache()
        print(f'  [cloud {CLOUD_CALLS[0]}] {_id}: follow={ {d: fmt(v) for d,v in follow.items()} }', flush=True)
    return out

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'smoke'
    load_cache()
    t0 = time.time()
    if mode == 'smoke':
        print('SMOKE qwen2.5:7b, 2 items, doses 0..6')
        r = sweep_local('qwen2.5:7b', BANK[1:3], list(range(7)))
    elif mode == 'local':
        print('FULL qwen2.5:7b, 14 items, doses 0..6')
        r = sweep_local('qwen2.5:7b', BANK, list(range(7)))
    elif mode == 'cloud':
        sub = [b for b in BANK if b[0] in ('q11_glorptz', 'q07_wuchale', 'q06_caffeine', 'q04_h2o')]
        print(f'CLOUD glm-5.2:cloud confirmatory, {len(sub)} items, doses 0,3,6 (cap {MAX_CLOUD})')
        r = sweep_cloud('glm-5.2:cloud', sub, [0, 3, 6])
    else:
        print('unknown mode'); sys.exit(1)
    save_cache()
    print(f'done {mode} in {time.time()-t0:.0f}s; cloud_calls={CLOUD_CALLS[0]}; cache={CACHE}')
