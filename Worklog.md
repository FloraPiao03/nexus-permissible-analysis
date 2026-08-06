## 数据请求与字段
- 从 Clinicaltrial.gov 的 API 请求数据，下载的每条 raw study 只请求了本次分析需要的字段，并非该研究的相关完整记录。

        具体包括：
        NCTId：NCT 编号
        BriefTitle：研究简短标题
        StudyType：研究类型，例如 INTERVENTIONAL、OBSERVATIONAL
        OverallStatus：总体状态，例如 RECRUITING、COMPLETED
        LocationFacility：注册或计划中的研究设施名称
        LocationCity：城市
        LocationState：州、省或地区
        LocationZip：邮政编码
        LocationCountry：国家

- 后面还增加了 startdate、phase？等数据，同时对需要的数据的范围重新进行了规范。

> 所以这个流程告诉我：需要对实际业务的需求进行提前的明确，如果作为提高效率的手段，需要在第一次 meeting 的时候就尽量确认；而能够确认的前提是，你知道这个数据库里面有哪些分类标准或者叫做每个 clinical trial 的 data 有哪些标签，我们可能需要限制的维度有哪些，这些属于对业务的熟悉程度，如果在第一次 meeting 的时候对业务细节还不熟悉，就需要尽快在会后熟悉并确认

        一个 study 可以包含：
        0 个 location；
        1 个 location；
        很多个 location。

- AI 自动进行烟雾测试，即使用低通量先检测这个体系的可行程度，再把全部的 trials 数据导入

> 问题：烟雾测试的比例是如何确定的？一般使用全部数据量的百分之多少作为烟雾测试的数据？

- 最初实现主要按照需求中指定的固定工作表：Locations, 并在三页烟雾测试中验证。
    
    三页只有 18,998 条 location，远低于 Excel 的 1,048,576 行上限，所以测试能够正常通过。但我没有在初始设计阶段用全量规模做容量推演：

        约 59 万 studies
        × 平均约 6 个 locations
        ≈ 300 多万 location rows
    这导致最初代码虽然满足小规模功能测试，却无法安全覆盖真实全量规模。正确做法应该从一开始就同时考虑：

        Excel 单工作表的硬行数限制；
        openpyxl 普通模式的内存占用；
        一项研究可能对应多个 locations；
        烟雾测试成功不代表全量规模一定安全。

而且这个风险其实可以提前从业务结构推断出来，不应该等下载后才发现。

> 问题：在进行大体积数据的处理和下载的过程中，应该先从小体量开始测试系统的可行度；同时评估大体量数据的内存占用和生成的过程文件对系统的占用的问题，需要考虑经过数据处理之后系统内不应该留有过多的无效文件、垃圾文件的问题。

---
# 首个snapshot
对Clinicaltrial.gov 中的数据的单个字段 location 进行了提取，区分开 Nexus 和 Permissible 类别。以及 US_only, Unknown.
后续发现 USonly 的定义有误，重新进行了统计。因此此阶段的结果就先不放在这里。

- 最后确认的 snapshot 是

        StudyType == INTERVENTIONAL
        AND LeadSponsorClass == INDUSTRY
        AND contains at least one InterventionType == DRUG

### Eligible Study 数量
| 指标 | 数量 |
|---|---:|
| Eligible studies | 78,893 |
| 有效 Start Year | 77,914 |
| Start Date 缺失或无效 | 979 |
| 无有效 location country | 8,329 |
| 1991 年以前 | 32 |
| 2026 年以后 | 52 |
| 1991–2026 主报告期 | 77,830 |

- 每年的 study 数量情况：
从2000-2005 迅速上升（考虑可能是临床试验注册规范性增加，可能并不完全代表真实临床试验的数量变化，但是仍需要证据证明是否在 2006 开始，规范性就逐渐稳定了？是否有某些条款发布？）； 
2006 年开始至2019，基本维持在 3000 左右；
在 2020-2021 有 study 数量的跃升，2021 的 study 数量是巅峰（4079）；
2021 之后有所回落，但是也大约维持在比2020 之前更高的水平（约 3500）



# 统计/分析维度
## Overall Annual Country Count Trend
统计每年符合筛选条件的 study 涉及到的国家的数量的变化趋势。
- 最大同比增加：+24 个国家1994 相比 1993：2 → 26
1998 相比 1997：29 → 53

- 最大同比下降：−20 个国家2025 相比 2024：105 → 85

本分析衡量的是：
本分析统计每个研究开始年份中，所有符合条件的 ClinicalTrials.gov 临床研究所覆盖的去重 location-country 数量。
没有根据 sponsor、城市、标题或 investigator 推断国家。

> 因此就是，一个临床试验有多个 register 的 location country，这个字段统计的就是一共注册了多少个 location country。

## Nexus count
## Continent participation count 
每项 study 在每个大洲最多计算一次。每个 study 如果在同一大洲有多个 location 也只计算一次。
分母是当年开始的所有 study 数量，每个study 在每个大洲只计算一次，说明的是在这么多个 study 当中，有多少个涉及了这个大洲。
> 为什么不用所有 study 涉及的 country 数量为分母，对不同大洲，每个 study 每涉及一个 country 分子就加一（也就是每个 study 如果涉及一个大洲内的多个国家就按照国家数量计算？是因为如果涉及国家的话，那是否还要按照国家内的 study site数量计算？

在当前 ClinicalTrials.gov 研究范围内，industry-sponsored drug studies 的地点配置明显增加了对亚洲的覆盖；与此同时，北美洲和欧洲在年度研究组合中的相对参与比例下降。

