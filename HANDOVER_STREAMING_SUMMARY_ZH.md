# Nexus / Permissible 时间分析与轻量流式模式交接文档

## 1. 文档目的

本文档记录项目当前状态、已经完成但尚未提交的 Start Date 时间分析扩展，以及用户最新提出的轻量化要求。

最新目标是：

> 保留可审计的 ClinicalTrials.gov raw snapshot，但在统计阶段按页、按研究流式处理；如果用户只需要汇总结果，则不在内存中累计全部 studies 或 locations，也不生成大型 row-level CSV 和明细 Excel。

需要明确区分：

- Start Date 时间分析代码已经实现并通过测试；
- `--summary-only` 流式轻量模式已经完整实现并通过标准模式 parity 与真实历史 snapshot 验证；
- 尚未重新下载包含 Start Date 的完整 snapshot；
- 尚未提交或推送当前修改。

## 2. 当前已验证的历史基线

历史完整 snapshot：

```text
runs/run_20260716T092516Z
```

该 snapshot 的主要状态：

```text
snapshot_complete: true
unique NCT IDs: 594,066
raw snapshot size: approximately 546 MB
```

历史五分类结果：

| 分类 | 数量 |
|---|---:|
| UNKNOWN | 59,855 |
| PERMISSIBLE | 340,665 |
| US_ONLY | 167,656 |
| US_NON_CHINA_MULTI | 23,369 |
| NEXUS | 2,521 |
| 合计 | 594,066 |

Interventional-only 结果：

| 指标 | 数量 |
|---|---:|
| Total Interventional | 453,297 |
| Known location | 411,859 |
| UNKNOWN | 41,438 |
| PERMISSIBLE | 250,059 |
| US_ONLY | 138,498 |
| US_NON_CHINA_MULTI | 20,925 |
| NEXUS | 2,377 |
| HAS_US | 161,800 |

上述已发布结果保持不变，不应被新的时间分析重新定义。

## 3. 当前 geographic classification

必须继续使用现有五分类，不能在轻量模式中改写：

```text
UNKNOWN
没有可用的注册地点国家值。

PERMISSIBLE
至少有一个可用地点国家，但不包含精确值 "United States"。

US_ONLY
唯一国家集合严格等于 {"United States"}。

US_NON_CHINA_MULTI
包含 "United States"、不包含 "China"，并包含至少一个其他非美国国家。

NEXUS
同时包含 "United States" 和 "China"，允许存在其他国家。
```

国家基线仍然是精确归一化匹配：

```text
US = United States
China = China
```

Puerto Rico 和其他美国领地不自动视为美国；Hong Kong、Macau/Macao 和 Taiwan 不自动视为中国。

## 4. Start Date 数据现状

### 4.1 旧 snapshot 不能用于时间比较

已检查 `runs/run_20260716T092516Z` 的 manifest 和 raw JSON。旧 harvest 当时只请求：

```text
NCTId
BriefTitle
StudyType
OverallStatus
LocationFacility
LocationCity
LocationState
LocationZip
LocationCountry
```

旧 raw 的 `protocolSection.statusModule` 只有 `overallStatus`，没有：

```text
protocolSection.statusModule.startDateStruct.date
protocolSection.statusModule.startDateStruct.type
```

因此旧 snapshot 可以继续支持 all-time geographic 和 Interventional-only 分析，但不能凭空补出 Start Date。

### 4.2 已完成的 harvest 修改

`harvest.py` 已增加且只增加：

```text
StartDate
StartDateType
```

一页、1,000 studies 的真实 API smoke harvest 已成功，确认 API 返回诸如：

```json
{
  "date": "2021-10-15",
  "type": "ACTUAL"
}
```

真实 smoke 中还观察到月精度日期和 `ESTIMATED` 类型。该 smoke snapshot 是 partial，不能作为正式统计结果。

## 5. 已完成的时间分析实现

`analyze.py` 已增加：

```text
start_date_raw
start_date_parsed
start_date_type
start_date_precision
time_cohort
```

允许的 `time_cohort`：

```text
RECENT_3Y
YEARS_4_TO_6_AGO
OLDER_THAN_6Y
FUTURE
TIME_UNKNOWN
TIME_AMBIGUOUS
```

默认 reference date 来自所选 snapshot 的：

```text
manifest.json -> harvest_timestamp_utc 的 UTC 日期
```

可显式覆盖：

```bash
python analyze.py \
  --run runs/run_<timestamp> \
  --reference-date YYYY-MM-DD
```

时间边界使用精确日历年：

```text
RECENT_3Y:
reference_date - 3 calendar years < Start Date <= reference_date

YEARS_4_TO_6_AGO:
reference_date - 6 calendar years < Start Date <= reference_date - 3 calendar years
```

如果 reference date 是 2026-07-16：

```text
RECENT_3Y:
2023-07-16 < Start Date <= 2026-07-16

YEARS_4_TO_6_AGO:
2020-07-16 < Start Date <= 2023-07-16
```

所以：

```text
2023-07-16 -> YEARS_4_TO_6_AGO
2020-07-16 -> OLDER_THAN_6Y
```

## 6. 部分日期处理

支持以下精度：

```text
YYYY-MM-DD -> DAY
YYYY-MM    -> MONTH
YYYY       -> YEAR
```

处理原则是保守区间法，不隐式补日期：

- `2024-02` 表示从 2024-02-01 到 2024-02-29；
- `2022` 表示从 2022-01-01 到 2022-12-31；
- 只有完整可能日期区间全部位于同一 cohort，才进行分配；
- 如果区间跨越 cohort 边界，则为 `TIME_AMBIGUOUS`；
- 缺失或无法解析为 `TIME_UNKNOWN`。

以 2026-07-16 为 reference date：

```text
2024-02 -> RECENT_3Y
2022    -> YEARS_4_TO_6_AGO
2023-07 -> TIME_AMBIGUOUS
```

Start Date 是 ClinicalTrials.gov 注册字段，不应被描述为实际首位受试者入组日期。时间比较是描述性的，不表示因果关系。

## 7. 已完成的时间输出设计

当前标准模式仍会生成完整输出，并新增：

```text
summary.json 中的 time_analysis
summary.md 中的 Start-date period comparison
trials.csv 中的日期和 cohort 字段
Excel Time_Comparison
Excel Time_Location_Pivot
Excel Study_Detail 日期字段
Excel Definitions 时间定义
```

每个目标 cohort 都有硬性 reconciliation：

```text
UNKNOWN
+ PERMISSIBLE
+ US_ONLY
+ US_NON_CHINA_MULTI
+ NEXUS
= cohort denominator
```

`Time_Comparison` 报告 Recent 3Y 与 4–6 years ago 的：

- NEXUS count；
- NEXUS % of cohort；
- NEXUS % of known-location；
- PERMISSIBLE count；
- PERMISSIBLE % of cohort；
- PERMISSIBLE % of known-location；
- US_ONLY %；
- US_NON_CHINA_MULTI %；
- UNKNOWN %；
- Recent 减去 4–6 years 的 percentage-point change。

## 8. 已完成的测试

新增 `tests/test_time_analysis.py`，覆盖：

- 明确属于 Recent 3Y；
- 明确属于 4–6 years ago；
- older than 6 years；
- future；
- 精确 3 年边界；
- 精确 6 年边界；
- month precision；
- year precision；
- missing date；
- malformed date；
- 跨边界 partial date；
- cohort 五分类 reconciliation；
- 添加日期后 geographic classification 不变。

当前测试结果：

```text
27/27 passed
git diff --check passed
synthetic end-to-end smoke passed
one-page live API smoke passed
```

真实一页 smoke 的时间统计只用于验证流程，不能作为业务结果。

## 9. 当前资源占用

当前磁盘状态约为：

```text
disk size: 460 GiB
used: 406 GiB
available: 17 GiB
capacity used: 96%
```

7-16 完整 run：

```text
total: approximately 1.9 GB
raw: 546 MB
historical out/: 605 MB
out_v2/: 627 MB
out_interventional/: 135 MB
```

根据一页真实 smoke，新增 Start Date 后 raw 每 study 大约增加 7%。预计新的完整 raw snapshot 约为 580–650 MB。

当前标准分析还会产生大型 `locations_long.csv`、`trials.csv`、完整 Study Detail 和 Locations Excel，因此新 run 最终可能约为 1.3–1.5 GB。

## 10. 已完成：轻量流式 summary-only 模式

用户已经确认采用以下方向：

> 统计时不需要在内存中累计所有 studies 或几百万条 location rows；统计完成后也不需要把大型 row-level CSV、Locations Excel 或 Study Detail Excel 保存在电脑上。保留可审计 raw snapshot，并只生成小型汇总结果。

需要注意：RAM 中的数据在进程结束后本来就会自动释放。最新需求同时包含两方面：

1. 降低运行时 RAM 峰值；
2. 降低运行结束后的磁盘占用。

## 11. 实际实现方式

### 11.1 CLI 模式

`analyze.py` 已增加：

```bash
--summary-only
```

没有增加一组复杂的细粒度开关，保持单一、清晰的 `--summary-only`，避免把项目扩张成通用数据平台。

### 11.2 流式分析流程

当前 `analyze.py` 的高内存原因是：

```text
读取全部 raw pages
-> studies_by_id 保存全部 study JSON
-> trials 保存全部 study-level rows
-> locations 保存全部 location rows
-> 最后统一写 CSV 和 Excel
```

summary-only 实际流程为：

```text
逐个读取 manifest 中的 raw page
-> 验证该 page SHA-256
-> 逐 study 提取 NCT ID
-> 使用 seen_nct_ids 做去重
-> 仅为当前 study 构建 country set
-> 立即计算 geographic bucket 和 time cohort
-> 立即更新 Counter / set 等汇总结构
-> 不保存完整 study JSON
-> 不保存 location rows
-> 处理下一个 study
```

主要常驻内存应只有：

- 当前 API page；
- `seen_nct_ids` 去重集合；
- geographic/time counters；
- country -> unique NCT ID 的集合仅在需要 Country Counts 时保留；summary-only 首版可以不生成 Country Counts，从而避免这些集合。

### 11.3 summary-only 输出

实际只生成：

```text
summary.json
summary.md
nexus_permissible_summary.xlsx
```

小型 Excel 只包含：

```text
Executive_Summary
Classification_Summary
Time_Comparison
Time_Location_Pivot
Definitions
Run_Metadata
```

summary-only 不生成：

```text
trials.csv
locations_long.csv
country_counts.csv
country_vocabulary.csv
Excel Study_Detail
Excel Locations / Locations_###
```

是否保留 `country_counts.csv` 不应默认开启，因为按 country 做唯一 NCT 去重仍可能需要较大的 `country -> set(NCT IDs)` 结构。当前核心业务问题只需要五分类和时间对比。

### 11.4 保留 raw snapshot

推荐继续保留：

```text
raw/page_*.json
manifest.json
```

原因：

- 能验证完整分页和 page hashes；
- 能重新运行不同 reference date；
- 能复现已报告结果；
- 能由 mentor 或审计脚本复核。

不推荐一边调用 live API 一边统计后丢弃所有 raw，因为这会失去固定 snapshot 和可复现性。

预期轻量 run 的磁盘占用：

```text
raw snapshot: approximately 600 MB
summaries and summary workbook: typically below a few MB
```

相比标准模式可减少约 600–900 MB 的生成输出。

## 12. 流式实现必须保持的验证

`--summary-only` 必须继续执行：

1. manifest 存在且结构有效；
2. 每个 raw page 存在；
3. 每个 raw page SHA-256 正确；
4. raw record count 与 manifest 一致；
5. unique NCT count 与 manifest 一致；
6. duplicate NCT count 可解释；
7. 五 geographic buckets 等于总 unique denominator；
8. `PERMISSIBLE + HAS_US = known location`；
9. US 三个子类等于 HAS_US；
10. 每个目标 time cohort 的五 buckets 等于 cohort denominator；
11. 所有 time cohort 加总等于总 unique denominator；
12. JSON、Markdown 和 summary workbook 汇总数值一致；六个时间 cohort 均独立执行五分类 reconciliation，零分母百分比保持为空值。

不得为了节省内存而取消 hash、分页完整性或 reconciliation 验证。

## 13. 推荐代码结构

避免维护两套不同分类逻辑。建议：

- 保留 `classify()`、`assign_time_cohort()` 和日期解析函数作为唯一规则来源；
- 增加一个逐行 accumulator，例如 `SummaryAccumulator`；
- 标准模式和 summary-only 模式调用同一提取与分类函数；
- 标准模式可以继续写明细；
- summary-only 模式只更新 accumulator；
- summary JSON 的生成使用同一公共函数，防止两种模式数值漂移。

不要把项目改造成数据库或通用 ETL 平台，也不需要引入 pandas、SQLite、Spark 等额外依赖。

## 14. summary-only 测试与结果

已经覆盖：

- 同一 synthetic raw fixture 分别运行标准模式和 summary-only；
- 比较两种模式的总数、五 buckets、HAS_US、所有 time cohort、comparison metrics，要求完全一致；
- 验证 summary-only 输出目录不存在 row-level CSV；
- 验证 summary-only Excel 不存在 `Study_Detail` 和 `Locations`；
- 验证 summary-only 仍能发现 raw hash 错误；
- 验证 duplicate NCT ID 仍只计一次；
- 验证 3 年和 6 年边界不变；
- 验证缺失/部分日期处理不变；
- 验证旧 snapshot 缺少 StartDate 时全部进入 TIME_UNKNOWN，且不会伪造正式时间比较。

最终离线测试结果：

```text
33/33 passed
standard vs summary-only aggregate parity: PASS
hash mismatch rejection: PASS
missing page rejection: PASS
incomplete snapshot rejection: PASS
manifest count mismatch rejection: PASS
output suppression: PASS
```

真实历史完整 snapshot 流式验证：

```text
total unique studies: 594,066
NEXUS: 2,521
PERMISSIBLE: 340,665
US_ONLY: 167,656
US_NON_CHINA_MULTI: 23,369
UNKNOWN: 59,855
historical out_v2 parity: PASS
summary-only output size: approximately 28 KB
measured peak RSS on 594,066-study historical snapshot: approximately 162 MiB
```

旧 snapshot 没有 StartDate，因此：

```text
time_analysis_status: UNAVAILABLE_START_DATE_NOT_HARVESTED
TIME_UNKNOWN: 594,066
```

这只验证 all-time geographic parity，不构成时间比较结果。

## 15. 预期使用命令

先抓取一个包含 Start Date 的新完整 snapshot：

```bash
.venv/bin/python harvest.py --outdir runs
```

完成后使用输出的精确 run 路径运行轻量汇总：

```bash
.venv/bin/python analyze.py \
  --run runs/run_<new_timestamp> \
  --output-name out_time_summary \
  --summary-only
```

默认 reference date 是该 snapshot 的 harvest date。如业务需要固定日期：

```bash
.venv/bin/python analyze.py \
  --run runs/run_<new_timestamp> \
  --output-name out_time_summary \
  --summary-only \
  --reference-date 2026-07-16
```

## 16. 不应执行的操作

- 不要删除或覆盖 `runs/run_20260716T092516Z`；
- 不要修改已发布 all-time 或 Interventional-only 结果；
- 不要自动启动新的 full harvest；
- 不要将 raw snapshot、large CSV 或 large Excel 提交到 Git；
- 不要 commit 或 push，除非用户随后明确要求；
- 不要为了轻量模式复制一套 geographic classification；
- 不要把 Start Date 描述成真实 participant enrollment date。

## 17. 当前 Git 状态

当前未提交修改预期为：

```text
 M HANDOVER_EN.md
 M HANDOVER_ZH.md
 M README.md
 M analyze.py
 M harvest.py
?? HANDOVER_STREAMING_SUMMARY_ZH.md
?? tests/test_summary_only.py
?? tests/test_time_analysis.py
```

所有当前修改均未 commit、未 push。
