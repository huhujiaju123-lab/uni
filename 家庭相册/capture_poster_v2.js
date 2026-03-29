const puppeteer = require('puppeteer');
const path = require('path');
const { execSync } = require('child_process');
const fs = require('fs');

(async () => {
  const htmlPath = path.resolve(__dirname, '同人卦海报.html');
  const framesDir = path.resolve(__dirname, 'poster_frames');
  const outputMp4 = path.resolve(__dirname, '同人卦海报.mp4');
  const outputGif = path.resolve(__dirname, '同人卦海报.gif');

  execSync(`rm -rf "${framesDir}" && mkdir -p "${framesDir}"`);

  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();

  // iPhone 尺寸 (9:16竖屏视频)，用 1080x1920
  await page.setViewport({ width: 375, height: 700, deviceScaleFactor: 3 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 15000 });
  await new Promise(r => setTimeout(r, 2500));

  // 获取海报尺寸
  const posterBox = await page.evaluate(() => {
    const el = document.getElementById('poster');
    const rect = el.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  });

  console.log(`Poster: ${posterBox.width}x${posterBox.height} (CSS), rendered at 3x = ${posterBox.width*3}x${posterBox.height*3}`);

  // 策略：先截完整静态图，再截篝火区域的动画帧，最后合成视频
  // 视频方案：缓慢从上往下滚动 + 篝火区域停留展示动画

  const fps = 24;
  const totalHeight = posterBox.height;
  const viewHeight = 700; // viewport height in CSS px
  const scale = 3;

  // Phase 1: 从顶部缓慢滚动到底部 (4秒)
  // Phase 2: 滚回篝火区域停留 (2秒展示动画)
  // Phase 3: 继续滚到底部二维码 (2秒)

  const scrollDuration = 5; // seconds to scroll top to bottom
  const pauseDuration = 2; // pause at bonfire
  const endPause = 1.5; // pause at QR code

  // 找篝火区域的位置
  const bonfireY = await page.evaluate(() => {
    // bonfire-wrap 元素位置
    const el = document.querySelector('.bonfire-wrap');
    if (!el) return 300;
    return el.getBoundingClientRect().top;
  });

  console.log(`Bonfire at y=${bonfireY}`);

  // 总共：scroll(5s) + pause(2s) + scroll_to_end(1.5s) + end_pause(1.5s) = 10s
  const totalDuration = scrollDuration + pauseDuration + scrollDuration * 0.3 + endPause;
  const totalFrames = Math.ceil(totalDuration * fps);
  const scrollableDistance = Math.max(0, totalHeight - viewHeight);

  console.log(`Total frames: ${totalFrames}, duration: ${totalDuration}s, scrollable: ${scrollableDistance}px`);

  // 计算篝火停留点（让篝火在视口中央偏上）
  const bonfirePauseScroll = Math.max(0, Math.min(bonfireY - 150, scrollableDistance));
  // 终点
  const endScroll = scrollableDistance;

  let frameIdx = 0;

  async function captureFrame(scrollY) {
    await page.evaluate(y => window.scrollTo(0, y), scrollY);
    await new Promise(r => setTimeout(r, 30)); // settle

    const frameNum = String(frameIdx).padStart(4, '0');
    await page.screenshot({
      path: path.join(framesDir, `frame_${frameNum}.png`),
      clip: {
        x: 0,
        y: 0,
        width: 375 * scale,
        height: 700 * scale
      },
      captureBeyondViewport: false
    });
    frameIdx++;
  }

  // Ease function
  function easeInOut(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  }

  console.log('Phase 1: Scroll to bonfire...');
  const phase1Frames = Math.ceil(scrollDuration * 0.6 * fps);
  for (let i = 0; i < phase1Frames; i++) {
    const t = easeInOut(i / (phase1Frames - 1));
    const scrollY = t * bonfirePauseScroll;
    await captureFrame(scrollY);
    if (i % 10 === 0) console.log(`  frame ${frameIdx}/${totalFrames}`);
  }

  console.log('Phase 2: Pause at bonfire (show animation)...');
  const phase2Frames = Math.ceil(pauseDuration * fps);
  for (let i = 0; i < phase2Frames; i++) {
    await captureFrame(bonfirePauseScroll);
    await new Promise(r => setTimeout(r, 1000 / fps));
    if (i % 10 === 0) console.log(`  frame ${frameIdx}/${totalFrames}`);
  }

  console.log('Phase 3: Scroll to end...');
  const phase3Frames = Math.ceil(scrollDuration * 0.4 * fps);
  for (let i = 0; i < phase3Frames; i++) {
    const t = easeInOut(i / (phase3Frames - 1));
    const scrollY = bonfirePauseScroll + t * (endScroll - bonfirePauseScroll);
    await captureFrame(scrollY);
    if (i % 10 === 0) console.log(`  frame ${frameIdx}/${totalFrames}`);
  }

  console.log('Phase 4: Pause at QR code...');
  const phase4Frames = Math.ceil(endPause * fps);
  for (let i = 0; i < phase4Frames; i++) {
    await captureFrame(endScroll);
    if (i % 10 === 0) console.log(`  frame ${frameIdx}/${totalFrames}`);
  }

  console.log(`Total captured: ${frameIdx} frames`);
  await browser.close();

  // 转 MP4 (H.264, iPhone兼容)
  console.log('Converting to MP4...');
  execSync(`ffmpeg -y -framerate ${fps} -i "${framesDir}/frame_%04d.png" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -vf "scale=1080:-2:flags=lanczos" -movflags +faststart "${outputMp4}"`, { stdio: 'inherit' });

  // 也做一个短GIF（只截篝火区域的动画，适合微信表情包）
  console.log('Creating bonfire GIF...');
  const gifFramesDir = path.resolve(__dirname, 'gif_frames');
  execSync(`rm -rf "${gifFramesDir}" && mkdir -p "${gifFramesDir}"`);

  // 用phase2的帧（已经在篝火位置）
  const phase2Start = phase1Frames;
  const gifFrameCount = Math.min(phase2Frames, 30);
  for (let i = 0; i < gifFrameCount; i++) {
    const srcNum = String(phase2Start + i).padStart(4, '0');
    const dstNum = String(i).padStart(4, '0');
    fs.copyFileSync(
      path.join(framesDir, `frame_${srcNum}.png`),
      path.join(gifFramesDir, `frame_${dstNum}.png`)
    );
  }

  execSync(`ffmpeg -y -framerate ${fps} -i "${gifFramesDir}/frame_%04d.png" -vf "scale=750:-1:flags=lanczos,palettegen=max_colors=256" "${gifFramesDir}/palette.png" -update 1`, { stdio: 'inherit' });
  execSync(`ffmpeg -y -framerate ${fps} -i "${gifFramesDir}/frame_%04d.png" -i "${gifFramesDir}/palette.png" -lavfi "scale=750:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=sierra2_4a" -loop 0 "${outputGif}"`, { stdio: 'inherit' });

  // Sizes
  const mp4Size = (fs.statSync(outputMp4).size / 1024 / 1024).toFixed(1);
  const gifSize = (fs.statSync(outputGif).size / 1024 / 1024).toFixed(1);

  console.log(`\n✅ MP4: ${outputMp4} (${mp4Size} MB) — 朋友圈发视频用这个`);
  console.log(`✅ GIF: ${outputGif} (${gifSize} MB) — 篝火动画循环`);

  execSync(`rm -rf "${framesDir}" "${gifFramesDir}"`);
})();
