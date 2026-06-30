# 个人 LLM Wiki

按 Andrej Karpathy 描述的 [LLM Wiki](https://github.com/karpathy/llm-wiki) 模式搭建的个人知识库模板。

## 一句话说明

> **LLM 在我和原始资料之间，持续地"编译"出一份越来越丰富的、互相链接的 wiki。我负责搜集和提问，LLM 负责所有 bookkeeping。**

## 快速开始

1. Clone 本仓库，用 Obsidian 打开为 Vault。
2. 创建本地目录：`raw/`、`clippings/`、`wiki/`、`output/`、`lint/`（首次 ingest 时 LLM 也会自动建页）。
3. 对 Cursor Agent 说："请先读 `AGENTS.md`，按里面的规范工作。"

## 怎么用

1. 把任何资料（PDF / 文章 / 网页 markdown / 笔记）丢到 `raw/` 或用 Web Clipper 抓到 `clippings/`。
2. 对 LLM 说："帮我 ingest 这份资料"。
3. LLM 会读资料 → 跟你讨论要点 → 在 `wiki/` 下创建/更新页面 → 更新 `index.md` 和 `log.md`。
4. 之后任何提问，LLM 都会**先查 wiki**，再回 raw。
5. 周期性地让 LLM 跑一次 lint（产出在 `lint/`），找矛盾、孤立页、缺口。

## 目录速查

| 目录 | 谁拥有 | 说明 |
| --- | --- | --- |
| `raw/` | 你 | 原始资料，**不可改** |
| `clippings/` | 你 | Web Clipper 抓的网页 |
| `wiki/` | LLM | 全部知识页面，含 `index.md` / `log.md` |
| `output/` | LLM | 衍生物：幻灯片、图表、导出 |
| `lint/` | LLM | 健康检查报告 |
| `AGENTS.md` | 共同 | **给 LLM 看的操作手册**（最重要的一份配置） |
| `.cursor/skills/` | 共用 | Cursor Agent 技能：`wiki` + `video2wiki` |

## 启动 LLM 会话的第一句话

> "请先读 `AGENTS.md`，按里面的规范工作。"

就够了。
