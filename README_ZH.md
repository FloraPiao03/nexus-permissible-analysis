# ClinicalTrials.gov Nexus 与 Permissible 分析

这是一个独立的 Python 3.11 项目，用于回答一个基于注册地点的业务问题：按照可配置的司法辖区定义，ClinicalTrials.gov 中的唯一研究有多大比例属于 **NEXUS** 或 **PERMISSIBLE**？

ClinicalTrials.gov记录的是已登记或计划中的研究设施。Location metadata只能作为代理指标：它不能确认受试者国籍，也不能证明各国实际入组情况。

## 分母与分类定义

主分母是在一次**完整抓取**时，通过ClinicalTrials.gov官方API v2可访问的全部唯一study records。不预先应用study type、sponsor、status、phase、date、intervention或therapeutic-area筛选。分析单位是一个唯一NCT ID。

- `UNKNOWN`：没有可用的注册location-country值。
- `PERMISSIBLE`：至少有一个可用国家，并且没有配置中定义的美国地点。
- `US_ONLY`：完整的unique country set恰好为`{United States}`。
- `US_NON_CHINA_MULTI`：包含美国、不包含中国，并且至少包含另一个非美国国家。
- `NEXUS`：至少包含一个美国地点和一个中国地点；也可以同时包含其他国家。

基线定义严格使用`United States`和`China`。Puerto Rico及其他美国领地不会自动视为美国；Hong Kong、Macau/Macao和Taiwan不会自动视为中国。全部定义位于`config.json`。

五个类别互斥且穷尽。缺失location data绝不会被分类为Permissible。Nexus和Permissible本身不能划分整个registry：known-location studies首先分为`NO_US`（即PERMISSIBLE）和`HAS_US`；`HAS_US`再分为`US_ONLY`、`US_NON_CHINA_MULTI`和`NEXUS`。

```text
All studies
├── UNKNOWN
└── Known-location studies
    ├── NO_US
    │   └── PERMISSIBLE
    └── HAS_US
        ├── US_ONLY
        ├── US_NON_CHINA_MULTI
        └── NEXUS
```

以known-location studies和HAS_US studies为分母的比例属于辅助诊断。主口径仍然使用all-study denominator。

## 支持的分析范围

项目使用同一个经过验证的五分类地理模型，保留两个独立标记的视图：

1. **全部可访问研究**：原始完整snapshot视图，输出到`runs/run_<timestamp>/out_v2/`。
2. **仅Interventional**：仅包含`study_type == "INTERVENTIONAL"`，输出到`runs/run_<timestamp>/out_interventional/`。

Interventional分母只包含registry中的精确值`INTERVENTIONAL`；不包含`OBSERVATIONAL`、`EXPANDED_ACCESS`、空值或其他study types。该视图筛选已验证的`out_v2/trials.csv`并复用最终分类，因此不需要再次调用API，也不会修改raw snapshot。

## Start Date时间段比较

新snapshot还保留ClinicalTrials.gov的`StartDate`和`StartDateType`。时间比较回答：注册Start Date位于不同时期的研究，其注册地点地理分布如何变化？Start Date是registry metadata，并不等于已确认的first-participant enrollment；该描述性比较不代表因果关系。

默认使用`manifest.json`中的UTC harvest date作为确定性的reference date。可以通过`--reference-date YYYY-MM-DD`覆盖。项目使用精确日历边界：

- `RECENT_3Y`：`reference date − 3 years < Start Date <= reference date`。
- `YEARS_4_TO_6_AGO`：`reference date − 6 years < Start Date <= reference date − 3 years`。
- 更早、未来、缺失/无法解析，以及部分日期跨越边界的记录，分别标记为`OLDER_THAN_6Y`、`FUTURE`、`TIME_UNKNOWN`和`TIME_AMBIGUOUS`。

只有月或年精度的日期被视为可能日期区间。只有当整个区间完全落在同一个cohort内时才进行分组；程序不会默默补造具体日期或月份。

### 轻量streaming summary

如果只需要Nexus / Permissible和时间段聚合结果，请使用`--summary-only`。该模式验证完整manifest、所有page及SHA-256 hash，逐页读取raw data，按NCT ID去重并立即更新共享的地理和时间计数器，不在内存中保留全部studies或locations。

```bash
python analyze.py \
  --run runs/run_<full-run-timestamp> \
  --output-name out_time_summary \
  --summary-only
```

它只输出`summary.json`、`summary.md`和`nexus_permissible_summary.xlsx`，不会创建row-level CSV、country files、Study Detail或Locations sheets。

summary workbook包含：

- Executive Summary
- Classification Summary
- Time Comparison
- Time Location Pivot
- Definitions
- Run Metadata

完整manifest必须明确确认不存在剩余next-page token。summary-only模式仍然强制检查hash、raw/unique count、duplicates、六个time cohorts的geographic reconciliation，以及JSON/Markdown/Excel聚合结果一致性。部分snapshot或内部矛盾的snapshot会被拒绝。

该模式将持久化分析输出从数百MB降低到几KB，同时保留raw snapshot以支持可复现性。Standard mode仍可用于详细导出，并与summary-only使用相同的geographic classifier、date parser、time-cohort assignment和aggregate-summary builder。

### Industry Drug-containing候选审计

新snapshot请求API v2结构化字段`InterventionType`、`LeadSponsorClass`和`Phase`。使用`--study-product drug`分析以下候选总体：

```text
LeadSponsorClass == INDUSTRY
AND at least one InterventionType == DRUG
```

默认值为`--study-product all`，因此原有all-study行为保持不变。

使用`--study-product drug-only`可以要求去重后的Intervention Type集合精确等于`{DRUG}`。该filter不会纳入`DRUG + DEVICE`、`DRUG + OTHER`或其他混合组合。

```bash
python analyze.py \
  --run runs/run_<completed-timestamp> \
  --output-name out_time_drug_summary \
  --summary-only \
  --study-product drug
```

加入`--phase-audit`会强制要求snapshot包含`Phase`，并在summary-only Excel中生成`Phase_Audit_Summary`和`Phase_By_Intervention`。审计保留精确phase组合，同时划分为`EARLY_TO_PHASE3_ONLY`、`CONTAINS_PHASE4`、`NA_ONLY`、`MISSING`和`OTHER_COMBINATION`五个互斥组。它比较全部DRUG-containing、DRUG-only及各自不含PHASE4的诊断视图，但不会自动决定最终“创新药”filter；PHASE4仅作为postmarketing proxy。

候选筛选在NCT ID去重之后、更新所选时间/地理计数器之前执行。在`--summary-only`模式下，一个小型counter会保留Industry Drug-containing studies中出现的每种精确intervention-type组合，并生成`Intervention_Type_Audit` sheet，而不保留row-level studies。

对于DRUG + DEVICE、DRUG + OTHER或DRUG + PROCEDURE等组合，在查看实际分布前不预先设置最终排除规则。如果snapshot的manifest缺少任一必需字段，程序会拒绝分析；缺失字段不会被推断。

加入`--study-type interventional`可以把所有分析分母和intervention-type audit限制为结构化`StudyType`恰好等于`INTERVENTIONAL`的records。默认仍为`--study-type all`，以保持旧输出不变。

```bash
.venv/bin/python analyze.py \
  --run runs/run_<timestamp> \
  --output-name out_time_interventional_industry_drug_audit \
  --summary-only \
  --study-type interventional \
  --study-product drug
```

### 国家参与趋势

`country_participation.py`是一个附加的、仅聚合分析，用于按Study Start Year描述注册location-country的地理广度。其cohort精确定义为：

```text
StudyType == INTERVENTIONAL
AND LeadSponsorClass == INDUSTRY
AND contains at least one InterventionType == DRUG
```

包含DRUG的混合intervention组合仍然纳入。脚本验证完整manifest和每个raw page的SHA-256，按NCT ID去重，且不改变Nexus/Permissible模型。

```bash
.venv/bin/python country_participation.py \
  --run runs/run_<completed-timestamp> \
  --outdir reports/country_participation_trend
```

输出包括轻量年度CSV、首次参与和returning-country CSV、summary-only workbook、Markdown report，以及PNG/SVG趋势图。不会生成study-level export。2000年以前的Start Dates明确标记为回溯登记时期数据。表格保留snapshot当年并标记为partial year，三张趋势图则统一截止到最后一个完整Start Year，排除当前未完整年度。

同一分析还使用显式且纳入版本控制的`continent_mapping.json`报告年度大洲参与率。六大洲定义由联合国统计司M49地区派生：Northern America、Central America和Caribbean合并为North America，South America保持独立。

一项study若在多个大洲有注册地点，会在每个参与大洲分别计算一次，因此大洲比例是非互斥的，总和可能超过100%。主分母仍是当年开始的全部eligible studies，包括没有可用location country的studies。

额外的年度NEXUS序列统计注册location-country set同时包含精确`United States`和`China`的eligible studies，也允许同时存在其他国家。输出年度数量、占全部和known-location studies的比例、三年移动平均、PNG/SVG图以及summary-only Excel sheet。

## 安装与快速开始

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python selftest.py

python harvest.py --outdir runs --limit-pages 3
python analyze.py --run runs/run_<smoke-test-timestamp> --output-name out_v2

python harvest.py --outdir runs
python analyze.py --run runs/run_<full-run-timestamp> --output-name out_time \
  --reference-date 2026-07-16

python analyze.py --run runs/run_<full-run-timestamp> \
  --output-name out_time_summary --summary-only

python analyze_interventional.py \
  --source runs/run_<full-run-timestamp>/out_v2/trials.csv \
  --all-summary runs/run_<full-run-timestamp>/out_v2/summary.json \
  --outdir runs/run_<full-run-timestamp>/out_interventional

python audit_interventional.py \
  --source runs/run_<full-run-timestamp>/out_v2/trials.csv \
  --outdir runs/run_<full-run-timestamp>/out_interventional
```

不要把limited-page output作为最终结果引用。生成的Markdown、JSON和Excel都会明确标记`PARTIAL_NON_FINAL_SMOKE_TEST`。只有分页正常结束且不存在next-page token时，snapshot才是完整的；程序不会硬编码预期study总数。

## 工作流程

`harvest.py`只请求API v2中必要的字段，包括注册Start Date、Start Date type、Intervention Type和Lead Sponsor Class。它支持可配置的page size、timeout、User-Agent，以及针对网络错误、HTTP 429和5xx响应的指数退避重试，并持续跟随所有next-page tokens。

Raw page JSON写入带时间戳的目录。manifest记录参数、counts、completeness、duplicates和SHA-256 hashes。抓取失败的run会生成`HARVEST_FAILED.txt`，不能作为有效snapshot分析。

`analyze.py`验证manifest、每个raw file hash、raw count和unique count，然后按NCT ID去重；第一个经过byte verification的record被确定性保留。Study type和status作为metadata保留，默认不参与筛选。

Standard mode输出：

- `summary.md`和`summary.json`
- `trials.csv`：每个唯一NCT ID一行
- `locations_long.csv`：每个注册facility/location一行
- `country_counts.csv`和`country_vocabulary.csv`
- `nexus_permissible_results.xlsx`及其所需worksheets

大型location数据会根据`excel_location_rows_per_sheet`自动拆分为`Locations`、`Locations_002`及后续sheets；默认每个sheet包含500,000条数据行。

Workbook还包含`Time_Comparison`和`Time_Location_Pivot`；`Study_Detail`保留raw/canonical Start Date、原始日期精度、type和分配的time cohort。每个目标cohort都有独立分母，并进行五分类zero-difference reconciliation。

修订后的五分类输出默认放在`runs/run_<timestamp>/out_v2/`，保留历史`out/`结果。可以使用`--output-name`指定其他版本化目录。整个`runs/`目录默认被gitignore，因此生成的API数据和报告不会进入Git，除非明确使用force-add。

Interventional-only命令在独立的`out_interventional/`目录生成：

- `summary_interventional.md`
- `summary_interventional.json`
- `trials_interventional.csv`
- `nexus_permissible_interventional.xlsx`

Workbook包含Executive Summary、Classification Summary、Study Detail、Definitions、Run Metadata和All-vs-Interventional Comparison sheets。

## 已发布结果——2026-07-16 snapshot

- **All-study结果：** 594,066项studies；原有workbook可从[`results-20260716` release](https://github.com/FloraPiao03/nexus-permissible-analysis/releases/tag/results-20260716)下载。
- **Interventional-only结果：** 精确范围为`study_type == "INTERVENTIONAL"`；共453,297项studies，其中2,377项NEXUS（0.5244%），250,059项PERMISSIBLE（55.1645%）。可查看[已提交的Interventional summary](runs/run_20260716T092516Z/out_interventional/summary_interventional.md)，或从[`results-interventional-20260716` release](https://github.com/FloraPiao03/nexus-permissible-analysis/releases/tag/results-interventional-20260716)下载详细workbook。

Interventional workbook SHA-256：

```text
697b80cab03bc55c57863ffd47ecc7fbbad696deb6f8077db66071e84e9f45ce
```

## 验证

强制检查覆盖NCT IDs、duplicate reporting、raw-file hashes和counts、bucket exhaustiveness、category invariants、正确分母，以及Excel/JSON count agreement。缺失或无法验证的manifest会被拒绝。Partial snapshots可以用于smoke test，但会在Markdown、JSON和Excel中明确标记为非最终结果。

运行离线结构化测试：

```bash
python selftest.py
python -m unittest discover -v
```

Synthetic cases手工指定以下预期结果：

- 美国+中国
- 仅美国
- 美国+非中国国家
- 仅中国
- 欧洲地点
- 缺失、空白及纯空格地点
- Puerto Rico及美国领地
- Hong Kong
- Macau/Macao
- Taiwan
- exact-string aliases
- duplicate NCT IDs
- observational和interventional studies

## 已知限制

- Registry facilities可能处于计划状态，也可能不完整、过时或缺失。
- Country strings严格按照`config.json`解释；每次运行后应检查`country_vocabulary.csv`。
- 每次run是特定时间点的API snapshot，可能与之后的run不同。
- Facility location不代表participant nationality，也不能证明国家层面的实际recruitment或enrollment。
- 去重时保留第一个通过byte verification的NCT ID记录，并报告duplicates供复查。

## 相关文档

- [英文README](README.md)
- [中文交接文档](HANDOVER_ZH.md)
- [英文交接文档](HANDOVER_EN.md)
- [Streaming summary交接](HANDOVER_STREAMING_SUMMARY_ZH.md)
- [对话交互记录](CONVERSATION_RECORD_ZH.md)
