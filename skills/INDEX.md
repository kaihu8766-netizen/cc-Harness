# 技能索引（自动生成，别手改）

> 冷启动读这份就够；命中触发词再用 `python tools/gateway.py skill <name>` 加载全文。

| 技能 | 用途 | 触发词 | 加载命令 |
|---|---|---|---|
| **apply_form** | 网申填表（apply_form）· 辅助模式：2026-11-02 起改为辅助模式：用户主操作，执行层做备料、高置信度填入、验真与记账。 | 网申、投递、填表、保存简历、改岗 | `gateway.py skill apply_form` |
| **deploy_verify** | 部署验证（deploy_verify）：1. 本地先过本地渲染/语法检查。 | 部署、上线、发布、线上校验 | `gateway.py skill deploy_verify` |
| **doc_build** | 文档构建（doc_build）：1. 事实清单确认（不得写未发生的事）。 | 改简历、生成、PDF、排版、导出文档 | `gateway.py skill doc_build` |

## 使用纪律

1. 用户提到上表任一触发词 → **先加载技能再动手**，不许凭记忆做。
2. 加载后按 SKILL.md 的步骤与红线执行；技能里的"实证坑"优先于你的直觉。
3. 新技能加进 skills/<name>/SKILL.md 后，跑 `python tools/skills_index.py` 刷新本表。
