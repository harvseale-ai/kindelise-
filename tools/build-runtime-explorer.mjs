#!/usr/bin/env node

// # KEYWORD: module — a JavaScript file that can load named tools from another file.
// # KEYWORD: regular expression — a written pattern used to recognise a particular piece of text.
// # KEYWORD: Mermaid — the small diagram language used by the local runtime guide.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// # WHY: Keeps every important local path based on this file so the tool works from any terminal folder.
const toolsDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(toolsDirectory, "..");
const guidePath = path.join(repositoryRoot, "docs", "RUNTIME.md");
const outputPath = path.join(repositoryRoot, "runtime-explorer.html");

// # WHY: Protects punctuation before a code name is placed inside a text-matching pattern.
function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// # WHY: Finds the current line of a named function or class so generated links do not become stale.
function findSymbolLine(absolutePath, symbol) {
  const escapedSymbol = escapeRegExp(symbol);
  const patterns = [
    new RegExp(`\\b(?:async\\s+)?function\\s+${escapedSymbol}\\b`),
    new RegExp(`\\b(?:const|let|var)\\s+${escapedSymbol}\\s*=`),
    new RegExp(`^\\s*(?:async\\s+)?def\\s+${escapedSymbol}\\b`),
    new RegExp(`^\\s*class\\s+${escapedSymbol}\\b`),
  ];
  const lines = fs.readFileSync(absolutePath, "utf8").split(/\r?\n/);

  for (const pattern of patterns) {
    const index = lines.findIndex((line) => pattern.test(line));
    if (index >= 0) {
      return index + 1;
    }
  }
  throw new Error(`Could not find ${symbol} in ${path.relative(repositoryRoot, absolutePath)}`);
}

// # WHY: Turns one guide link into a checked file, line, and clickable VS Code address.
function parseTarget(rawTarget) {
  const [relativePath, fragment = ""] = rawTarget.split("#", 2);
  const absolutePath = path.resolve(repositoryRoot, relativePath);
  const repositoryPrefix = `${repositoryRoot}${path.sep}`;

  if (absolutePath !== repositoryRoot && !absolutePath.startsWith(repositoryPrefix)) {
    throw new Error(`Runtime target leaves the repository: ${rawTarget}`);
  }
  if (!fs.existsSync(absolutePath) || !fs.statSync(absolutePath).isFile()) {
    throw new Error(`Runtime target is not a file: ${rawTarget}`);
  }

  const lineMatch = /^L(\d+)$/.exec(fragment);
  const symbolMatch = /^S(.+)$/.exec(fragment);
  const symbol = symbolMatch ? decodeURIComponent(symbolMatch[1]) : "";
  const line = symbol ? findSymbolLine(absolutePath, symbol) : lineMatch ? Number(lineMatch[1]) : 1;
  const lineCount = fs.readFileSync(absolutePath, "utf8").split(/\r?\n/).length;
  if (line < 1 || line > lineCount) {
    throw new Error(`Runtime target line is out of range: ${rawTarget}`);
  }

  const posixPath = absolutePath.split(path.sep).join("/");
  return {
    path: relativePath,
    line,
    symbol,
    vscodeUri: `vscode://file${encodeURI(posixPath)}:${line}:1`,
  };
}

// # WHY: Reads every labelled diagram block so each one can be matched with its source-code link.
function parseDiagramNodes(source) {
  const nodes = [];
  const seen = new Set();
  const pattern = /(?:^|\s)([A-Za-z][\w-]*)\s*(?:\["([^"]*)"\]|\[([^\]\n]*)\]|\{"([^"}]*)"\}|\{([^}\n]*)\})/gm;

  for (const match of source.matchAll(pattern)) {
    if (seen.has(match[1])) {
      continue;
    }
    seen.add(match[1]);
    nodes.push({
      nodeId: match[1],
      label: match[2] || match[3] || match[4] || match[5] || match[1],
    });
  }
  return nodes;
}

// # WHY: Converts the written runtime guide into complete diagrams and rejects missing or incorrect links.
function parseRuntimeGuide(markdown) {
  const lines = markdown.split(/\r?\n/);
  const diagrams = [];
  let currentHeading = "Runtime flow";
  let descriptionLines = [];

  for (let index = 0; index < lines.length; index += 1) {
    const headingMatch = /^##\s+(.+)$/.exec(lines[index]);
    if (headingMatch) {
      currentHeading = headingMatch[1];
      descriptionLines = [];
      continue;
    }
    if (lines[index] !== "```mermaid") {
      if (currentHeading !== "Runtime flow" && lines[index].trim()) {
        descriptionLines.push(lines[index].trim());
      }
      continue;
    }

    const diagramLines = [];
    index += 1;
    while (index < lines.length && lines[index] !== "```") {
      diagramLines.push(lines[index]);
      index += 1;
    }
    if (index >= lines.length) {
      throw new Error(`Unclosed Mermaid block under "${currentHeading}"`);
    }

    const targets = [];
    const sourceLines = [];
    for (const line of diagramLines) {
      const clickMatch = /^\s*click\s+([A-Za-z][\w-]*)\s+"([^"]+)"(?:\s+"([^"]*)")?\s*$/.exec(line);
      if (clickMatch) {
        targets.push({
          nodeId: clickMatch[1],
          label: clickMatch[3] || `Open ${clickMatch[1]}`,
          ...parseTarget(clickMatch[2]),
        });
      } else {
        sourceLines.push(line);
      }
    }

    const source = sourceLines.join("\n").trim();
    const nodes = parseDiagramNodes(source);
    const targetIds = new Set(targets.map((target) => target.nodeId));
    const missingTargets = nodes.filter((node) => !targetIds.has(node.nodeId));
    const unknownTargets = targets.filter((target) => !nodes.some((node) => node.nodeId === target.nodeId));
    if (missingTargets.length) {
      throw new Error(
        `Missing source targets under "${currentHeading}": ${missingTargets.map((node) => node.nodeId).join(", ")}`,
      );
    }
    if (unknownTargets.length) {
      throw new Error(
        `Unknown source targets under "${currentHeading}": ${unknownTargets.map((target) => target.nodeId).join(", ")}`,
      );
    }
    if (targetIds.size !== targets.length) {
      throw new Error(`Duplicate source target under "${currentHeading}"`);
    }

    diagrams.push({
      title: currentHeading,
      description: descriptionLines.join(" "),
      source,
      targets,
    });
    descriptionLines = [];
  }

  if (!diagrams.length) {
    throw new Error("No Mermaid runtime diagrams were found");
  }
  return diagrams;
}

// # WHY: Rechecks every generated code destination before an explorer page is allowed to be saved.
function verifyRuntimeNavigation(diagrams) {
  let functionTargets = 0;
  for (const diagram of diagrams) {
    const nodeIds = new Set(parseDiagramNodes(diagram.source).map((node) => node.nodeId));
    for (const target of diagram.targets) {
      if (!nodeIds.has(target.nodeId)) {
        throw new Error(`Target ${target.nodeId} is not present in ${diagram.title}`);
      }
      if (target.symbol) {
        const absolutePath = path.resolve(repositoryRoot, target.path);
        const expectedLine = findSymbolLine(absolutePath, target.symbol);
        if (target.line !== expectedLine) {
          throw new Error(`${target.symbol}() has a stale line target in ${diagram.title}`);
        }
        functionTargets += 1;
      }
    }
  }
  return { functionTargets };
}

// # WHY: Builds one portable page containing the diagrams, search control, and checked source links.
function buildHtml(diagrams) {
  const data = JSON.stringify(diagrams).replaceAll("<", "\\u003c");
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Kindelise Runtime Explorer</title>
    <style>
      :root {
        color-scheme: dark;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #08090b;
        color: #f5f5f7;
      }
      * { box-sizing: border-box; }
      html { scroll-behavior: smooth; }
      body { margin: 0; background: #08090b; color: #f5f5f7; }
      header {
        position: sticky;
        top: 0;
        z-index: 20;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1rem 1.25rem;
        border-bottom: 1px solid #292930;
        background: rgba(8, 9, 11, 0.96);
        backdrop-filter: blur(12px);
      }
      h1, h2, h3, p { margin-top: 0; }
      h1 { margin-bottom: 0.2rem; font-size: 1.3rem; }
      header p { margin-bottom: 0; color: #9999a5; font-size: 0.88rem; }
      .header-status { color: #8de0b2; font-size: 0.82rem; text-align: right; }
      main { width: min(1720px, 100%); margin: 0 auto; padding: 1.5rem; }
      .intro { max-width: 850px; color: #c6c6ce; line-height: 1.65; }
      .tool-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.75rem;
        margin: 1.25rem 0 1.5rem;
      }
      .flow-search {
        width: min(420px, 100%);
        min-height: 2.8rem;
        padding: 0.65rem 0.85rem;
        border: 1px solid #3b3b45;
        border-radius: 0.7rem;
        background: #17181d;
        color: #fff;
        font: inherit;
      }
      .flow-search:focus { border-color: #a6a6b2; outline: 2px solid transparent; }
      .legend { display: flex; flex-wrap: wrap; gap: 0.45rem; }
      .legend span {
        padding: 0.42rem 0.62rem;
        border: 1px solid #34343d;
        border-radius: 999px;
        color: #b8b8c2;
        font-size: 0.78rem;
      }
      .flow-contents {
        margin-bottom: 2rem;
        padding: 1.75rem 1.25rem;
        border: 1px solid #292930;
        border-radius: 0.9rem;
        background: #111216;
      }
      .flow-contents h2 { margin-bottom: 0.3rem; font-size: 1rem; }
      .flow-contents p { margin-bottom: 0.9rem; color: #8f8f9a; font-size: 0.88rem; }
      .flow-contents ol {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 0.55rem 2rem;
        margin: 0;
        padding-left: 1.4rem;
      }
      .flow-contents a { color: #d9d9df; text-decoration: none; }
      .flow-contents a:hover, .flow-contents a:focus { color: #fff; text-decoration: underline; }
      .runtime-flow {
        scroll-margin-top: 6rem;
        padding: 1.65rem 0 2.7rem;
        border-top: 1px solid #292930;
      }
      .runtime-flow[hidden] { display: none; }
      .runtime-flow h2 { margin-bottom: 0.55rem; font-size: 1.5rem; }
      .flow-description { max-width: 900px; color: #a9a9b4; font-size: 1rem; line-height: 1.55; }
      .diagram-shell {
        overflow-x: auto;
        margin-top: 1rem;
        padding: 1rem;
        border: 1px solid #292930;
        border-radius: 0.9rem;
        background: #101116;
      }
      .mermaid { min-width: 1100px; text-align: center; }
      .mermaid svg {
        width: 160% !important;
        max-width: none !important;
        height: auto;
      }
      .runtime-node-link { cursor: pointer; outline: none; }
      .runtime-node-link rect,
      .runtime-node-link polygon,
      .runtime-node-link path { transition: stroke 120ms ease, filter 120ms ease; }
      .runtime-node-link:hover rect,
      .runtime-node-link:hover polygon,
      .runtime-node-link:hover path,
      .runtime-node-link:focus rect,
      .runtime-node-link:focus polygon,
      .runtime-node-link:focus path {
        stroke: #8de0b2 !important;
        stroke-width: 3px !important;
        filter: drop-shadow(0 0 5px rgba(141, 224, 178, 0.3));
      }
      .source-links { margin-top: 0.85rem; }
      .source-links summary { cursor: pointer; color: #b8b8c2; }
      .source-links ul {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 0.5rem 1rem;
        margin: 0.75rem 0 0;
        padding: 0;
        list-style: none;
      }
      .source-links a { color: #9ddbb9; overflow-wrap: anywhere; }
      .empty-result { color: #ffadad; }
      .error { color: #ff8f8f; }
      @media (max-width: 720px) {
        header { align-items: flex-start; flex-direction: column; }
        .header-status { text-align: left; }
        main { padding: 1rem; }
        .mermaid { min-width: 980px; }
        .mermaid svg { width: 210% !important; }
        .source-links ul { grid-template-columns: 1fr; }
      }
      @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Kindelise Runtime Explorer</h1>
        <p>Click a flowchart block to open the code that owns it in VS Code.</p>
      </div>
      <div class="header-status" id="status">Loading runtime diagrams...</div>
    </header>
    <main>
      <p class="intro">
        This is a local learning tool, not a product page. It shows how each part of Kindelise passes work to the
        next part. Use a diagram for the simple overview, then click a block to see the code behind it.
      </p>
      <div class="tool-row">
        <label>
          <span hidden>Filter runtime flows</span>
          <input class="flow-search" id="flow-search" type="search" placeholder="Find plans, messages, Stripe, profiles...">
        </label>
        <div class="legend" aria-label="Runtime layers">
          <span>Opening and showing pages</span>
          <span>Checking details and permission</span>
          <span>Loading and saving</span>
          <span>Stored information</span>
          <span>Outside services</span>
        </div>
      </div>
      <section class="flow-contents" aria-labelledby="flow-contents-title">
        <h2 id="flow-contents-title">Flowchart contents</h2>
        <p>Choose a behavior to jump to its diagram.</p>
        <ol id="flow-contents"></ol>
      </section>
      <p class="empty-result" id="empty-result" hidden>No runtime flows match that search.</p>
      <div id="explorer"></div>
    </main>
    <script id="runtime-data" type="application/json">${data}</script>
    <script type="module">
      // # KEYWORD: import — loads a named tool supplied by another JavaScript file.
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

      // # WHY: Reads the checked diagram information placed inside this same generated page.
      const diagrams = JSON.parse(document.getElementById("runtime-data").textContent);
      const explorer = document.getElementById("explorer");
      const contents = document.getElementById("flow-contents");
      const search = document.getElementById("flow-search");
      const emptyResult = document.getElementById("empty-result");
      const status = document.getElementById("status");

      // # WHY: Turns a heading into a short, safe page link used by the contents list.
      function slugify(value) {
        return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      }

      // # WHY: Builds a plain link list so every code destination remains available if a diagram cannot load.
      function makeSourceLinks(diagram) {
        const details = document.createElement("details");
        details.className = "source-links";
        const summary = document.createElement("summary");
        summary.textContent = "Source links";
        details.append(summary);
        const list = document.createElement("ul");
        for (const target of diagram.targets) {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = target.vscodeUri;
          link.textContent = target.label + " — " + target.path + ":" + target.line;
          item.append(link);
          list.append(item);
        }
        details.append(list);
        return details;
      }

      // # WHY: Gives every guide entry its own heading, diagram space, and contents link.
      for (const [index, diagram] of diagrams.entries()) {
        const section = document.createElement("section");
        section.className = "runtime-flow";
        section.dataset.diagramIndex = String(index);
        section.dataset.search = [diagram.title, diagram.description, ...diagram.targets.map((target) => target.path + " " + target.symbol)]
          .join(" ")
          .toLowerCase();
        section.id = "flow-" + slugify(diagram.title);

        const heading = document.createElement("h2");
        heading.textContent = diagram.title;
        const description = document.createElement("p");
        description.className = "flow-description";
        description.textContent = diagram.description;
        const shell = document.createElement("div");
        shell.className = "diagram-shell";
        const chart = document.createElement("div");
        chart.className = "mermaid";
        shell.append(chart);
        section.append(heading, description, shell, makeSourceLinks(diagram));
        explorer.append(section);

        const contentsItem = document.createElement("li");
        contentsItem.dataset.diagramIndex = String(index);
        const contentsLink = document.createElement("a");
        contentsLink.href = "#" + section.id;
        contentsLink.textContent = diagram.title;
        contentsItem.append(contentsLink);
        contents.append(contentsItem);
      }

      // # WHY: Hides diagrams that do not match the visitor's words while keeping contents in step.
      search.addEventListener("input", () => {
        const query = search.value.trim().toLowerCase();
        let visibleCount = 0;
        for (const section of explorer.querySelectorAll(".runtime-flow")) {
          const visible = !query || section.dataset.search.includes(query);
          section.hidden = !visible;
          contents.querySelector('[data-diagram-index="' + section.dataset.diagramIndex + '"]').hidden = !visible;
          if (visible) visibleCount += 1;
        }
        emptyResult.hidden = visibleCount !== 0;
      });

      // # WHY: Uses the same readable colours and spacing for every diagram on the page.
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: "loose",
        theme: "dark",
        flowchart: {
          htmlLabels: true,
          useMaxWidth: true,
          curve: "basis",
          nodeSpacing: 55,
          rankSpacing: 70,
        },
        themeVariables: {
          primaryColor: "#202127",
          primaryBorderColor: "#52525e",
          primaryTextColor: "#f5f5f7",
          lineColor: "#777783",
          secondaryColor: "#17181d",
          tertiaryColor: "#111216",
          fontSize: "18px",
        },
      });

      // # WHY: Draws each diagram and connects its blocks to the already checked source destinations.
      try {
        let linkedNodes = 0;
        for (const [index, diagram] of diagrams.entries()) {
          const section = document.querySelector('.runtime-flow[data-diagram-index="' + index + '"]');
          const chart = section.querySelector(".mermaid");
          const rendered = await mermaid.render("runtime-flow-" + index, diagram.source);
          chart.innerHTML = rendered.svg;
          if (rendered.bindFunctions) rendered.bindFunctions(chart);
          const nodes = [...chart.querySelectorAll("g.node")];
          for (const target of diagram.targets) {
            const node = nodes.find((candidate) =>
              candidate.dataset.id === target.nodeId
              || candidate.id === target.nodeId
              || candidate.id.includes("-flowchart-" + target.nodeId + "-")
            );
            if (!node) {
              console.warn("Could not bind node " + target.nodeId + " in " + diagram.title);
              continue;
            }
            // # WHY: Opens the exact source line when a diagram block is clicked or used from a keyboard.
            const openSource = () => { window.location.href = target.vscodeUri; };
            node.classList.add("runtime-node-link");
            node.setAttribute("role", "link");
            node.setAttribute("tabindex", "0");
            node.setAttribute("aria-label", target.label + ", " + target.path + ", line " + target.line);
            node.addEventListener("click", openSource);
            // # WHY: Gives keyboard visitors the same source-opening action as a mouse click.
            node.addEventListener("keydown", (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openSource();
              }
            });
            linkedNodes += 1;
          }
        }
        status.textContent = diagrams.length + " flows · " + linkedNodes + " linked blocks";
      } catch (error) {
        status.textContent = "Diagram rendering failed. Source links are still available.";
        status.classList.add("error");
        console.error(error);
      }
    </script>
  </body>
</html>
`;
}

// # WHY: Reads the hand-written guide before producing anything so it remains the single source of the diagrams.
const markdown = fs.readFileSync(guidePath, "utf8");
const diagrams = parseRuntimeGuide(markdown);
const navigationSummary = verifyRuntimeNavigation(diagrams);
const generatedHtml = buildHtml(diagrams);
const checkOnly = process.argv.includes("--check");

// # WHY: Check mode proves the saved explorer matches its guide without changing any file.
if (checkOnly) {
  if (!fs.existsSync(outputPath) || fs.readFileSync(outputPath, "utf8") !== generatedHtml) {
    throw new Error("runtime-explorer.html is stale; rebuild it before running --check");
  }
} else {
  fs.writeFileSync(outputPath, generatedHtml);
}

const nodeCount = diagrams.reduce((total, diagram) => total + diagram.targets.length, 0);
const action = checkOnly ? "Verified" : "Built";
console.log(
  `${action} ${path.relative(repositoryRoot, outputPath)} with ${diagrams.length} flows, `
  + `${nodeCount} linked blocks and ${navigationSummary.functionTargets} verified symbol targets.`,
);
