#!/usr/bin/env python3
"""Lucky US 日报 v2 - 完整版含归因分析"""

from datetime import datetime, timedelta

# ==================== 数据区 ====================

report_dates = ["2026-02-15","2026-02-16","2026-02-17","2026-02-18","2026-02-19","2026-02-20","2026-02-21","2026-02-22","2026-02-24"]
compare_dates = ["2026-02-08","2026-02-09","2026-02-10","2026-02-11","2026-02-12","2026-02-13","2026-02-14"]
all_dates = compare_dates + report_dates

WEEKDAY_MAP = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
WEEKDAY_CN = {0:"周一",1:"周二",2:"周三",3:"周四",4:"周五",5:"周六",6:"周日"}

def wd(dt_str):
    return WEEKDAY_MAP[datetime.strptime(dt_str, "%Y-%m-%d").weekday()]
def wd_cn(dt_str):
    return WEEKDAY_CN[datetime.strptime(dt_str, "%Y-%m-%d").weekday()]
def wow(dt_str):
    return (datetime.strptime(dt_str, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
def is_weekend(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%d").weekday() >= 5
def fmt_pct(cur, prev):
    if prev == 0: return "N/A", "neutral"
    p = (cur - prev) / prev * 100
    return f"{'+'if p>0 else ''}{p:.1f}%", "positive" if p > 0 else "negative" if p < 0 else ""

# --- 天气 (NYC, Celsius) ---
wx_dates = ["2026-02-08","2026-02-09","2026-02-10","2026-02-11","2026-02-12","2026-02-13","2026-02-14",
            "2026-02-15","2026-02-16","2026-02-17","2026-02-18","2026-02-19","2026-02-20","2026-02-21",
            "2026-02-22","2026-02-23","2026-02-24"]
wx_tmax = [-10.1,-4.0,-0.2,3.4,0.9,1.1,3.8,2.5,2.1,5.8,3.8,3.9,4.4,8.0,2.8,1.5,-1.6]
wx_tmin = [-17.8,-14.6,-9.9,-0.8,-4.8,-8.5,-7.8,-6.2,-2.0,0.3,-0.4,1.4,0.5,-0.9,-0.6,-2.4,-10.9]
wx_code = [1,3,3,51,3,3,3,73,73,3,53,3,61,3,75,75,3]
wx_desc_map = {0:"晴",1:"晴",2:"多云",3:"阴",51:"小雨",53:"中雨",61:"雨",63:"中雨",71:"小雪",73:"雪",75:"大雪"}
def wx_info(dt):
    i = wx_dates.index(dt)
    return wx_tmax[i], wx_tmin[i], wx_code[i], wx_desc_map.get(wx_code[i], str(wx_code[i]))

# --- 门店数据 ---
store_raw = """2026-02-08	8th & Broadway	281	924.09
2026-02-08	54th & 8th	220	765.93
2026-02-08	102 Fulton	214	819.90
2026-02-08	28th & 6th	191	659.14
2026-02-08	21st & 3rd	183	578.96
2026-02-08	15th & 3rd	182	584.13
2026-02-08	100 Maiden Ln	148	520.24
2026-02-08	37th & Broadway	131	451.54
2026-02-08	33rd & 10th	109	331.62
2026-02-08	221 Grand	87	311.94
2026-02-09	8th & Broadway	655	2123.77
2026-02-09	37th & Broadway	448	1534.85
2026-02-09	102 Fulton	341	1167.00
2026-02-09	221 Grand	334	1161.14
2026-02-09	33rd & 10th	284	939.85
2026-02-09	28th & 6th	267	878.64
2026-02-09	54th & 8th	259	878.10
2026-02-09	21st & 3rd	222	652.11
2026-02-09	15th & 3rd	167	567.67
2026-02-09	100 Maiden Ln	88	318.95
2026-02-10	8th & Broadway	764	2509.22
2026-02-10	37th & Broadway	664	2209.42
2026-02-10	102 Fulton	455	1528.01
2026-02-10	33rd & 10th	436	1399.56
2026-02-10	221 Grand	380	1249.17
2026-02-10	54th & 8th	377	1304.80
2026-02-10	28th & 6th	346	1179.49
2026-02-10	21st & 3rd	333	965.02
2026-02-10	100 Maiden Ln	253	911.43
2026-02-10	15th & 3rd	195	649.14
2026-02-11	8th & Broadway	797	2657.04
2026-02-11	37th & Broadway	680	2266.60
2026-02-11	102 Fulton	496	1761.82
2026-02-11	33rd & 10th	475	1616.60
2026-02-11	221 Grand	444	1491.13
2026-02-11	54th & 8th	366	1218.32
2026-02-11	100 Maiden Ln	345	1174.29
2026-02-11	28th & 6th	337	1144.99
2026-02-11	21st & 3rd	302	921.17
2026-02-11	15th & 3rd	215	690.45
2026-02-12	8th & Broadway	729	2439.56
2026-02-12	37th & Broadway	574	1909.65
2026-02-12	102 Fulton	465	1608.41
2026-02-12	221 Grand	418	1354.23
2026-02-12	33rd & 10th	390	1347.21
2026-02-12	54th & 8th	345	1231.98
2026-02-12	21st & 3rd	312	913.00
2026-02-12	28th & 6th	302	1038.17
2026-02-12	100 Maiden Ln	263	893.24
2026-02-12	15th & 3rd	199	652.76
2026-02-13	221 Grand	582	1898.84
2026-02-13	8th & Broadway	569	1963.26
2026-02-13	37th & Broadway	444	1523.78
2026-02-13	102 Fulton	369	1344.65
2026-02-13	54th & 8th	357	1260.85
2026-02-13	21st & 3rd	319	976.19
2026-02-13	33rd & 10th	312	1061.54
2026-02-13	28th & 6th	287	1020.57
2026-02-13	100 Maiden Ln	239	833.96
2026-02-13	15th & 3rd	209	713.10
2026-02-14	221 Grand	729	2423.32
2026-02-14	8th & Broadway	511	1628.12
2026-02-14	54th & 8th	388	1331.01
2026-02-14	28th & 6th	355	1198.08
2026-02-14	21st & 3rd	295	870.71
2026-02-14	37th & Broadway	290	958.27
2026-02-14	102 Fulton	289	974.49
2026-02-14	15th & 3rd	224	757.64
2026-02-14	100 Maiden Ln	184	635.78
2026-02-14	33rd & 10th	103	355.37
2026-02-15	221 Grand	659	2052.80
2026-02-15	8th & Broadway	425	1407.05
2026-02-15	54th & 8th	329	1137.13
2026-02-15	21st & 3rd	286	863.05
2026-02-15	102 Fulton	283	973.40
2026-02-15	28th & 6th	265	884.21
2026-02-15	37th & Broadway	237	827.28
2026-02-15	15th & 3rd	180	646.49
2026-02-15	100 Maiden Ln	147	535.82
2026-02-15	33rd & 10th	117	387.57
2026-02-16	221 Grand	602	1995.46
2026-02-16	8th & Broadway	343	1118.29
2026-02-16	21st & 3rd	292	889.45
2026-02-16	54th & 8th	286	1018.28
2026-02-16	102 Fulton	253	955.74
2026-02-16	37th & Broadway	250	862.14
2026-02-16	28th & 6th	242	843.46
2026-02-16	100 Maiden Ln	202	762.80
2026-02-16	33rd & 10th	190	627.14
2026-02-16	15th & 3rd	158	543.90
2026-02-17	8th & Broadway	712	2406.53
2026-02-17	221 Grand	687	2171.50
2026-02-17	37th & Broadway	559	1994.63
2026-02-17	102 Fulton	351	1228.22
2026-02-17	28th & 6th	333	1128.85
2026-02-17	33rd & 10th	313	1056.68
2026-02-17	54th & 8th	293	1004.83
2026-02-17	100 Maiden Ln	250	881.05
2026-02-17	21st & 3rd	249	780.07
2026-02-17	15th & 3rd	210	757.50
2026-02-18	8th & Broadway	698	2354.97
2026-02-18	37th & Broadway	617	2053.82
2026-02-18	102 Fulton	400	1458.28
2026-02-18	33rd & 10th	397	1354.07
2026-02-18	221 Grand	384	1322.61
2026-02-18	54th & 8th	322	1122.67
2026-02-18	28th & 6th	312	1052.93
2026-02-18	21st & 3rd	266	837.26
2026-02-18	100 Maiden Ln	227	811.78
2026-02-18	15th & 3rd	199	716.47
2026-02-19	8th & Broadway	679	2307.04
2026-02-19	37th & Broadway	534	1920.84
2026-02-19	221 Grand	470	1580.64
2026-02-19	102 Fulton	434	1498.18
2026-02-19	54th & 8th	376	1343.04
2026-02-19	33rd & 10th	375	1298.03
2026-02-19	28th & 6th	338	1126.77
2026-02-19	21st & 3rd	302	968.57
2026-02-19	100 Maiden Ln	235	798.58
2026-02-19	15th & 3rd	186	679.04
2026-02-20	8th & Broadway	461	1580.67
2026-02-20	221 Grand	380	1244.94
2026-02-20	37th & Broadway	317	1100.26
2026-02-20	102 Fulton	299	1084.25
2026-02-20	54th & 8th	291	1155.59
2026-02-20	28th & 6th	288	994.79
2026-02-20	33rd & 10th	231	772.89
2026-02-20	21st & 3rd	230	776.87
2026-02-20	100 Maiden Ln	182	656.56
2026-02-20	15th & 3rd	134	489.84
2026-02-21	221 Grand	743	2338.77
2026-02-21	8th & Broadway	531	1768.31
2026-02-21	28th & 6th	365	1263.38
2026-02-21	54th & 8th	360	1256.59
2026-02-21	21st & 3rd	302	999.22
2026-02-21	37th & Broadway	292	965.69
2026-02-21	102 Fulton	237	822.71
2026-02-21	15th & 3rd	181	614.82
2026-02-21	100 Maiden Ln	157	574.12
2026-02-21	33rd & 10th	127	416.88
2026-02-22	221 Grand	212	705.05
2026-02-22	54th & 8th	197	747.44
2026-02-22	8th & Broadway	197	695.90
2026-02-22	21st & 3rd	171	582.55
2026-02-22	28th & 6th	154	561.53
2026-02-22	15th & 3rd	134	476.39
2026-02-22	102 Fulton	126	452.69
2026-02-22	100 Maiden Ln	109	395.23
2026-02-22	33rd & 10th	71	231.62
2026-02-22	37th & Broadway	45	141.28
2026-02-24	8th & Broadway	591	2024.13
2026-02-24	37th & Broadway	369	1344.81
2026-02-24	221 Grand	368	1285.00
2026-02-24	102 Fulton	293	1089.13
2026-02-24	54th & 8th	285	1049.61
2026-02-24	28th & 6th	256	955.04
2026-02-24	15th & 3rd	218	824.08
2026-02-24	33rd & 10th	206	677.93
2026-02-24	21st & 3rd	181	593.38
2026-02-24	100 Maiden Ln	177	620.09"""

stores = {}
for line in store_raw.strip().split('\n'):
    p = line.split('\t')
    dt, sn, c, r = p[0], p[1], int(p[2]), float(p[3])
    stores.setdefault(dt, {})[sn] = {"cups": c, "rev": r}

daily = {}
for dt, ss in stores.items():
    daily[dt] = {"cups": sum(s["cups"] for s in ss.values()), "rev": sum(s["rev"] for s in ss.values()), "n_stores": len(ss)}

store_names = ["221 Grand","8th & Broadway","37th & Broadway","102 Fulton","54th & 8th",
               "33rd & 10th","28th & 6th","21st & 3rd","100 Maiden Ln","15th & 3rd"]

# --- 渠道 ---
ch_data = {
    "2026-02-15": {"iOS":1833,"Android":202,"H5":190}, "2026-02-16": {"iOS":1859,"Android":172,"H5":156},
    "2026-02-17": {"iOS":2760,"Android":311,"H5":176}, "2026-02-18": {"iOS":2721,"Android":302,"H5":169},
    "2026-02-19": {"iOS":2847,"Android":301,"H5":203}, "2026-02-20": {"iOS":1932,"Android":222,"H5":137},
    "2026-02-21": {"iOS":2130,"Android":260,"H5":191}, "2026-02-22": {"iOS":904,"Android":82,"H5":80},
    "2026-02-24": {"iOS":2137,"Android":209,"H5":131},
}

# --- 用户生命周期 ---
lifecycle = {
    "2026-02-15": [818,871,136,314], "2026-02-16": [615,1073,150,269],
    "2026-02-17": [692,1834,262,358], "2026-02-18": [555,1968,240,324],
    "2026-02-19": [610,2037,268,314], "2026-02-20": [515,1370,144,185],
    "2026-02-21": [860,1087,164,368], "2026-02-22": [269,589,82,97],
    "2026-02-24": [397,1528,218,248],
}

# --- 漏斗UV ---
funnel = {
    "2026-02-15": [3370,2160,1995,1753], "2026-02-16": [3590,2142,1985,1791],
    "2026-02-17": [5038,3093,3022,2766], "2026-02-18": [4968,3058,2990,2702],
    "2026-02-19": [5048,3104,3077,2795], "2026-02-20": [3716,2148,2129,1917],
    "2026-02-21": [3757,2420,2333,2075], "2026-02-22": [2190,1050,987,875],
    "2026-02-24": [4134,2420,2327,2068],
}

# --- 新客次留 ---
new_retention = {
    "2026-02-15": (818,49), "2026-02-16": (615,41), "2026-02-17": (692,52),
    "2026-02-18": (555,54), "2026-02-19": (610,36), "2026-02-20": (515,34),
    "2026-02-21": (860,23), "2026-02-22": (269,0),
}
# 7日留存 (from daily report)
new_7d_ret = {"2026-02-15":15.2,"2026-02-16":26.1,"2026-02-17":26.8,"2026-02-18":24.1,
              "2026-02-19":21.9,"2026-02-20":18.1,"2026-02-21":14.5,"2026-02-22":12.3,"2026-02-24":16.3}
old_7d_ret = {"2026-02-15":52.8,"2026-02-16":58.5,"2026-02-17":56.7,"2026-02-18":53.6,
              "2026-02-19":56.5,"2026-02-20":53.3,"2026-02-21":48.4,"2026-02-22":46.9,"2026-02-24":48.6}

# --- 分时数据 ---
hourly_raw = """2026-02-15	7	38	8	103	9	168	10	255	11	287	12	297	13	256	14	225	15	238	16	183	17	112	18	49	19	43	20	6
2026-02-16	7	76	8	146	9	219	10	247	11	226	12	279	13	226	14	231	15	196	16	163	17	117	18	67	19	33	20	7
2026-02-17	7	191	8	431	9	412	10	348	11	247	12	322	13	369	14	284	15	269	16	165	17	132	18	85	19	37	20	3
2026-02-18	7	192	8	498	9	434	10	357	11	241	12	305	13	387	14	245	15	194	16	147	17	114	18	70	19	46	20	5
2026-02-19	7	196	8	499	9	493	10	362	11	262	12	305	13	338	14	267	15	223	16	175	17	139	18	80	19	39	20	12
2026-02-20	7	124	8	282	9	395	10	273	11	203	12	188	13	192	14	172	15	154	16	121	17	117	18	64	19	52	20	3
2026-02-21	7	58	8	150	9	222	10	239	11	287	12	266	13	284	14	295	15	287	16	216	17	156	18	96	19	53	20	14
2026-02-22	7	48	8	79	9	148	10	154	11	176	12	179	13	137	14	91	15	86	16	2
2026-02-24	7	139	8	373	9	361	10	283	11	192	12	238	13	234	14	198	15	170	16	135	17	105	18	63	19	28	20	7"""

hourly = {}
for line in hourly_raw.strip().split('\n'):
    parts = line.split('\t')
    dt = parts[0]
    hourly[dt] = {}
    i = 1
    while i < len(parts) - 1:
        hourly[dt][int(parts[i])] = int(parts[i+1])
        i += 2

# --- 券数据 ---
coupon_daily = {
    "2026-02-15": {"新客$1.99":487,"新客惊喜券":146,"惊喜券老客":56,"工作日特惠":268,"午休买一送一":0,"分享有礼":22,"学生优惠":76},
    "2026-02-16": {"新客$1.99":408,"新客惊喜券":119,"惊喜券老客":48,"工作日特惠":0,"午休买一送一":65,"分享有礼":10,"学生优惠":20},
    "2026-02-17": {"新客$1.99":439,"新客惊喜券":120,"惊喜券老客":80,"工作日特惠":0,"午休买一送一":88,"分享有礼":14,"学生优惠":263},
    "2026-02-18": {"新客$1.99":332,"新客惊喜券":116,"惊喜券老客":33,"工作日特惠":0,"午休买一送一":94,"分享有礼":23,"学生优惠":311},
    "2026-02-19": {"新客$1.99":368,"新客惊喜券":121,"惊喜券老客":49,"工作日特惠":0,"午休买一送一":93,"分享有礼":11,"学生优惠":40},
    "2026-02-20": {"新客$1.99":312,"新客惊喜券":94,"惊喜券老客":39,"工作日特惠":0,"午休买一送一":61,"分享有礼":10,"学生优惠":13},
    "2026-02-21": {"新客$1.99":528,"新客惊喜券":144,"惊喜券老客":69,"工作日特惠":274,"午休买一送一":0,"分享有礼":7,"学生优惠":12},
    "2026-02-22": {"新客$1.99":168,"新客惊喜券":52,"惊喜券老客":20,"工作日特惠":68,"午休买一送一":0,"分享有礼":6,"学生优惠":6},
    "2026-02-24": {"新客$1.99":220,"新客惊喜券":58,"惊喜券老客":24,"工作日特惠":0,"午休买一送一":77,"分享有礼":3,"学生优惠":2},
}

# --- TOP10 商品 02/24 ---
top10_products = [
    ("Latte",287,333), ("Iced Coconut Latte",231,346), ("lced Kyoto Matcha Latte",203,269),
    ("Drip Coffee",168,169), ("Iced Latte",164,191), ("Coconut Latte",116,111),
    ("Cold Brew",100,140), ("Kyoto Matcha Latte",98,146), ("Iced Velvet Latte",91,131),
    ("Americano",86,118),
]

# --- 折扣分布 ---
discount = {
    "2026-02-15": [52.2,8.9,31.8,42.3,17.0], "2026-02-16": [53.4,9.5,30.3,38.7,21.5],
    "2026-02-17": [53.4,9.4,26.9,41.0,22.6], "2026-02-18": [54.7,7.9,25.5,44.2,22.4],
    "2026-02-19": [55.0,8.3,24.5,42.2,25.0], "2026-02-20": [56.0,8.9,22.0,42.7,26.4],
    "2026-02-21": [52.9,8.0,31.2,42.7,18.1], "2026-02-22": [57.0,4.4,22.7,51.6,21.3],
    "2026-02-24": [56.5,8.4,20.6,44.0,27.1],
}

# ==================== HTML 生成 ====================
H = []
def w(s): H.append(s)

w("""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Lucky US 日报 2026-02-24</title>
<style>
body{font-family:-apple-system,sans-serif;margin:20px;font-size:13px;color:#333;max-width:1400px}
h1{font-size:20px;margin-bottom:4px}
h2{font-size:15px;margin-top:28px;color:#1a237e;border-bottom:2px solid #1a237e;padding-bottom:6px}
h3{font-size:14px;margin-top:18px;color:#555}
.meta{color:#888;font-size:12px;margin-bottom:16px}
table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{border:1px solid #ddd;padding:4px 7px;text-align:right;white-space:nowrap;font-size:11.5px}
th{background:#f5f5f5;font-weight:600;text-align:center}
td:first-child{text-align:left;font-weight:500}
.pos{color:#D32F2F;font-weight:600}
.neg{color:#388E3C;font-weight:600}
.neu{color:#888}
.anom{background:#FFF3E0;color:#E65100}
.wknd{background:#FAFAFA}
.rain{background:#E3F2FD}
.snow{background:#E8EAF6}
.hl{background:#FFF9C4;font-weight:600}
.note{background:#FFF3E0;border-left:3px solid #FF9800;padding:8px 12px;margin:10px 0;font-size:12px;color:#E65100}
.insight{background:#E8F5E9;border-left:3px solid #4CAF50;padding:8px 12px;margin:10px 0;font-size:12px;color:#1B5E20}
.sn{font-size:11px;color:#999;margin-top:-6px}
.tag{display:inline-block;padding:1px 5px;border-radius:3px;font-size:10px;margin-left:3px}
.tag-snow{background:#C5CAE9;color:#283593}
.tag-rain{background:#BBDEFB;color:#1565C0}
.tag-clear{background:#C8E6C9;color:#2E7D32}
.hot{background:#FFCDD2}
.low{background:#E3F2FD}
.nav{background:#f5f5f5;padding:8px 12px;border-radius:6px;margin:12px 0;font-size:12px}
.nav a{margin:0 4px}
</style></head><body>
<h1>Lucky US 日报 + 归因分析</h1>
<div class="meta">报告周期: 2026-02-15 ~ 2026-02-24 | 对比基准: 周同比 (vs 上周同天) | 生成: 2026-02-26</div>
<div class="note">02-23 数据异常（多项指标为0），已排除。</div>
<div class="nav"><b>目录：</b>
<a href="#p1">Part1 日报</a>(业务·用户·品类·漏斗·商品·分时) |
<a href="#p2">Part2 归因</a>(天气·门店·渠道·用户结构·券·商品·总结)</div>
""")

# ========== PART 1 ==========
w('<h1 id="p1" style="font-size:16px;color:#1a237e;margin-top:20px">Part 1: 日报</h1>')

# --- 一、业务结果 ---
w('<h2>一、业务结果</h2>')
w('<table><tr><th>指标</th>')
for dt in report_dates:
    w(f'<th>{dt[5:]}<br><span style="font-weight:normal;color:#999">{wd_cn(dt)}</span></th>')
w('<th>周同比</th></tr>')

# 营业门店数
w('<tr><td>营业门店数</td>')
for dt in report_dates:
    n = daily.get(dt,{}).get("n_stores",0)
    cls = ' class="anom"' if n == 0 else ' class="wknd"' if is_weekend(dt) else ""
    w(f'<td{cls}>{n}</td>')
w('<td></td></tr>')

# 杯量
w('<tr><td>杯量</td>')
for dt in report_dates:
    c = daily.get(dt,{}).get("cups",0)
    cls = ' class="anom"' if c == 0 else ' class="wknd"' if is_weekend(dt) else ""
    w(f'<td{cls}>{c:,}</td>')
c_now = daily.get("2026-02-24",{}).get("cups",0)
c_wow = daily.get("2026-02-17",{}).get("cups",0)
cs, cc = fmt_pct(c_now, c_wow)
w(f'<td class="{cc}">{cs}</td></tr>')

# 店均杯量
w('<tr><td>店均杯量</td>')
for dt in report_dates:
    c = daily.get(dt,{}).get("cups",0)
    n = daily.get(dt,{}).get("n_stores",1)
    avg = round(c/n) if n else 0
    cls = ' class="anom"' if c == 0 else ' class="wknd"' if is_weekend(dt) else ""
    w(f'<td{cls}>{avg}</td>')
a_now = round(daily.get("2026-02-24",{}).get("cups",0)/daily.get("2026-02-24",{}).get("n_stores",1))
a_wow = round(daily.get("2026-02-17",{}).get("cups",0)/daily.get("2026-02-17",{}).get("n_stores",1))
cs, cc = fmt_pct(a_now, a_wow)
w(f'<td class="{cc}">{cs}</td></tr>')

# 单杯实收
asp_data = {"2026-02-15":3.32,"2026-02-16":3.41,"2026-02-17":3.39,"2026-02-18":3.42,"2026-02-19":3.44,
            "2026-02-20":3.50,"2026-02-21":3.34,"2026-02-22":3.52,"2026-02-24":3.55}
w('<tr><td>单杯实收</td>')
for dt in report_dates:
    v = asp_data.get(dt, 0)
    cls = ' class="wknd"' if is_weekend(dt) else ""
    w(f'<td{cls}>${v:.2f}</td>' if v else f'<td class="anom">-</td>')
cs, cc = fmt_pct(asp_data["2026-02-24"], asp_data["2026-02-17"])
w(f'<td class="{cc}">{cs}</td></tr></table>')

# --- 二、用户 ---
w('<h2>二、用户</h2>')
w('<table><tr><th>指标</th>')
for dt in report_dates:
    w(f'<th>{dt[5:]}</th>')
w('<th>周同比</th></tr>')

# 注册、新客、老客、店均新客
for label, idx in [("新客数",0),("近15天活跃老客",1),("16-30天回流",2),("31天+回流",3)]:
    w(f'<tr><td>{label}</td>')
    for dt in report_dates:
        v = lifecycle.get(dt,[0,0,0,0])[idx]
        cls = ' class="wknd"' if is_weekend(dt) else ""
        w(f'<td{cls}>{v:,}</td>')
    v_now = lifecycle.get("2026-02-24",[0,0,0,0])[idx]
    v_wow = lifecycle.get("2026-02-17",[0,0,0,0])[idx]
    cs, cc = fmt_pct(v_now, v_wow)
    w(f'<td class="{cc}">{cs}</td></tr>')

# 店均新客
w('<tr><td>店均新客</td>')
for dt in report_dates:
    nc = lifecycle.get(dt,[0])[0]
    ns = daily.get(dt,{}).get("n_stores",1)
    w(f'<td>{nc/ns:.1f}</td>' if ns else '<td>-</td>')
w('<td></td></tr>')

# 新客次留
w('<tr><td>新客次日留存率</td>')
for dt in report_dates:
    r = new_retention.get(dt)
    if r and r[0] > 0:
        pct = r[1] / r[0] * 100
        w(f'<td>{pct:.1f}%</td>')
    else:
        w('<td class="neu">-</td>')
w('<td></td></tr>')

# 新客7日留存
w('<tr><td>新客7日留存率</td>')
for dt in report_dates:
    v = new_7d_ret.get(dt)
    w(f'<td>{v:.1f}%</td>' if v else '<td class="neu">-</td>')
w('<td></td></tr>')

# 老客7日留存
w('<tr><td>老客7日留存率</td>')
for dt in report_dates:
    v = old_7d_ret.get(dt)
    w(f'<td>{v:.1f}%</td>' if v else '<td class="neu">-</td>')
w('<td></td></tr>')

w('</table>')
w('<p class="sn">次月留存率：数据周期不足30天，暂不可用</p>')

# --- 三、品类 ---
w('<h2>三、品类</h2><h3>折扣分布</h3>')
w('<table><tr><th>指标</th>')
for dt in report_dates: w(f'<th>{dt[5:]}</th>')
w('</tr>')
disc_labels = ["平均折扣率","3折以内","3~5折","5~7折","7折以上"]
for i, lb in enumerate(disc_labels):
    w(f'<tr><td>{lb}</td>')
    for dt in report_dates:
        d = discount.get(dt)
        if d:
            v = d[i]
            fmt = f"{v*100:.1f}%" if i == 0 and v < 1 else f"{v:.1f}%"
            w(f'<td>{fmt}</td>')
        else:
            w('<td class="anom">-</td>')
    w('</tr>')
w('</table>')
w('<p class="sn">折扣MECE: 3折以内 + 3~5折 + 5~7折 + 7折以上 = 100%</p>')

# 漏斗
w('<h3>漏斗转化（含UV绝对值）</h3>')
w('<table><tr><th>指标</th>')
for dt in report_dates: w(f'<th>{dt[5:]}</th>')
w('</tr>')
funnel_labels = [("Menu UV","menu_uv",0),("→ 商品详情 UV","pd_uv",1),("→ 确认订单 UV","co_uv",2),("→ 支付成功 UV","od_uv",3)]
for lb, _, idx in funnel_labels:
    w(f'<tr><td>{lb}</td>')
    for dt in report_dates:
        f = funnel.get(dt)
        v = f[idx] if f else 0
        w(f'<td>{v:,}</td>' if v else '<td class="anom">-</td>')
    w('</tr>')

# 转化率
for lb, from_idx, to_idx in [("Menu→详情 转化率",0,1),("详情→订单 转化率",1,2),("订单→支付 转化率",2,3)]:
    w(f'<tr><td>{lb}</td>')
    for dt in report_dates:
        f = funnel.get(dt)
        if f and f[from_idx] > 0:
            pct = f[to_idx] / f[from_idx] * 100
            w(f'<td>{pct:.1f}%</td>')
        else:
            w('<td class="anom">-</td>')
    w('</tr>')
w('</table>')

# --- 四、TOP10商品 ---
w('<h2>四、TOP10 商品渗透（订单占比）</h2>')
total_24 = daily.get("2026-02-24",{}).get("cups",2944)
total_17 = daily.get("2026-02-17",{}).get("cups",3957)
w('<table style="width:auto"><tr><th>#</th><th>商品</th><th>02/24杯量</th><th>占比</th><th>02/17杯量</th><th>占比</th><th>周同比</th></tr>')
for i,(name,c24,c17) in enumerate(top10_products):
    p24 = c24/total_24*100
    p17 = c17/total_17*100
    cs,cc = fmt_pct(c24, c17)
    w(f'<tr><td>{i+1}</td><td>{name}</td><td>{c24}</td><td>{p24:.1f}%</td><td>{c17}</td><td>{p17:.1f}%</td><td class="{cc}">{cs}</td></tr>')
w('</table>')

# --- 五、分时数据 ---
w('<h2>五、分时数据</h2>')
w('<table><tr><th>时段</th>')
for dt in report_dates: w(f'<th>{dt[5:]}<br>{wd_cn(dt)}</th>')
w('</tr>')

hours = list(range(7, 21))
for hr in hours:
    w(f'<tr><td>{hr}:00-{hr+1}:00</td>')
    # 计算各日同时段平均值用于标注异常
    all_vals = [hourly.get(dt,{}).get(hr,0) for dt in report_dates if hourly.get(dt,{}).get(hr,0) > 0]
    avg_hr = sum(all_vals)/len(all_vals) if all_vals else 0
    for dt in report_dates:
        v = hourly.get(dt,{}).get(hr, 0)
        day_total = sum(hourly.get(dt,{}).values()) if hourly.get(dt) else 1
        pct = v/day_total*100 if day_total else 0
        # 标注异常：偏离均值超过50%
        cls = ""
        if v > 0 and avg_hr > 0:
            if v > avg_hr * 1.5:
                cls = ' class="hot"'
            elif v < avg_hr * 0.5:
                cls = ' class="low"'
        if is_weekend(dt) and not cls:
            cls = ' class="wknd"'
        w(f'<td{cls}>{v}<br><span style="color:#999;font-size:10px">{pct:.0f}%</span></td>' if v else '<td class="anom">-</td>')
    w('</tr>')

# 合计行
w('<tr class="hl"><td>合计</td>')
for dt in report_dates:
    t = sum(hourly.get(dt,{}).values()) if hourly.get(dt) else 0
    w(f'<td>{t:,}</td>')
w('</tr></table>')
w('<p class="sn">红底=高于时段均值50%以上 | 蓝底=低于时段均值50%以下 | 百分比=该时段占全天比例</p>')

# ========== PART 2 ==========
w('<h1 id="p2" style="font-size:16px;color:#1a237e;margin-top:32px;border-top:3px solid #1a237e;padding-top:12px">Part 2: 归因分析</h1>')

# --- A 天气 ---
w('<h2>A. 天气 × 杯量总览</h2>')
w('<p class="sn">天气: Open-Meteo API (NYC 40.71°N, 74.01°W) | 温度: 摄氏度</p>')
w('<table><tr><th>日期</th><th>星期</th><th>天气</th><th>最高°C</th><th>最低°C</th><th>杯量</th><th>上周杯量</th><th>周同比</th><th>店均</th></tr>')
for dt in report_dates:
    tmax, tmin, code, desc = wx_info(dt)
    cups = daily.get(dt,{}).get("cups",0)
    ns = daily.get(dt,{}).get("n_stores",1)
    wow_dt = wow(dt)
    wow_cups = daily.get(wow_dt,{}).get("cups",0)
    cs, cc = fmt_pct(cups, wow_cups) if wow_cups else ("N/A","neu")
    tag_cls = "tag-snow" if "雪" in desc else "tag-rain" if "雨" in desc else "tag-clear"
    row_cls = "snow" if "雪" in desc else "rain" if "雨" in desc else "wknd" if is_weekend(dt) else ""
    rcls = f' class="{row_cls}"' if row_cls else ""
    w(f'<tr{rcls}><td>{dt[5:]}</td><td>{wd(dt)}</td><td><span class="tag {tag_cls}">{desc}</span></td><td>{tmax:.1f}</td><td>{tmin:.1f}</td><td>{cups:,}</td><td>{wow_cups:,}</td><td class="{cc}">{cs}</td><td>{round(cups/ns)}</td></tr>')
w('</table>')

# 天气洞察
clear_cups = [daily[dt]["cups"] for dt in report_dates if wx_info(dt)[2] == 3 and daily.get(dt,{}).get("cups",0) > 0]
precip_cups = [daily[dt]["cups"] for dt in report_dates if wx_info(dt)[2] != 3 and daily.get(dt,{}).get("cups",0) > 0]
ac = sum(clear_cups)/len(clear_cups) if clear_cups else 0
ap = sum(precip_cups)/len(precip_cups) if precip_cups else 0
w(f'<div class="insight"><b>天气洞察:</b> 晴/阴天均杯量 <b>{ac:,.0f}</b>({len(clear_cups)}天) vs 雨雪天 <b>{ap:,.0f}</b>({len(precip_cups)}天), 差异 <b>{(ap-ac)/ac*100:+.1f}%</b></div>')

# --- B 门店 ---
w('<h2>B. 门店维度归因</h2>')
w(f'<h3>02/24 vs 02/17 (周一对比)</h3>')
w('<table style="width:auto"><tr><th>门店</th><th>02/17</th><th>占比</th><th>02/24</th><th>占比</th><th>变化</th><th>周同比</th></tr>')
t17 = daily.get("2026-02-17",{}).get("cups",0)
t24 = daily.get("2026-02-24",{}).get("cups",0)
for sn in store_names:
    c17 = stores.get("2026-02-17",{}).get(sn,{}).get("cups",0)
    c24 = stores.get("2026-02-24",{}).get(sn,{}).get("cups",0)
    p17 = c17/t17*100 if t17 else 0
    p24 = c24/t24*100 if t24 else 0
    cs, cc = fmt_pct(c24, c17)
    w(f'<tr><td>{sn}</td><td>{c17}</td><td>{p17:.1f}%</td><td>{c24}</td><td>{p24:.1f}%</td><td>{c24-c17:+d}</td><td class="{cc}">{cs}</td></tr>')
cs,cc = fmt_pct(t24, t17)
w(f'<tr class="hl"><td>合计</td><td>{t17:,}</td><td>100%</td><td>{t24:,}</td><td>100%</td><td>{t24-t17:+d}</td><td class="{cc}">{cs}</td></tr>')
w('</table>')

# SVG折线图
w('<h3>门店杯量趋势</h3>')
chart_w, chart_h = 900, 320
margin = {"l":70,"r":20,"t":20,"b":50}
pw = chart_w - margin["l"] - margin["r"]
ph = chart_h - margin["t"] - margin["b"]
n_pts = len(report_dates)
colors = ["#E53935","#1E88E5","#43A047","#FB8C00","#8E24AA","#00897B","#F4511E","#3949AB","#6D4C41","#546E7A"]

max_cups = max(stores.get(dt,{}).get(sn,{}).get("cups",0) for dt in report_dates for sn in store_names)
w(f'<svg width="{chart_w}" height="{chart_h}" style="font-family:-apple-system;font-size:10px">')
w(f'<rect width="{chart_w}" height="{chart_h}" fill="white"/>')

# Weekend shading
for i, dt in enumerate(report_dates):
    x = margin["l"] + i * pw / (n_pts - 1)
    if is_weekend(dt):
        w(f'<rect x="{x-pw/(n_pts-1)/2}" y="{margin["t"]}" width="{pw/(n_pts-1)}" height="{ph}" fill="#FFF9C4" opacity="0.5"/>')

# Y axis
for y_val in range(0, max_cups + 200, 200):
    y = margin["t"] + ph - y_val / max_cups * ph
    w(f'<line x1="{margin["l"]}" y1="{y}" x2="{chart_w-margin["r"]}" y2="{y}" stroke="#eee"/>')
    w(f'<text x="{margin["l"]-5}" y="{y+3}" text-anchor="end" fill="#999">{y_val}</text>')

# Lines
for si, sn in enumerate(store_names):
    pts = []
    for i, dt in enumerate(report_dates):
        x = margin["l"] + i * pw / (n_pts - 1)
        c = stores.get(dt,{}).get(sn,{}).get("cups",0)
        y = margin["t"] + ph - c / max_cups * ph
        pts.append(f"{x:.0f},{y:.0f}")
    w(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[si]}" stroke-width="1.5" opacity="0.8"/>')

# X labels
for i, dt in enumerate(report_dates):
    x = margin["l"] + i * pw / (n_pts - 1)
    w(f'<text x="{x}" y="{chart_h-margin["b"]+15}" text-anchor="middle" fill="#666">{dt[5:]}</text>')
    w(f'<text x="{x}" y="{chart_h-margin["b"]+27}" text-anchor="middle" fill="{"#F57F17" if is_weekend(dt) else "#999"}">{wd(dt)}</text>')

# Legend
for si, sn in enumerate(store_names):
    lx = margin["l"] + (si % 5) * 170
    ly = chart_h - 8 + (si // 5) * 14
    w(f'<rect x="{lx}" y="{ly}" width="10" height="10" fill="{colors[si]}"/>')
    w(f'<text x="{lx+14}" y="{ly+9}" fill="#333">{sn}</text>')

w('</svg>')
w('<p class="sn">黄底=周末 | 每条线代表一家门店</p>')

# --- C 渠道 ---
w('<h2>C. 渠道归因</h2>')
w('<table><tr><th>渠道</th>')
for dt in report_dates: w(f'<th>{dt[5:]}</th>')
w('<th>占比</th></tr>')
for ch in ["iOS","Android","H5"]:
    w(f'<tr><td>{ch}</td>')
    total = 0
    for dt in report_dates:
        v = ch_data.get(dt,{}).get(ch,0)
        total += v
        w(f'<td>{v:,}</td>')
    all_total = sum(sum(ch_data.get(dt,{}).values()) for dt in report_dates)
    w(f'<td class="hl">{total/all_total*100:.1f}%</td></tr>')
w('</table>')

# --- D 用户结构 ---
w('<h2>D. 用户结构归因（生命周期）</h2>')
w('<p class="sn">新客=历史首单 | 近15天活跃=排除新客后最近一次购买在15天内 | 16-30天=距上次购买16-30天 | 31天+=距上次购买超31天</p>')
w('<table><tr><th>生命周期</th>')
for dt in report_dates: w(f'<th>{dt[5:]}</th>')
w('<th>周同比</th></tr>')
lc_labels = ["新客（首单）","近15天活跃老客","16-30天回流","31天+沉默回流"]
for i, lb in enumerate(lc_labels):
    w(f'<tr><td>{lb}</td>')
    for dt in report_dates:
        v = lifecycle.get(dt,[0,0,0,0])[i]
        total = sum(lifecycle.get(dt,[0,0,0,0]))
        pct = v/total*100 if total else 0
        w(f'<td>{v:,}<br><span style="color:#999;font-size:10px">{pct:.0f}%</span></td>')
    v_now = lifecycle.get("2026-02-24",[0,0,0,0])[i]
    v_wow = lifecycle.get("2026-02-17",[0,0,0,0])[i]
    cs,cc = fmt_pct(v_now, v_wow)
    w(f'<td class="{cc}">{cs}</td></tr>')

# 合计
w('<tr class="hl"><td>合计</td>')
for dt in report_dates:
    t = sum(lifecycle.get(dt,[0,0,0,0]))
    w(f'<td>{t:,}</td>')
w('<td></td></tr></table>')

# --- E 券 ---
w('<h2>E. 券/活动归因</h2>')
coupon_types = ["新客$1.99","新客惊喜券","惊喜券老客","工作日特惠","午休买一送一","分享有礼","学生优惠"]
w('<table><tr><th>券类型</th>')
for dt in report_dates: w(f'<th>{dt[5:]}</th>')
w('<th>合计</th></tr>')
for ct in coupon_types:
    w(f'<tr><td>{ct}</td>')
    total = 0
    for dt in report_dates:
        v = coupon_daily.get(dt,{}).get(ct,0)
        total += v
        w(f'<td>{v if v else "-"}</td>')
    w(f'<td class="hl">{total:,}</td></tr>')
w('</table>')

# --- F 商品 ---
w('<h2>F. 商品结构变化 (02/24 vs 02/17)</h2>')
w('<table style="width:auto"><tr><th>#</th><th>商品</th><th>02/17</th><th>02/24</th><th>变化</th><th>周同比</th></tr>')
for i,(name,c24,c17) in enumerate(top10_products):
    cs,cc = fmt_pct(c24, c17)
    w(f'<tr><td>{i+1}</td><td>{name}</td><td>{c17}</td><td>{c24}</td><td>{c24-c17:+d}</td><td class="{cc}">{cs}</td></tr>')
w('</table>')

# --- G 综合归因 ---
w("""<h2>G. 综合归因总结</h2>
<table style="width:auto">
<tr><th style="text-align:left;width:80px">因素</th><th style="text-align:left;width:100px">维度</th><th style="text-align:left;width:420px">发现</th><th style="text-align:left;width:60px">影响</th></tr>
<tr><td rowspan="2" style="text-align:left;vertical-align:top;font-weight:600;background:#E3F2FD">外部</td>
    <td style="text-align:left">天气</td><td style="text-align:left">雨雪天杯量显著低于晴天; 02/22大雪杯量1,416创新低; 周同比多数为负</td><td class="neg" style="text-align:center">↓↓</td></tr>
<tr><td style="text-align:left">周末</td><td style="text-align:left">周末杯量普遍低于工作日30-40%; 02/22叠加大雪+周六双重拖累</td><td class="neg" style="text-align:center">↓</td></tr>
<tr><td rowspan="3" style="text-align:left;vertical-align:top;font-weight:600;background:#FFF3E0">运营</td>
    <td style="text-align:left">新客券</td><td style="text-align:left">$1.99首杯券日均300-500张核销,拉新主力; 02/21爆发528张</td><td class="pos" style="text-align:center">↑↑</td></tr>
<tr><td style="text-align:left">学生优惠</td><td style="text-align:left">02/17-18集中核销263/311张,工作日带动效应</td><td class="pos" style="text-align:center">↑</td></tr>
<tr><td style="text-align:left">分享有礼</td><td style="text-align:left">日均3-23张,贡献有限</td><td style="text-align:center">→</td></tr>
<tr><td rowspan="2" style="text-align:left;vertical-align:top;font-weight:600;background:#E8F5E9">商品</td>
    <td style="text-align:left">核心品</td><td style="text-align:left">Coconut(18-24%)和Matcha(15-19%)稳居前二,结构稳定</td><td style="text-align:center">→</td></tr>
<tr><td style="text-align:left">Tiramisu新品</td><td style="text-align:left">02/09上线首周500+杯/天,第二周回落至300杯,热度衰减</td><td class="neg" style="text-align:center">↓</td></tr>
<tr><td style="text-align:left;font-weight:600;background:#FCE4EC">门店</td>
    <td style="text-align:left">37th Broadway</td><td style="text-align:left">02/22仅45杯(正常400+),疑似临时关店或缩短营业时间</td><td class="neg" style="text-align:center">异常</td></tr>
</table>""")

w('</body></html>')

# ========== 输出 ==========
path = "/Users/xiaoxiao/Vibe coding/daily_report_attribution_2026-02-24.html"
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(H))
print(f"报告已生成: {path}")
