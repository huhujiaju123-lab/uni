const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  const filePath = path.resolve(__dirname, '0212涨价实验报告_0212-0304.html');
  await page.goto('file://' + filePath, { waitUntil: 'networkidle0' });

  await page.setViewport({ width: 1400, height: 800 });

  await page.screenshot({
    path: path.resolve(__dirname, '0212涨价实验报告_0212-0304.png'),
    fullPage: true
  });

  console.log('截图已保存: 0212涨价实验报告_0212-0304.png');
  await browser.close();
})();
