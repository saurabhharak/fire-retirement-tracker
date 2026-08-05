// Runs vitest with NODE_ENV=test. The ambient environment (e.g. CI or a
// production shell) may set NODE_ENV=production, which makes npm prune
// devDependencies and Vite resolve React's production build (no React.act),
// breaking @testing-library/react. This wrapper forces test mode.
process.env.NODE_ENV = "test";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const vitestBin = path.join(__dirname, "..", "node_modules", "vitest", "vitest.mjs");
const args = process.argv.slice(2);
const result = spawnSync(process.execPath, [vitestBin, ...args], {
  stdio: "inherit",
  cwd: path.join(__dirname, ".."),
});
process.exit(result.status ?? 1);
