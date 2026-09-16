# 主结果表（方法论文草案）

下表只汇总冻结、可复现的实现与协议审计结果。它不包含机制发现、临床效用、模型排名或独立生物医学样本量。

| 评估层 | 预设问题 | 结果 | 可写入论文的边界 |
| --- | --- | --- | --- |
| 因子化合成套件 | 完整 TRACER 是否遵守五项冻结准入条件？ | 32/32 完整草稿与 evaluator-only 高优先级标签一致 | 确定性实现验证，不是模型行为或生物学结论 |
| 溯源覆盖消融 | 漏引冻结证据能否被拦截？ | 32/32 漏引草稿被完整 TRACER 拒绝 | 证明草稿完整性约束，不代表真实文献综述表现 |
| 运输门消融 | 若关闭跨测量层级/区室运输门，何时发生错误升级？ | 32/32 与预设反事实一致；1 个仅运输失败的包错误升为 `HIGH` | 证明该门的实现级保护作用，不估计临床风险 |
| 来源独立性门消融 | 若按队列名称而非审计来源组计数，何时发生错误升级？ | 32/32 与预设反事实一致；1 个仅来源独立性失败的包错误升为 `HIGH` | 证明同源重复计数的实现级保护作用，不证明真实队列必然独立 |
| 全队列 FDR 门消融 | 若只检查前两队列 FDR，何时发生错误升级？ | 32/32 与预设反事实一致；1 个第三队列 FDR 失败的包错误升为 `HIGH` | 证明不能选择性忽略后续复制队列，不估计统计功效 |
| 朴素计数式基线 | 若只按队列名和前两个 FDR 决定优先级，会放行多少冻结错误？ | 32/32 与预设比较器规则一致；7 个不合格包错误升为 `HIGH`，完整 TRACER 为 0 | 算法比较器，不是临床或已有商业系统的性能比较 |
| 真实跨层级硬负例 | 小模型是否会声称注册表不支持的同测量层级复现？ | 270/270 解析成功；18/18 单元均为 15/15 假同层级声明 | 全部包来自一个依赖来源簇，不能作为模型排名 |
| 完整 TRACER 对真实硬负例 | 是否发生危险 `HIGH` 准入？ | 0/270 被接纳为 `HIGH`；0/270 危险升级 | 说明此固定压力测试中的协议门行为，不是一般安全性证明 |

## Table 1 的冻结因子化版本

正式可复核的 Table 1 已由 `scripts/29_summarize_factorized_safety_benchmark_v2.py` 生成：

- [英文投稿表](table1_factorized_safety_benchmark_v1.md)：完整草稿中 Full TRACER 为 `0/31` unsafe `HIGH`，去掉 transport、source-independence 或 all-cohort FDR 任一门均为 `1/31`，朴素计数基线为 `7/31`；
- [机器可读 TSV](../results/tables/table1_factorized_safety_benchmark_v1.tsv)：保留每个错误升级所对应的冻结 packet ID；
- [机器可读汇总](../results/factorized_safety_benchmark_summary_v1.json)：保留精确决策率、所有分母及源结果哈希；
- [冻结校验清单](../config/factorized_safety_benchmark_freeze_v1.json)：对 32 个包、注册表和原始算法验证结果的 SHA-256 进行锁定。

该表将完整草稿与 32 个“漏引证据”草稿分开报告。后者是 provenance-coverage 的草稿完整性压力测试，不能与完整草稿的 31 个不合格准入包混为同一个分母。它们也不能与 270 条依赖簇内的小模型文本轨迹合并计算。

## 可复跑顺序

```bash
python3 scripts/28_run_factorized_synthetic_suite_v2.py
python3 scripts/29_summarize_factorized_safety_benchmark_v2.py
python3 scripts/30_freeze_factorized_safety_benchmark_v1.py --verify
```

## 推荐结果表述

“在冻结的、跨测量层级的真实硬负例中，三种资源受限本地模型在三个随机种子和两种提示条件下均产生未经注册表支持的同测量层级复现声明。TRACER 将所有此类草稿拒绝或降为低优先级。由于 15 个包共享同一来源面板，该结果应被解释为依赖簇内的压力测试，而非模型间效能比较或生物医学结论。”
