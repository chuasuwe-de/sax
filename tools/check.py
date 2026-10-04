#!/usr/bin/env python3
"""给 song.json 里写好的和弦逐拍打分：三个识别模型的根音 + 低音，一共四票。

用法：python check.py songs/<曲名>
同样几个音、只是名字不同的写法算一致（比如 A7sus4 和 G/A，Em7 和 G6）。
分数低于 0.75 的小节会列出来，逐个回去听。需要先跑完 analyze.py。
"""
import sys, os, json
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
        'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def root(lab):
    if lab == 'N': return None
    return NOTE[lab[:2] if len(lab) > 1 and lab[1] in 'b#' else lab[:1]]


def ok(e, lab):
    r = root(lab)
    if r is None or e.get('r') is None: return r is None and e.get('r') is None
    if r == e['r']: return True
    q = e['q']
    if q in ('m7', 'm7♭5', '7sus4', 'm') and r == (e['r'] + 3) % 12: return True   # Em7=G6, G#m7b5=Bm6
    if q == '7sus4' and r == (e['r'] + 10) % 12: return True                        # A7sus4 ≈ G/A
    if q == '6' and r == (e['r'] + 9) % 12: return True
    return False


def main(folder):
    d = json.load(open(os.path.join(folder, 'song.json')))
    rows = json.load(open(os.path.join(folder, 'work', 'beat_table.json')))
    n, scores, low = 0, [], []
    for sec in d['sections']:
        for bb in sec['bars']:
            n += 1
            bt = d['beats'][n - 1]
            exp = [None] * 4
            for it in bb:
                for k in range(it['beat'] - 1, 4): exp[k] = it
            a = t = 0
            for k, tb in enumerate(bt):
                r = min(rows, key=lambda x: abs(x['t'] - tb))
                if abs(r['t'] - tb) > 0.1: continue
                e = exp[k]; eb = e['b'] if e.get('b') is not None else e.get('r')
                v = [ok(e, r['lv']), ok(e, r['btc']), ok(e, r['mm']), eb is not None and NOTE[r['bass']] == eb]
                a += sum(v); t += 4
            s = a / t if t else 0; scores.append(s)
            if s < 0.75: low.append((n, sec['title'], s))
    good = sum(1 for s in scores if s >= 0.75)
    print(f'{d["title"]}: {good}/{len(scores)} 小节一致（≥0.75），平均 {sum(scores) / len(scores):.3f}')
    for n, title, s in low:
        print(f'  第 {n:3d} 小节（{title}）{s:.2f}')


if __name__ == '__main__':
    main(sys.argv[1])
