const fs = require('node:fs')
const path = require('node:path')

if (process.platform !== 'win32') {
  throw new Error('The portable Windows build must run on Windows')
}

const desktopDir = __dirname
const electronDist = path.join(desktopDir, 'node_modules', 'electron', 'dist')
const rendererDir = path.join(desktopDir, 'renderer')
const releaseDir = path.join(desktopDir, 'release')
const packageJson = require('./package.json')

for (const requiredFile of [
  path.join(electronDist, 'electron.exe'),
  path.join(rendererDir, 'index.html'),
  path.join(rendererDir, 'favicon.ico')
]) {
  if (!fs.statSync(requiredFile, { throwIfNoEntry: false })?.isFile()) {
    throw new Error(`Required build file is missing: ${requiredFile}`)
  }
}

fs.mkdirSync(releaseDir, { recursive: true })
const outputDir = fs.mkdtempSync(path.join(releaseDir, `iCinema-win32-${process.arch}-`))
fs.cpSync(electronDist, outputDir, { recursive: true })
fs.renameSync(path.join(outputDir, 'electron.exe'), path.join(outputDir, 'iCinema.exe'))

const appDir = path.join(outputDir, 'resources', 'app')
fs.mkdirSync(appDir)
for (const file of [
  'main.cjs',
  'navigation.cjs',
  'app-protocol.cjs',
  'runtime-config.cjs',
  'storage-policy.cjs',
  'preload.cjs'
]) {
  fs.copyFileSync(path.join(desktopDir, file), path.join(appDir, file))
}
fs.cpSync(rendererDir, path.join(appDir, 'renderer'), { recursive: true })
fs.writeFileSync(path.join(appDir, 'package.json'), JSON.stringify({
  name: packageJson.name,
  productName: 'iCinema',
  version: packageJson.version,
  main: packageJson.main,
  private: true
}, null, 2))
fs.writeFileSync(path.join(appDir, 'distribution.json'), JSON.stringify({ mode: 'portable' }))

console.log(`Portable Windows app: ${path.join(outputDir, 'iCinema.exe')}`)
