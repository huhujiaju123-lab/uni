#!/usr/bin/env python3
"""发布美国新客循环补丁策略简版飞书文档（含真实表格）"""

import time
import requests

APP_ID = "cli_a937e91d7f38dbd8"
APP_SECRET = "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze"
BASE = "https://open.feishu.cn/open-apis"
OPEN_BASE = "https://lkusco.feishu.cn/docx"

token = None
headers = {}


def init():
    global token, headers
    resp = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=20,
    ).json()
    token = resp["tenant_access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def txt(s, bold=False):
    e = {"text_run": {"content": s}}
    if bold:
        e["text_run"]["text_element_style"] = {"bold": True}
    return e


def H(lv, s):
    return {"block_type": lv + 2, f"heading{lv}": {"elements": [txt(s)]}}


def P(*elements):
    return {"block_type": 2, "text": {"elements": list(elements)}}


def B(*elements):
    return {"block_type": 12, "bullet": {"elements": list(elements)}}


def TABLE(rows, cols):
    return {
        "block_type": 31,
        "table": {"property": {"row_size": rows, "column_size": cols, "header_row": True}},
    }


def add(doc_id, parent_id, children):
    resp = requests.post(
        f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
        headers=headers,
        json={"children": children, "index": -1},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(data)
    time.sleep(0.2)
    return data.get("data", {}).get("children", [])


def add_table(doc_id, parent_id, data_rows):
    results = add(doc_id, parent_id, [TABLE(len(data_rows), len(data_rows[0]))])
    table_block = results[0]
    cells = table_block.get("table", {}).get("cells", [])
    flat = [str(cell) for row in data_rows for cell in row]
    cols = len(data_rows[0])
    for i, (cell_id, text_value) in enumerate(zip(cells, flat)):
        is_header = i < cols
        requests.post(
            f"{BASE}/docx/v1/documents/{doc_id}/blocks/{cell_id}/children",
            headers=headers,
            json={"children": [{"block_type": 2, "text": {"elements": [txt(text_value, bold=is_header)]}}]},
            timeout=20,
        ).raise_for_status()
        time.sleep(0.05)


def update_permission(doc_id):
    payload = {
        "external_access": False,
        "security_entity": "anyone_can_view",
        "comment_entity": "anyone_can_view",
        "share_entity": "anyone",
        "link_share_entity": "tenant_readable",
        "invite_external": False,
    }
    resp = requests.patch(
        f"{BASE}/drive/v1/permissions/{doc_id}/public?type=docx",
        headers=headers,
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(data)


def build_doc(doc_id):
    add(doc_id, doc_id, [
        P(txt("适用范围：", bold=True), txt("美国新客循环补丁策略简版说明")),
        P(txt("默认前提：", bold=True), txt("新注册用户首发券包固定为 1.99 / 2.99 / 3.99 / 5折")),
        P(txt("策略目标：", bold=True), txt("在首单后 T+60 内把用户稳定承接到第3单，提升次月留存率")),
        H(1, "一、分阶段执行表"),
    ])

    add_table(doc_id, doc_id, [
        ["阶段", "生命周期窗口", "目标", "发券规则", "提醒节奏", "频控", "退出条件"],
        ["0→1单", "注册后首周", "推动首单", "默认首发 1.99 / 2.99 / 3.99 / 5折", "D1、D6", "首周最多2次；同日最多1次", "完成首单后切到1→2单"],
        ["1→2单", "首单后T+60内", "承接二单", "每天检查；若当前无有效2.99或5折，补发2.99或5折1张；1天有效；过期后若仍未下二单，次日继续补", "D3、D7、D14、D21、D30、D45、D58", "注册首周仍受最多2次限制；第2周起每周最多1次", "完成二单后切到2→3单；或到T+60退出"],
        ["2→3单", "首单后T+60内", "承接三单", "每天检查；若当前无有效2.99或5折，补发2.99或5折1张；1天有效；过期后若仍未下三单，次日继续补", "D3、D7、D14、D21、D30", "第2周起每周最多1次", "完成三单后退出；或到T+60退出"],
    ])

    add(doc_id, doc_id, [
        H(1, "二、统一规则"),
    ])

    add_table(doc_id, doc_id, [
        ["项目", "规则"],
        ["首发券包", "固定为 1.99 / 2.99 / 3.99 / 5折"],
        ["补券类型", "2.99 或 5折，并列任选，不分阶段细拆"],
        ["补券频率", "每天检查一次"],
        ["券有效期", "1天"],
        ["循环逻辑", "过期后若仍未完成当前阶段目标，次日继续补"],
        ["提醒频控", "注册后第一周最多2次；第二周起每周最多1次"],
        ["运行逻辑", "同一时刻只跑当前阶段，不并行"],
        ["总目标", "在首单后T+60内把用户稳定承接到第3单，提升次月留存率"],
    ])

    add(doc_id, doc_id, [
        H(1, "三、备注"),
        B(txt("本版只保留已确认信息，不写未定文案、渠道或额外券型逻辑。")),
        B(txt("1→2单与2→3单的补券类型统一写为 2.99 或 5折，并列任选。")),
        B(txt("达到第3单后，退出本次新客强提醒主链路。")),
    ])


def main():
    init()
    resp = requests.post(
        f"{BASE}/docx/v1/documents",
        headers=headers,
        json={"title": "美国新客循环补丁策略简版"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(data)
    doc_id = data["data"]["document"]["document_id"]
    build_doc(doc_id)
    update_permission(doc_id)
    print(f"{OPEN_BASE}/{doc_id}")


if __name__ == "__main__":
    main()
