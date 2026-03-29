const puppeteer = require('puppeteer');
const path = require('path');

const URL = 'http://134.175.228.73:8081/view/69a34eaa66e2c30377cc4071';
const OUTPUT_DIR = path.join(__dirname, 'podcast-screenshots');
const WIDTH = 1280;
const HEIGHT = 960;

(async () => {
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: WIDTH, height: HEIGHT, deviceScaleFactor: 2 });

  console.log('正在加载页面...');
  await page.goto(URL, { waitUntil: 'networkidle0', timeout: 120000 });
  await new Promise(r => setTimeout(r, 3000));

  // 滚动到底部触发所有懒加载
  console.log('触发懒加载...');
  const totalHeight = await page.evaluate(async () => {
    const delay = ms => new Promise(r => setTimeout(r, ms));
    let currentPos = 0;
    const maxHeight = document.documentElement.scrollHeight;
    while (currentPos < maxHeight) {
      window.scrollTo(0, currentPos);
      currentPos += 800;
      await delay(200);
    }
    window.scrollTo(0, 0);
    await delay(500);
    return document.documentElement.scrollHeight;
  });

  console.log('页面总高度:', totalHeight);

  // 重新获取标题位置（横屏下布局会变）
  const headings = await page.evaluate(() => {
    const els = document.querySelectorAll('h1, h2');
    return Array.from(els).map(el => {
      const rect = el.getBoundingClientRect();
      return {
        tag: el.tagName,
        text: el.textContent?.trim(),
        top: Math.round(rect.top + window.scrollY)
      };
    });
  });

  console.log('横屏标题位置:');
  headings.forEach(h => console.log(`  [${h.tag}] y=${h.top} "${h.text}"`));

  // 根据横屏布局重新选位置
  const positions = [
    { y: 0, label: '封面标题' },
  ];

  // 根据实际标题位置动态选取
  const targetSections = [
    '陈林',           // 嘉宾介绍
    '开场',           // 开场
    '发生了什么',     // 军事冲突
    '美国内部',       // 内部分裂
    '抵抗教义',       // 威慑失效
    '核心观点',       // 深度解析
    '关键概念',       // 知识图谱
    '详细时间轴',     // 时间轴
  ];

  for (const keyword of targetSections) {
    const match = headings.find(h => h.text.includes(keyword));
    if (match) {
      // 往上偏移一点让标题出现在画面上方
      positions.push({ y: Math.max(0, match.top - 60), label: match.text });
    }
  }

  // 确保9张
  const finalPositions = positions.slice(0, 9);

  console.log('\n截图计划:');
  finalPositions.forEach((p, i) => console.log(`  第${i+1}张: y=${p.y} — ${p.label}`));

  for (let i = 0; i < finalPositions.length; i++) {
    const pos = finalPositions[i];
    await page.evaluate(y => window.scrollTo({ top: y, behavior: 'instant' }), pos.y);
    await new Promise(r => setTimeout(r, 1000));

    const filename = `${String(i + 1).padStart(2, '0')}.png`;
    await page.screenshot({
      path: path.join(OUTPUT_DIR, filename),
      type: 'png'
    });
    console.log(`✓ 第${i+1}张: ${filename} — ${pos.label}`);
  }

  await browser.close();
  console.log(`\n完成！9张横屏截图已保存到: ${OUTPUT_DIR}`);
})();
