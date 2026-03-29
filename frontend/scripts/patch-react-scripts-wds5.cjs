#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function patchReactScriptsWdsConfig() {
  const configPath = path.join(
    __dirname,
    "..",
    "node_modules",
    "react-scripts",
    "config",
    "webpackDevServer.config.js"
  );

  if (!fs.existsSync(configPath)) {
    console.warn(
      `[patch-react-scripts-wds5] Skipping: ${configPath} does not exist`
    );
    return;
  }

  const original = fs.readFileSync(configPath, "utf8");
  let patched = original;
  let changed = false;

  const middlewareHooks =
    /onBeforeSetupMiddleware\(devServer\)\s*\{[\s\S]*?\n\s*\},\n\s*onAfterSetupMiddleware\(devServer\)\s*\{[\s\S]*?\n\s*\},/m;

  const replacement = `setupMiddlewares(middlewares, devServer) {
      if (!devServer) {
        throw new Error('webpack-dev-server is not defined');
      }

      // Keep evalSourceMapMiddleware before redirectServedPath.
      devServer.app.use(evalSourceMapMiddleware(devServer));

      if (fs.existsSync(paths.proxySetup)) {
        // Register user-provided middleware for proxy reasons.
        require(paths.proxySetup)(devServer.app);
      }

      // Redirect to PUBLIC_URL/homepage when URL does not match.
      devServer.app.use(redirectServedPath(paths.publicUrlOrPath));

      // Reset old service workers in development.
      devServer.app.use(noopServiceWorkerMiddleware(paths.publicUrlOrPath));

      return middlewares;
    },`;

  if (!patched.includes("setupMiddlewares(middlewares, devServer)")) {
    if (!middlewareHooks.test(patched)) {
      throw new Error(
        "[patch-react-scripts-wds5] Unable to locate CRA middleware hooks to patch"
      );
    }
    patched = patched.replace(middlewareHooks, replacement);
    changed = true;
  }

  if (patched.includes("https: getHttpsConfig(),")) {
    patched = patched.replace(
      "    https: getHttpsConfig(),",
      `    server: (() => {
      const httpsConfig = getHttpsConfig();
      if (httpsConfig && typeof httpsConfig === 'object') {
        return { type: 'https', options: httpsConfig };
      }
      return httpsConfig ? 'https' : 'http';
    })(),`
    );
    changed = true;
  }

  if (!changed) {
    console.log("[patch-react-scripts-wds5] Already patched");
    return;
  }

  fs.writeFileSync(configPath, patched, "utf8");
  console.log("[patch-react-scripts-wds5] Patched react-scripts dev server config");
}

patchReactScriptsWdsConfig();
