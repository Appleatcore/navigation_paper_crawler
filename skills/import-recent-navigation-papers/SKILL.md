---
name: import-recent-navigation-papers
description: Discover navigation papers from a rolling recent-date window (five days by default), manually assess them without calling an external LLM API, import only qualifying non-duplicates into this repository's Notion literature database, and fill Chinese Question details plus verified official GitHub source website links. Use when asked to 检索最近 N 天导航论文, repeat the five-day literature-import workflow, import recent arXiv navigation papers into Notion, or complete the newly imported records' Question details and source website fields.
---

# Import Recent Navigation Papers

## Goal

Act as the paper searcher, reviewer, and database operator. Discover papers in the requested recent window, read and assess them yourself, import only qualifying navigation papers, and safely enrich every newly created Notion record.

Do not call an external LLM API. Use Codex's own reading and reasoning. Treat “不调用 API” as “不调用外部大模型 API” for this established workflow: arXiv access is needed for discovery and the Notion API is needed for database writes. If the user explicitly forbids all network APIs, do not mutate Notion; explain that only a local candidate package can be prepared.

## Locate the repository

Work from the repository root containing:

- `paper_crawler.py`
- `vla_filter.py`
- `prepare_manual_question_queue.py`
- `write_manual_question_detail.py`
- `write_manual_source_website.py`
- `skills/enrich-notion-papers/SKILL.md`
- `config.local.json` or another user-specified config

Read `skills/enrich-notion-papers/SKILL.md` completely before researching or writing `Question details` and `source website`. Apply its taxonomy, Chinese output format, repository-verification standard, no-overwrite rule, and readback requirements.

Never print, quote, log, or expose `notion_token`, `llm_api_key`, or other credentials. Read only the configuration values needed for the run.

Expect these Notion properties with their existing types:

- `Name`: title
- `Authors`: rich text
- `Year`: number
- `Abstract`: rich text
- `userDefined:URL`: URL
- `PDF Link`: URL
- `DOI`: rich text
- `Date`: date
- `Recommend Score`: number
- `Recommend Rationale`: rich text
- `Question details`: rich text
- `source website`: URL

Inspect the schema read-only before writing. Stop and report a mismatch instead of changing the schema unless the user explicitly authorizes a schema change.

## Establish the run contract

Resolve these values before discovery:

- Use the user's requested duration; default to 5 days only when the request refers to the established five-day workflow.
- Define a rolling UTC interval: `now_utc - N days <= original_v1_submission_time <= now_utc`.
- State the exact start and end timestamps or dates in the work log.
- Use arXiv's original `[v1]` submission time, not the latest revision time. Exclude an old paper merely revised inside the window.
- Read `min_recommend_score` from the config; default to 60 when absent.
- Honor `max_papers` only after relevance, duplicate, and score filtering.

Do not infer completion from a calendar label such as “past week.” Record the concrete interval so a rerun is reproducible.

## Discover broadly, then filter strictly

Use the repository's `ArxivCrawler` as the primary metadata collector, but expand beyond exact phrases in the config. Search at least these concepts together with the configured keywords:

```text
navigation
motion planning
path planning
trajectory planning
local planner
obstacle avoidance
autonomous flight
embodied navigation
vision-language navigation
visual navigation
object navigation
point navigation
robot navigation
```

Request enough sorted results to cross the lower time boundary. Deduplicate candidates locally by normalized arXiv ID, DOI, canonical URL, and normalized title.

If the arXiv Atom API returns persistent HTTP 429, zero results unexpectedly, or stops before crossing the boundary, switch to the official arXiv HTML search/listing pages. Do not substitute an unofficial aggregator for authoritative title, author, abstract, PDF, identifier, or submission-history metadata.

Treat `vla_filter.is_navigation_related(title, abstract)` only as a first-pass signal. Inspect both accepted and plausible rejected candidates because lexical rules can create false positives and false negatives.

Keep a paper only when navigation, planning, obstacle avoidance, or embodied goal reaching is a central contribution or a primary evaluated task. Normally exclude:

- database, schema, website, or document “navigation” with no embodied agent;
- medical/endoscopic tool control unrelated to the library's navigation scope;
- autonomous driving papers unless the user includes driving or the work contributes a general embodied navigation method;
- papers that mention navigation only as a downstream example or minor module;
- surveys, editorials, withdrawn entries, or records with insufficient primary-source evidence;
- old `[v1]` submissions whose newer revision falls inside the window.

Maintain a batch manifest under `output/`, for example:

```text
output/recent_navigation_import_<start>_<end>.jsonl
```

Store only non-secret operational data: arXiv ID, title, original submission time, authors, abstract, URLs, relevance decision, duplicate decision, score, rationale, page ID, detail file, verified repository, and processing status.

## Check Notion duplicates before expensive work

Instantiate `NotionClient` from the specified config and perform a successful read-only inventory with `fetch_existing_papers()`. Compare candidates against existing records using title, DOI, and URL. Then use `check_duplicate(title, doi, url)` or `filter_duplicates()` for the repository's server-side check.

Treat a Notion query error as an unknown duplicate state, not as “not a duplicate.” Stop before insertion if the duplicate check did not complete successfully.

Perform the first duplicate check before downloading and reading PDFs. Recheck each paper immediately before insertion because the database may have changed during a long run.

## Read and score each candidate manually

Read the official PDF whenever available. Prioritize the introduction/problem statement, related limitations, method and architecture, experiment setup, main results, ablations, real-robot or sim-to-real evidence, limitations, and conclusion. Use the abstract alone only when full text is genuinely unavailable, and mark that limitation in the manifest and final report.

Assign `Recommend Score` from 0 to 100 using this stable rubric:

- Navigation relevance: 30%.
- Method novelty: 25%.
- Experimental rigor: 20%.
- Technical depth: 15%.
- Impact and reproducibility potential: 10%.

Use these anchors:

- 90–100: potentially field-shaping navigation work with strong novelty and validation.
- 75–89: clear, useful innovation with solid navigation experiments.
- 60–74: relevant work with moderate novelty, narrow scope, or limited validation.
- 40–59: peripheral relevance, thin experiments, or a minor navigation component.
- 0–39: outside scope or unsupported as a navigation contribution.

Write a concise Chinese `Recommend Rationale` that names concrete strengths, experiments, and deductions. Avoid score inflation for new papers merely because they are recent. Apply the configured threshold exactly and do not add papers with `score < min_recommend_score`.

Do not invoke `LLMScoringEngine`, `QuestionDetailsAnswerer`, `answer_question_details.py`, or `answer_high_score_question_details.py`. Do not run `python3 paper_crawler.py <config>` for this manual workflow because its configured main path can call external LLM, Semantic Scholar, OpenAlex, image-hosting, or other enrichment services.

## Create the base Notion record

Use the existing `NotionClient.add_paper()` implementation rather than constructing an unrelated raw Notion payload. Provide normalized fields including:

```text
title, authors, year, abstract, url, pdf_url, doi,
venue, tags, published_date, recommend_score, recommend_rationale
```

Use the canonical arXiv abstract URL, canonical PDF URL, and `arXiv:<id>` DOI-style identifier when no publisher DOI exists. Keep `question_details` absent from the base payload and leave `source website` empty so the guarded single-field writers can enforce no-overwrite and exact readback.

Insert one paper at a time. Preserve the returned `page_id` immediately in the batch manifest. If insertion returns no page ID, inspect Notion before retrying; never blindly rerun the whole batch.

## Create a batch-specific manual queue

Create an exact queue for the new page IDs, for example:

```text
output/recent_navigation_<start>_<end>_manual_question_queue.jsonl
```

Write one JSON object per line with exactly the information needed by the safe writer:

```json
{"page_id":"...","title":"...","recommend_score":85,"pdf_url":"...","abstract":"...","status":"pending"}
```

Use the available patch/file-edit mechanism for local artifacts. Keep all generated manifests, queues, and summaries under the gitignored `output/` directory.

Do not assume this command creates a batch-only queue:

```bash
python3 prepare_manual_question_queue.py config.local.json --threshold 60
```

It queries the whole database and exports every qualifying paper whose `Question details` is empty. Use it only as a cross-check, or restrict subsequent processing to the exact newly returned page IDs.

## Fill `source website` and `Question details`

Research every accepted paper according to `skills/enrich-notion-papers/SKILL.md`. Search the current web for an official repository because publication-time placeholders can change.

Accept `source website` only for a canonical, public, non-empty, officially connected GitHub repository containing meaningful paper artifacts. Leave the field empty for project pages, Hugging Face pages, third-party reproductions, anonymous review repos, empty/README-only placeholders, or “Code coming soon” announcements.

Generate `Question details` in simplified Chinese with exactly these five labels and no extra heading or Markdown:

```text
主要问题：...
方法概述：...
导航类型：...
判断依据：...
是否开源：...
```

Keep the entire value at or below 2000 characters. Classify the primary evaluated task as `VLN`, `VN`, `Point Navigation`, or `其他` using the goal representation and required inputs, not the title or model architecture.

Save each answer as UTF-8 text:

```text
output/manual_question_details/<safe-title-slug>.txt
```

When a verified official repository exists, write it first:

```bash
python3 write_manual_source_website.py <config> \
  --page-id <page_id> \
  --url https://github.com/<owner>/<repository>
```

Then write the details and pass the exact batch queue:

```bash
python3 write_manual_question_detail.py <config> \
  --page-id <page_id> \
  --text-file output/manual_question_details/<safe-title-slug>.txt \
  --queue output/recent_navigation_<start>_<end>_manual_question_queue.jsonl
```

Process one page at a time. Stop on a non-zero exit code and inspect the page before continuing. Both guarded writers reject existing values and re-read the page; never bypass them with a raw PATCH. If no repository qualifies, do not call the source writer and explicitly record the empty-field decision.

## Audit from Notion, not from local state

After all writes, freshly fetch every page created in this run by its exact `page_id`. Verify:

- title, DOI/URL, PDF URL, publication date, score, and rationale match the accepted paper;
- `Question details` exactly equals the saved UTF-8 text file;
- `source website` exactly equals the verified canonical GitHub URL, or remains empty when no repository qualified;
- every corresponding batch queue status is `done`;
- no below-threshold or duplicate candidate was inserted.

Use the fresh Notion page response as the source of truth. Do not claim success from command exit logs, local files, or queue state alone.

## Report the result

Report concisely:

- exact search interval and original-submission-time rule;
- number discovered, manually reviewed, rejected as irrelevant, deduplicated, below threshold, and inserted;
- each inserted title with score, navigation type, and source website result;
- papers read from abstract only or carrying uncertain evidence;
- exact-match Notion audit count;
- paths of the batch manifest, queue, and detail files.

State explicitly that no external LLM API was called. Distinguish that statement from the arXiv and Notion network access required to complete the workflow.
