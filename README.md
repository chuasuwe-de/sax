# 萨克斯自练

自练用，不对外分享。这里存的是我练萨克斯即兴用的和弦谱和伴奏，每首歌一页。

打开 [index.html](index.html) 是曲目首页。每首歌的页面能直接播放伴奏，谱子跟着走，可以在中音萨克斯调、实际音高和次中音萨克斯调之间切换，也能放慢、循环某一段。

## 曲目

<!-- songs:start -->
| 曲目 | 调（实际音高 / 中音萨克斯） | 速度 | 时长 |
|---|---|---|---|
| [In My Heart](songs/in-my-heart/) | C 大调，B 段转 E♭ / A 大调，B 段转 C | 约 102 拍/分 | 7:23 |
| [Just Like a Woman](songs/just-like-a-woman/) | D 大调 / B 大调 | 约 124 拍/分 | 6:58 |
<!-- songs:end -->

## 怎么用

GitHub 网页上不能直接运行这些页面。下载整个仓库（Code → Download ZIP），解压后用浏览器打开 `index.html`。

在 GitHub 上想直接看谱，就打开每首歌文件夹里的 `chords.md`，那是纯文字版，实际音高和中音萨克斯调对照。

## 目录

```
index.html                 曲目首页（自动生成）
songs/<曲名>/
  song.json                这首歌的全部数据：和弦、小节时间、调、说明文字
  backing.mp3              去掉萨克斯的伴奏
  index.html               带伴奏播放的和弦谱（自动生成）
  chords.md                文字版和弦谱（自动生成）
  artifact.html            发布到 claude.ai 用的版本（自动生成）
tools/
  build.py                 从 song.json 生成上面这些页面
  analyze.py               从伴奏识别节拍、和弦、低音
  check.py                 给写好的和弦谱逐拍打分
  template/                页面共用的样式和脚本
```

## 加一首新歌

1. 用 MVSEP 之类的工具把萨克斯从原曲里去掉，得到伴奏 mp3。
2. 新建 `songs/<曲名>/`，把伴奏放进去，命名为 `backing.mp3`。
3. 跑 `tools/analyze.py` 识别节拍和和弦（环境准备见 `tools/README.md`）。
4. 对照识别结果和低音写 `song.json`，用 `tools/check.py` 打分，把对不上的小节逐个核对。
5. 跑 `python3 tools/build.py`，生成这首歌的页面，首页和上面的曲目表会自动更新。

和弦是从伴奏音频用 AI 模型识别、再交叉核对出来的。根音和大小三度比较可靠，七音和延伸音不一定准。

伴奏来自商业录音，只用于个人练习。这个仓库请保持私有。
