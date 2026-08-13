# 当前分析进度简报

**整理日期：** 2026-07-30  
**最新数据snapshot：** 2026-07-22  
**当前结论：** 主分析已经完成并可用于mentor汇报；Phase分析尚未开展，混合DRUG intervention的进一步排除规则尚未决定。

## 1. 当前真正的主分析范围

当前最终使用的filter是：

```text
StudyType == INTERVENTIONAL
AND LeadSponsorClass == INDUSTRY
AND contains at least one InterventionType == DRUG
```

具体含义：

- 只保留结构化`StudyType`精确等于`INTERVENTIONAL`的研究；
- Lead Sponsor的结构化class必须精确等于`INDUSTRY`；
- 至少有一个结构化`InterventionType == DRUG`；
- `DRUG + DEVICE`、`DRUG + OTHER`、`DRUG + BIOLOGICAL`等混合组合目前仍然保留；
- 没有额外按phase、status、therapeutic area或completion date筛选；
- 分析单位是一个唯一NCT ID，同一研究只计算一次；
- 总体分析不要求有Start Date或location，缺失值进入相应的UNKNOWN/time-unknown类别；
- 年度趋势使用注册的Study Start Date，而不是Completion Date。

最新主分析总体为：

| 项目 | 数量 |
|---|---:|
| 符合最终filter的研究 | 78,893 |
| 有可用location country | 70,564 |
| 没有可用location country | 8,329 |

需要特别区分：

- **83,159**是前一版“Industry + Drug-containing”候选总体，尚未限制StudyType；
- **78,893**是当前最终主分析总体，已经进一步限制为Interventional；
- 后续正式汇报应以**78,893**为主，不要把两个分母混用。

## 2. 数据是否完整

最新完整run：

```text
runs/run_20260722T020135Z
```

完整性状态：

| 检查项 | 结果 |
|---|---:|
| API | ClinicalTrials.gov API v2 |
| Raw pages | 595 |
| Raw studies | 594,972 |
| Unique NCT IDs | 594,972 |
| Duplicate NCT IDs | 0 |
| `snapshot_complete` | true |
| 剩余next-page token | 无 |
| Limited-page smoke test | 否 |

该snapshot抓取了：

- NCT ID
- Brief Title
- Study Type
- Overall Status
- Start Date和Start Date Type
- Intervention Type
- Lead Sponsor Class
- Location facility、city、state、zip和country

它**没有抓取Phase字段**，所以当前不能可靠输出Phase 1/2/3/4比例。

## 3. 当前地理分类

每项研究按完整unique country set进入以下五个互斥类别之一：

| 类别 | 定义 |
|---|---|
| `NEXUS` | 同时包含精确`United States`和精确`China`；允许还有其他国家 |
| `PERMISSIBLE` | 有至少一个可用国家，但不包含`United States` |
| `US_ONLY` | 完整国家集合恰好为`{United States}` |
| `US_NON_CHINA_MULTI` | 包含美国、不包含中国，并至少包含另一个非美国国家 |
| `UNKNOWN` | 没有可用location country |

这些类别互斥且穷尽：

```text
NEXUS + PERMISSIBLE + US_ONLY + US_NON_CHINA_MULTI + UNKNOWN
= 全部符合filter的研究
```

国家定义是精确匹配：

- 美国：`United States`
- 中国：`China`
- Hong Kong、Macau/Macao、Taiwan不自动归入China；
- Puerto Rico和其他美国领地不自动归入United States。

## 4. 当前主结果

### 五分类总体结果

| 类别 | Study数 | 占78,893项研究 |
|---|---:|---:|
| NEXUS | 2,130 | 2.70% |
| PERMISSIBLE | 32,188 | 40.80% |
| US_ONLY | 21,601 | 27.38% |
| US_NON_CHINA_MULTI | 14,645 | 18.56% |
| UNKNOWN | 8,329 | 10.56% |
| **总计** | **78,893** | **100.00%** |

为了简化业务汇报，报告中还使用：

```text
NON_EXEMPT = US_ONLY + US_NON_CHINA_MULTI
```

因此：

| 汇总类别 | Study数 | 比例 |
|---|---:|---:|
| NEXUS | 2,130 | 2.70% |
| PERMISSIBLE | 32,188 | 40.80% |
| NON_EXEMPT | 36,246 | 45.94% |
| UNKNOWN | 8,329 | 10.56% |

`NON_EXEMPT`只是汇报层面的合并类别，不替代底层五分类。

## 5. 已完成的时间分析

使用字段：

```text
ClinicalTrials.gov registered Start Date
```

Reference date固定为2026-07-22：

```text
RECENT_3Y:
2023-07-22 < Start Date <= 2026-07-22

YEARS_4_TO_6_AGO:
2020-07-22 < Start Date <= 2023-07-22
```

每个时间段的比例都使用该时间段内符合最终filter的全部研究作为分母。

### 两个主要时间段

| 指标 | Recent 3Y | 4–6 Years Ago | 变化 |
|---|---:|---:|---:|
| Cohort研究数 | 11,242 | 11,591 | -349 |
| NEXUS数 | 708 | 585 | +123 |
| NEXUS比例 | 6.30% | 5.05% | +1.25个百分点 |
| PERMISSIBLE数 | 5,539 | 5,501 | +38 |
| PERMISSIBLE比例 | 49.27% | 47.46% | +1.81个百分点 |
| US_ONLY比例 | 21.30% | 23.93% | -2.63个百分点 |
| US_NON_CHINA_MULTI比例 | 15.34% | 19.69% | -4.34个百分点 |
| UNKNOWN比例 | 7.78% | 3.87% | +3.91个百分点 |

可以进行的描述性表述：

> 在当前ClinicalTrials.gov样本及filter下，Recent 3Y的NEXUS绝对数量和占比均高于4–6 Years Ago；PERMISSIBLE比例也有所提高，而US_ONLY和US_NON_CHINA_MULTI比例下降。

不能据此直接解释原因。特别是Recent 3Y的UNKNOWN比例更高，说明location缺失对时间比较有影响，因此报告同时保留known-location分母作为敏感性口径。

## 6. 已完成的Intervention Type审计

在78,893项当前研究中：

| Intervention组合 | 数量 | 比例 |
|---|---:|---:|
| 仅DRUG | 71,337 | 90.42% |
| DRUG + OTHER | 3,160 | 4.01% |
| DRUG + BIOLOGICAL | 2,063 | 2.61% |
| DRUG + DEVICE | 779 | 0.99% |
| DRUG + PROCEDURE | 414 | 0.52% |
| 其他包含DRUG的组合 | 其余 | 小比例 |

目前规则是“只要包含DRUG就保留”。尚未决定是否排除`DRUG + DEVICE`、`DRUG + OTHER`等组合。

## 7. 已完成的年度国家趋势

分析范围仍然是同一批78,893项Interventional + Industry + Drug-containing studies。

已统计：

- 每个Start Year的eligible studies；
- 每年涉及的unique countries；
- 三年滚动活跃国家数；
- 自1991年以来的累计国家数；
- 首次出现的国家；
- 中断至少一年后重新出现的国家；
- 2024–2025国家覆盖变化。

核心观察：

- 完整年度最高unique-country count为108，出现在2006和2018；
- 2024年覆盖105个国家；
- 2025年覆盖85个国家，减少20个；
- 但eligible studies从2024年的3,574增加到2025年的3,784；
- 因此2025更像是地域覆盖收窄或集中，而不是研究总量下降；
- 2026是partial year，不能与完整年度直接比较。

## 8. 已完成的大洲趋势

六大洲mapping由联合国M49地区定义派生。

大洲比例的公式是：

```text
当年在该大洲至少有一个注册地点的study数
÷
当年全部eligible studies数
```

不是“该大洲国家数÷全部国家数”。

一项跨洲study会在每个涉及的大洲分别计数一次，所以各洲比例非互斥，合计可能超过100%。

部分结果：

| 大洲 | 2015 | 2025 |
|---|---:|---:|
| Asia | 27.82% | 51.03% |
| North America | 57.48% | 45.40% |
| Europe | 37.27% | 26.11% |

可以描述为：

> 亚洲在年度研究组合中的参与率明显提高；北美洲和欧洲的相对参与率下降。

这不等于患者比例、site比例或国家数量比例。

## 9. 已完成的年度NEXUS趋势

年度NEXUS定义与总体分析一致：同一study的注册location中同时包含`United States`和`China`。

已输出：

- 每年NEXUS study数；
- NEXUS占当年全部eligible studies的比例；
- NEXUS占当年known-location studies的比例；
- 三年移动平均；
- PNG、SVG、CSV和Excel sheet。

部分结果：

| 年份 | NEXUS数 | 占当年全部eligible studies |
|---:|---:|---:|
| 2015 | 41 | 1.28% |
| 2020 | 148 | 4.44% |
| 2025 | 292 | 7.72% |
| 2026 | 104 | 3.83%，partial year |

2025是当前最高的完整年度。

总体NEXUS为2,130，而1991–2026年度图中合计为2,128。两者口径不同：年度图只纳入主报告年份范围内具有可用Start Year的研究，因此不应要求与不受年份限制的总体数完全相等。

## 10. 已生成的主要文件

### 当前主分析

- [主Summary Markdown](reports/INTERVENTIONAL_Industry_DRUG/summary.md)
- [主Summary JSON](reports/INTERVENTIONAL_Industry_DRUG/summary.json)
- [主Summary Excel](reports/INTERVENTIONAL_Industry_DRUG/nexus_permissible_summary.xlsx)

这些文件与最新run中的原始分析输出hash一致。

### 国家、大洲和年度NEXUS趋势

- [趋势分析说明](reports/country_participation_trend/country_participation_summary.md)
- [趋势分析Excel](reports/country_participation_trend/country_participation_analysis.xlsx)
- [年度国家数图](reports/country_participation_trend/annual_country_participation_trend.png)
- [年度大洲参与率图](reports/country_participation_trend/annual_continent_participation_trend.png)
- [年度NEXUS图](reports/country_participation_trend/annual_nexus_studies_trend.png)

### 历史mentor报告——不要作为当前最终filter的主报告

- [历史Markdown报告](reports/FINAL_NEXUS_TIME_ANALYSIS_REPORT.md)
- [历史Word报告](reports/FINAL_NEXUS_TIME_ANALYSIS_REPORT.docx)

虽然文件名中包含`FINAL`，但这两个文件使用的是2026-07-20的**all-study snapshot**（594,543项研究），不是当前78,893项Interventional + Industry + Drug-containing总体。

因此：

- 可以将它们作为旧版方法和报告结构参考；
- 不应将其中的总体数和比例作为当前主分析结果汇报；
- 当前可信的主结果应以`reports/INTERVENTIONAL_Industry_DRUG/`和`reports/country_participation_trend/`为准；
- 如果mentor需要一份合并后的最终Word报告，下一步应基于当前78,893项结果重新生成，而不是继续使用旧`FINAL_NEXUS_TIME_ANALYSIS_REPORT.docx`。

## 11. 技术完成度

- 完整snapshot已下载并保留；
- manifest、page count、next-page token和duplicate count已确认；
- 支持streaming summary，不生成几百万条location rows；
- summary JSON、Markdown和Excel已生成；
- 国家、大洲和NEXUS年度图已生成；
- 当前测试：**53/53通过**；
- reports目录中的主summary与最新run输出hash一致。

## 12. 尚未完成或需要决定的事项

### 尚未完成

1. **Phase分析没有完成。**  
   当前snapshot没有请求Phase字段。若需要Phase 1/2/3/4比例，必须扩展harvest字段并重新抓取，或从另一份确实包含Phase的可验证数据源读取。

2. **尚未加入ClinicalTrials.gov以外的registry。**  
   当前结果只代表ClinicalTrials.gov，不能代表全球全部临床试验。

3. **没有进行因果推断。**  
   当前是描述性registry analysis，不能证明政策、成本、市场或监管因素导致了趋势。

4. **当前filter下的合并版mentor Word报告尚未重新生成。**  
   现有`FINAL_NEXUS_TIME_ANALYSIS_REPORT.docx`属于旧all-study口径。

### 仍需业务决定

1. 是否继续保留所有mixed DRUG combinations；
2. 是否将known-location比例作为主口径，还是继续把all-eligible比例作为主口径；
3. 最终向mentor重点展示时间cohort比较，还是年度国家/大洲/NEXUS趋势；
4. 是否需要新增Phase字段并重新抓取。

## 13. 最简结论

如果现在只需要知道项目做到哪里，可以记住以下四点：

1. **主filter已经确定：Interventional + Industry + 包含DRUG，共78,893项。**
2. **五分类、Recent 3Y vs 4–6Y、国家趋势、大洲趋势和年度NEXUS趋势都已完成。**
3. **最新数据显示NEXUS在Recent 3Y及近年年度序列中均有所上升，但这只是描述性证据。**
4. **当前唯一明显缺口是Phase没有抓取；mixed DRUG组合是否进一步排除仍需决定。**
