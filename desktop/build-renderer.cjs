const fs = require('node:fs')
const path = require('node:path')

const source = path.resolve(__dirname, '../frontend/dist')
const target = path.resolve(__dirname, 'renderer')
if (path.dirname(target) !== path.resolve(__dirname) || !fs.statSync(path.join(source, 'index.html')).isFile()) {
  throw new Error('Frontend build is missing or renderer path is invalid')
}

fs.rmSync(target, { recursive: true, force: true })
fs.cpSync(source, target, { recursive: true })
console.log('Copied frontend build into desktop/renderer')
