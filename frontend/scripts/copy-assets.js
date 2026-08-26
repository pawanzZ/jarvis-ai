/**
 * Jarvis AI - Asset Copy Script
 * Synchronizes HTML and CSS files from src/ to dist/ after compilation.
 */

const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '..', 'src');
const distDir = path.join(__dirname, '..', 'dist');

function copyRecursive(src, dest) {
  if (!fs.existsSync(src)) return;
  const stats = fs.statSync(src);

  if (stats.isDirectory()) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    const files = fs.readdirSync(src);
    for (const file of files) {
      copyRecursive(path.join(src, file), path.join(dest, file));
    }
  } else if (stats.isFile()) {
    const ext = path.extname(src);
    if (ext === '.html' || ext === '.css' || ext === '.json' || ext === '.svg') {
      const destDir = path.dirname(dest);
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }
      fs.copyFileSync(src, dest);
      console.log(`Copied: ${path.relative(srcDir, src)} -> ${path.relative(distDir, dest)}`);
    }
  }
}

console.log('Synchronizing HUD assets to dist/...');
copyRecursive(srcDir, distDir);
console.log('Asset synchronization complete.');
