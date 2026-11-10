# A股六维公司研究 Skill

一套可复用的上市公司六维深度研究与估值方法，将“公司是否优秀”与“证券当前是否有吸引力”分开回答。

## 安装

前往 [Releases](https://github.com/laizhenxing/company-analysis/releases) 下载最新的 `a-share-six-dimension-research.skill`，在支持本地技能导入的 Kimi 环境中选择“导入本地技能”。

也可以直接查看[中文使用说明](docs/A股六维公司研究-使用说明.md)。

## 使用方法

导入后直接说：

- “用六维框架全面分析贵州茅台，兼顾长期价值与当前估值。”
- “帮我研究三花智控，区分已实现业绩、券商预测和情景假设。”
- “根据最新季报更新这家公司的分析，告诉我哪些核心假设变了。”

## 研究框架

1. 商业模式与单位经济；
2. 行业地位与护城河；
3. 财务质量；
4. 管理层、治理与资本配置；
5. 成长驱动与历史／同业／反向／情景估值；
6. 风险、催化剂与证伪路径。

所有关键数字须注明报告期、单位、口径和来源。公司事实、公司表述、市场观察、券商预测、自主复算和情景假设分层展示，不凭记忆编造金融数据。

## 仓库内容

- `a-share-six-dimension-research/`：可直接打包的 Skill 源文件；
- `docs/`：面向最终用户的中文使用说明；
- `scripts/package_skill.py`：本地打包工具，仅依赖 Python 标准库；
- `.github/workflows/release-skill.yml`：自动校验、打包并发布安装包到 Releases。

## 本地打包

需要 Python 3.9 或更高版本：

```bash
python3 scripts/package_skill.py
```

安装包生成于 `dist/a-share-six-dimension-research.skill`。

## 免责声明

本项目仅用于研究方法和信息交流，不构成个性化投资建议或收益保证。金融数据、预测与估值均须结合最新披露独立核验。
