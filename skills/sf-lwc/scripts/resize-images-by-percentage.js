// resize-images-by-percentage.js
// Usage: node resize-images-by-percentage.js
// Requires: npm install sharp

const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const README_PATH = path.join(__dirname, '..', 'README.md');
const IMAGE_DIR = path.join(__dirname, 'docs', 'images');

// Regex to match <img src="..." ... width="XX%">
const IMG_TAG_REGEX = /<img\s+[^>]*src=["']([^"']+)["'][^>]*width=["'](\d+)%["'][^>]*>/gi;

function getAllImgTags(content) {
  const matches = [];
  let match;
  while ((match = IMG_TAG_REGEX.exec(content)) !== null) {
    matches.push({
      src: match[1],
      percent: parseInt(match[2], 10),
    });
  }
  return matches;
}

async function resizeImage(src, percent) {
  const imgPath = path.isAbsolute(src) ? src : path.join(__dirname, src);
  if (!fs.existsSync(imgPath)) {
    console.warn(`Image not found: ${imgPath}`);
    return;
  }
  const img = sharp(imgPath);
  const metadata = await img.metadata();
  const targetWidth = Math.round(metadata.width * (percent / 100));
  const ext = path.extname(imgPath);
  const base = path.basename(imgPath, ext);
  const outPath = path.join(path.dirname(imgPath), `${base}-${percent}${ext}`);
  await img.resize({ width: targetWidth }).toFile(outPath);
  console.log(`Resized ${src} to ${percent}% (${targetWidth}px): ${outPath}`);
}

async function main() {
  const readme = fs.readFileSync(README_PATH, 'utf8');
  const imgTags = getAllImgTags(readme);
  if (imgTags.length === 0) {
    console.log('No <img> tags with width="XX%" found.');
    return;
  }
  for (const { src, percent } of imgTags) {
    try {
      await resizeImage(src, percent);
    } catch (e) {
      console.error(`Failed to resize ${src}:`, e.message);
    }
  }
}

main();
