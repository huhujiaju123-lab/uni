const puppeteer = require('puppeteer');
const path = require('path');
const { execSync } = require('child_process');

(async () => {
  const htmlPath = path.resolve(__dirname, '同人卦海报.html');
  const framesDir = path.resolve(__dirname, 'poster_frames');
  const outputGif = path.resolve(__dirname, '同人卦海报.gif');

  // Clean up
  execSync(`rm -rf "${framesDir}" && mkdir -p "${framesDir}"`);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 375, height: 1200, deviceScaleFactor: 2 });
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0', timeout: 15000 });

  // Wait for QR code and fonts
  await new Promise(r => setTimeout(r, 2000));

  // Get poster element bounds
  const posterBox = await page.evaluate(() => {
    const el = document.getElementById('poster');
    const rect = el.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  });

  // Capture 60 frames over 3 seconds (20fps)
  const fps = 15;
  const duration = 3; // seconds
  const totalFrames = fps * duration;

  console.log(`Capturing ${totalFrames} frames at ${fps}fps...`);
  console.log(`Poster size: ${posterBox.width}x${posterBox.height}`);

  for (let i = 0; i < totalFrames; i++) {
    const frameNum = String(i).padStart(4, '0');
    await page.screenshot({
      path: path.join(framesDir, `frame_${frameNum}.png`),
      clip: {
        x: posterBox.x * 2,
        y: posterBox.y * 2,
        width: posterBox.width * 2,
        height: posterBox.height * 2
      },
      captureBeyondViewport: true
    });

    // Wait for next frame
    if (i < totalFrames - 1) {
      await new Promise(r => setTimeout(r, 1000 / fps));
    }

    if (i % 10 === 0) console.log(`  frame ${i}/${totalFrames}`);
  }

  console.log('Frames captured. Converting to GIF...');
  await browser.close();

  // Use ffmpeg to create high quality GIF
  // First generate palette for better quality
  execSync(`ffmpeg -y -framerate ${fps} -i "${framesDir}/frame_%04d.png" -vf "scale=750:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff" "${framesDir}/palette.png"`, { stdio: 'inherit' });

  execSync(`ffmpeg -y -framerate ${fps} -i "${framesDir}/frame_%04d.png" -i "${framesDir}/palette.png" -lavfi "scale=750:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3" -loop 0 "${outputGif}"`, { stdio: 'inherit' });

  // Get file size
  const stats = require('fs').statSync(outputGif);
  const sizeMB = (stats.size / 1024 / 1024).toFixed(1);
  console.log(`\nDone! ${outputGif}`);
  console.log(`Size: ${sizeMB} MB`);

  // Cleanup frames
  execSync(`rm -rf "${framesDir}"`);
})();
