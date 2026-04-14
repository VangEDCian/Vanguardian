import { renderMermaidSVG } from "../../vendor/beautiful-mermaid/index.js";

function renderEventDefinitionsDiagram() {
  const diagramElement = document.getElementById("event-definitions-diagram");
  const mermaidElement = document.getElementById("event-definitions-diagram-mermaid");

  if (!diagramElement || !mermaidElement) {
    return;
  }

  const mermaidSource = JSON.parse(mermaidElement.textContent || '""');

  if (!mermaidSource.trim()) {
    diagramElement.textContent = "No event definitions available for visualization.";
    return;
  }

  try {
    const svg = renderMermaidSVG(mermaidSource, {
      bg: "#f8fbfe",
      fg: "#1e2b36",
      line: "#90a4b4",
      accent: "#1e88b9",
      muted: "#607080",
      surface: "#ffffff",
      border: "#d6dee5",
      font: "Segoe UI",
      transparent: true,
      padding: 28,
      nodeSpacing: 28,
      layerSpacing: 56,
      componentSpacing: 40,
      thoroughness: 4,
    });

    diagramElement.classList.remove("event-definitions-diagram--empty", "event-definitions-diagram--error");
    diagramElement.innerHTML = `<div class="event-definitions-diagram__canvas">${svg}</div>`;
  } catch (error) {
    console.error("Failed to render event definitions diagram", error);
    diagramElement.classList.add("event-definitions-diagram--error");
    diagramElement.textContent = "Unable to render event workflow.";
  }
}

renderEventDefinitionsDiagram();
