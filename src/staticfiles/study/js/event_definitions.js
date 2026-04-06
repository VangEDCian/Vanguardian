(function () {
  const diagramElement = document.getElementById("event-definitions-diagram");
  if (!diagramElement || typeof window.go === "undefined") {
    return;
  }

  const nodesData = JSON.parse(document.getElementById("event-definitions-diagram-nodes").textContent || "[]");
  const linksData = JSON.parse(document.getElementById("event-definitions-diagram-links").textContent || "[]");

  if (!nodesData.length) {
    diagramElement.classList.add("event-definitions-diagram--empty");
    diagramElement.textContent = "No event definitions available for visualization.";
    return;
  }

  const $ = window.go.GraphObject.make;
  const diagram = $(window.go.Diagram, diagramElement, {
    initialAutoScale: window.go.AutoScale.Uniform,
    layout: $(window.go.LayeredDigraphLayout, {
      direction: 0,
      layerSpacing: 48,
      columnSpacing: 28,
    }),
    allowMove: false,
    allowCopy: false,
    allowDelete: false,
    isReadOnly: true,
    "toolManager.mouseWheelBehavior": window.go.WheelMode.Zoom,
  });

  diagram.nodeTemplate = $(
    window.go.Node,
    "Auto",
    $(
      window.go.Shape,
      "RoundedRectangle",
      { strokeWidth: 1.5, parameter1: 10 },
      new window.go.Binding("fill", "fill"),
      new window.go.Binding("stroke", "stroke")
    ),
    $(
      window.go.Panel,
      "Vertical",
      { margin: 10, width: 170, defaultAlignment: window.go.Spot.Left },
      $(
        window.go.TextBlock,
        { font: "700 12px Segoe UI, sans-serif", stroke: "#1b2b34", margin: new window.go.Margin(0, 0, 4, 0) },
        new window.go.Binding("text", "code", (code, data) => `${data.sequence}. ${code}`)
      ),
      $(
        window.go.TextBlock,
        { font: "600 13px Segoe UI, sans-serif", stroke: "#1b2b34", wrap: window.go.WrapFit, maxSize: new window.go.Size(150, NaN) },
        new window.go.Binding("text", "label")
      ),
      $(
        window.go.TextBlock,
        { font: "11px Segoe UI, sans-serif", stroke: "#5b6976", margin: new window.go.Margin(6, 0, 0, 0), wrap: window.go.WrapFit, maxSize: new window.go.Size(150, NaN) },
        new window.go.Binding("text", "subtitle")
      )
    )
  );

  diagram.linkTemplate = $(
    window.go.Link,
    { routing: window.go.Routing.Orthogonal, corner: 8 },
    $(window.go.Shape, { stroke: "#90a4b4", strokeWidth: 1.5 }),
    $(window.go.Shape, { toArrow: "Standard", fill: "#90a4b4", stroke: null })
  );

  diagram.model = new window.go.GraphLinksModel(nodesData, linksData);
})();
