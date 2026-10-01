// Lace website: theme picker, hero rotation, code tabs, a tiny Python highlighter, copy buttons.
(() => {
  "use strict";

  // Canvas and accent colours straight from lace's DOCK_THEMES (CORE.canvas_bg / accent_color).
  // Grouped as lace's theme_groups() groups them.
  const THEMES = [
    { group: "Basics",          key: "midnight_neo",    name: "Midnight Neo",    bg: "#0b0d14", accent: "#375fe2" },
    { group: "Basics",          key: "dark",            name: "Dark",            bg: "#121314", accent: "#0078d4" },
    { group: "Basics",          key: "mocha_neo",       name: "Mocha Neo",       bg: "#241e1b", accent: "#c86e3c" },
    { group: "Basics",          key: "slate",           name: "Slate",           bg: "#969ca6", accent: "#164696" },
    { group: "Basics",          key: "caramel_neo",     name: "Caramel Neo",     bg: "#c5c2bd", accent: "#aa5900" },
    { group: "Basics",          key: "neutral",         name: "Neutral",         bg: "#bebfc2", accent: "#0068c0" },
    { group: "Basics",          key: "cream_neo",       name: "Cream Neo",       bg: "#f0ebe1", accent: "#b05c00" },
    { group: "Basics",          key: "light",           name: "Light",           bg: "#eeeef1", accent: "#0066c0" },
    { group: "Editor Classics", key: "dracula",         name: "Dracula",         bg: "#282a36", accent: "#bd93f9" },
    { group: "Editor Classics", key: "monokai",         name: "Monokai",         bg: "#1c1a1d", accent: "#ffd866" },
    { group: "Editor Classics", key: "nordic",          name: "Nordic",          bg: "#282e3a", accent: "#88c0d0" },
    { group: "Editor Classics", key: "catppuccin",      name: "Catppuccin",      bg: "#1e1e2e", accent: "#cba6f7" },
    { group: "Editor Classics", key: "tokyo_night",     name: "Tokyo Night",     bg: "#1a1b26", accent: "#7aa2f7" },
    { group: "Editor Classics", key: "solarized_dark",  name: "Solarized Dark",  bg: "#002b36", accent: "#268bd2" },
    { group: "Editor Classics", key: "solarized_light", name: "Solarized Light", bg: "#fdf6e3", accent: "#137fc6" },
    { group: "Neon & Edge",     key: "cyberpunk_neon",  name: "Cyberpunk Neon",  bg: "#0e0b1c", accent: "#ff007f" },
    { group: "Neon & Edge",     key: "violet_haze",     name: "Violet Haze",     bg: "#282a36", accent: "#bd93f9" },
  ];
  const src = (t) => `img/themes/${t.key}.webp`;
  const root = document.documentElement;
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Dark accents (light themes') are lifted so they stay readable on the dark page.
  function pageAccent(hex) {
    return `color-mix(in oklab, ${hex} 78%, white)`;
  }

  // Preload theme screenshots once the page has settled.
  addEventListener("load", () => THEMES.forEach((t) => { new Image().src = src(t); }));

  function swap(img, url, alt) {
    if (img.getAttribute("src") === url) return;
    if (reducedMotion) { img.src = url; img.alt = alt; return; }
    img.classList.add("fading");
    setTimeout(() => {
      img.src = url;
      img.alt = alt;
      const done = () => img.classList.remove("fading");
      if (img.complete) requestAnimationFrame(done); else img.addEventListener("load", done, { once: true });
    }, 220);
  }

  // Theme picker
  const picker = document.getElementById("theme-picker");
  const stage = document.getElementById("theme-img");
  const rows = {};
  const chips = THEMES.map((t, i) => {
    if (!rows[t.group]) {
      const row = document.createElement("div");
      row.className = "picker-group";
      row.innerHTML = `<span class="picker-label">${t.group}</span>`;
      picker.appendChild(row);
      rows[t.group] = row;
    }
    const b = document.createElement("button");
    b.type = "button";
    b.className = "theme-chip";
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", i === 0 ? "true" : "false");
    b.style.setProperty("--chip-bg", t.bg);
    b.style.setProperty("--chip-accent", t.accent);
    b.innerHTML = `<span class="chip-dot" aria-hidden="true"></span>${t.name}`;
    b.addEventListener("click", () => select(i, true));
    rows[t.group].appendChild(b);
    return b;
  });

  function select(i, fromUser) {
    const t = THEMES[i];
    chips.forEach((c, j) => c.setAttribute("aria-selected", j === i ? "true" : "false"));
    swap(stage, src(t), `The demo app in the ${t.name} theme`);
    root.style.setProperty("--accent", pageAccent(t.accent));
    if (fromUser) stopHero();
  }

  // Hero rotation
  const heroImg = document.getElementById("hero-img");
  const heroName = document.getElementById("hero-name");
  const heroSwatch = document.getElementById("hero-swatch");
  const heroOrder = ["cyberpunk_neon", "tokyo_night", "light", "monokai", "nordic", "cream_neo", "dracula", "solarized_light", "mocha_neo"]
    .map((k) => THEMES.find((t) => t.key === k));
  let heroIndex = 0;
  let heroTimer = null;

  function showHero(t) {
    swap(heroImg, src(t), `The Lace demo app in the ${t.name} theme`);
    heroName.textContent = t.name;
    heroSwatch.style.background = t.accent;
  }
  function stopHero() { clearInterval(heroTimer); heroTimer = null; }

  showHero(heroOrder[0]);
  root.style.setProperty("--accent", pageAccent("#7aa2f7"));
  if (!reducedMotion) {
    heroTimer = setInterval(() => {
      if (document.hidden) return;
      heroIndex = (heroIndex + 1) % heroOrder.length;
      showHero(heroOrder[heroIndex]);
    }, 4200);
  }

  // Code tabs
  const tabs = document.querySelectorAll(".code-tabs [role=tab]");
  const panels = document.querySelectorAll(".code[data-panel]");
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((t) => t.setAttribute("aria-selected", t === tab ? "true" : "false"));
    panels.forEach((p) => { p.hidden = p.dataset.panel !== tab.dataset.tab; });
  }));

  // Minimal Python highlighter: comments, strings, keywords, numbers, builtins, calls.
  const KW = new Set("import from as if elif else for in while def class return with not and or is None True False pass try except finally lambda yield raise".split(" "));
  const BUILTIN = new Set("self print len range".split(" "));
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const TOKEN = /(#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|\b(\d+(?:\.\d+)?)\b|([A-Za-z_]\w*)(?=\s*\()|([A-Za-z_]\w*)|([\s\S])/g;
  document.querySelectorAll(".code code").forEach((el) => {
    const text = el.textContent;
    let out = "";
    for (const m of text.matchAll(TOKEN)) {
      const [tok, com, str, num, call, word] = m;
      if (com) out += `<span class="c">${esc(com)}</span>`;
      else if (str) out += `<span class="s">${esc(str)}</span>`;
      else if (num) out += `<span class="n">${num}</span>`;
      else if (call) out += KW.has(call) ? `<span class="k">${call}</span>` : `<span class="f">${call}</span>`;
      else if (word) out += KW.has(word) ? `<span class="k">${word}</span>` : BUILTIN.has(word) ? `<span class="b">${word}</span>` : word;
      else out += esc(tok);
    }
    el.innerHTML = out;
  });

  // Copy buttons
  async function copy(btn, text) {
    try {
      await navigator.clipboard.writeText(text);
      btn.classList.add("done");
      setTimeout(() => btn.classList.remove("done"), 1400);
    } catch { /* clipboard blocked: nothing to do */ }
  }
  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => copy(b, b.dataset.copy)));
  const codeCopy = document.querySelector(".code-copy");
  codeCopy.addEventListener("click", () => {
    const panel = [...panels].find((p) => !p.hidden);
    copy(codeCopy, panel.textContent);
  });
})();
