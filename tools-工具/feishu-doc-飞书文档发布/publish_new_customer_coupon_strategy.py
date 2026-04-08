#!/usr/bin/env python3
"""发布「新人循环补券方案」到飞书文档。"""

import time

import requests

APP_ID = "cli_a937e91d7f38dbd8"
APP_SECRET = "r2Qm0OBs7cA7x9CpD29hwg1BMJpfx4Ze"
BASE = "https://open.feishu.cn/open-apis"


def get_token():
    resp = requests.post(
        f"{BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def txt(content, bold=False):
    element = {"text_run": {"content": content}}
    if bold:
        element["text_run"]["text_element_style"] = {"bold": True}
    return element


def para(*elements):
    return {"block_type": 2, "text": {"elements": list(elements)}}


def heading(level, content):
    return {"block_type": level + 2, f"heading{level}": {"elements": [txt(content)]}}


def bullet(*elements):
    return {"block_type": 12, "bullet": {"elements": list(elements)}}


def add_blocks(doc_id, parent_id, children, headers):
    batch_size = 20
    for i in range(0, len(children), batch_size):
        batch = children[i:i + batch_size]
        resp = requests.post(
            f"{BASE}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children",
            headers=headers,
            json={"children": batch, "index": -1},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"写入文档失败: {data}")
        time.sleep(0.2)


def build_blocks():
    blocks = []

    blocks.append(para(txt("文档版本：v1.0 | 更新日期：2026-03-30")))
    blocks.append(para(txt("负责人：用户运营 | 场景：美国瑞幸新客运营")))

    blocks.append(heading(1, "一、背景"))
    blocks.append(
        para(
            txt("当前新人券包为：", bold=True),
            txt("1.99（7天有效）、2.99（次日-15天有效）、3.99（15天有效）、5折（15天有效）。")
        )
    )
    blocks.append(
        para(
            txt("现状问题：", bold=True),
            txt("大部分新客在前15天仅使用首张1.99，后续2.99、3.99、5折未被有效承接即过期，导致第二单、第三单阶段缺少价格梯度承接，影响后续转化与留存。")
        )
    )
    blocks.append(
        para(
            txt("因此需要增加一套循环补券策略，在不造成券冗余的前提下，对处于新人承接阶段但当前无有效承接券的用户进行补券。")
        )
    )

    blocks.append(heading(1, "二、目标"))
    blocks.append(
        para(
            txt("策略目标：", bold=True),
            txt("提升首单用户后续转化，重点改善留存表现。")
        )
    )
    blocks.append(
        para(
            txt("评估口径：", bold=True),
            txt("业务评估看自然月次月留存；策略执行采用滚动窗口，统一按首单后T+60执行，以保证策略稳定性并覆盖自然月次月留存影响周期。")
        )
    )
    blocks.append(para(txt("本次策略原则：", bold=True)))
    blocks.append(bullet(txt("仅做塞券，不展开触达。")))
    blocks.append(bullet(txt("一个策略完成圈人与补券，降低配置复杂度。")))
    blocks.append(bullet(txt("避免券冗余，用户当前若仍持有2.99或5折，则不再补发。")))
    blocks.append(bullet(txt("不额外区分用户第二单具体使用了2.99还是5折，统一补承接券即可。")))

    blocks.append(heading(1, "三、方案"))
    blocks.append(
        para(
            txt("本次采用统一补2.99的简化方案。", bold=True),
            txt("2.99与5折到手价接近，但2.99成本更稳定，后台配置更简单，后续效果复盘也更清晰。")
        )
    )
    blocks.append(para(txt("圈人规则：", bold=True), txt("以下条件全部满足AND。")))
    blocks.append(bullet(txt("首单距今时间 >= 1天")))
    blocks.append(bullet(txt("首单距今时间 <= 60天")))
    blocks.append(bullet(txt("累计完成订单数 >= 1")))
    blocks.append(bullet(txt("累计完成订单数 <= 2")))
    blocks.append(bullet(txt("持有优惠券 不包含 新人2.99")))
    blocks.append(bullet(txt("持有优惠券 不包含 新人5折")))
    blocks.append(para(txt("发券动作：", bold=True), txt("发放2.99补券。")))
    blocks.append(
        para(
            txt("策略含义：", bold=True),
            txt("针对首单后60天内、仍处于1-2单阶段、且当前手中没有2.99或5折的用户，统一补发一张2.99，用于承接其二单或三单转化。")
        )
    )
    blocks.append(
        para(
            txt("该方案可以覆盖当前新人链路中“已有首单但后续承接券缺失”的核心人群，同时满足“不重复补券、不叠券”的要求。")
        )
    )

    blocks.append(heading(1, "四、执行计划"))
    blocks.append(para(txt("1. 后台配置", bold=True)))
    blocks.append(para(txt("基于上述条件建立圈人规则，设置每日自动跑批，对命中用户发放2.99补券。")))
    blocks.append(para(txt("2. 上线方式", bold=True)))
    blocks.append(para(txt("先以单策略上线，不叠加更多分支逻辑，保证执行简单、效果可归因。")))
    blocks.append(para(txt("3. 效果观察", bold=True)))
    blocks.append(bullet(txt("首单用户T+30 / T+60留存")))
    blocks.append(bullet(txt("自然月次月留存")))
    blocks.append(bullet(txt("首单后7天、14天、30天二单率")))
    blocks.append(bullet(txt("首单后30天、60天三单率")))
    blocks.append(bullet(txt("2.99补券领取率、核销率")))
    blocks.append(bullet(txt("补券用户与非补券用户的留存差异")))
    blocks.append(para(txt("4. 后续优化", bold=True)))
    blocks.append(para(txt("若该策略验证有效，再进一步评估是否需要增加补券次数控制、细分二单/三单承接逻辑，或叠加触达策略联动优化。")))

    return blocks


def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{BASE}/docx/v1/documents",
        headers=headers,
        json={"title": "新人循环补券方案"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"创建文档失败: {data}")

    doc_id = data["data"]["document"]["document_id"]
    add_blocks(doc_id, doc_id, build_blocks(), headers)
    print(f"https://lkusco.feishu.cn/docx/{doc_id}")


if __name__ == "__main__":
    main()
