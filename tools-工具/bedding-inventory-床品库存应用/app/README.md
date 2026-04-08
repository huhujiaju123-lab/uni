# 套件库存自动计算系统 (ICAS)

电商四件套库存自动计算工具，根据零部件库存、销售比例和SKU映射表，自动计算各SKU的可售库存。

## 功能特点

- 上传三个Excel文件即可自动计算
- 支持按销售比例加权分配零部件库存
- 可调整安全库存系数（默认30%）
- 可选择在售颜色进行筛选
- 支持下载计算结果（简版/详细版）

## 本地运行

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 启动应用

```bash
# 方式一：使用启动脚本
./run.sh

# 方式二：命令行启动
python3 -m streamlit run app.py
```

### 3. 访问应用

打开浏览器访问：http://localhost:8501

## 云端部署（Streamlit Cloud）

### 步骤一：上传到GitHub

1. 在GitHub创建新仓库（如 `bedding-inventory`）
2. 将本文件夹内容推送到仓库：

```bash
cd bedding-inventory-app
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/bedding-inventory.git
git push -u origin main
```

### 步骤二：部署到Streamlit Cloud

1. 访问 https://share.streamlit.io
2. 点击 "New app"
3. 选择你的GitHub仓库
4. Main file path 填写：`app.py`
5. 点击 "Deploy"

部署完成后会获得一个公开链接，如：
`https://你的应用名.streamlit.app`

## 输入文件格式

### 库存源文件
必须包含列：`商品名称`、`可用数`

商品名称示例：
- 床笠150*200*35-木青绿四季款
- 床单240*250-米白四季款
- 被套220*240-丁香紫四季款
- 枕套（一对）-木青绿四季款

### 销售比例表
两列数据（无表头）：套件名称 | 比例

示例：
```
【床单款】1.5米床套件，搭配200x230cm被套    0.0602
【床笠款】1.5米床套件，搭配200x230cm被套    0.0555
```

### SKU映射表
三列数据：SKU_ID | 套件描述 | 颜色

## 计算逻辑

1. **加权分配**：按销售比例分配共享零部件
2. **木桶效应**：取被套、床单/笠、枕套的最小值
3. **安全系数**：最终库存 = 理论库存 × 30%
