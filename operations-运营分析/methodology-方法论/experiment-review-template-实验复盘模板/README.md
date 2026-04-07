# 实验复盘模板库

## 目录用途

这里专门维护线上运营实验的复盘规则、提示词、样例和迭代记录。

适用范围：
- 触达实验
- 塞券策略
- 弹窗资源位
- 新客召回
- 滚动培养
- 任务活动
- 其他通过 AB、分群包、尾号分流等方式上线的运营动作

这套模板的目标不是“生成一段看起来像分析的文字”，而是稳定产出可决策的实验复盘结果。

当前主模板已经覆盖三类场景：
- 通用结果层实验
- 任务类活动
- 分享有礼活动

## 目录结构

- `prompts-提示词/universal-experiment-review-prompt-通用实验复盘Prompt.md`
  - 当前主模板，后续默认都从这里出发
- `reference-参考样例/0326-experiment-analysis-0326数据分析.xlsx`
  - 第一份参考样例，来自 0326 时段实验
- `notes-迭代记录/experiment-review-template-changelog-实验复盘模板迭代记录.md`
  - 后续每次规则调整、口径收紧、结构变化，都记录在这里

## 当前模板的核心原则

1. 先确认核心假设，再开始分析
2. 缺口必须显式写出，不能静默跳过
3. 输出必须使用固定结构和固定表头
4. 统计不显著时，只能讲方向，不能折算收益
5. 结论要先说谁优谁弱、差多少、是否显著
6. 任务类活动必须补任务链路
7. 分享有礼必须补裂变链路

## 使用方式

默认把下面两类材料一起喂给 AI：

1. 实验背景材料
   - 实验名称
   - 实验编号 / 实验层
   - 上线时间
   - 实验组与对照组定义
   - 观察窗
   - 业务目标

2. 数据材料
   - 分组累计结果
   - 显著性检验
   - 补充指标
   - 缺失项说明

然后使用：
- [universal-experiment-review-prompt-通用实验复盘Prompt.md](/Users/xiaoxiao/Vibe%20coding/operations-%E8%BF%90%E8%90%A5%E5%88%86%E6%9E%90/methodology-%E6%96%B9%E6%B3%95%E8%AE%BA/experiment-review-template-%E5%AE%9E%E9%AA%8C%E5%A4%8D%E7%9B%98%E6%A8%A1%E6%9D%BF/prompts-%E6%8F%90%E7%A4%BA%E8%AF%8D/universal-experiment-review-prompt-%E9%80%9A%E7%94%A8%E5%AE%9E%E9%AA%8C%E5%A4%8D%E7%9B%98Prompt.md)

## 后续维护约定

后续所有通用复盘规则都只在这个目录更新，不再分散写在单个实验文件里。
