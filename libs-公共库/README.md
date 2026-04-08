# libs-公共库 Shared Libraries

跨项目复用的公共模块。

## 已实现 Implemented

### `cyberdata/` — CyberData API Client

统一的数据查询客户端，替代各脚本中重复的 `run_sql()` 实现。

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'libs-公共库'))
from cyberdata import CyberDataClient

client = CyberDataClient()
headers, rows = client.query("店均杯量", "SELECT ...")
```

## 待抽取 Planned

- `feishu/` — 飞书文档发布（从 `tools-工具/feishu-飞书/` 和 `新客留存提升/publish_feishu.py` 合并）
- `report/` — HTML 报告模板引擎（从各实验的 HTML 拼接逻辑抽取）
- `stats/` — 统计检验（SRM、显著性检验，从 `0212_significance_test.py` 抽取）
