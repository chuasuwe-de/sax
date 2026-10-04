#!/usr/bin/env python3
"""把 songs/<slug>/song.json 生成和弦谱页面（index.html）和文字谱（chords.md），
再更新首页 index.html 和 README 里的曲目表。

用法：python3 tools/build.py            # 重建所有曲目
      python3 tools/build.py in-my-heart  # 只重建某一首
"""
import json, html, sys, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, 'tools', 'template')
OFF = {'alto': 9, 'concert': 0, 'tenor': 2}
MODES = ('alto', 'concert', 'tenor')
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&family=Bodoni+Moda:ital,wght@1,600&display=swap">'
HEAD = ('<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n')


def mmss(t):
    t = int(t); return '%d:%02d' % (t // 60, t % 60)


def acc(s):
    return s.replace('♯', '<i class="ac">♯</i>').replace('♭', '<i class="ac">♭</i>')


def modal(tag, val, cls=''):
    """val 是字符串（三种调都一样）或 {alto, concert, tenor}。"""
    if not isinstance(val, dict):
        return f'<{tag} class="{cls}">{val}</{tag}>'
    return ''.join(f'<{tag} class="{cls}" data-mode="{m}"{"" if m == "alto" else " hidden"}>{val[m]}</{tag}>' for m in MODES)


class Song:
    def __init__(self, d):
        self.d = d
        self.spell = d['spell']

    def nm(self, pc, mode):
        return self.spell[mode][(pc + OFF[mode]) % 12]

    def inner(self, it, so, mode='alto'):
        if it.get('r') is None:
            return '<span class="r">N.C.</span>'
        h = ''
        if not so:
            h += '<span class="r">' + acc(self.nm(it['r'], mode)) + '</span>'
            if it['q']:
                h += '<span class="q">' + acc(it['q']) + '</span>'
        if it.get('b') is not None:
            h += '<span class="sl">/' + acc(self.nm(it['b'], mode)) + '</span>'
        return h

    def text(self, it, mode):
        if it.get('r') is None:
            return 'N.C.'
        s = self.nm(it['r'], mode) + it['q']
        if it.get('b') is not None:
            s += '/' + self.nm(it['b'], mode)
        return s

    def is_out(self, it, key):
        if it.get('r') is None:
            return False
        return it['q'] not in self.d['diatonic'][key].get(str(it['r']), [])

    def bar_html(self, n, t, items, key, first_in_sys, last_in_sec, sec_title, si,
                 beats=None, extra_cls='', lab=None, caption=None):
        spans = [(items[i + 1]['beat'] if i + 1 < len(items) else 5) - it['beat'] for i, it in enumerate(items)]
        multi = len(items) > 1
        chs, prev = [], None
        for ii, it in enumerate(items):
            so = (prev is not None and it.get('r') is not None and prev.get('r') == it['r']
                  and prev.get('q') == it['q'] and it.get('b') is not None)
            cls = 'ch' + (' out' if self.is_out(it, key) else '') + (' unsure' if isinstance(n, int) and n in self.unsure else '')
            if it.get('r') is None:
                attrs = 'data-nc=""'
            else:
                attrs = f'data-r="{it["r"]}" data-q="{html.escape(it["q"])}"'
                if it.get('b') is not None:
                    attrs += f' data-b="{it["b"]}"'
            if so:
                attrs += ' data-so=""'
            ct = beats[it['beat'] - 1] if beats else t
            attrs += f' data-t="{ct:.2f}"'
            if multi:
                attrs += f' style="min-width:{spans[ii] * 25}%"'
            chs.append(f'<span class="{cls}" {attrs}>{self.inner(it, so)}</span>')
            prev = it
        lbl = ''
        if first_in_sys:
            lbl = f'<span class="lbl"><span>{n if isinstance(n, int) else ""}</span><span>{mmss(t)}</span></span>'
        cap = f'<span class="cap">{caption}</span>' if caption else ''
        cls = 'bar' + (' end' if last_in_sec else '') + (' ' + extra_cls if extra_cls else '')
        labtxt = lab or f'第 {n} 小节'
        bt = (' data-beats="' + ','.join(f'{x:.2f}' for x in beats) + '"') if beats else ''
        style = (' style="grid-template-columns:' + ' '.join(f'{s}fr' for s in spans) + '"') if multi else ''
        return (f'<button class="{cls}" type="button" data-t="{t:.2f}" data-si="{si}"{bt} data-sec="{sec_title}" '
                f'data-lab="{labtxt}" aria-label="从{labtxt}开始播放，{mmss(t)}">{lbl}'
                f'<span class="chs{" multi" if multi else ""}"{style}>{"".join(chs)}</span>{cap}</button>')

    def special_section(self, sec, si):
        cells = []
        for i, c in enumerate(sec['cells']):
            item = c.get('chord') or {'r': None, 'q': '', 'b': None}
            item = {'beat': 1, **item}
            cells.append(self.bar_html(c.get('id', f'x{si}_{i}'), c['t'], [item], sec.get('key', self.d['home_key']),
                                       True, i == len(sec['cells']) - 1, sec['title'], si,
                                       extra_cls='wide', lab=c['lab'], caption=c.get('caption')))
        sub = modal('span', sec['sub'], 'sub') if sec.get('sub') else ''
        when = sec.get('when') or mmss(sec['cells'][0]['t'])
        return (f'<section class="sec" id="s{si}"><header class="sec-h"><span class="mark">{sec["mark"]}</span>'
                f'<h2>{sec["title"]}</h2>{sub}<span class="when">{when}</span></header><div class="sys">{"".join(cells)}</div></section>',
                f'<a class="chip" href="#s{si}"><b>{sec["mark"]}</b>{mmss(sec["cells"][0]["t"])}</a>')

    def page(self):
        d = self.d
        self.unsure = set(d.get('unsure', []))
        downs, beats = d['downbeats'], d['beats']
        sec_html, chips, si, n = [], [], 0, 0
        for sec in d.get('pre', []):
            h, c = self.special_section(sec, si); sec_html.append(h); chips.append(c); si += 1
        for sec in d['sections']:
            start, t0 = n + 1, downs[n]
            bars = []
            for bi, bb in enumerate(sec['bars']):
                n += 1
                bars.append(self.bar_html(n, downs[n - 1], bb, sec['key'], bi % 4 == 0, bi == len(sec['bars']) - 1,
                                          sec['title'], si, beats=beats[n - 1]))
            sub = modal('span', sec['sub'], 'sub') if sec.get('sub') else ''
            sec_html.append(f'<section class="sec" id="s{si}"><header class="sec-h"><span class="mark">{sec["mark"]}</span>'
                            f'<h2>{sec["title"]}</h2>{sub}<span class="when">{mmss(t0)} · 第 {start}–{n} 小节</span></header>'
                            f'<div class="sys">{"".join(bars)}</div></section>')
            note = f' <i>{sec["chip_note"]}</i>' if sec.get('chip_note') else ''
            chips.append(f'<a class="chip" href="#s{si}"><b>{sec["mark"]}</b>{mmss(t0)}{note}</a>')
            si += 1
        for sec in d.get('post', []):
            h, c = self.special_section(sec, si); sec_html.append(h); chips.append(c); si += 1
        self.nbars = n
        css = open(os.path.join(TPL, 'page.css')).read()
        js = open(os.path.join(TPL, 'page.js')).read()
        song_js = json.dumps({'slug': d['slug'], 'spell': self.spell}, ensure_ascii=False)
        dur = d['duration']
        notes = d['notes_html'].replace('{NBARS}', str(n))
        return f'''<title>{d["title"]} 和弦谱</title>
{FONTS}
<style>{css}</style>
<div class="wrap">
<header>
<p class="eyebrow"><a href="../../index.html" class="home">萨克斯自练</a> · 和弦谱 · 从伴奏音频识别</p>
<h1>{d["title"]}</h1>
<p class="meta">{modal("span", d["key_label"])} · <span class="tempo">{d["tempo_text"]} · {mmss(dur)}</span></p>
<p class="seg-title" id="seg-title">按哪种乐器看谱</p>
<div class="seg" role="radiogroup" aria-labelledby="seg-title">
<input type="radio" name="keymode" id="k-alto" value="alto" checked><label for="k-alto">E♭ 乐器<small>中音 / 上低音</small></label>
<input type="radio" name="keymode" id="k-concert" value="concert"><label for="k-concert">实际音高<small>钢琴 / 吉他</small></label>
<input type="radio" name="keymode" id="k-tenor" value="tenor"><label for="k-tenor">B♭ 乐器<small>次中音 / 高音</small></label>
</div>
</header>
<nav class="form" aria-labelledby="form-h">
<h2 id="form-h">曲式</h2>
<p>{d["form_html"]}</p>
<div class="chips">{"".join(chips)}</div>
</nav>
<p class="how">伴奏已经放在页面里了。按底部的播放键，谱子会跟着走：当前小节变蓝，底部大字是现在的和弦和下一个和弦，圆点是第几拍。点任意一格就从那一小节开始放。<span class="brass">棕色</span>的和弦不在当前调里，音阶要改音（见文末）；带 ? 的和弦把握较低。</p>
<main class="chart">{"".join(sec_html)}</main>
<section class="notes">
{notes}
</section>
</div>
<div class="player" id="player"><div class="pl-in"><div class="now-row"><div class="now-ch" id="nowCh"></div><div class="next"><span class="k">下一个</span><span class="nc" id="nextCh"></span></div><div class="pos"><span class="pos-lab" id="posLab"></span><span class="dots" id="dots"><i></i><i></i><i></i><i></i></span></div></div><div class="ctl-row"><button type="button" class="play" id="play" aria-label="播放"><svg viewBox="0 0 24 24" aria-hidden="true"><path id="icon" d="M7 4.5v15l13-7.5z"/></svg></button><span class="tm" id="tCur">0:00</span><input type="range" id="seek" min="0" max="{int(dur)}" step="0.1" value="0" aria-label="播放位置"><span class="tm r" id="tDur">{mmss(dur)}</span></div><div class="opt-row"><div class="spd" role="group" aria-label="播放速度"><button type="button" data-rate="0.75" aria-pressed="false">0.75×</button><button type="button" data-rate="0.9" aria-pressed="false">0.9×</button><button type="button" data-rate="1" aria-pressed="true">1×</button></div><button type="button" class="opt" id="loop" aria-pressed="false">循环本段</button><span class="status" id="status"></span></div><div class="err" id="err" hidden><span>伴奏没有加载出来。可以从手机里选伴奏文件，谱子照样跟着走：</span><input type="file" id="pick" accept="audio/*"></div></div></div>
<audio id="aud" src="{d["audio"]}" preload="metadata"></audio>
<script>window.__SONG={song_js};</script>
<script>{js}</script>
'''

    def markdown(self):
        d = self.d

        def barstr(items, mode):
            if len(items) == 1:
                return self.text(items[0], mode)
            return ' '.join(('' if it['beat'] == 1 else f"({it['beat']})") + self.text(it, mode) for it in items)
        L = [f'# {d["title"]} 和弦谱（自练）', '', d['md_key_text'], '',
             '每行 4 小节，`|` 是小节线。一格里有两个和弦时，括号里的数字是第二个和弦从第几拍开始。', '']
        for sec in d.get('pre', []):
            for c in sec['cells']:
                L += [f'{sec["title"]}（{mmss(c["t"])}）：{c.get("caption") or c["lab"]}', '']
        n = 0
        for sec in d['sections']:
            t = d['downbeats'][n]
            title = sec['title'] + (f'（{sec["md_note"]}）' if sec.get('md_note') else '')
            L += [f'## {title}（{mmss(t)}，第 {n + 1}–{n + len(sec["bars"])} 小节）', '', '| 实际音高 | 中音萨克斯 |', '|---|---|']
            for i in range(0, len(sec['bars']), 4):
                row = sec['bars'][i:i + 4]
                L.append('| ' + ' \\| '.join(barstr(b, 'concert') for b in row) + ' | ' + ' \\| '.join(barstr(b, 'alto') for b in row) + ' |')
            L.append('')
            n += len(sec['bars'])
        for sec in d.get('post', []):
            parts = []
            for c in sec['cells']:
                ch = c.get('chord')
                name = f'{self.text(ch, "concert")}（中音萨克斯 {self.text(ch, "alto")}）' if ch else 'N.C.'
                parts.append(f'{mmss(c["t"])} {name}，{c.get("caption") or c["lab"]}')
            L += [f'{sec["title"]}：' + '；'.join(parts) + '。', '']
        return '\n'.join(L)


def build_song(slug):
    folder = os.path.join(ROOT, 'songs', slug)
    d = json.load(open(os.path.join(folder, 'song.json')))
    s = Song(d)
    page = s.page()
    open(os.path.join(folder, 'index.html'), 'w').write(HEAD + '<title>' + d['title'] + ' 和弦谱</title>\n</head>\n<body>\n' + page.split('\n', 1)[1] + '\n</body>\n</html>\n')
    open(os.path.join(folder, 'artifact.html'), 'w').write(page)  # 发布到 claude.ai Artifact 用的版本（不带 html/head/body）
    open(os.path.join(folder, 'chords.md'), 'w').write(s.markdown())
    return d, s.nbars


def build_home(songs):
    css = open(os.path.join(TPL, 'page.css')).read()
    rows = ''.join(
        f'<a class="song" href="songs/{d["slug"]}/index.html"><span class="st">{d["title"]}</span>'
        f'<span class="sk">{d["home_key_text"]}</span><span class="sm">{d["tempo_text"]} · {mmss(d["duration"])} · {nb} 小节</span></a>'
        for d, nb in songs)
    extra = ('.songs{display:flex;flex-direction:column;border-top:1px solid var(--rule)}'
             '.song{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;padding:14px 2px;border-bottom:1px solid var(--rule);color:var(--ink);text-decoration:none}'
             '.song:focus-visible{outline:2px solid var(--accent);outline-offset:2px}'
             '.st{font-family:var(--f-display);font-style:italic;font-weight:600;font-size:24px;line-height:1.15}'
             '.sk{grid-column:1;color:var(--ink-2);font-size:14px}.sm{grid-column:2;grid-row:1/span 2;align-self:center;text-align:right;color:var(--ink-3);font-family:var(--f-chord);font-size:13.5px;font-variant-numeric:tabular-nums}'
             '@media (max-width:480px){.song{grid-template-columns:1fr}.sm{grid-column:1;grid-row:auto;text-align:left}}')
    page = (HEAD + '<title>萨克斯自练</title>\n' + FONTS + f'\n<style>{css}{extra}</style>\n</head>\n<body>\n'
            '<div class="wrap" style="padding-bottom:48px">\n<header><p class="eyebrow">自练存档 · 不对外分享</p><h1>萨克斯自练</h1>'
            '<p class="meta">每首歌一页：带伴奏播放的和弦谱，可以在中音萨克斯调、实际音高和次中音萨克斯调之间切换。</p></header>\n'
            f'<nav class="songs" aria-label="曲目">{rows}</nav>\n</div>\n</body>\n</html>\n')
    open(os.path.join(ROOT, 'index.html'), 'w').write(page)
    # README 曲目表
    rp = os.path.join(ROOT, 'README.md')
    readme = open(rp).read()
    a, b = readme.index('<!-- songs:start -->'), readme.index('<!-- songs:end -->')
    table = ['<!-- songs:start -->', '| 曲目 | 调（实际音高 / 中音萨克斯） | 速度 | 时长 |', '|---|---|---|---|']
    for d, nb in songs:
        table.append(f'| [{d["title"]}](songs/{d["slug"]}/) | {d["home_key_text"]} | {d["tempo_text"].split(" · ")[0]} | {mmss(d["duration"])} |')
    open(rp, 'w').write(readme[:a] + '\n'.join(table) + '\n' + readme[b:])


if __name__ == '__main__':
    only = sys.argv[1:]
    built = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'songs', '*', 'song.json'))):
        slug = os.path.basename(os.path.dirname(f))
        if only and slug not in only:
            d = json.load(open(f)); built.append((d, sum(len(s['bars']) for s in d['sections']))); continue
        d, nb = build_song(slug); built.append((d, nb)); print('built', slug, nb, 'bars')
    built.sort(key=lambda x: x[0].get('added', ''))
    build_home(built)
    print('home + README updated:', len(built), 'songs')
