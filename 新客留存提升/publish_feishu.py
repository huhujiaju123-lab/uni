#!/usr/bin/env python3
"""将新客次月留存提升方案发布为飞书文档（含真实表格）"""
import requests, json, time

APP_ID = "cli_a937e91d7f38dbd8"
APP_SECRET = "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze"
BASE = "https://open.feishu.cn/open-apis"

token = None
headers = {}

def init():
    global token, headers
    token = requests.post(f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET}).json()["tenant_access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ── block 构造器 ──
def txt(s, bold=False):
    e = {"text_run": {"content": s}}
    if bold: e["text_run"]["text_element_style"] = {"bold": True}
    return e

def H(lv, s):   return {"block_type": lv+2, f"heading{lv}": {"elements": [txt(s)]}}
def P(*e):       return {"block_type": 2, "text": {"elements": list(e)}}
def B(*e):       return {"block_type": 12, "bullet": {"elements": list(e)}}
def O(*e):       return {"block_type": 13, "ordered": {"elements": list(e)}}
def Q(*e):       return {"block_type": 15, "quote": {"elements": list(e)}}
def TABLE(rows, cols): return {"block_type": 31, "table": {"property": {"row_size": rows, "column_size": cols, "header_row": True}}}

def add(doc_id, parent_id, children, label=""):
    """添加子块，返回结果"""
    BATCH = 30
    results = []
    for i in range(0, len(children), BATCH):
        batch = children[i:i+BATCH]
        r = requests.post(f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
            headers=headers, json={"children": batch, "index": -1})
        d = r.json()
        if d.get("code") == 0:
            results.extend(d.get("data", {}).get("children", []))
        else:
            print(f"  ⚠️ {label} batch {i//BATCH+1}: {d.get('msg','')[:120]}")
        time.sleep(0.3)
    return results

def fill_table(doc_id, table_result, data_rows):
    """填充表格。data_rows = [[cell_str, ...], ...]"""
    cells = table_result.get("table", {}).get("cells", [])
    flat_data = [cell for row in data_rows for cell in row]
    for cell_id, text in zip(cells, flat_data):
        bold = (data_rows.index([r for r in data_rows if text in r][0]) == 0)  # header row bold
        r = requests.post(f"{BASE}/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
            headers=headers,
            json={"children": [{"block_type": 2, "text": {"elements": [txt(str(text), bold=bold)]}}]})
        time.sleep(0.05)

def add_table(doc_id, parent_id, data_rows, label=""):
    """创建表格并填充数据。data_rows[0] = header。"""
    rows = len(data_rows)
    cols = len(data_rows[0])
    results = add(doc_id, parent_id, [TABLE(rows, cols)], label)
    if results:
        tbl = results[0]
        cells = tbl.get("table", {}).get("cells", [])
        flat = [str(c) for row in data_rows for c in row]
        for i, (cell_id, text) in enumerate(zip(cells, flat)):
            is_header = i < cols
            requests.post(f"{BASE}/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
                headers=headers,
                json={"children": [{"block_type": 2, "text": {"elements": [txt(text, bold=is_header)]}}]})
            time.sleep(0.05)
        print(f"  ✅ 表格 {label}: {rows}×{cols}")
    return results

# ── 文档内容 ──
def build_doc(doc_id):
    # 顶部信息
    add(doc_id, doc_id, [
        P(txt("文档版本：v1.0 | 更新日期：2026-03-24")),
        P(txt("负责人：李宵霄 | 部门：数据分析 / 增长运营")),
    ], "header")

    # 一、项目背景
    add(doc_id, doc_id, [
        H(1, "一、项目背景"),
        H(2, "1.1 为什么做这个项目"),
        P(txt("Lucky US 新客次月留存率目前在 "), txt("15-18%", bold=True), txt(" 水平。当前的核心矛盾是：我们有很多零散的策略和实验（涨价实验、分享有礼、券包测试），但没有一个系统性的留存提升框架。")),
        H(2, "1.2 项目目标"),
    ], "s1")
    add_table(doc_id, doc_id, [
        ["指标", "当前基线", "3个月目标", "6个月目标"],
        ["新客次月留存率", "~15-18%", "22-25%", "28-30%"],
        ["首单→二单转化率", "待测", "+5pp", "+10pp"],
        ["二单间隔天数(中位数)", "待测", "<10天", "<7天"],
    ], "目标")

    add(doc_id, doc_id, [
        H(2, "1.3 已有基础"),
        B(txt("数据能力成熟：SQL 模板库、470 份生产 SQL 学习沉淀、CyberData API 直连")),
        B(txt("已完成 3 轮价格实验（0119新客涨价/0212老客涨价/0311价格实验）")),
        B(txt("分享有礼已运行数月，有完整漏斗数据（2月拉新占比 5.23%）")),
        B(txt("用户生命周期分层（0-15天/16-30天/30+天）已建立")),
        B(txt("AB 实验框架完善：Fixed/Rolling Cohort/Daily Dimension 三种模式")),
    ], "基础")

    # 二、国内经验
    add(doc_id, doc_id, [
        H(1, "二、国内经验（2026-03-24 会议纪要）"),
        Q(txt("3月24日与国内策略负责人进行了46分钟的深度沟通，以下是核心结论。")),
        H(2, "2.1 留存基准对比"),
    ], "s2")
    add_table(doc_id, doc_id, [
        ["市场", "次月留存", "门店数", "运营时长", "说明"],
        ["中国（现在）", "~20%出头", "30,000+", "多年", "早期也是30%+"],
        ["马来（第9个月）", "~30%", "40+", "9个月", "对标意义更大"],
        ["Lucky US（现在）", "15-18%", "12", "~12个月", "门店密度是底层限制"],
    ], "基准")

    add(doc_id, doc_id, [
        P(txt("关键认知：", bold=True), txt("门店密度是留存的底层变量。用户喝完首杯后如果门店覆盖不到，策略再好也拉不动。但在门店密度受限的前提下，券包+触达+品类引导仍有明确提升空间。")),
        H(2, "2.2 核心差距诊断"),
    ], "认知")
    add_table(doc_id, doc_id, [
        ["维度", "国内做法", "US现状", "差距"],
        ["券包设计", "多张低价券(~1.5折/¥9.9)按时间窗口拆", "$1.99/$2.99/$3.99/5折，$2.99和$3.99基本废券", "需重新设计"],
        ["滚动培养", "D3/D7/D14/D30自动检索未二单用户塞券+触达", "仅券到期提醒，无主动培养", "从0到1"],
        ["新人专区", "注册后跳专属页面：简化菜单+首位价", "注册后进普通首页", "产品缺失"],
        ["单品引导", "低价单品券(¥0.99生椰浆)引导尝试爆品", "品类上无特别引导", "需分析"],
        ["触达频控", "每人每周最多1次，严格品控", "无系统化频控", "需建规则"],
        ["实验体系", "所有策略留对照组，最优合并为新基线", "有实验但策略分散", "需整合"],
    ], "差距")

    add(doc_id, doc_id, [
        H(2, "2.3 国内同事给的三条核心路线"),
        Q(txt('"就是三条路。"——国内策略负责人')),
    ], "路线标题")
    add_table(doc_id, doc_id, [
        ["#", "路线", "具体内容", "对US适用性"],
        ["1", "新人券包加深", "去掉废券，换成多张低价券，按0-7天/7-14天拆窗口", "立即可做"],
        ["2", "站内营销工具", "首单后弹窗领券、新人专区、任务体系", "需产品支持"],
        ["3", "站外滚动触达", "D3/D7/D14/D30滚动客群，塞券+Push/短信", "核心抓手"],
    ], "三条路")

    # 三、现状摸底
    add(doc_id, doc_id, [
        H(1, "三、现状摸底计划（第1-2周）"),
        H(2, "3.1 需要跑的数据"),
    ], "s3")
    add_table(doc_id, doc_id, [
        ["#", "数据项", "口径", "分维度"],
        ["1", "近6个月新客次月留存率趋势", "当月首单→次月有下单比例", "按月"],
        ["2", "D3/D7/D14/D30留存曲线", "首单后N天内有二单的比例", "按月cohort"],
        ["3", "分门店次月留存率", "按首单门店拆分", "12家店"],
        ["4", "开店首月vs后续月份留存对比", "开业首月vs第3月新客差异", "门店×开店月"],
        ["5", "首单品类→留存率", "不同首单品类的D14/D30留存", "品类分组"],
        ["6", "首单券面额→留存率", "不同面额首单券的留存差异", "券面额"],
        ["7", "二单品类分布", "复购用户第二单喝什么", "TOP10品"],
        ["8", "首单→二单间隔天数", "中位数/P75/P90", "整体+分店"],
        ["9", "复购vs流失用户特征对比", "客单价、品类、时段、券面额差异", "—"],
    ], "数据项")

    add(doc_id, doc_id, [H(2, "3.2 历史策略效果回顾")], "回顾标题")
    add_table(doc_id, doc_id, [
        ["策略", "时间", "对留存影响", "关键数据"],
        ["0119新客涨价", "2026-01-19起", "D30复购率-4.99pp,LTV+4.2%", "对照34.39%vs涨价29.40%"],
        ["新客弹层券AB", "2026-01", "低价券留存更高", "A组$2.99:63.3% B组$1.99:70.9%"],
        ["0212老客涨价", "2026-02-12起", "活跃用户最敏感", "涨价组2 -7.4%"],
        ["分享有礼", "持续", "拉首单,不直接提复购", "D14转化率61.3%"],
    ], "历史策略")

    add(doc_id, doc_id, [H(2, "3.3 门店维度洞察")], "门店洞察标题")
    add_table(doc_id, doc_id, [
        ["发现", "说明", "行动"],
        ["开店首月新客留存最高", "30-40%次月复购,吸引咖啡忠实用户", "作为基线上限参考"],
        ["第3-4个月开始下降", "周边该转化的都转化了", "自然衰减,可解释"],
        ["机场店排除", "纯流量型(JFK)", "分析时排除"],
        ["学校店体量最大", "4-5家学校店,9月开学季暴增", "重点关注学校店"],
        ["店少=单店分析更有意义", "12家店逐店看", "逐店拉留存率"],
    ], "门店洞察")

    # 四、优化策略
    add(doc_id, doc_id, [
        H(1, "四、优化策略（整合国内经验+自有数据）"),
        H(2, "4.1 策略全景图"),
        P(txt("四大方向：", bold=True), txt("券包重构(P0) + 滚动培养(P0) + 产品体验(P1) + 单品引导(P1)")),
        H(2, "4.2 P0：券包重构"),
        P(txt("问题：", bold=True), txt("现有券包中 $2.99 与大盘持平无优势，$3.99 核销率仅 1.99%，基本是废券。")),
    ], "s4")
    add_table(doc_id, doc_id, [
        ["券序", "现有", "建议调整", "依据"],
        ["首单券", "$1.99(次日可用)", "保持不变", "次日生效防当天用完"],
        ["第二张", "$2.99(无时间限制)", "$1.99,有效期0-7天", "需低于大盘70-80%"],
        ["第三张", "$3.99(无时间限制)", "$1.99,有效期7-14天", "$3.99几乎无人核销"],
        ["第四张", "5折(无时间限制)", "去掉或改$0.99单品券", "折扣券在低客单价无感知差异"],
        ["新增", "无", "D14-30天再塞一张$1.99", "覆盖30天完整窗口"],
    ], "券包重构")

    add(doc_id, doc_id, [
        P(txt("核心逻辑：", bold=True), txt("券的核心不是核销，是回访。塞了券用户就知道「我还有券」，回访率就提升。宁可多塞几张 $1.99，也不要一张 $3.99 废券。")),
        H(2, "4.3 P0：滚动培养机制"),
        P(txt("当前缺失的核心能力：", bold=True), txt("没有对「首单后未复购」用户的主动干预。")),
    ], "券逻辑")
    add_table(doc_id, doc_id, [
        ["时间节点", "客群定义", "动作", "触达方式", "文案方向"],
        ["D+3", "首单后3天未下二单", "塞券$1.99", "Push", "送你一张$1.99券"],
        ["D+7", "首单后7天未下二单", "塞券$1.99", "短信", "你的专属券即将到期"],
        ["D+14", "首单后14天未下二单", "塞券+单品推荐", "Push", "很多新朋友都在喝XX"],
        ["D+30", "首单后30天未下二单", "最后一次触达", "短信", "为你保留了一张专属券"],
    ], "滚动培养")

    add(doc_id, doc_id, [
        P(txt("关键规则：", bold=True)),
        B(txt("客群每天滚动更新（今天的D3客群=3天前首单且未复购的用户）")),
        B(txt("每人每周最多触达1次（Push和短信算同一触点）")),
        B(txt("已自然复购的用户自动移出客群")),
        B(txt('文案用「送你」而非「提醒你」，强调获得感')),
        H(2, "4.4 P1：产品体验优化"),
    ], "规则")
    add_table(doc_id, doc_id, [
        ["策略", "国内做法", "US可行方案", "依赖"],
        ["新人专区", "注册→跳专区→简化菜单+塞券", "短期用弹窗+Banner;中期提需求", "产品团队"],
        ["首单后弹窗", "首单后弹领券活动(有获得感)", "用现有弹窗工具实现", "运营配置"],
        ["任务体系", "新客完成任务获奖励", "探索「下3单解锁XX」", "需产品支持"],
    ], "产品优化")

    add(doc_id, doc_id, [
        H(2, "4.5 P1：单品引导策略"),
    ], "单品标题")
    add_table(doc_id, doc_id, [
        ["策略", "说明", "行动"],
        ["分析品→留存", "首单品类与D14/D30留存关系", "跑数据确认哪些品留存最高"],
        ["推爆品", "国内首推生椰(市占最高/成本低)", "US生椰占比20%+,可主推"],
        ["低价单品券", "国内用¥0.99生椰浆引导尝试", "做$0.99指定品券"],
        ["看二单品分布", "复购用户第二单喝什么", "跑数据看二单品类TOP10"],
    ], "单品引导")

    # 五、实验路线图
    add(doc_id, doc_id, [
        H(1, "五、实验路线图"),
        H(2, "第一批（第3-5周）：券包+触达"),
    ], "s5")
    add_table(doc_id, doc_id, [
        ["实验", "假设", "方案", "核心指标"],
        ["券包重构", "多张$1.99按时间拆>现有券包", "全局切换,前后对比", "次月留存率"],
        ["滚动培养D3", "D3塞券>无干预", "先做D3一个节点", "D7复购率"],
        ["触达文案AB", "「送你」>「提醒你」", "两种文案分批测试", "Push打开率"],
    ], "实验1")

    add(doc_id, doc_id, [H(2, "第二批（第6-8周）：品类+体验")], "实验2标题")
    add_table(doc_id, doc_id, [
        ["实验", "假设", "方案", "核心指标"],
        ["低价单品券", "$0.99指定品>通用折扣券", "二单券改$0.99爆品券", "D14复购率"],
        ["首单后弹窗", "弹窗领券>静默发券", "首单完成后弹领券弹窗", "二单转化率"],
        ["滚动培养全链路", "D3+D7+D14+D30>仅D3", "完整链路上线", "D30留存率"],
    ], "实验2")

    add(doc_id, doc_id, [H(2, "第三批（第9-12周）：精细化")], "实验3标题")
    add_table(doc_id, doc_id, [
        ["实验", "假设", "方案", "核心指标"],
        ["门店差异化", "低留存门店专属券>通用策略", "按门店定向发券", "单店留存率"],
        ["成长任务", "下3单解锁奖励>无任务", "阶梯奖励", "30天3单以上占比"],
        ["竞对门店券", "星巴克旁放码>无物料", "A字架+$3.99领券码", "该店新客量"],
    ], "实验3")

    add(doc_id, doc_id, [
        P(txt("实验方法论：", bold=True)),
        B(txt("所有策略都留对照组")),
        B(txt("最优实验组合并为新对照组 → 再上新实验 → 持续迭代")),
        B(txt("US产品限制不能对新客分流，用「按周切换」或「前后对比」替代")),
        B(txt("注意纽约天气波动对前后对比的干扰")),
    ], "方法论")

    # 六、工具与能力建设
    add(doc_id, doc_id, [
        H(1, "六、工具与能力建设"),
        H(2, "6.1 能力Gap分析"),
    ], "s6")
    add_table(doc_id, doc_id, [
        ["能力", "现状", "目标", "行动"],
        ["留存看板", "无自动化看板", "自动化D3/D7/D14/D30趋势图", "基于日报系统扩展"],
        ["滚动客群", "无", "每日自动生成未复购客群", "确认品控是否支持"],
        ["触达频控", "无系统化规则", "每人每周最多1次", "与运营对齐"],
        ["门店级分析", "手动", "自动化逐店留存报告", "SQL模板已有"],
        ["品→留存", "从未做过", "品类×留存率交叉表", "跑一次数据"],
    ], "能力Gap")

    add(doc_id, doc_id, [H(2, "6.2 US产品限制")], "限制标题")
    add_table(doc_id, doc_id, [
        ["限制", "影响", "替代方案"],
        ["新客不能分流", "无法AB测试不同券包", "按时间切换,前后对比"],
        ["无新人专区", "新客注册后进普通首页", "弹窗+Banner替代"],
        ["券包只能全局配一个", "不能同时测多种券包", "按周切换"],
        ["品控客群功能存疑", "曾出现不生效问题", "先测试功能可用性"],
    ], "限制")

    # 七、项目节奏
    add(doc_id, doc_id, [H(1, "七、项目节奏")], "s7")
    add_table(doc_id, doc_id, [
        ["周次", "阶段", "关键产出", "负责"],
        ["W1-2", "现状摸底", "留存基线报告(9项)、门店级分析", "数据"],
        ["W2", "工具建设", "留存看板v1、滚动客群方案", "数据+运营"],
        ["W3", "策略设计", "券包重构方案、培养SOP", "运营"],
        ["W3-5", "第一批实验", "券包重构+D3触达上线", "运营"],
        ["W6-8", "第二批实验", "单品券、弹窗、全链路", "运营+产品"],
        ["W9-12", "第三批实验", "门店差异化、成长任务", "运营+产品"],
        ["W12", "阶段总结", "ROI评估、策略合并", "全员"],
    ], "节奏")

    # 八、风险
    add(doc_id, doc_id, [H(1, "八、风险与应对")], "s8")
    add_table(doc_id, doc_id, [
        ["风险", "影响", "应对"],
        ["留存需30+天评估", "实验周期长", "用D3/D7作早期预测"],
        ["产品不支持新客分流", "无法AB", "前后对比+按周切换"],
        ["Push触达率低", "策略打折", "Push+短信+弹窗组合"],
        ["门店密度低(12家)", "天花板限制", "单店提升+线下物料"],
        ["天气波动大", "前后对比不干净", "选稳定期或拉长窗口"],
        ["涨价策略与留存冲突", "ARPU vs 留存", "建平衡模型"],
    ], "风险")

    # 九、关键认知
    add(doc_id, doc_id, [
        H(1, "九、关键认知（6条铁律）"),
        O(txt("门店密度是留存的底层变量", bold=True), txt(" — 12家店覆盖不了，用户喝完首杯回不来。但券+触达+品类仍有明确空间。")),
        O(txt("券的核心不是核销，是回访", bold=True), txt(' — 塞了券用户就知道「我还有券」→回访率提升。文案写「送你」不写「提醒你」。')),
        O(txt("养到4单就稳了", bold=True), txt(" — 国内数据：4单以内不稳定，4单以上相对稳定。30天内完成3-4单是关键。")),
        O(txt("裂变不提留存", bold=True), txt(" — 分享有礼是拉新量的工具，复购靠券包+触达+品类引导。两件事分开做分开看。")),
        O(txt("先整合基础框架，再叠加测试", bold=True), txt(' — 不是零散做实验，而是先搭「券包+触达+专区」基础架构，然后叠加测试。')),
        O(txt("开店首月新客质量最高", bold=True), txt(" — 30-40%留存率，之后下降是正常的。新店开业是获取高质量新客的黄金窗口。")),
    ], "铁律")

    # 十、附录
    add(doc_id, doc_id, [
        H(1, "十、附录"),
        H(2, "10.1 数据口径约定"),
    ], "s10")
    add_table(doc_id, doc_id, [
        ["指标", "口径"],
        ["新客", "当月首次下单用户（按自然月切）"],
        ["次月留存", "当月首单用户中，次自然月有下单的比例"],
        ["成功订单", "order_status=90（DWD表）"],
        ["杯量", "COUNT(*)，不是COUNT(DISTINCT order_id)"],
        ["饮品实收", "one_category_name='Drink'的pay_amount"],
        ["排除", "type NOT IN(3,4,5)、排除测试店、门店订单"],
    ], "口径")

def main():
    print("1/3 初始化...")
    init()
    print("  ✅ Token OK")

    print("2/3 创建飞书文档...")
    r = requests.post(f"{BASE}/docx/v1/documents", headers=headers,
        json={"title": "Lucky US 新客次月留存率提升方案"})
    d = r.json()
    if d.get("code") != 0:
        print(f"  ❌ {d.get('msg','')[:200]}")
        return
    doc_id = d["data"]["document"]["document_id"]
    print(f"  ✅ doc_id: {doc_id}")

    print("3/3 写入内容（含16张表格）...")
    build_doc(doc_id)

    url = f"https://lkusco.feishu.cn/docx/{doc_id}"
    print(f"\n🎉 完成！\n📄 {url}")

if __name__ == "__main__":
    main()
