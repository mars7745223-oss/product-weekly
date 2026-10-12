# 国内外来源种子

初始设计日期 2026-10-07。以下部分入口在设计时曾核验；这是发现索引，不是活跃连接清单。每次选用时确认主体、产品、当前 URL、内容、地区与访问方式。不把本文件日期当作消息日期。

先按[竞品选择](competitor-selection.md)确定具体对象，再取入口。以XREAL为参照时，优先扫描VITURE、RayNeo和Rokid的相关产品线，XREAL提供简短参照；不会默认把所有大厂、跨界产品和供应商都扩成竞品。跨界对象只有达到特别观察门槛才独立刊出，外部机制研究按技术专题处理。

## 评论区优先

按目标产品寻找商品评价、伴随 App 评价、产品视频评论及品牌社区回复。可从京东/天猫/品牌商城、App Store/安卓商店、B站/YouTube、Amazon 等候选平台检索具体型号/应用；上述渠道的产品页面、读取条件和自动化权限均需实际验证。

评论区原声方法见 [user-voice.md](user-voice.md)。不要只读取视频或商品介绍后声称读过评论。

## 产品与工程入口

| 方向 | 种子 | 使用条件 |
|---|---|---|
| XREAL | [支持](https://www.xreal.com/support/one)、[OTA](https://www.xreal.com/ota)、[开发者](https://developer.xreal.com/)、[Reddit](https://www.reddit.com/r/Xreal/) | 支持页可发现官方社区，Discord 邀请可变；需验证具体消息与频道 |
| VITURE | [官网](https://www.viture.com/) | 从当前产品导航寻找具体型号、软件、固件、开发者与社区入口；官网媒体推荐不等于商品或社群评论 |
| RayNeo/雷鸟 | [官方商城](https://www.rayneo.com/pages/rayneo-shop) | 区分显示、AI及其他产品线，核验地区、交付阶段及配件；再寻找具体型号评论 |
| Rokid | [中文官网](https://www.rokid.com/zh-CN)、[英文官网](https://www.rokid.com/en-US)、[开放平台](https://open.rokid.com/) | 按显示/空间计算/AI等具体产品分层；论坛、App、更新与评论从当前官方入口发现，不把旧访问状态视为本次成功 |
| 小米 | [官网](https://www.mi.com/shop)、[社区](https://www.xiaomi.cn/)、[小米眼镜 App](https://app.mi.com/details?id=com.xiaomi.superhexa) | 社区有动态加载限制；对应 App/型号核实，需读取评价而非只看介绍 |
| 华为 | [消费者新闻](https://consumer.huawei.com/cn/press/news/)、[官方反馈指引](https://www.huawei.com/cn/contact-us) | 设计时反馈指向我的华为 App/花粉；路径及权限复核 |
| Apple | [Newsroom](https://www.apple.com/newsroom/) | 发布、上市、地区和系统支持条件分开 |
| Meta | [Wearables 开发者](https://developers.meta.com/wearables/) | 平台接口、地区与设备边界核实 |
| Android XR | [SDK](https://developer.android.com/develop/xr/jetpack-xr-sdk) | 预览/稳定状态、设备支持和子库更新日志 |
| Samsung | [Newsroom](https://news.samsung.com/global/) | 官方 RSS/页面是否可读实际测试 |
| Oura | [固件版本](https://support.ouraring.com/hc/en-us/articles/34036777934227-Oura-Device-Firmware-Versions) | 推送日期的语义按原文确认 |
| rabbit | [release notes](https://forum.rabbitcommunity.tech/t/rabbitos-release-notes/40)、[更新说明](https://www.rabbit.tech/support/article/rabbit-r1-software-updates) | 云端更新与 OTA 分开；公告与回复分开 |
| Omi | [仓库](https://github.com/BasedHardware/omi)、[文档](https://docs.omi.me/) | release/commit/issue 区分，社区链接从官方入口发现 |
| 上游/拆解 | [Qualcomm 发布](https://www.qualcomm.com/news/releases)、[iFixit 眼镜](https://www.ifixit.com/Device/Smart_Glasses) | 厂商宣称与样品拆解测量分别标记 |

## AI 软件与开发者产品的来源适配

参照切换到模型、API或开发工具时，沿已有观察池重建具体产品入口，不沿用硬件品牌配额。官方模型更新日志、开发文档、中文/国际发布、价格页与产品仓库分别扫描；只看模型日志可能漏掉客户端、Harness、SDK和订阅权益。版本兼容、会话管理、工具接入及完成判定可构成交付层增量，不能自动归因于底层模型。

按任务采集产品发布评论、官方开发者论坛、GitHub issue/discussion、权重讨论及可读中文社区。查旧问题后续时连接原报告、修复PR、发行说明和用户回报，区分预发布修复与实际环境成功。维护真实读取状态与日期；渠道数量不作证据独立性或质量指标。

## 研究原文入口

- [arXiv](https://arxiv.org/)及[RSS](https://info.arxiv.org/help/rss.html)/[API](https://info.arxiv.org/help/api/user-manual.html)：按任务、关键词和机构过滤，记录版本与录用状态。
- [ACM CHI](https://chi2026.acm.org/)：交互、UX、社会接受；年度入口会变。
- [IMWUT](https://dl.acm.org/journal/imwut)：移动、可穿戴和真实场景计算。
- [CVF Open Access](https://openaccess.thecvf.com/)：CVPR/ICCV 的原论文、补充材料。
- [Nature Electronics](https://www.nature.com/natelectron/)：传感、显示、低功耗与系统；原始研究与评论分开。
- [中国科学：信息科学](https://scis.scichina.com/)：国内中英文研究；单篇全文权限另核验。

国内机构的国际会议论文也记录机构和研发来源，不按发表网站所在地代替研究归属。

检索不局限品类名称。将“目标能力/系统问题＋机制＋应用条件”组合：移动参考系、观测性与重定位；流式语音、增量解码与压缩；边缘任务划分、同步和自适应渲染；事件感知、低功耗电路、光学材料与制造。通过上述原文入口追溯机制和实验，不把关键词命中当作可迁移结论。完整路径见[研究到应用](research-to-product.md)。

## 接入时需核实的规则

Reddit API 与商业用途按当前[Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)及[Data API Terms](https://redditinc.com/policies/data-api-terms)核实授权；网页可读不代表可批量采集。

Discord 按服务器/频道权限、当前 Bot/OAuth2 文档接入，不使用普通账号 self-bot；[官方说明](https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots)。没有频道读取或 Bot 权限时用人工可访问内容或公开公告镜像，标缺口。

公众号/B站账号先从企业官网或认证主体确认身份。平台无法读取时如实写状态，不凭昵称或搜索摘要编造内容。
