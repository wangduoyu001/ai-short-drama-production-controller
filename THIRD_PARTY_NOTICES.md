# Third-Party Notices / 第三方来源声明

本仓库的 `novel-to-drama.v1` 总工作流在独立重写的基础上，移植和改造了以下 MIT 项目的部分数据结构、任务编排思想与合成策略。未复制 ArcReel 的 AGPL 源码，也未复制 Toonflow 受补充商业条款约束的核心源码。

## Alibaba LumenX

- Repository: `https://github.com/alibaba/lumenx`
- Reviewed commit: `7a1213a0db73ab90ca976f5c4b4ca680e1ae1d2d`
- License: MIT
- Copyright: `Copyright (c) 2026 Alibaba`
- Adapted concepts:
  - `pending / processing / completed / failed` generation lifecycle
  - image and video variant history with selected take
  - character full-body → three-view/headshot reference chain
  - storyboard frames bound to character and scene references
  - storyboard image → shot video → final assembly production order

## LocalMiniDrama

- Repository: `https://github.com/xuanyustudio/LocalMiniDrama`
- Reviewed commit: `b695284b8288e392a4ce2a63717406f3830966af`
- License: MIT
- Copyright: `Copyright (c) 2026 xuanyustudio`
- Adapted concepts:
  - one-click pipeline represented as resumable tasks
  - skip-completed and retry-failed policy
  - task dependency graph for images, videos, audio and assembly
  - deterministic FFmpeg concat command planning
  - hard failure instead of silently pretending the first clip is a completed episode

## MIT License Notice

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notices and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Explicitly Not Copied / 明确未复制

- `ArcReel/ArcReel`: AGPL-3.0. Only high-level orchestration ideas were studied.
- `HBAI-Ltd/Toonflow-app`: Apache-2.0 plus supplementary commercial terms. Only product flow and chapter-event concepts were studied.
- TypeTale and other closed or binary-distributed products: no source code copied.
