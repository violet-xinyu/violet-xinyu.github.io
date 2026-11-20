# 作品集网站（violet-xinyu）

刘心语 Violet Liu 影视制片作品集。纯静态站，GitHub Pages 托管。

- 网址：https://violet-xinyu.github.io/
- 仓库：https://github.com/violet-xinyu/violet-xinyu.github.io

## 技术架构

- 纯 HTML + CSS + JS，无框架、无构建步骤。三个核心文件：`index.html`、`styles.css`、`app.js`
- 播放器：原生 `<video>` + 自定义控件（进度、音量、倍速、全屏、键盘），代码在 `app.js`
- 视频：**GitHub Releases 托管 MP4 + 直链引用**，不用 HLS/m3u8/hls.js
- 封面图：本地 `assets/`
- 飞书 / 百度网盘入口：作为「播放不流畅」时的备用跳转，保留

## 关键文件

| 文件 | 作用 |
|---|---|
| `index.html` | 页面结构。第 1 部作品的默认视频地址在 `<source id="srcMp4">` |
| `app.js` | 5 部作品的数据数组 `WORKS`（标题/简介/视频链接/封面），播放器逻辑 |
| `styles.css` | 全部样式 |
| `assets/` | 封面图 |
| `transcode.py` | 视频转码脚本（见下） |

## 换成真实片子（用户提供原片后）

1. **转码**（本机需先装 ffmpeg：`brew install ffmpeg`）：
   ```bash
   # 精确控制体积（推荐）：把整部片压到 45MB 以内，两遍编码
   python3 transcode.py source/真实片1.mov --target-mb 45 --out out/work-01.mp4
   # 抽封面（自动避开片头黑帧）
   python3 transcode.py out/work-01.mp4 --poster assets/poster-01.jpg
   ```
2. **上传视频**：在 GitHub 仓库建一个 Release（tag 例如 `videos`），把转好的 mp4 作为附件上传，得到形如
   `https://github.com/violet-xinyu/violet-xinyu.github.io/releases/download/videos/work-01.mp4` 的直链。
3. **改链接**：
   - `app.js` 里对应作品的 `mp4` 改成该直链；`poster` 改成新封面路径；标题、`meta`、`role`、`award`、`duration` 改成真实信息。
   - 第 1 部还要同步改 `index.html` 里 `<source id="srcMp4">` 的默认地址和 `poster`。
4. **改文案**：`index.html` 里「占位影片」「测试片」「非本人作品」等说明文字，换成真实作品说明；
   `app.js` 顶部注释、`index.html` 的 `works-footnote`、播放器提示与兜底条说明也要一起改。
5. **推送**：`git add . && git commit -m "更新真实作品" && git push origin main`，等 Pages 构建完成后刷新。

## 踩过的坑（务必避免重复）

1. **视频直链的 MIME**：GitHub Release 直链返回 `application/octet-stream`，无头浏览器会卡在 STALLED，但真实浏览器可正常播放。以用户真机实测为准，别被无头测试的假阴性误导。
2. **不要用 HLS**：对话后期试过 HLS 切片 + hls.js，最终交接文档明确弃用，回到 Releases MP4 直链。
3. **H.264 要求偶数宽高**：超宽银幕片缩放后可能出现奇数宽度导致转码失败，脚本里 `even_scale()` 已强制偶数。
4. **VP9/WebM 不一定更小**：短片上 VP9 默认参数反而比 H.264 大；最终方案统一用 MP4。
5. **封面黑帧**：片头抽帧容易抽到黑帧，脚本取自片长 12% 处。
6. **PR/分支合并会覆盖改动**：每次接手先 `git fetch` + `git pull --ff-only` 对齐 `origin/main`，确认当前线上版本，再改。
7. **GitHub 体积红线**：仓库单文件 >50MiB 警告、>100MiB 拒收；视频一律放 Release（不受此限），不要放进仓库目录。

## 视频体积的现实约束

GitHub Pages + Release 直链方案下，完整长片要压到合理体积才能流畅边下边播。10-15 分钟片压到 30-50MB 时码率仅 400-800kbps，画质有上限。若追求真正高清，需要另走 HLS/专业视频托管，但那会偏离当前交接文档确定的架构。
