# 产品周刊 · product-weekly

面向有固定研究范围的产品经理和研究者，组织周度竞争情报：确定问题、检查原始入口、核验日期与交付条件、读取产品评论、比较信息关系、分析技术机制，输出正文和独立研究说明。

当前方法版本3.4，属于研究工作流与辅助脚本。已经产出多品牌样刊并有程序、结构和教学验证；相对人工研究或普通AI提示的真实召回、节时及读者收益仍未验证。不承诺全网完整、科学自动排名、实时监控或所有渠道自动可用。

## 安装

将本仓库的文件放入skills目录下的product-weekly子目录，保持SKILL.md、references、scripts等相对结构。已安装Git时，在终端执行：

```text
git clone https://github.com/mars7745223-oss/product-weekly.git
```

随后把克隆得到的product-weekly目录复制到宿主的skills目录。调用标识为$product-weekly；仓库不提供自动定时或后台监测服务。

本仓库公开自有研究方法和辅助工具，第三方采集引擎位于vendor；自有内容目前保留版权，MIT草案未生效，详见下文许可说明。

## 适用与最小输入

适合连续跟踪多条产品线、需要说明出处与比较条件的研究。偶尔了解几条新闻可用更轻量的方法。正文分析止于事实与有条件推断，不制定本品功能、研发或路线图建议。

最低输入是本品参照和研究期限。尽量提供读者、任务、地区、已有竞品池；缺失时以公开任务形成有限研究范围，不假设内部痛点。

```text
使用 $product-weekly 制作本周豆包产品周刊，关注中国消费端的文件制作、图像和语音任务。
```

把本目录复制到宿主的skills发现目录，并保留相对结构；在Codex中通常为用户目录下`.codex/skills/product-weekly`。用其他宿主时按其技能发现方式配置。安装文件与个人研究台账分开。

## 运行条件

- 方法执行需要宿主代理具备搜索、网页读取和文件读写能力，权限决定实际来源可达性。
- 记录校验、评分与采集适配入口使用Python标准库；采集引擎自己的最低版本和依赖见vendor文档。实际测试环境为Python3.12.14，跨操作系统的完整行为尚未逐一验证。
- 采集适配器可尝试无凭证模式；API、社区或网络不可用时使用宿主常规检索，并记录缺口。引擎exit0和文件存在不表示已经取得线索。
- 默认输出正文PDF、研究说明PDF与可编辑原稿。基线渲染器需要ReportLab和包含中文的TrueType字体；不内嵌第三方商业字体，不依赖个人缓存或其他品牌目录。

PDF可选依赖：`python -m pip install -r requirements-pdf.txt`。使用已安装的依赖时无需重复安装。`--font`可指定本机有权使用的字体；未找到兼容字体会报错，不把缺字输出当成功。已有确认样式优先，基线不承诺与历史样刊像素相同。

## 可复现教学例子

examples里的品牌、评论、数字和网址都是虚构材料，不是新闻，不联网核验。覆盖计划故意保留失败单元；检查通过不代表覆盖完全。

```text
python scripts/check_issue.py examples/teaching-issue.json --output teaching-check.json
python scripts/score_priority.py assets/priority-input-template.json
python scripts/score_priority.py assets/priority-input-template.json --sensitivity examples/weight-scenarios.json
python scripts/render_weekly.py examples/teaching-weekly.md --output teaching-weekly.pdf
python -m unittest discover -s tests -v
```

`check_issue.py`exit0只表示记录规则通过，exit1表示发现记录错误，exit2表示输入不可读取。它不检查网页真实性、主张是否科学或用户是否得益。旧JSON需显式备份迁移，不会自动改写历史。

新建完整JSON参考assets/issue-record-template.json及references/record-schema.md。普通周刊按references/coverage-and-priority.md做轻检查；用户要求验证流程效果时才读references/evaluation.md。程序、行为、检索与读者效果分别报告。

## 输出与限制

正文保持先本品后竞品，原声内嵌相应产品，技术专题有机制、应用关系和关键条件。方法、日期精度、访问缺口、采样、评分和排序理由放独立说明。来源、主张、事件与判断关联并保留更正历史。

PDF渲染支持标题、段落、列表、常见表格、链接和本地图片。原始HTML按文字处理；复杂Markdown、公式或Mermaid需专门处理并视觉核验，不能把代码块称为流程图。跨地区可用性、评论身份和样本规模按实际证据限定。

## 许可与归属

本目录自有内容尚未选择对外复用许可，暂按默认版权状态保留；“公开仓库”不自动授予开源许可。LICENSE.proposed-MIT只是未来发布时可选草案，未生效。用户明确选择后再配置根级LICENSE，不影响本机使用。

第三方last30days与bird-search的MIT许可和固定版本记录保持原样，见THIRD_PARTY_NOTICES.md。采集引擎不是本项目从零开发；本项目贡献在研究编排、证据/日期约束、适配、记录校验和交付。个人研究数据、原始附件、第三方图片及评论不随skill默认打包。

定时、消息、持续监测和GitHub发布需用户另行明确要求；本更新不自动创建这些外部动作。
