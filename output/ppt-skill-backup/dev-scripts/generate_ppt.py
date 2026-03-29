#!/usr/bin/env python3
"""讯飞智文 API 生成 PPT"""
import hashlib
import hmac
import base64
import json
import time
import requests
from urllib.parse import urlencode
from datetime import datetime

# API 配置
APPID = "ea841d23"
API_SECRET = "OTIwNDg3MGJjNWUzMGNkODBjYTk5MGVk"
API_KEY = "41151822adc10a7e6df13ad062356a3f"

def generate_signature(ts):
    """生成签名 - 按照讯飞文档：MD5(APPID+timestamp)，再HmacSHA1加密，最后Base64"""
    # 第1步：MD5加密 APPID+timestamp
    md5_str = f"{APPID}{ts}"
    md5_hash = hashlib.md5(md5_str.encode('utf-8')).hexdigest()

    # 第2步：HmacSHA1加密 MD5结果和API_SECRET
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        md5_hash.encode('utf-8'),
        hashlib.sha1
    ).digest()

    # 第3步：Base64编码
    return base64.b64encode(signature).decode('utf-8')

def create_ppt(content, title="用户策略进展与计划"):
    """调用讯飞智文API生成PPT"""

    # 生成时间戳和签名
    ts = str(int(time.time()))
    signature = generate_signature(ts)

    # API地址
    url = "https://zwapi.xfyun.cn/api/aippt/create"

    # 请求头
    headers = {
        "appId": APPID,
        "timestamp": ts,
        "signature": signature,
        "Content-Type": "application/json; charset=utf-8"
    }

    # 请求体
    payload = {
        "query": content,
        "pptName": title,
        # 设置风格参数（深蓝色商务风格）
        "style": "business",
        "color": "blue"
    }

    print(f"正在生成PPT: {title}")
    print(f"请求URL: {url}")
    print(f"时间戳: {ts}")

    # 发送请求
    response = requests.post(url, headers=headers, json=payload, timeout=60)

    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")

    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 0:
            task_id = result.get('data', {}).get('sid')
            print(f"任务ID: {task_id}")
            return task_id
        else:
            print(f"创建失败: {result.get('message')}")
            return None
    else:
        print(f"请求失败: HTTP {response.status_code}")
        return None

def check_ppt_status(task_id):
    """查询PPT生成状态"""

    ts = str(int(time.time()))
    signature = generate_signature(ts)

    url = "https://zwapi.xfyun.cn/api/aippt/progress"

    headers = {
        "appId": APPID,
        "timestamp": ts,
        "signature": signature,
        "Content-Type": "application/json; charset=utf-8"
    }

    payload = {
        "sid": task_id
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        return result
    else:
        return None

def download_ppt(task_id, save_path):
    """下载生成的PPT"""

    # 等待生成完成
    print("等待PPT生成中...")
    max_wait = 120  # 最多等待2分钟
    start_time = time.time()

    while time.time() - start_time < max_wait:
        status = check_ppt_status(task_id)
        if status and status.get('code') == 0:
            data = status.get('data', {})
            progress = data.get('progress', 0)
            print(f"生成进度: {progress}%")

            if progress == 100:
                ppt_url = data.get('pptUrl')
                if ppt_url:
                    print(f"PPT生成完成！下载地址: {ppt_url}")

                    # 下载PPT
                    response = requests.get(ppt_url, timeout=60)
                    if response.status_code == 200:
                        with open(save_path, 'wb') as f:
                            f.write(response.content)
                        print(f"PPT已保存到: {save_path}")
                        return True
                    else:
                        print(f"下载失败: HTTP {response.status_code}")
                        return False

        time.sleep(5)  # 每5秒查询一次

    print("生成超时")
    return False

if __name__ == '__main__':
    # PPT内容
    content = """
# 第1页：新客策略进展与计划

## 新人券包
- 策略详情：1月19日上线AB实验，对照组1.99（7天）+1.99（次日15天）+2.99（15天）+5折（15天），实验组1.99（7天）+2.99（次日15天）+3.99（15天）+5折（15天）
- 1月进展：拉齐后下单+4.8%，杯量+2.5%，单杯实收+2.6%，3日复购率-0.6pp。对首次转化影响较小，主要观察后续复购影响
- 2月计划：结合档当前实验结果与各方决策新客策略的数据效果

## 分享有礼
- 策略详情：利益点调整为拉新累计奖励，奖励金额从free drink调整为1.99。用户累计拉新1/2/3/4人分别获得1/3/5/7张1.99券。上线实时push触达策略，推进实物奖励方案
- 1月进展：日均拉新36人（完单口径），占大盘拉新6.93%，占比整体在5-7%，1月下旬（25-28日）有明显上升达到9-12%，呈现月末走强趋势
- 2月计划：1.素材换新，点击率优化 2.实物奖励方案优化

# 第2页：老客策略进展与计划

## 活跃用户（0~15天有交易）
- 1月进展：1月15日上线，拉齐后下单用户+0.5%，杯量+1.2%，单杯实收+0.5%。从0-7天看7折效果最好，建议考虑扩量并拓展为券包形态
- 2月计划：涨价实验覆盖，对照组6折限品+7折全品，实验组1为7折全品+7折全品，实验组2为75折全品+75折全品

## 浏览未购
- 1月进展：1月16日上线，收补后效果显著：下单用户+1.4%，杯量+5.7%，实收+7.6%，3日复购率13.2% vs 9.9%（+3.3pp）。用户质量好，建议全量
- 2月计划：涨价实验覆盖，对照组5折，实验组1为55折，实验组2为6折

## 沉默召回
- 16-30天：1月16日上线，5折提升后单杯实收提升明显，但用户及单量下降。待权衡决策
- 30天以上：拉齐后vs对照组：3折组下单+10.8%实收+6.6%，4折组下单+0.6%实收+17.9%。4折组实收效果最优，但人均杯量-8%
"""

    # 生成PPT
    task_id = create_ppt(content, "用户策略进展与计划")

    if task_id:
        # 下载PPT
        save_path = "/Users/xiaoxiao/Vibe coding/用户策略进展与计划.pptx"
        download_ppt(task_id, save_path)
    else:
        print("PPT生成失败")
