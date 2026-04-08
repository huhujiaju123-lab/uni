#!/usr/bin/env python3
"""
易经64卦 读者团评审脚本
模拟专家+普通读者双视角审查，输出评审报告

用法: python review.py data/gua/01-qian.json
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
RULES_PATH = BASE_DIR / 'review' / 'structural_rules.json'


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_rules():
    if RULES_PATH.exists():
        return load_json(RULES_PATH)
    return None


def review_expert(gua):
    """专家学者视角评审"""
    issues = []
    warnings = []

    name = gua['meta']['name']
    number = gua['meta']['number']

    # 1. 检查卦辞是否存在
    if not gua.get('guaci'):
        issues.append("[红线] 缺少卦辞原文")

    # 2. 检查步骤完整性
    required_steps = ['guanxiang', 'dutuan', 'xunzi', 'xiwei', 'wanci', 'chabian', 'guide', 'zhengyin', 'yingshe']
    steps = gua.get('steps', {})
    for step in required_steps:
        if step not in steps or not steps[step]:
            issues.append(f"[红线] 缺少步骤: {step}")

    # 3. 检查训字来源标注
    xunzi = steps.get('xunzi', [])
    for item in xunzi:
        if not item.get('source'):
            issues.append(f"[红线] 训字「{item.get('char', '?')}」缺少来源标注")

    # 4. 检查爻位分析
    xiwei = steps.get('xiwei', {})
    yao_analysis = xiwei.get('yaoAnalysis', [])
    if len(yao_analysis) != 6:
        issues.append(f"[红线] 析位应有6爻，实际 {len(yao_analysis)} 爻")

    # 验证当位判断
    for yao in yao_analysis:
        pos = yao.get('position', '')
        yin_yang = yao.get('yinYang', '')
        is_proper = yao.get('isProper', None)

        # 初/三/五为阳位，二/四/上为阴位
        yang_positions = ['初', '三', '五']
        is_yang_pos = any(p in pos for p in yang_positions)

        if yin_yang == 'yang':
            expected_proper = is_yang_pos  # 阳爻在阳位=当位
        else:
            expected_proper = not is_yang_pos  # 阴爻在阴位=当位

        if is_proper != expected_proper:
            issues.append(f"[红线] {pos} 当位判断可能有误: 实际={is_proper}, 预期={expected_proper}")

    # 5. 检查玩辞
    wanci = steps.get('wanci', {})
    yao_cards = wanci.get('yao', [])
    if len(yao_cards) < 6:
        issues.append(f"[红线] 玩辞应有6爻卡片，实际 {len(yao_cards)}")
    for yao in yao_cards:
        if not yao.get('yaoci'):
            issues.append(f"[红线] {yao.get('position', '?')} 缺少爻辞原文")
        if not yao.get('source'):
            warnings.append(f"[黄线] {yao.get('position', '?')} 玩辞缺少来源标注")

    # 6. 检查征引
    zhengyin = steps.get('zhengyin', [])
    for cite in zhengyin:
        if not cite.get('source'):
            warnings.append(f"[黄线] 征引「{cite.get('event', '?')}」缺少出处")
        if not cite.get('contentSource'):
            issues.append(f"[红线] 征引「{cite.get('event', '?')}」缺少内容来源标注")

    # 7. 检查映射
    yingshe = steps.get('yingshe', [])
    if len(yingshe) < 6:
        warnings.append(f"[黄线] 映射场景只有 {len(yingshe)} 个，建议覆盖六爻")

    # 8. 检查AI洞察
    ai = gua.get('aiInsights', {})
    if not ai:
        warnings.append("[黄线] 缺少AI独创洞察板块")
    else:
        if not ai.get('crossHexagram'):
            warnings.append("[黄线] 缺少跨卦分析")
        if not ai.get('network'):
            warnings.append("[黄线] 缺少关系网络")
        if not ai.get('modernFramework'):
            warnings.append("[黄线] 缺少现代框架映射")

    return issues, warnings


def review_reader(gua):
    """普通读者视角评审"""
    feedback = []

    steps = gua.get('steps', {})

    # 1. 检查可读性 - 段落长度
    wanci = steps.get('wanci', {})
    for yao in wanci.get('yao', []):
        interp = yao.get('interpretation', '')
        if len(interp) > 300:
            feedback.append(f"[可读性] {yao.get('position', '?')} 解读段落过长（{len(interp)}字），考虑分段")

    # 2. 检查映射的生动性
    yingshe = steps.get('yingshe', [])
    for item in yingshe:
        scenario = item.get('scenario', '')
        if len(scenario) < 10:
            feedback.append(f"[启发性] {item.get('yao', '?')} 映射场景描述太短，不够具体")

    # 3. 检查结语
    conclusion = gua.get('conclusion', {})
    if not conclusion.get('practicalAdvice'):
        feedback.append("[收获感] 缺少实践指引，读者看完不知道该怎么做")

    # 4. 检查观象的意象感
    guanxiang = steps.get('guanxiang', {})
    if not guanxiang.get('scene'):
        feedback.append("[意象感] 观象缺少场景描述")

    return feedback


def collect_all_text(gua):
    """递归收集 JSON 中所有字符串值"""
    texts = []
    if isinstance(gua, dict):
        for v in gua.values():
            texts.extend(collect_all_text(v))
    elif isinstance(gua, list):
        for item in gua:
            texts.extend(collect_all_text(item))
    elif isinstance(gua, str):
        texts.append(gua)
    return texts


def review_structural(gua):
    """结构性校验 — 防止用叙事逻辑覆盖结构逻辑"""
    rules = load_rules()
    if not rules:
        return [], []

    issues = []
    warnings = []

    all_text = '\n'.join(collect_all_text(gua))

    # === 1. 检查叙事污染：结构术语不应带时间性修饰 ===
    contamination = rules.get('narrative_contamination', {})
    forbidden = contamination.get('forbidden_modifiers_for_structural_terms', {})

    for term, modifiers in forbidden.items():
        for mod in modifiers:
            pattern = re.escape(mod) + re.escape(term)
            if re.search(pattern, all_text):
                issues.append(f"[红线·结构] 「{mod}{term}」— {term}是结构定义，不应加时间修饰词「{mod}」")

    # === 2. 检查析位文本中的时间线叙事 ===
    xiwei = gua.get('steps', {}).get('xiwei', {})
    xiwei_text = '\n'.join(collect_all_text(xiwei))

    timeline_patterns = contamination.get('forbidden_timeline_words_in_xiwei', [])
    for pat in timeline_patterns:
        if re.search(pat, xiwei_text):
            issues.append(f"[红线·结构] 析位中出现时间线叙事: 匹配「{pat}」— 六爻是结构模型，不是故事线")

    # === 3. 验证九五必须标注君位 ===
    yao_analysis = xiwei.get('yaoAnalysis', [])
    for yao in yao_analysis:
        pos = yao.get('position', '')
        traits = yao.get('traits', [])

        # 九五/五 必须包含「君位」
        if '五' in pos and '九' in pos:
            has_junwei = any('君位' in t for t in traits)
            if not has_junwei:
                issues.append(f"[红线·结构] {pos} 的 traits 中缺少「君位」— 五爻永远是君位")

        # 初爻不应标注为「起点」「出发点」
        if '初' in pos:
            for t in traits:
                if any(w in t for w in ['起点', '出发', '旅程开始']):
                    warnings.append(f"[黄线·结构] {pos} 标注了「{t}」— 初爻是「初位/始位」，不是叙事起点")

        # 上爻不应标注为「终点」「目的地」
        if '上' in pos:
            for t in traits:
                if any(w in t for w in ['终点', '目的地', '终极目标']):
                    warnings.append(f"[黄线·结构] {pos} 标注了「{t}」— 上爻是「极位」，不是叙事终点")

    # === 4. 检查 overview 中对九五的描述 ===
    overview = xiwei.get('overview', '')
    if '九五' in overview:
        for mod in ['未来的君位', '最终目标', '要到达的', '终将']:
            if mod in overview:
                issues.append(f"[红线·结构] 析位概述中「{mod}」— 九五就是君位，不是未来/目标")

    return issues, warnings


def main():
    if len(sys.argv) < 2:
        print("用法: python review.py data/gua/01-qian.json")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        path = BASE_DIR / sys.argv[1]

    gua = load_json(path)
    name = gua['meta']['name']
    number = gua['meta']['number']

    print(f"\n{'=' * 60}")
    print(f"  读者团评审报告: {name}卦（第{number}卦）")
    print(f"{'=' * 60}\n")

    # 专家评审
    issues, warnings = review_expert(gua)
    print(f"--- 专家学者视角 ---\n")
    if issues:
        print(f"  红线问题（必须修复）: {len(issues)}")
        for i in issues:
            print(f"    {i}")
    else:
        print("  红线问题: 0 (全部通过)")

    if warnings:
        print(f"\n  黄线提醒（可迭代）: {len(warnings)}")
        for w in warnings:
            print(f"    {w}")
    else:
        print("  黄线提醒: 0")

    # 结构性校验
    struct_issues, struct_warnings = review_structural(gua)
    print(f"\n--- 结构 vs 叙事 校验 ---\n")
    if struct_issues:
        print(f"  红线问题（必须修复）: {len(struct_issues)}")
        for si in struct_issues:
            print(f"    {si}")
    else:
        print("  红线问题: 0 (未检测到叙事污染)")
    if struct_warnings:
        print(f"\n  黄线提醒: {len(struct_warnings)}")
        for sw in struct_warnings:
            print(f"    {sw}")

    issues.extend(struct_issues)
    warnings.extend(struct_warnings)

    # 读者评审
    feedback = review_reader(gua)
    print(f"\n--- 普通读者视角 ---\n")
    if feedback:
        print(f"  反馈: {len(feedback)}")
        for fb in feedback:
            print(f"    {fb}")
    else:
        print("  反馈: 0 (体验良好)")

    # 汇总
    total_issues = len(issues)
    total_warnings = len(warnings) + len(feedback)
    print(f"\n{'=' * 60}")
    if total_issues == 0:
        print(f"  结果: 通过 (红线 0 | 黄线 {total_warnings})")
    else:
        print(f"  结果: 未通过 (红线 {total_issues} | 黄线 {total_warnings})")
    print(f"{'=' * 60}\n")

    # 输出到文件
    review_dir = BASE_DIR / 'review'
    review_dir.mkdir(exist_ok=True)
    review_file = review_dir / f"{number:02d}-{gua['meta']['pinyin'].replace(' ', '-')}-review.md"

    with open(review_file, 'w', encoding='utf-8') as out:
        out.write(f"# {name}卦 评审记录\n\n")
        out.write(f"## 专家视角\n\n")
        if issues:
            out.write("### 红线问题\n")
            for i in issues:
                out.write(f"- {i}\n")
        else:
            out.write("红线: 全部通过\n")
        out.write("\n")
        if warnings:
            out.write("### 黄线提醒\n")
            for w in warnings:
                out.write(f"- {w}\n")
        out.write("\n## 结构 vs 叙事 校验\n\n")
        if struct_issues or struct_warnings:
            for si in struct_issues:
                out.write(f"- {si}\n")
            for sw in struct_warnings:
                out.write(f"- {sw}\n")
        else:
            out.write("未检测到叙事污染。\n")
        out.write("\n## 读者视角\n\n")
        if feedback:
            for fb in feedback:
                out.write(f"- {fb}\n")
        else:
            out.write("体验良好，无显著问题。\n")
        out.write(f"\n## 评审结论\n\n")
        out.write(f"- 红线: {total_issues}\n")
        out.write(f"- 黄线: {total_warnings}\n")
        out.write(f"- 状态: {'通过' if total_issues == 0 else '未通过'}\n")

    print(f"  评审记录已保存: {review_file}")


if __name__ == '__main__':
    main()
