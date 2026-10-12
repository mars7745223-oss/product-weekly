# 当期结构化记录契约 v2

完整JSON记录使用`schema_version: product-weekly-issue/2`。Markdown轻量任务可以表达同样关系，不强制生成全部对象。`scripts/check_issue.py`只检验结构、关联与日期/状态一致性；不会检索网页、测量市场覆盖或替代人工事实核验。

顶层对象：issue、competitors、sources、events、claims、voices、research、inferences、coverage_plan、editorial；KIQ可通过kiqs数组提供。稳定ID沿用，不以方法升级重建。旧格式先备份并显式迁移，校验器不会悄悄改写文件。

| 对象 | 必要字段/关系 |
|---|---|
| issue | issue_id、scope_id、window_start、window_end、cutoff_at、timezone；日期未知不捏造 |
| competitors | competitor_id、product_line、tier、aliases、tier_history；aliases只用于追溯旧ID，规范外键用当前ID |
| sources | source_id、url、access_status；状态read/partial/failed/not_attempted/unknown，read_scope保存实际读取范围 |
| events | event_id、competitor_id（跨竞品或研究可null）、claim_ids、source_ids、event_date、weekly_status；progress另存new_evidence_date |
| claims | claim_id、competitor_id（可null）、event_id（可null）、source_ids；单一说法及其条件、原始位置另存 |
| voices | voice_id、competitor_id、source_ids、published_at、collected_at；原文、身份、任务与采样照原证据规则保留 |
| research | research_id、source_ids；正文/元数据/代码已读范围、基线和系统条件分别保存 |
| inferences | inference_id、claim_ids、voice_ids、research_ids；机制、条件、不同解释和判断历史另存 |
| coverage_plan | plan_version、origin、locked_at、cells；origin为prospective或retrospective |
| coverage cell | cell_id、competitor_id（可null）、kiq_ids、requirement、status、source_ids、checked_scope、checked_at、reason |
| editorial.must_read | item_id、rank、event_ids、inference_ids、reason、impact_band、evidence_state、review_origin |
| editorial.decisions | decision_id（可选）、event_ids、inference_ids、disposition、reason；保留排除与背景，不仅入刊项 |

weekly_status为new/progress/background/outside/unknown；new需事件时间在窗口，原材料只提供区间时可用event_date_range{start,end}且全部在窗口内，不取某一天伪装精确日期；progress需当期新证据日期，outside需已知窗口外时间。未知不能升级new。来源发表时间、事件时间、采集时间和方法修订时间保持分离；只有日期时不能假装核验到秒。

coverage requirement为required/rotation/exploration；status为completed/partial/failed/not_checked/not_applicable/unknown。completed须至少一个read来源和非空checked_scope；只读搜索片段不足以完成原页核验单元。not_applicable须理由，失败不能删除分母。校验输出只统计计划完成，retrospective结果注明事后整理。

impact_band为critical/important/context，rank连续且唯一。必读必须关联存在的事件或推断；选中事件须关联已有主张，推断须有证据对象。脚本检查“理由存在”不检查理由科学性。view/阅读量、源数量和CPS不能自动决定顺序。

迁移保存旧schema、旧ID映射、备份哈希、方法修订日期与处理理由；若已有初筛和定稿Tier冲突，记录两者及采用依据，不回填过去的调整时刻。无新检索不改事实采集/核验日期。底座保存当前有效状态和aliases，期记录与底座冲突必须修复或解释版本关系，不能用同名字符串自行合并不同产品线。

```text
python scripts/check_issue.py 当期证据.json --base 研究底座.json --output 记录检查.json
```

exit 0是记录检查通过，exit 1是发现错误，exit 2是输入不可读取；warnings表示保留的缺口，不能自动填补。旧schema返回unsupported_schema，不能因为未满足新格式认定旧事实错误。模板和教学例子分别见assets/issue-record-template.json、examples/teaching-issue.json。

使用--base时提供与期记录匹配的完整底座版本：期内每个竞品都须存在且当前Tier一致，底座可含其他观察对象。旧期若需保留旧分层，使用已保存的当期底座快照，不能把历史有效状态覆盖为今天的状态。事件列出的主张须反向指向该事件；独立背景主张可保持event_id=null并不列入某一事件。
