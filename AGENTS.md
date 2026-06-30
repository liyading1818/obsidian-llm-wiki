# AGENTS.md — 个人 LLM Wiki 操作手册

> 本文件是给 LLM Agent（Claude Code / Cursor / Codex / OpenCode 等）看的"工作章程"。
> 任何 Agent 在对这个仓库做任何修改前，**必须先完整阅读本文件**。
> 本文件由"人 + LLM"共同演化 —— 当你发现更好的工作流，请直接修改它。

---

## 1. 这个仓库是什么

这是一个基于 Andrej Karpathy [LLM Wiki](raw/karpathy-llm-wiki.md) 模式构建的**个人知识库**。
核心理念：**LLM 不是在每次提问时重新检索原始文档，而是持续地把原始资料"编译"成一份结构化、互相链接的 wiki，知识在其中累积、对照、综合。**

- 人类负责：**搜集来源、提出问题、决定方向**。
- LLM 负责：**总结、交叉引用、归档、维护一致性、记录日志**——一切繁琐的 bookkeeping。

仓库是一个普通的 Obsidian Vault + Git 仓库，所有内容都是 Markdown。

---

## 2. 目录结构（三层 + 衍生）

```
知识库/
├── AGENTS.md            ← 你（LLM）现在正在读的文件：schema / 操作手册
├── README.md            ← 给人类看的总览
│
├── raw/                 ← 原始资料层（只读）：文章、论文、PDF、转写
│   └── assets/          ← 图片、附件（Obsidian 自动下载到这里）
├── clippings/           ← Obsidian Web Clipper 抓回来的网页 markdown
│                         （视作 raw 的子集；处理完后可移入 raw/ 或保留原位）
│
├── wiki/                ← LLM 维护层（你可读可写的主战场）
│   ├── index.md         ← 内容目录（按类别列出所有页面 + 一句话摘要）
│   ├── log.md           ← 时间线日志（追加式）
│   ├── entities/        ← 实体页（人物、组织、产品、地点…）
│   ├── concepts/        ← 概念页（理论、术语、方法）
│   ├── topics/          ← 主题/综合页（跨多份资料的综述）
│   ├── sources/         ← 每份 raw 资料的摘要页（一份资料对应一篇）
│   └── questions/       ← 你向 wiki 提的问题及其回答归档
│
├── output/              ← 衍生产物：幻灯片（Marp）、图表、导出
│
└── lint/                ← 健康检查报告（矛盾、孤立页、缺口…）
    └── YYYY-MM-DD.md
```

**铁律**：
- `raw/` 与 `clippings/` 中的文件 **永远不要修改**。它们是 source of truth。
- `wiki/` 完全由 LLM 拥有：你创建、更新、重命名、删除页面都可以，但每次改动都要更新 `index.md` 与 `log.md`。
- 所有 wiki 页面互相之间用 Obsidian 的 `[[双链]]` 语法引用；引用 raw 资料时用相对路径 `[文章名](../raw/xxx.md)`。

---

## 3. 页面规范

### 3.1 Frontmatter（YAML 头）
每个 wiki 页面顶部必须有 frontmatter，便于 Dataview 查询：

```yaml
---
type: entity | concept | topic | source | question
tags: [tag1, tag2]
created: 2026-06-26
updated: 2026-06-26
sources: [../raw/xxx.md, ../raw/yyy.md]   # 本页引用的原始资料
status: stub | draft | mature              # 成熟度
---
```

### 3.2 页面骨架
```markdown
# <页面标题>

> 一句话定义/摘要。

## 关键事实
- …

## 详细内容
…

## 与其他页的关系
- [[xxx]] — 关系说明
- [[yyy]] — …

## 矛盾 / 待核实
- （如果不同来源说法冲突，明确记录在这里）

## 来源
- [[sources/xxx]]
```

### 3.3 命名约定
- 文件名用**中文或英文短语**，避免空格用 `-` 连接。
- `sources/` 下的页面命名为 `YYYY-MM-DD-<标题缩写>.md`，与 raw 同名以便对应。

---

## 4. 三大工作流

### 4.1 Ingest（吸收一份新资料）

当用户说"帮我处理这份资料"或往 `raw/` / `clippings/` 丢了新文件时：

1. **读取**原始资料的全文。
2. 与用户**简要讨论** 3–5 个 key takeaways（一两段话即可，不要长篇大论）。
3. 在 `wiki/sources/` 下新建摘要页（含 frontmatter、要点、引用、与现有页的关联）。
4. 扫描 `wiki/index.md`，找出该资料**牵涉到的现有实体/概念/主题页**：
   - 已有的页面 → 更新内容，记录新信息与原有内容是否冲突。
   - 应该有但没有的页面 → 新建 stub。
5. 更新 `wiki/index.md`（追加/修改条目）。
6. 在 `wiki/log.md` 顶部 append 一条记录（格式见 §5）。
7. 向用户**汇报**：本次新建/修改了哪些页面，触发了哪些矛盾或新问题。

**一份资料典型会触及 5–15 个 wiki 页面，不要害怕大规模 touch。**

### 4.2 Query（提问）

当用户提问时：

1. **先读** `wiki/index.md`，找候选页。
2. 顺着 `[[双链]]` 钻取相关页面。
3. **必要时**再回查 `raw/` 原文（用于核对、找原话）。
4. 用引用回答用户。引用格式：`见 [[页面名]]` 或 `源自 [文章](../raw/xxx.md)`。
5. **关键习惯**：如果这个回答本身有沉淀价值（对比、分析、新发现），主动问用户"要不要把这个答复归档为 `wiki/questions/...` 或一篇新的 topic 页？"

### 4.3 Lint（健康检查）

当用户说"做一次 lint"或每累计 10 次 ingest 后主动建议：

检查清单：
- [ ] **矛盾**：不同页面对同一事实的说法是否一致？
- [ ] **过时**：是否有 claim 被更新的来源覆盖却没改？
- [ ] **孤立页**：哪些页没有 inbound link？
- [ ] **缺页**：哪些概念被多次提及但没有自己的页？
- [ ] **断链**：`[[xxx]]` 指向不存在的页面？
- [ ] **缺口**：哪些方向值得补一份 web 搜索 / 新来源？

输出一份 `lint/YYYY-MM-DD.md` 报告，列出问题与建议，**不要直接动手修**，让用户决定优先级。

---

## 5. 日志格式（log.md）

**追加在文件顶部**（最新的在最上面），每条必须以 `## [YYYY-MM-DD] <action> | <对象>` 开头，便于命令行解析：

```bash
grep "^## \[" wiki/log.md | head -10   # 看最近 10 次操作
```

示例：

```markdown
## [2026-06-26] ingest | Karpathy LLM Wiki

- 新建 `wiki/sources/2026-06-26-karpathy-llm-wiki.md`
- 新建概念页 `[[wiki/concepts/LLM-Wiki模式]]`、`[[wiki/concepts/Memex]]`
- 新建实体页 `[[wiki/entities/Andrej-Karpathy]]`、`[[wiki/entities/Vannevar-Bush]]`
- 更新 `wiki/index.md`
- 触发问题：是否要专门讨论 qmd vs 传统 RAG？（已记录到 `wiki/questions/`）

## [2026-06-26] init | 仓库初始化

- 按 Karpathy LLM Wiki 模式建立目录结构
- 写入 AGENTS.md（schema）
- 创建空的 index.md / log.md
```

---

## 6. CLI 工具：`wiki`（极简）

只有 4 个命令，故意保持小。其他操作（建页、改 frontmatter、更新 index.md、追加 log.md…）一律**直接读写 markdown 文件**完成——这是 LLM 的本职工作，不用包装成命令。

```text
wiki stats              仓库概览（页面数、按 type/status 分布）
wiki log -n 10          看 wiki/log.md 最近 N 条
wiki search <regex>     全文搜索 (--scope wiki|raw|clippings|all)
wiki lint               生成体检报告到 lint/YYYY-MM-DD.md
```

入口在仓库根目录的 `wiki.cmd` / `wiki.ps1`，主程序 `tools/wiki.py`（零依赖，纯 Python stdlib）。

## 7. Query 工作流：答案要落到 `output/`

当用户提问、要对比、要综述、要做幻灯——而不是简单的事实查询时，**最终产物必须写成文件**放到 `output/`，不要只藏在聊天里。这样探索会和 ingest 一样持续沉淀。

```
output/
├── 2026-06-26-rag-vs-llm-wiki.md          # 对比 / 分析 / 综述
├── 2026-06-26-karpathy-summary.slides.md  # Marp 幻灯
├── scripts/                                # 生成图表的辅助脚本
└── assets/                                 # 渲染产物、导出文件
```

每个 `output/` 文件必须有 frontmatter，便于以后把它"提升"为正式 wiki 页：

```yaml
---
type: artifact
kind: answer | comparison | analysis | report | slides
created: 2026-06-26
question: "<用户原话>"
sources_used: [wiki/concepts/X.md, wiki/sources/Y.md]
---
```

输出完后，**主动问用户**："要不要把这份归档为 `wiki/questions/<slug>.md`？" 如果用户同意，再把它正式纳入 wiki 并更新 index.md / log.md。

简单的事实查询直接在聊天里回答即可，不必每问都建文件。

## 8. 一些可选小工具

- **Obsidian Web Clipper**：浏览器扩展，一键把网页转成 markdown 存到 `clippings/`。
- **图片本地化**：`Settings → Files and links` 中 attachment folder 设为 `raw/assets/`，绑定 `Ctrl+Shift+D` 触发 "Download attachments for current file"。
- **Graph view**：看 wiki 的形状，找枢纽页和孤立页。
- **Dataview**：通过 frontmatter 自动生成动态表（如"所有 status: stub 的概念页"）。
- **Marp**：从 wiki 内容生成幻灯片，输出到 `output/slides/`。
- **qmd / 自建脚本**：当 `index.md` 不够用（>100 资料）时再引入 BM25/vector 搜索。

---

## 9. 给 LLM 的最终提醒

- **绝不修改 `raw/`、`clippings/` 中的文件。**
- **每次 ingest 都要更新 `index.md` 和 `log.md`，不可省略。**
- 不确定时**问用户**，不要擅自做大幅重构。
- 写作风格：**简洁、有事实、有引用**。不要堆形容词。
- 中英文混排时，中文之间不加空格、中英文之间加一个空格。
- 这个仓库的目的是**长期累积**，所以页面要写得让"半年后的自己"也能看懂。
