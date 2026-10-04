# 工具

## 生成页面

```
python3 tools/build.py              # 重建所有曲目、首页和 README 曲目表
python3 tools/build.py in-my-heart  # 只重建一首
```

只用到 Python 标准库。

## 识别节拍和和弦

要两个 Python 3.11 环境，因为 madmom 只能配 numpy 1.x，其他模型要 numpy 2.x 和 PyTorch。系统里还要有 ffmpeg 和 git。

```
uv venv .venv     && . .venv/bin/activate    && uv pip install lv-chordia librosa soundfile mir_eval pyyaml torch
uv venv .venv_mm  && . .venv_mm/bin/activate && uv pip install "numpy<2" "cython<3" scipy mido setuptools wheel \
                  && uv pip install --no-build-isolation "git+https://github.com/CPJKU/madmom.git"
```

```
.venv/bin/python    tools/analyze.py prep   songs/<曲名>
.venv_mm/bin/python tools/analyze.py beats  songs/<曲名> --bpm 90-130
.venv/bin/python    tools/analyze.py chords songs/<曲名>
.venv/bin/python    tools/analyze.py table  songs/<曲名>
```

`work/table.txt` 每一拍有四项：lv-chordia、BTC、madmom 三个模型的和弦，加上那一拍最响的低音。对着它写 `song.json` 的 `sections`，再跑

```
.venv/bin/python tools/check.py songs/<曲名>
```

列出来的小节回去听，或者看 `work/beat_table.json` 里的 `treb`（每个音级的能量）判断和弦类型。

## song.json 主要字段

- `sections`：每段的 `mark`（方框字母）、`title`、`sub`（小字说明，可以写成 `{alto, concert, tenor}` 三种调各一句）、`key`（用来判断哪些和弦算调外，标成棕色）和 `bars`。
- `bars`：每小节一个列表，每个和弦是 `{beat, r, q, b}`：从第几拍开始、根音（0=C…11=B，按实际音高）、和弦性质（如 `m7`、`maj7`、`7sus4`）、斜线低音。
- `downbeats`、`beats`：每小节第一拍和四拍的时间（秒），从 `work/db4c.npy` 来。
- `pre`、`post`：第一小节之前和最后一小节之后的格子（前奏、结尾延长等）。
- `spell`：三种调的音名拼法，按这首歌的调选升号还是降号。
- `diatonic`：每个调里算调内的和弦。
- `unsure`：要加 ? 的小节号。
- `notes_html`、`form_html`：页面上的说明文字。
