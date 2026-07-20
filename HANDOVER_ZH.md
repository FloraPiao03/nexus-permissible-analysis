# Nexus / Permissible ClinicalTrials.gov 分析项目交接文档

## 1. 项目目的

本仓库使用 ClinicalTrials.gov 官方 API v2，基于研究记录中登记或计划的设施国家信息，计算所有可访问研究中 `NEXUS` 与 `PERMISSIBLE` 研究的比例。

本分析是**位置代理分析**，不是受试者分析。ClinicalTrials.gov 的 location 表示登记或计划的研究设施，不证明：

- 受试者国籍；
- 各国家实际招募人数；
- 设施最终是否启用；
- 研究是否按登记地点完成入组。

## 2. 核心业务定义

### 2.1 分析单位

一个唯一 NCT ID 为一个分析单位。同一 NCT ID 即使有多个设施，也只进入研究分母一次。

### 2.2 主要分母

主要分母为：

> 完整快照中，通过 ClinicalTrials.gov API 可访问的全部唯一研究记录。

不按 study type、sponsor、status、phase、日期、intervention 或 therapeutic area 过滤。

### 2.3 国家定义

- 美国仅指精确字符串 `United States`。
- 中国仅指精确字符串 `China`。
- Puerto Rico、Guam 等美国属地不自动并入美国。
- Hong Kong、Macau/Macao、Taiwan 不自动并入中国。
- 所有定义集中存放在 `config.json`，不应散落在代码中。

### 2.4 五类互斥分类

| Bucket | 定义 |
|---|---|
| `UNKNOWN` | 没有任何可用的 location-country 值 |
| `PERMISSIBLE` | 不包含 `United States`，且至少有一个非空国家 |
| `US_ONLY` | 完整唯一国家集合严格等于 `{United States}` |
| `US_NON_CHINA_MULTI` | 包含 `United States`、不包含 `China`，并且至少还有一个非美国国家 |
| `NEXUS` | 国家集合同时包含 `United States` 和 `China`，可以还有其他国家 |

五类必须互斥且穷尽：

```text
UNKNOWN + PERMISSIBLE + US_ONLY + US_NON_CHINA_MULTI + NEXUS = 总分母
```

缺少 location-country 的研究必须进入 `UNKNOWN`，不能进入 `PERMISSIBLE`。

```text
All studies
│
├── UNKNOWN
│
└── Known-location studies
    │
    ├── NO_US
    │   └── PERMISSIBLE
    │
    └── HAS_US
        ├── US_ONLY
        ├── US_NON_CHINA_MULTI
        └── NEXUS
```

`NEXUS` 与 `PERMISSIBLE` 两者本身不构成全库分区。所有已知位置研究满足 `PERMISSIBLE + HAS_US = known-location`，所有 HAS_US 研究再分为三个子类。

## 3. 仓库结构

```text
nexus-permissible-analysis/
├── README.md
├── HANDOVER_ZH.md
├── HANDOVER_EN.md
├── requirements.txt
├── config.json
├── harvest.py
├── analyze.py
├── selftest.py
├── tests/
└── runs/                  # 生成数据，默认被 Git 忽略
```

主要依赖为 Python 3.11 和 `openpyxl>=3.1,<4`。本机执行时实际可用解释器为 Python 3.13.12，但代码只使用 Python 3.11 兼容语法。

## 4. 配置说明

`config.json` 包含：

- API endpoint；
- User-Agent；
- 每页记录数；
- timeout 和重试参数；
- US/China 精确国家值；
- 单独追踪的 Hong Kong、Macau/Macao、Taiwan 和美国属地；
- Excel Locations 分片大小，默认每张表 500,000 条数据行。

正式维护时应将示例 User-Agent 邮箱替换为真实维护者联系方式。

## 5. 数据采集逻辑：`harvest.py`

### 5.1 请求字段

API 仅请求本分析需要的字段：

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

这不是完整 ClinicalTrials.gov 研究记录，不包含受试者级数据、结果、不良事件或完整方案。

### 5.2 分页与可靠性

采集器：

1. 调用 `https://clinicaltrials.gov/api/v2/studies`；
2. 默认每页请求 1,000 个 study；
3. 每页立即写入 `raw/page_XXXXXX.json`；
4. 根据 `nextPageToken` 请求下一页；
5. 对网络错误、HTTP 429 和 5xx 使用指数退避重试；
6. 使用 request timeout 和可配置 User-Agent；
7. 检测缺失 NCT ID 和重复 NCT ID；
8. 最后一页没有 token 时才将快照标记为完整。

采集不是把全部记录同时放入内存，而是逐页下载并写盘。

### 5.3 Manifest

采集成功后生成 `manifest.json`，包含：

- UTC harvest timestamp；
- endpoint 与请求参数；
- page count；
- raw study count；
- unique NCT count；
- duplicate count；
- `snapshot_complete`；
- 是否仍有 next-page token；
- 每个 raw 文件的 SHA-256 和 study count。

若采集失败，会生成 `HARVEST_FAILED.txt`。失败目录不能被当作完整快照。

### 5.4 烟雾测试与全量运行

三页烟雾测试：

```bash
.venv/bin/python harvest.py --outdir runs --limit-pages 3
```

它只验证 API、分页和下游输出，不是业务最终结果。只要第三页后仍有 token，manifest 就会标记为不完整。

全量运行：

```bash
.venv/bin/python harvest.py --outdir runs
```

不要硬编码预期研究总数；ClinicalTrials.gov 会持续变化。

## 6. 分析逻辑：`analyze.py`

### 6.1 输入验证

分析器只接受带有效 manifest 的 run 目录，并执行：

- 每个 raw 文件存在性检查；
- SHA-256 校验；
- raw count 与 manifest 对账；
- unique NCT count 对账；
- NCT ID 必填检查；
- 重复 ID 报告。

部分快照允许生成技术烟雾测试输出，但会被标记为：

```text
PARTIAL_NON_FINAL_SMOKE_TEST
```

完整快照标记为：

```text
FINAL_COMPLETE_SNAPSHOT
```

### 6.2 标准化与分类

对于每个唯一 NCT ID：

1. 读取 `protocolSection.contactsLocationsModule.locations`；
2. 收集每个 location 的 `country`；
3. 去除首尾空格，丢弃空字符串；
4. 形成唯一国家集合；
5. 按配置中的 US/China 值分配 bucket；
6. 保留 Hong Kong、Macau、Taiwan 和美国属地独立 flags；
7. study type 和 overall status 仅作为元数据保留，不用于过滤。

### 6.3 输出

修订后的五分类输出默认写入 `runs/run_<timestamp>/out_v2/`，历史四分类 `out/` 保持不变：

| 文件 | 内容 |
|---|---|
| `summary.md` | 人类可读摘要 |
| `summary.json` | 机器可读计数、百分比与定义 |
| `trials.csv` | 每个唯一 NCT ID 一行 |
| `locations_long.csv` | 每个 NCT ID × 注册设施一行 |
| `country_counts.csv` | 每个国家的唯一研究数及百分比 |
| `country_vocabulary.csv` | API 中实际出现的国家字符串 |
| `nexus_permissible_results.xlsx` | 面向业务用户的 Excel workbook |

### 6.4 Excel 大数据处理

完整快照包含 3,488,092 条 location，超过 Excel 单工作表 1,048,576 行限制。代码后来增加了：

- `Workbook(write_only=True)` 流式写入，降低 Excel 构建内存压力；
- 自动分片 `Locations`、`Locations_002`、`Locations_003`……；
- 默认每张 location sheet 500,000 条数据行；
- 配置键 `excel_location_rows_per_sheet`；
- 每张表保留标题行、筛选和冻结首行。

修订版 workbook 有 7 张 location sheets：前 6 张各 500,000 行，最后一张 488,092 行。完整无分片版本始终保存在 `locations_long.csv`。

## 7. 测试与硬校验

执行：

```bash
.venv/bin/python selftest.py
.venv/bin/python -m unittest discover -v
```

当前离线测试为 6/6 通过，涵盖：

- US + China → NEXUS；
- US only → US_ONLY；
- US + Canada → US_NON_CHINA_MULTI，且明确不为 US_ONLY；
- US + Germany + Japan → US_NON_CHINA_MULTI；
- US + China + Canada → NEXUS；
- China only、Germany + France → PERMISSIBLE；
- no location → UNKNOWN；
- Puerto Rico + China 基线下为 PERMISSIBLE；
- US + Hong Kong 基线下为 US_NON_CHINA_MULTI；
- Taiwan + Japan → PERMISSIBLE；
- duplicate NCT ID 只计一次；
- observational/interventional 均保留；
- 五类手工汇总、US presence group 和百分比。

生产分析另有硬校验：五类之和、NO_US/HAS_US reconciliation、每类逻辑不变量、JSON/Excel 计数一致性，以及不完整快照状态。

## 8. 完整运行与最终结果

完整 run：

```text
runs/run_20260716T092516Z
```

Manifest 验证：

```text
snapshot_complete: true
next_page_token_remaining: false
page count: 595
raw study count: 594,066
unique NCT IDs: 594,066
duplicate NCT IDs: 0
missing/hash/count errors: 0
```

修订后五分类主要结果（`out_v2/`）：

| Bucket | Count | Percentage of all studies |
|---|---:|---:|
| NEXUS | 2,521 | 0.4243636228971192%（报告为 0.42%） |
| PERMISSIBLE | 340,665 | 57.344638474512934% |
| US_ONLY | 167,656 | 28.221780071574535% |
| US_NON_CHINA_MULTI | 23,369 | 3.933738002174843% |
| UNKNOWN | 59,855 | 10.075479828840567% |
| Total | 594,066 | 100% |

已知位置研究为 534,211；Nexus/已知位置为 0.4719109116060882%，Permissible/已知位置约 63.77%。已知位置百分比是次要指标，不能替换主要分母。

旧四分类的 `US_ONLY=191,025` 被纠正为真正 US_ONLY 167,656 和 US_NON_CHINA_MULTI 23,369。NEXUS、PERMISSIBLE、UNKNOWN 均不变。HAS_US 总数为 193,546。

## 9. 独立审计

历史四分类曾于 2026-07-17 完成独立 Nexus 审计。五分类修订后，`audit_v2.py` 再次在不导入生产分类函数的条件下直接读取 raw JSON，并核对 revised CSV、JSON、Markdown 和 Excel。

### 9.1 Raw 快照重算

独立脚本直接读取 595 个 raw 页面，只使用 NCT ID 和 `locations[].country` 重新分类：

```text
unique raw IDs: 594,066
independent NEXUS: 2,521
independent PERMISSIBLE: 340,665
independent US_ONLY: 167,656
independent US_NON_CHINA_MULTI: 23,369
independent UNKNOWN: 59,855
trials.csv row/group mismatches: 0
summary.json discrepancies: 0
summary.md discrepancies: 0
Excel discrepancies: 0
verdict: PASS
```

### 9.2 历史四分类行级抽样

以下是修订前 Nexus 审计的历史抽样（不是五分类转移抽样），使用固定随机种子 `20260717`：

- 30 NEXUS；
- 20 PERMISSIBLE；
- 20 US_ONLY；
- 20 UNKNOWN。

当时的 90/90 expected bucket 与历史 production bucket 一致，且 30/30 NEXUS raw country 列表明确同时包含 `United States` 和 `China`。五分类的全量逐行零差异验证由 `audit_v2.py` 完成。

审计临时证据位于：

```text
/private/tmp/nexus_raw_audit.py
/private/tmp/nexus_raw_audit_report.json
/private/tmp/nexus_raw_audit_report.samples.csv
/private/tmp/nexus_api_audit.py
/private/tmp/nexus_api_audit_results.json
```

`/private/tmp` 不是长期存储。如需永久保留，应复制到受版本控制的 `audit/` 目录并再次审查后提交。

### 9.3 独立 API 查询

2026-07-17 live API 返回 all studies 594,309、US+China 2,522。相对 2026-07-16 快照分别增加 243 和 1，说明 live registry 已更新，不构成快照结果错误。冻结 raw 快照与生产结果完全一致。

官方查询使用精确字段语义：

```text
(AREA[LocationCountry]EXPANSION[None]COVERAGE[FullMatch]"United States")
AND
(AREA[LocationCountry]EXPANSION[None]COVERAGE[FullMatch]"China")
```

不要将两个国家放入同一个 `SEARCH[Location](...)`，否则会要求同一 location 对象的 country 同时匹配两个值。

历史 live API 审计结论为 `VALIDATED WITH MINOR DIFFERENCES`，minor difference 仅为第二天 live API 多 1 个 Nexus。当前冻结快照五分类 reconciliation 为 `PASS`。

### 9.4 国家字符串审计

冻结快照中与 US/China 可能相关的 observed strings 只有：

| Exact value | Unique NCT IDs | Location rows | 结论 |
|---|---:|---:|---|
| `United States` | 193,546 | 1,486,005 | baseline US canonical value |
| `China` | 52,324 | 166,635 | baseline mainland-China canonical value |
| `United States Minor Outlying Islands` | 2 | 2 | 独立属地，不并入 US |

未观察到 `US`、`U.S.`、`USA`、`U.S.A.`、`United States of America`、`the US`、`America`、`PRC`、`P.R.C.`、`People's Republic of China`、`People’s Republic of China` 或 `Mainland China`。US/China 没有大小写、标点或首尾空白变体。全库仅有 1 个无关国家值 `Bonaire, Saint Eustatius and Saba ` 带尾空格，因此安全 `.strip()` 应保留，精确匹配 `United States` / `China` 对该快照充分。

持久审计文件：

```text
runs/run_20260716T092516Z/out_v2/country_string_audit.csv
runs/run_20260716T092516Z/out_v2/reclassification_audit.json
```

## 10. 诊断分母

以下仅用于解释，不改变主要分母：

| Denominator | Count | Nexus | Nexus % |
|---|---:|---:|---:|
| 所有唯一研究 | 594,066 | 2,521 | 0.4243636228971192% |
| 有已知位置 | 534,211 | 2,521 | 0.4719109116060882% |
| 所有 interventional | 453,297 | 2,377 | 0.5243802628298886% |
| interventional 且有已知位置 | 411,859 | 2,377 | 0.5771392636800458% |
| 至少一个 China location | 52,324 | 2,521 | 4.818056723492088% |
| 至少一个 US 或 China location | 243,349 | 2,521 | 1.0359606984207868% |

五分类的 HAS_US 内部占比：US_ONLY 86.62333502113194%，US_NON_CHINA_MULTI 12.074132247631054%，NEXUS 1.3025327312370187%。

## 11. Git 与 GitHub 状态

当前工作分支：

```text
agent/publish-final-results
```

发布提交：

```text
e94aef8 Publish verified final analysis results
```

Draft PR：

```text
https://github.com/FloraPiao03/nexus-permissible-analysis/pull/1
```

大型 Excel 超过 GitHub 普通 Git 单文件 100 MB 限制，因此作为 Release asset 发布：

```text
https://github.com/FloraPiao03/nexus-permissible-analysis/releases/tag/results-20260716
```

Release 中 workbook SHA-256：

```text
890ae0dc8dfe27a37fcae2bedd696a2f640e74912217db5e8aa41ee31e905700
```

`.venv/`、`__pycache__/` 和大部分 `runs/` 被忽略，因为它们分别是本机环境、自动缓存和大型生成数据。PR 中强制加入了最终 summary 和 manifest；大型 Excel 使用 Release，raw 页面和大型 CSV 未上传。

## 12. 常用命令

环境与测试：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python selftest.py
```

全量采集与分析：

```bash
python harvest.py --outdir runs
python analyze.py --run runs/run_<timestamp> --output-name out_v2
```

验证 manifest 状态：

```bash
python -c 'import json; print(json.load(open("runs/run_<timestamp>/manifest.json"))["snapshot_complete"])'
```

只有 `snapshot_complete: true` 且没有剩余 next-page token 的 run 才能作为最终结果。

## 13. 后续维护建议

1. 合并 PR 前复核 `agent/publish-final-results` 与 `main` 的差异。
2. 将临时审计脚本迁入正式 `audit/` 目录，以便未来重复审计。
3. 在新快照中保留 harvest timestamp；不要将不同日期的 live API count 与旧快照直接等同。
4. 定期检查 API v2 字段名、搜索语法和国家词汇变化。
5. 运行后检查 `country_vocabulary.csv`，尤其关注国家重命名或历史名称。
6. 如果数据规模继续增长，监控内存和 Excel 分片数量；CSV 应继续作为完整机器可读事实源。
7. 不要从 sponsor、title 或 organization 推断研究地点。
8. 对外引用结果时必须同时写明快照日期、主要分母与 location-proxy limitation。

推荐对外表述：

> 在 2026-07-16 完成的 ClinicalTrials.gov API 快照中，594,066 个唯一研究中的 2,521 个同时登记了 United States 和 China 的研究设施，占全部研究的 0.42%。地点信息表示登记或计划的设施，并不代表受试者国籍或各国实际入组人数。
