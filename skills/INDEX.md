# Skill index (generated)

> Read this index at startup. Load matching skills with `python tools/gateway.py skill <name>`.

| Skill | Purpose | Triggers | Load command |
|---|---|---|---|
| **apply_form** | Job application form assistance: Use this skill to prepare, fill, and verify supported fields | job application / apply for a job / fill a form / save resume / 网申 / 投递 / 填表 / 保存简历 / 改岗 | `python tools/gateway.py skill apply_form` |
| **deploy_verify** | Deployment verification: 1. Run local rendering or syntax checks. | deploy / release / go live / production check / 部署 / 上线 / 发布 / 线上校验 | `python tools/gateway.py skill deploy_verify` |
| **doc_build** | Document building: 1. Confirm the facts and trace the numbers to their sources. | edit resume / generate PDF / document layout / export document / 改简历 / 生成 PDF / 排版 / 导出文档 | `python tools/gateway.py skill doc_build` |

## Usage

1. Load the matching skill before acting.
2. Follow the steps and constraints in its SKILL.md.
3. Run `python tools/skills_index.py` after editing a skill.
