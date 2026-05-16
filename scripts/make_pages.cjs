const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const docsDir = path.join(root, "docs");
const assetsDir = path.join(docsDir, "assets");

function read(p) {
  return fs.readFileSync(p, "utf8");
}

function write(p, content) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content, "utf8");
}

function copy(src, dst) {
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
}

function toPagesPath(html) {
  return html
    .replaceAll('href="/"', 'href="./index.html"')
    .replaceAll('href="/register"', 'href="./register.html"')
    .replaceAll('href="/login"', 'href="./login.html"')
    .replaceAll('href="/chat"', 'href="./chat.html"')
    .replaceAll('href="/ui"', 'href="./chat.html"')
    .replaceAll('href="/docs"', 'href="#" id="apiDocs"')
    .replaceAll('<script src=/static/docs.js></script>', '<script src="./assets/docs.js"></script>')
    .replaceAll('href="/static/app.css"', 'href="./assets/app.css"');
}

function addApiBoot(html) {
  const inject = [
    '    <script src="./config.js"></script>',
    '    <script src="./assets/api.js"></script>',
  ].join("\n");
  if (html.includes(inject)) return html;
  if (html.includes("<script>")) {
    return html.replace("<script>", `${inject}\n\n    <script>`);
  }
  return html.replace("</body>", `${inject}\n  </body>`);
}

function patchPageScripts(html) {
  return html
    .replaceAll('fetch("/', 'apiFetch("/')
    .replaceAll("window.location.href = \"/login\"", "window.location.href = \"./login.html\"")
    .replaceAll("window.location.href = \"/chat\"", "window.location.href = \"./chat.html\"")
    .replaceAll("window.location.href = \"/register\"", "window.location.href = \"./register.html\"")
    .replaceAll("window.location.href = \"/\"", "window.location.href = \"./index.html\"");
}

function build() {
  fs.mkdirSync(assetsDir, { recursive: true });

  copy(path.join(root, "web", "static", "app.css"), path.join(assetsDir, "app.css"));
  copy(path.join(root, "web", "static", "docs.js"), path.join(assetsDir, "docs.js"));

  const pages = ["index", "login", "register", "chat"];
  for (const name of pages) {
    const src = path.join(root, "web", "templates", `${name}.html`);
    const dst = path.join(docsDir, `${name}.html`);
    let html = read(src);
    html = toPagesPath(html);
    html = patchPageScripts(html);
    html = html.replace(
      "let activeConvId = null;",
      "let activeConvId = null;\n      const apiDocs = document.getElementById(\"apiDocs\");\n      if (apiDocs) apiDocs.href = apiUrl(\"/docs\");"
    );
    html = html.replace(
      "const status = document.getElementById(\"status\");",
      "const status = document.getElementById(\"status\");\n        const apiDocs = document.getElementById(\"apiDocs\");\n        if (apiDocs) apiDocs.href = apiUrl(\"/docs\");"
    );
    html = addApiBoot(html);
    write(dst, html);
  }

  let docsJs = read(path.join(assetsDir, "docs.js"));
  docsJs = docsJs
    .replaceAll("fetch(\"/", "apiFetch(\"/")
    .replaceAll("fetch('/", "apiFetch('/")
    .replaceAll("window.location.href = \"/login\";", "window.location.href = \"./login.html\";");
  write(path.join(assetsDir, "docs.js"), docsJs);

  write(
    path.join(docsDir, "config.js"),
    [
      "// Set this to your Railway API domain, for example:",
      "// window.RAG_API_BASE = 'https://your-app.up.railway.app';",
      "window.RAG_API_BASE = '';",
      "",
    ].join("\n")
  );

  write(
    path.join(assetsDir, "api.js"),
    [
      "(function () {",
      "  var base = (window.RAG_API_BASE || '').trim().replace(/\\/+$/, '');",
      "  function apiUrl(p) {",
      "    var path = p || '/';",
      "    if (/^https?:\\/\\//i.test(path)) return path;",
      "    if (path.charAt(0) !== '/') path = '/' + path;",
      "    return base + path;",
      "  }",
      "  function apiFetch(p, opts) {",
      "    return fetch(apiUrl(p), opts || {});",
      "  }",
      "  window.apiUrl = apiUrl;",
      "  window.apiFetch = apiFetch;",
      "})();",
      "",
    ].join("\n")
  );

  write(path.join(docsDir, ".nojekyll"), "");
  console.log("GitHub Pages files generated in docs/");
}

build();
