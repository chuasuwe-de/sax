#!/usr/bin/env python3
"""从伴奏识别节拍、小节和和弦，生成逐拍对照表，供写 song.json 时参考。

结果都放在 songs/<曲名>/work/（不进 git）。分四步，用不同的 Python 环境跑
（原因见 tools/README.md）：

  python analyze.py prep   songs/<曲名>     # ffmpeg 转 wav
  python analyze.py beats  songs/<曲名>     # madmom：节拍、强拍、调性、第二套和弦（需要 numpy<2 的环境）
  python analyze.py chords songs/<曲名>     # lv-chordia 和 BTC 两套和弦 + 每个半音的能量
  python analyze.py table  songs/<曲名>     # 合成逐拍对照表 work/table.txt 和 work/beat_table.json

beats 一步可以加 --bpm 100-140 限定速度范围，让小节线更稳。
"""
import sys, os, json, subprocess, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
        'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
PC = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']


def work(folder):
    w = os.path.join(folder, 'work'); os.makedirs(w, exist_ok=True); return w


def prep(folder):
    w = work(folder); src = os.path.join(folder, 'backing.mp3')
    for sr, ch, name in ((44100, 2, 'song_44k.wav'), (22050, 1, 'song_22k.wav')):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', str(ch), '-ar', str(sr), os.path.join(w, name)], check=True)
    print('wav ready in', w)


def beats(folder, bpm):
    import numpy as np
    from madmom.features.downbeats import RNNDownBeatProcessor, DBNDownBeatTrackingProcessor
    from madmom.features.chords import CNNChordFeatureProcessor, CRFChordRecognitionProcessor
    from madmom.features.key import CNNKeyRecognitionProcessor, key_prediction_to_label
    w = work(folder); f = os.path.join(w, 'song_44k.wav')
    act = RNNDownBeatProcessor()(f); np.save(os.path.join(w, 'db_act.npy'), act)
    lo, hi = (int(x) for x in bpm.split('-'))
    res = DBNDownBeatTrackingProcessor(beats_per_bar=[4], fps=100, min_bpm=lo, max_bpm=hi, transition_lambda=100)(act)
    np.save(os.path.join(w, 'db4c.npy'), res)
    downs = res[res[:, 1] == 1, 0]
    print('beats', len(res), 'bars', len(downs), 'bar length median %.3f s (%.1f BPM)' % (np.median(np.diff(downs)), 240 / np.median(np.diff(downs))))
    ch = CRFChordRecognitionProcessor()(CNNChordFeatureProcessor()(f))
    json.dump([[float(a), float(b), str(c)] for a, b, c in ch], open(os.path.join(w, 'mm_chords.json'), 'w'))
    print('key', key_prediction_to_label(CNNKeyRecognitionProcessor()(f)))


def btc_repo():
    """下载 BTC 模型并修好它在新版 numpy / PyYAML 上的两处报错。"""
    repo = os.path.join(HERE, '.cache', 'BTC-ISMIR19')
    if not os.path.isdir(repo):
        os.makedirs(os.path.dirname(repo), exist_ok=True)
        subprocess.run(['git', 'clone', '--depth', '1', 'https://github.com/jayg996/BTC-ISMIR19', repo], check=True)
        hp = os.path.join(repo, 'utils', 'hparams.py'); s = open(hp).read()
        open(hp, 'w').write(s.replace('yaml.load(f)', 'yaml.load(f, Loader=yaml.FullLoader)'))
        tm = os.path.join(repo, 'utils', 'transformer_modules.py'); s = open(tm).read()
        open(tm, 'w').write(s.replace('np.float)', 'float)').replace('np.int)', 'int)'))
    return repo


def chords(folder):
    import numpy as np, librosa, torch
    import torch.nn.functional as F
    w = work(folder)
    # 1) lv-chordia（ISMIR 2019 大词汇量和弦识别）
    with open(os.path.join(w, 'lv.json'), 'w') as out:
        subprocess.run(['lv-chordia', os.path.abspath(os.path.join(w, 'song_44k.wav')), '--chord-dict', 'submission'], stdout=out, check=True)
    # 2) BTC（ChordMini 也用的模型）
    repo = btc_repo(); sys.path.insert(0, repo); cwd = os.getcwd(); os.chdir(repo)
    try:
        from btc_model import BTC_model, HParams
        from utils.mir_eval_modules import audio_file_to_features, idx2voca_chord
        cfg = HParams.load('run_config.yaml'); cfg.feature['large_voca'] = True; cfg.model['num_chords'] = 170
        labels = idx2voca_chord(); model = BTC_model(config=cfg.model)
        ck = torch.load('./test/btc_model_large_voca.pt', map_location='cpu', weights_only=False)
        model.load_state_dict(ck['model']); model.eval()
        feat, tu, _ = audio_file_to_features(os.path.join(cwd, w, 'song_22k.wav') if not os.path.isabs(w) else os.path.join(w, 'song_22k.wav'), cfg)
        feat = (feat.T - ck['mean']) / ck['std']; T = feat.shape[0]; n = cfg.model['timestep']
        feat = np.pad(feat, ((0, n - T % n), (0, 0))); x = torch.tensor(feat, dtype=torch.float32).unsqueeze(0); P = []
        with torch.no_grad():
            for i in range(feat.shape[0] // n):
                h, _ = model.self_attn_layers(x[:, n * i:n * (i + 1), :])
                P.append(F.softmax(model.output_layer.output_projection(h), -1).squeeze(0).numpy())
    finally:
        os.chdir(cwd)
    P = np.concatenate(P)[:T]; np.save(os.path.join(w, 'btc_probs.npy'), P)
    json.dump({'time_unit': tu, 'labels': [labels[i] for i in range(170)]}, open(os.path.join(w, 'btc_chords.json'), 'w'))
    # 3) 每个半音随时间的能量（谐波部分），用来核对低音和和弦音
    y, sr = librosa.load(os.path.join(w, 'song_22k.wav'), sr=22050)
    tun = librosa.estimate_tuning(y=y, sr=sr); yh = librosa.effects.harmonic(y, margin=2.0)
    C = np.abs(librosa.cqt(yh, sr=sr, hop_length=512, fmin=librosa.note_to_hz('C1'), n_bins=252, bins_per_octave=36, tuning=tun))
    S = np.stack([C[max(3 * k - 1, 0):min(3 * k + 2, 252)].sum(0) for k in range(84)])
    np.save(os.path.join(w, 'semitone.npy'), S.astype(np.float32))
    np.save(os.path.join(w, 'semitone_times.npy'), librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=512))
    print('chords done')


def norm(lab):
    if lab in ('N', 'X'): return 'N'
    r, q = (lab.split(':', 1) + ['maj'])[:2] if ':' in lab else (lab, 'maj')
    bass = ''
    if '/' in q: q, bass = q.split('/')
    q = {'maj': '', 'min': 'm', 'min7': 'm7', 'maj7': 'maj7', '7': '7', 'min6': 'm6', 'maj6': '6', 'dim': 'dim', 'aug': 'aug',
         'dim7': 'dim7', 'hdim7': 'm7b5', 'sus2': 'sus2', 'sus4': 'sus4', 'minmaj7': 'mM7', 'maj9': 'maj9', 'min9': 'm9',
         '9': '9', 'sus4(b7)': '7sus4'}.get(q, q)
    return PC[NOTE[r]] + q + (('/' + bass) if bass else '')


def table(folder):
    import numpy as np
    w = work(folder); L = lambda n: os.path.join(w, n)
    lv = json.load(open(L('lv.json'))); btc = json.load(open(L('btc_chords.json'))); P = np.load(L('btc_probs.npy'))
    mm = json.load(open(L('mm_chords.json'))); db = np.load(L('db4c.npy'))
    S = np.load(L('semitone.npy')); times = np.load(L('semitone_times.npy'))
    Sl = np.log1p(5 * S / np.percentile(S, 99)); tu = btc['time_unit']; labels = btc['labels']

    def seg(segs, a, b, key):
        ov = {}
        for s in segs:
            s0, s1, c = key(s); o = min(b, s1) - max(a, s0)
            if o > 0: ov[c] = ov.get(c, 0) + o
        return max(ov, key=ov.get) if ov else 'N'
    rows = []
    for i in range(len(db) - 1):
        a, b = db[i, 0], db[i + 1, 0]
        i0 = int(a / tu); p = P[i0:max(int(np.ceil(b / tu)), i0 + 1)].mean(0)
        j0, j1 = np.searchsorted(times, [a, b]); X = Sl[:, j0:max(j1, j0 + 1)].mean(1)
        bass = np.zeros(12); treb = np.zeros(12)
        for k in range(4, 36): bass[k % 12] += X[k] * (1 if k < 24 else 0.4)
        for k in range(24, 84): treb[k % 12] += X[k]
        rows.append(dict(t=float(a), dur=float(b - a), pos=int(db[i, 1]),
                         lv=norm(seg(lv, a, b, lambda s: (s['start_time'], s['end_time'], s['chord']))),
                         btc=norm(labels[int(p.argmax())]), mm=norm(seg(mm, a, b, lambda s: (s[0], s[1], s[2]))),
                         bass=PC[int(bass.argmax())], treb=(treb / treb.sum()).round(3).tolist()))
    json.dump(rows, open(L('beat_table.json'), 'w'))
    with open(L('table.txt'), 'w') as f:
        bar = 0
        for r in rows:
            if r['pos'] == 1:
                bar += 1; f.write(f"\nbar {bar:3d} {r['t']:7.2f} ")
            f.write(f"[{r['lv']:>7s}|{r['btc']:>6s}|{r['mm']:>3s}|{r['bass']:>2s}]")
    print('wrote', L('table.txt'), '— 每拍四项：lv-chordia | BTC | madmom | 低音')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('step', choices=['prep', 'beats', 'chords', 'table']); ap.add_argument('folder')
    ap.add_argument('--bpm', default='60-200', help='beats 一步的速度范围，比如 100-140')
    a = ap.parse_args()
    {'prep': lambda: prep(a.folder), 'beats': lambda: beats(a.folder, a.bpm), 'chords': lambda: chords(a.folder), 'table': lambda: table(a.folder)}[a.step]()
