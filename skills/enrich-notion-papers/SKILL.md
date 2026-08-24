---
name: enrich-notion-papers
description: Research papers from this navigation_paper_crawler repository's Notion database and safely enrich each record with Chinese Question details and a verified official GitHub source website. Use when processing the manual Notion paper queue, filling missing Question details, auditing source website fields, handling score thresholds or score ranges, or continuing a batch of high-score paper enrichment without calling an external LLM API.
---

# Enrich Notion Papers

## Goal

Act as the paper reader and researcher. Read each paper, produce the requested Chinese summary, verify whether an official public GitHub repository exists, and write only the authorized Notion fields through the repository's guarded scripts.

Do not call the project's external LLM API for this workflow. Use your own analysis of the paper and current web evidence.

## Locate the repository

Work from the repository root containing these files:

- `prepare_manual_question_queue.py`
- `write_manual_question_detail.py`
- `write_manual_source_website.py`
- `paper_crawler.py`
- `config.local.json` or another user-specified config

Never print, log, quote, or expose the Notion token from the config. Run all commands with the repository root as the working directory.

Expect these Notion properties:

- `Name`: title
- `Recommend Score`: number
- `PDF Link`: URL
- `Abstract`: text
- `Question details`: text/rich_text
- `source website`: URL

Stop and report a schema mismatch instead of changing the database schema unless the user explicitly asks for that change.

## Determine the processing scope

Honor the user's threshold, score interval, limit, and requested order exactly. Default to score-descending order and use title ascending as the tie-breaker.

For papers missing `Question details`, refresh the manual queue:

```bash
python3 prepare_manual_question_queue.py config.local.json --threshold 85
```

Read `output/manual_question_queue.jsonl` and process only entries whose `status` is `pending` and whose score is in scope.

Do not use this queue as the only source for a `source website` audit: it intentionally excludes papers whose `Question details` already exists. For a source-only audit, or when filling both fields for an entire score range, use a read-only Notion query through `NotionClient.fetch_existing_papers()`, then fetch the pages to inspect `source website`. Never mutate a page during enumeration.

Process one Notion page at a time. Keep the `page_id`, title, score, PDF, summary, repository evidence, and write result attached to the same paper.

## Research each paper

Use the following source priority:

1. Paper PDF or arXiv full text.
2. Official paper project page.
3. Authors' or laboratory's publication page.
4. Official GitHub repository and its README/files.
5. Abstract only when full text is genuinely unavailable.

Search the current web for repository availability because code releases can change after publication. Match repositories using the paper title, authors, project page, citation, and README. Do not infer that a repository belongs to a paper from a similar name alone.

If only the abstract is available, state the limitation in your work log and avoid adding unsupported implementation details.

## Generate `Question details`

Apply this prompt to every paper:

```text
请阅读全文，优先依据论文 PDF，并结合官方项目页或官方代码仓库核对事实。请用简体中文总结，不展示思维链，不使用空泛评价，也不要补写论文没有提供的内容。只按以下五个字段输出，总长度不超过 2000 个字符：

主要问题：说明论文要解决的具体任务、现有方法的关键不足，以及该不足为何影响导航。用一个紧凑段落表达。

方法概述：说明核心框架、主要模块、输入信息、关键中间表示、决策或规划方式和最终输出。保留必要的英文缩写，但主体使用中文。不要只改写摘要。

导航类型：只能优先选择 VLN、VN、Point Navigation 之一；如果论文确实不属于三者，写“其他”并给出准确任务名；如果覆盖多种任务，写主要类型并在括号中补充子任务。

判断依据：根据目标的表达形式、策略输入和评测任务解释分类。明确说明语言是路线指令/必要目标条件、视觉目标，还是给定坐标/相对位姿。不要仅凭论文标题分类。

是否开源：写“是”“部分开源”或“暂未开源”，并说明核验结果。只有确认存在与本文对应、公开且非空的官方 GitHub 仓库时才附仓库 URL；项目主页、第三方复现、匿名评审链接、空仓库、只有 README 的占位仓库或写着 Code coming soon 的仓库均不能表述为已开源。
```

Use exactly these labels and plain-text paragraphs:

```text
主要问题：...
方法概述：...
导航类型：...
判断依据：...
是否开源：...
```

Do not add a title, bullets, Markdown headings, citations, confidence scores, or a separate `source website` line inside `Question details`.

## Apply the navigation taxonomy

Classify by the task definition, not by the sensors or model architecture:

- Choose `VLN` when a natural-language route instruction or language-defined task/goal is an indispensable condition for navigation. Standard examples include R2R, RxR, VLN-CE, aerial VLN, and instruction-following navigation.
- Choose `VN` when navigation is driven by visual observations toward an object, object category, target image, or visually recognized semantic target without a route-language instruction. Treat ObjectNav, ImageNav, instance navigation, and zero-shot object navigation as VN for this database unless the paper's actual task requires language instructions.
- Choose `Point Navigation` when the goal is a metric coordinate, relative pose, GPS/compass vector, point goal, or geometric subgoal independent of semantic language understanding.
- Choose `其他` only when none of the three categories describes the evaluated navigation task. Name the actual task, such as exploration, mapping, local planning, or social navigation.

When a paper evaluates several types, select the paper's primary contribution and list the supported secondary tasks in parentheses. Explain the decision in `判断依据`.

## Verify `source website`

Accept a URL only when all of the following hold:

- It has the canonical form `https://github.com/<owner>/<repository>`.
- The owner is an author, laboratory, institution, or organization demonstrably connected to the paper.
- The README, citation, project page, or author page explicitly connects the repository to the paper.
- The repository is public and non-empty.
- It contains meaningful paper artifacts such as source code, evaluation code, dataset generation tools, benchmark data, model files, configs, or executable scripts.

Classify repository availability as follows:

- `是`: the official repository contains enough relevant artifacts to use, evaluate, train, or reproduce a material part of the work.
- `部分开源`: the official repository is non-empty and relevant but clearly omits a substantial component such as inference code, training code, weights, or a required dataset.
- `暂未开源`: no verified official GitHub repository exists, or the candidate is empty, README-only, a website-only repository, an announcement, or promises a future release.

Never write any of these into `source website`:

- Project pages, Google Sites, Hugging Face pages, paper URLs, or arbitrary websites.
- Third-party mirrors, unofficial reproductions, survey lists, or dependencies cited by the paper.
- Anonymous review repositories such as 4open/anonymous GitHub links.
- Guessed URLs, private/inaccessible repositories, empty repositories, or placeholder repositories.

If evidence is ambiguous, leave `source website` empty and report why. False positives are worse than missing links.

If `source website` already contains a value, do not overwrite it. Verify it and report a suspected error to the user; the guarded writer intentionally refuses replacement.

## Save and write one paper

Save each completed summary as UTF-8 text under:

```text
output/manual_question_details/<safe-title-slug>.txt
```

Use the available patch/file-edit mechanism to create the file. Do not use shell redirection or include secrets. Keep output files out of version control according to the repository's `.gitignore`.

When a verified official repository exists and the Notion field is empty, write it first:

```bash
python3 write_manual_source_website.py config.local.json \
  --page-id <page_id> \
  --url https://github.com/<owner>/<repository>
```

Then write the summary:

```bash
python3 write_manual_question_detail.py config.local.json \
  --page-id <page_id> \
  --text-file output/manual_question_details/<safe-title-slug>.txt
```

If using a non-default queue file, pass `--queue <queue-path>` to the question writer.

Use these scripts instead of sending a raw Notion PATCH. They enforce the configured database, modify only the intended property, reject existing content, and re-read the page to verify an exact match. The question writer also marks the local queue item `done`.

If `Question details` already contains text, skip it. Still audit or fill `source website` when that field is in scope and empty.

Stop on a non-zero writer exit code. Inspect the page state before continuing so a write failure cannot be attached to the next paper.

## Report progress and completion

During a long batch, report concise checkpoints containing:

- Number completed and remaining.
- Current score range.
- Newly verified repositories.
- Papers deliberately left without a link and the short reason.
- Any paper processed from abstract only.

At completion, run a fresh read-only Notion query and report:

- Number of papers in scope.
- Number of `Question details` fields filled and still empty.
- Number of `source website` fields filled and still empty.
- Exact-match readback result for writes from the current run.

Do not claim completion from the local queue alone. The Notion readback is the source of truth.
