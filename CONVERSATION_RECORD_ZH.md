# Nexus / Permissible 项目交互记录

## 文档说明

本文档按当前 Codex 对话中可见的时间顺序，整理用户的每一次主要提问及 Codex 的回答或实际处理结果。

- “用户问题”尽量保留原意，但对附件中的长 prompt 使用任务摘要。
- “回答／处理”是对当时答复和实际动作的忠实摘要，不冒充逐字聊天记录。
- 同一轮中连续的追问分别记录，便于复盘需求如何逐步形成。
- 项目的最终定义、运行命令和当前能力以根目录的 `README.md`、`README_ZH.md` 及当前代码为准。

## 第一阶段：建立项目、理解抓取和完整性

### 1. 建立独立 Python 项目

**用户问题：** 根据附件 prompt，在当前目录建立一个用于计算 ClinicalTrials.gov NEXUS / PERMISSIBLE 的独立 Python repository。

**回答／处理：** 建立了抓取、分析、配置、测试和文档结构。项目使用 ClinicalTrials.gov API v2，以 NCT ID 为研究单位，并保存可复核的 raw pages、manifest 和分析结果。

### 2. “三页烟雾测试”是什么意思，为什么只有约 3,000 条研究？

**用户问题：** 什么是三页 smoke test？为什么是三页？为什么 total NCT 只有约 3,000？

**回答／处理：** 三页是人为设置的快速测试上限，用于验证 API、分页、保存和分析流程，并不是完整抓取。每页约 1,000 条，因此三页约 3,000 条。其结果只能用于测试，不能作为最终研究总数。

### 3. `harvest.py --outdir runs` 会不会下载所有页面？

**用户问题：** 执行 `.venv/bin/python harvest.py --outdir runs` 后，pages 是否会全部下载？这么多 studies 是否有地方保存？

**回答／处理：** 不设置 `--limit-pages` 时会持续跟随 `nextPageToken`，直到分页结束。每个 API page 保存为 JSON，写入 timestamped run 目录；是否够空间取决于 raw JSON 和后续导出大小。

### 4. 大概需要多少空间？

**用户问题：** 完整下载大概需要多少磁盘空间？

**回答／处理：** 说明 raw pages、CSV 和 Excel 会分别占用空间，其中 locations long-format 和 Excel 可能显著大于 raw snapshot；建议抓取前检查磁盘余量，并避免同时保留多个不必要的大型派生结果。

### 5. 必须保存本地吗？Excel 怎么拆？能否看到 harvest 正在运行？

**用户问题：** 数据必须保存到本地吗？Excel 超过行数限制怎么办？Codex 能否看到当前 harvest？

**回答／处理：** 为了可复现和完整性审计，当前设计先保存 raw snapshot；Excel 的 location rows 需要按 worksheet 行数限制拆分。Codex只能检查当前主机上可见的进程、文件数量和 manifest 状态，不能凭空看到另一个不可访问终端的实时状态。

### 6. 通过 API 统计是否必须下载？

**用户问题：** 通过 API 获取数据并统计标签，是否必须下载一些内容到本地？

**回答／处理：** API统计至少需要接收数据，但不一定永久保存全部明细。可以逐页读取、即时聚合并丢弃内存对象；若要保证结果可复核，建议保留 raw snapshot 或至少保留完整 manifest、hash 和汇总依据。

### 7. 每条 raw study 包含什么 metadata？

**用户问题：** 当前下载的每条 raw study 包含哪些字段？

**回答／处理：** 解释了抓取器只请求分析需要的 API v2 结构化字段，例如 NCT ID、study type/status、注册地点国家等；后续扩展又加入 Start Date、Start Date Type、Intervention Type 和 Lead Sponsor Class。

### 8. 一共有多少条 raw study？

**用户问题：** 当前 raw snapshot 中一共有多少条 study？

**回答／处理：** 说明需要依据 run 的 manifest、所有 page 的 study count 和去重后的 NCT ID 数核对，不能用 page 数简单猜测。

### 9. ClinicalTrials.gov 上总共有多少 study？

**用户问题：** 指的是 ClinicalTrials.gov 网站上总共有多少 study。

**回答／处理：** 说明总数是随时间变化的 API snapshot 值，应使用 API v2 的 `totalCount` 或完整抓取 manifest 在具体时间点报告，而不是使用永久固定数字。

### 10. 如何验证下载完成？

**用户问题：** 下载好像完成了，如何验证？

**回答／处理：** 检查 `manifest.json` 中 `snapshot_complete`、最后一页是否没有 next-page token、page count、raw count、unique count、duplicates 和每页 SHA-256；同时确认不是 limited-page smoke test。

## 第二阶段：Excel、GitHub 和操作概念

### 11. “应先修改 Excel 生成逻辑”是什么意思？

**用户问题：** 为什么要修改，具体怎么改？

**回答／处理：** Excel 单个 worksheet 最多 1,048,576 行。location rows 可能超过限制，因此应将 Locations 自动拆成多个 sheets，或使用 summary-only 输出避免生成巨型明细表。

### 12. 为什么最初没有直接按 Excel 限制创建？

**用户问题：** 为什么一开始创建时没有直接处理这个限制？

**回答／处理：** 承认初版对完整 registry 的 location-row 规模估计不足；完整数据运行暴露了 Excel worksheet 上限，需要补充分片输出和大数据保护。

### 13. 帮忙修改以继续下一步

**用户问题：** 请直接修改。

**回答／处理：** 调整 Excel 输出逻辑，使大型 Locations 数据能够拆分到多个 sheet，并通过测试后继续生成结果。

### 14. 上传到 GitHub

**用户问题：** 希望上传项目，可以提供命令或直接上传。

**回答／处理：** 检查 Git repository、忽略规则、认证和待提交范围，协助准备 GitHub 发布流程。

### 15. 结果也要给 mentor 查看

**用户问题：** 除了代码，还需要上传结果。

**回答／处理：** 区分代码、轻量 summary 和大型 workbook；建议 summary 进入 repository，大文件使用 GitHub Release asset，避免普通 Git history 被大型二进制文件永久膨胀。

### 16. Git 操作协议选择 HTTPS 还是 SSH？

**用户问题：** GitHub CLI 登录时应选择哪一种？

**回答／处理：** 在当前配置和使用场景下建议 HTTPS，配合 GitHub CLI 的 keyring token，设置成本低；SSH 适合已经管理 SSH key 的用户。

### 17. 上传最新 run 的大型 XLSX

**用户问题：** 继续上传最新 run 的最终结果 XLSX，即使文件很大。

**回答／处理：** 采用 GitHub Release 保存大型 workbook，并在 repository 的结果 README/summary 中提供下载链接，避免直接把大文件提交进 Git。

### 18. GitHub 已登录

**用户问题：** 已完成登录，请继续。

**回答／处理：** 继续检查认证、remote、branch 和准备发布的文件范围。

### 19. 为什么不上传 `__pycache__`、`.venv` 和 `runs`？

**用户问题：** 这些目录不上传的原因是什么？

**回答／处理：** `__pycache__` 是可重新生成的解释器缓存；`.venv` 体积大且平台相关，可由 requirements 重建；`runs` 包含大量 raw/派生数据和本地 snapshot，通常过大且可能重复，因此默认 gitignore，只选择性发布必要 summary 或 release assets。

### 20. PR 是什么？

**用户问题：** PR 的含义是什么？

**回答／处理：** PR 是 Pull Request，即把某个 branch 的改动提交给目标 branch 审查、讨论和合并的 GitHub 工作流。

### 21. Codex action approval 的三种模式

**用户问题：** Codex action approval 三种模式有什么区别？

**回答／处理：** 解释不同批准模式对应 Codex执行命令或外部操作前的确认频率与授权范围；越自动的模式越方便，但越应注意命令、文件修改和外部发布风险。

## 第三阶段：NEXUS 结果独立审计

### 22. 审计 2,521 条 NEXUS 和 0.42%

**用户问题：** 独立验证总数、四类加总、snapshot完整性、API totalCount、raw-data分类、抽样、不同分母和最终 verdict；不要先修改生产代码，不要 commit/push。

**回答／处理：** 进行了独立算术、manifest、API query、raw page重算和行级核验；区分数学正确性、API口径、分类正确性和分母解释。在发现差异前不修改生产流程，并生成临时审计 JSON 供复核。

### 23. 生成中英文 handover

**用户问题：** 总结所有更新、代码逻辑、思路和概念定义，生成中英文两个 handover Markdown。

**回答／处理：** 创建 `HANDOVER_ZH.md` 和 `HANDOVER_EN.md`，记录数据模型、分类逻辑、审计方法、运行方式、限制和交接事项。

## 第四阶段：五分类和 Interventional-only 分析

### 24. 根据附件修改现有项目

**用户问题：** 按附件要求修订 Nexus / Permissible 项目。

**回答／处理：** 将 geography model完善为互斥且穷尽的五类：UNKNOWN、PERMISSIBLE、US_ONLY、US_NON_CHINA_MULTI、NEXUS，并保留旧输出、增加版本化输出和验证。

### 25. 增加 Interventional-only 分析

**用户问题：** 在验证后的模型上增加只分析 Interventional studies 的视图。

**回答／处理：** 增加独立 interventional输出，以结构化 `StudyType == INTERVENTIONAL` 精确筛选，复用已验证的 geography classification，不需要重新抓取 snapshot。

### 26. 合适的 commit 名称

**用户问题：** 为当前版本提供 commit 名。

**回答／处理：** 建议使用能够体现范围的命名，例如 `Add validated five-bucket and interventional analyses`。

### 27. 发布 Interventional-only 结果

**用户问题：** 按附件要求发布新结果。

**回答／处理：** 准备 summary、代码和 release workbook 的发布范围，避免把整个 runs 目录无选择地加入 Git。

### 28. 登录流程没有启动

**用户问题：** GitHub 登录没有弹出或启动。

**回答／处理：** 指导重新运行 `gh auth login`、选择 HTTPS，并使用浏览器或 device code 完成认证。

### 29. 已登录

**用户问题：** 已完成登录。

**回答／处理：** 继续认证状态和发布步骤。

### 30. 提供 `gh auth status`

**用户问题：** 展示已登录账号、HTTPS协议和token scopes。

**回答／处理：** 确认账号 `FloraPiao03` 已激活且 `repo` 等 scope 足以进行 repository/release 操作；没有回显或记录实际 token。

## 第五阶段：解释 NEXUS 比例与数据覆盖

### 31. NEXUS 比例低是否合理？

**用户问题：** NEXUS 比例这么低是否合理？

**回答／处理：** 数学上可以正确，但不能仅凭直觉判断。NEXUS要求同一研究同时有美国和中国地点，是较窄的交集；以全部registry studies作分母还包含不同study types、年代和无地点数据，因此比例会低。应结合独立API和raw audit判断。

### 32. 中国试验是否可能未登记在 ClinicalTrials.gov？

**用户问题：** 是否存在仅登记在中国平台而未登记在 ClinicalTrials.gov 的 trials？

**回答／处理：** 是。ClinicalTrials.gov不是全球所有临床试验的完整全集，中国还有本国注册平台等来源。因此结果只代表当前可访问的 ClinicalTrials.gov registry，不应外推为全球全部临床试验。

### 33. 当前字段能否按时间筛选？应该用开始还是结束时间？

**用户问题：** 是否已经抓取时间字段，时间窗口应按 trial start date 还是 completion date？

**回答／处理：** 检查现有snapshot字段并解释：开始时间更适合分析某时期“新启动研究”的地域配置，结束时间容易受随访长度和仍在进行状态影响。最终用户选择 Start Date。

## 第六阶段：Start Date、streaming summary 和磁盘策略

### 34. 按附件使用 Start Date 实现时间段分析

**用户问题：** 选择 Start Date，并按附件 prompt 修改项目。

**回答／处理：** 增加 `StartDate`、`StartDateType` 的抓取和时间分组逻辑，精确处理日、月、年精度以及边界不确定日期。

### 35. 是基于旧snapshot还是重新抓取？

**用户问题：** 当前实现是读取上次snapshot中的Start Date，还是重新以当前日期抓取？

**回答／处理：** 如果旧snapshot未抓取Start Date字段，就不能从不存在的数据恢复，必须生成包含新增字段的新snapshot；代码变化与数据snapshot变化需要分别说明。

### 36. 新snapshot需要多少磁盘，是否删除7月16日snapshot？

**用户问题：** 当前空间够不够，是否应删除旧snapshot？

**回答／处理：** 建议先检查实际磁盘余量和目录大小；旧snapshot具有可复现价值，不应在未确认备份和发布结果前直接删除。可优先删除可重建的巨大派生CSV/Excel，或移动/压缩历史raw snapshot。

### 37. 能否统计后不把几百万 location rows 留在内存或磁盘？

**用户问题：** 无论提取地址还是时间，能否统计后不保存海量明细？

**回答／处理：** 可以采用 streaming aggregation：逐页读取、逐条更新计数器、处理完立即释放，不创建 `locations_long.csv`、Study Detail 或大型 Locations sheets。内存只保留去重集合和聚合计数，输出轻量 summary。

### 38. 先为 streaming 方案写 handover

**用户问题：** 先生成当前进度和最新实现设想的交接文档。

**回答／处理：** 创建 `HANDOVER_STREAMING_SUMMARY_ZH.md`，记录不保留row-level输出、逐页聚合、完整性验证、去重和最小输出方案。

### 39. 按附件扩展项目

**用户问题：** 基于当前项目实现新的summary-only能力。

**回答／处理：** 增加 `--summary-only`：验证完整manifest和page hashes，逐页聚合，输出summary JSON/Markdown/XLSX，不生成大型明细文件。

### 40. 按第二个附件继续完善

**用户问题：** 按更新后的附件约束继续实现。

**回答／处理：** 完善streaming与standard模式的一致性检查、时间cohort reconciliation、缺失/模糊时间处理和输出验证。

### 41. 执行最终完整数据工作流

**用户问题：** 实现完成后，运行最终full-data流程并生成结果。

**回答／处理：** 对完整snapshot执行分析，验证manifest、hash、分页结束、unique NCT去重和输出一致性，生成最终summary-only结果。

## 第七阶段：统计解释、mentor报告和Industry Drug筛选

### 42. 数据能够得出什么结论，统计学上是否合理？

**用户问题：** 询问当前时间和地区比较的可解释性。

**回答／处理：** 将结果定位为registry-based descriptive analysis，而非因果推断。分母必须在每个时间cohort内独立计算，报告count和percentage，并说明missing metadata、registry coverage和时间边界限制。

### 43. 生成适合mentor的报告

**用户问题：** 希望生成Word或Markdown最终报告。

**回答／处理：** 生成适合汇报的结构化报告，包含研究问题、方法、定义、核心结果、解释、限制和可复现信息。

### 44. 按附件做最小改动

**用户问题：** 对当前项目做最小范围调整。

**回答／处理：** 保留validated geography和time逻辑，仅增加所需的Industry Drug候选筛选字段及相关输出。

### 45. 修订Drug筛选

**用户问题：** 按附件用最小改动修订drug-filter。

**回答／处理：** 使用结构化 `LeadSponsorClass == INDUSTRY` 且至少一个 `InterventionType == DRUG`；混合DRUG组合先保留并输出intervention-type audit，不使用title文本推断。

### 46. 执行新的完整抓取和分析

**用户问题：** 运行包含新字段的full-data harvest，生成结果。

**回答／处理：** 生成包含 StudyType、StartDate、InterventionType、LeadSponsorClass 和 LocationCountry 的新snapshot及summary结果。

### 47. 83,159个候选的StudyType分布

**用户问题：** Industry Drug-containing candidates分别属于什么StudyType？

**回答／处理：** 从结构化StudyType统计候选研究的类型分布，用于决定后续是否将分析范围收敛到Interventional。

### 48. 只要Interventional，重新生成同维度报告

**用户问题：** 将总体限制为Interventional，并按原报告相同维度统计时间和地区比例。

**回答／处理：** 采用精确 `StudyType == INTERVENTIONAL`，所有时间和地理分母同步收敛，重新生成summary JSON/Markdown和Excel。

### 49. Summary文件在哪里？

**用户问题：** 询问生成文件的准确位置。

**回答／处理：** 提供对应run下interventional Industry Drug输出目录及summary、JSON和XLSX路径。

### 50. 将summary和XLSX复制到reports目录

**用户问题：** 建立 `INTERVENTIONAL_Industry_DRUG` 文件夹；XLSX过大则在README提供release下载链接。

**回答／处理：** 将轻量结果整理到reports目录；大型workbook采用GitHub Release链接策略，避免直接提交过大文件。

### 51. 时间段内五类地理比例的分母

**用户问题：** `RECENT_3Y` 和 `YEARS_4_TO_6_AGO` 中，五类地理比例的分母是否为该时间段全部studies？

**回答／处理：** 是。每个时间cohort分别以该cohort内符合全部筛选条件的studies为分母；五类在该cohort内互斥且穷尽并加总至100%。

### 52. 在summary中加入核心表格

**用户问题：** Markdown不能只有文字，需要NEXUS、PERMISSIBLE、其他非豁免/美国类别和UNKNOWN的count与percentage表。

**回答／处理：** 在summary正文加入核心分类表，确保每个类别同时展示数量、比例和分母口径，并与JSON/Excel一致。

### 53. 是否抓取Phase，按分类统计Phase 1/2/3/4

**用户问题：** 当前78,893条数据是否包含Phase；若有，按drug+类别导出phase比例，否则先告知没有字段。

**回答／处理：** 先检查当前harvest字段；只有snapshot实际包含structured phases时才可分析，不从其他字段推断。若manifest字段列表没有Phase，需要修改字段请求并重新抓取后才能做可靠统计。

## 第八阶段：国家、大洲和NEXUS年度趋势

### 54. 增加country-participation trend

**用户问题：** 按附件增加聚焦的国家参与趋势分析。

**回答／处理：** 新增 `country_participation.py`，按Study Start Year统计年度unique countries、三年滚动活跃国家、首次参与、间隔后回归、缺失地点和年度诊断；保持aggregate-only。

### 55. 中文解释README和折线图

**用户问题：** 解释趋势分析README，以及如何解读折线图。

**回答／处理：** 说明年度国家数衡量地理广度，而非study或site数量；三年滚动线用于减少单年度偶然波动；2000年前和当前partial year需谨慎解释。

### 56. 为什么2025明显下降，并增加大洲比例趋势

**用户问题：** 分析2025下降，同时按大洲统计不同年份占全部研究的比例。

**回答／处理：** 对2024–2025做country-level reconciliation，区分消失、新增国家及研究集中度；增加六大洲非互斥参与率图，使用UN M49派生映射。

### 57. 如何向mentor结合大洲折线和年度country count汇报

**用户问题：** 两种趋势结合可以说什么？

**回答／处理：** 建议区分“global breadth”和“regional allocation”：国家数下降不等于study数量下降；大洲比例显示研究组合向哪些地区重新配置。用描述性语言，不把趋势解释为因果。

### 58. 增加NEXUS annual折线图

**用户问题：** 需要一张NEXUS study年度折线图。

**回答／处理：** 增加annual NEXUS count、三年移动平均、占全部studies比例和占known-location比例；同步写入CSV、Markdown、Excel和PNG/SVG。独立从595个raw pages重算，无差异，53项测试通过。

### 59. 大洲比例的分母和多国study算法

**用户问题：** 分母是否为当年参与国家总数？一项study涉及多国如何处理？

**回答／处理：** 分母不是国家数，而是当年全部符合条件studies数。每项study在每个大洲最多计算一次；跨洲study会在多个大洲分别计数，所以六洲比例可超过100%。

### 60. 梳理三张图的计算和证据链

**用户问题：** 解释三张图的计算、分子分母、为何使用、能反映什么及是否属于证据链。

**回答／处理：** 将三图定位为三个互补层面：年度unique country count衡量地理广度；大洲study participation rate衡量区域配置；NEXUS count/rate衡量美中共同地点结构。三者是描述性证据链，能支持趋势判断，不能单独证明原因或正式合作。

### 61. 再次确认大洲分母和多国study

**用户问题：** 再次询问大洲比例是否以国家数为分母。

**回答／处理：** 用公式和例子再次确认分母为annual eligible studies；美国+中国+德国的一项研究分别进入北美洲、亚洲、欧洲分子，但每洲只计一次。

### 62. 完整解释三图为何能够支持研究结论

**用户问题：** 要求系统梳理三图指标、含义、证据能力和限制。

**回答／处理：** 给出完整方法说明和mentor表述：图一回答覆盖多广，图二回答区域重心，图三回答美中共同参与；只有绝对数量与标准化比例共同变化时，才能更有力排除年度总量变化的解释。强调ClinicalTrials.gov覆盖、missing locations、每项study等权、pre-2000回溯登记和2026 partial-year等限制。

## 第九阶段：当前文档交付

### 63. 生成完整交互记录和中文README

**用户问题：** 将本对话每次问答整理成Markdown，并提供README中文版。

**回答／处理：** 新增本文件 `CONVERSATION_RECORD_ZH.md` 和 `README_ZH.md`。英文 `README.md` 保留不变；中文版翻译当前项目定义、命令、输出、验证和限制，而不是替代英文源文件。

## 当前核心结论

本项目最终形成了以下分析链：

1. 通过完整API snapshot和manifest/hash验证保证数据输入可复核；
2. 使用互斥、穷尽的五分类模型描述全部研究的地点结构；
3. 使用Interventional、Industry、Drug-containing筛选形成聚焦研究总体；
4. 使用Start Date构造可重复的时间cohort和年度趋势；
5. 使用年度unique countries衡量全球地理广度；
6. 使用大洲study participation rate衡量区域配置；
7. 使用年度NEXUS count和rate衡量美国—中国共同地点结构；
8. 使用summary-only streaming方式控制内存和磁盘占用；
9. 将所有结果定位为ClinicalTrials.gov注册数据上的描述性证据，而不是因果证明。

