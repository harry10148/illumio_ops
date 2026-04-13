const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber
} = require("docx");

const root = path.resolve(__dirname, "..");
const data = JSON.parse(fs.readFileSync(path.join(root, "reports", "security_assessment", "data.json"), "utf8"));
const outPath = path.join(root, "reports", "security_assessment", "Illumio_PCE_Assessment_2026-04-10.docx");

const S = {
  green: "00C48C", navy: "1A1F36", teal: "00B4D8", orange: "FF6B35", red: "E63946",
  gray: "6B7280", grayLight: "E5E7EB", light: "F0F7F4", amber: "FEF3C7", white: "FFFFFF"
};
const border = { style: BorderStyle.SINGLE, size: 1, color: S.grayLight };
const borders = { top: border, bottom: border, left: border, right: border };
const margins = { top: 80, bottom: 80, left: 120, right: 120 };

const statusFill = (text) => {
  const x = String(text).toUpperCase();
  if (x.includes("CRITICAL") || x.includes("FAIL") || x.includes("HIGH")) return S.red;
  if (x.includes("WARNING") || x.includes("MEDIUM")) return S.orange;
  if (x.includes("PASS") || x.includes("LOW") || x.includes("OK")) return S.green;
  return S.teal;
};

const P = (text, opts = {}) => new Paragraph({
  alignment: opts.alignment,
  spacing: { before: opts.before ?? 0, after: opts.after ?? 120, line: 276 },
  pageBreakBefore: opts.pageBreakBefore,
  border: opts.border,
  children: [new TextRun({ text, font: "Arial", size: opts.size ?? 20, color: opts.color ?? S.navy, bold: opts.bold, italics: opts.italics })]
});

const H = (text, level) => new Paragraph({
  heading: level,
  spacing: { before: level === HeadingLevel.HEADING_1 ? 260 : 180, after: 140 },
  children: [new TextRun({ text, font: "Arial", size: level === HeadingLevel.HEADING_1 ? 32 : 28, color: S.navy, bold: true })]
});

function cell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins,
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    children: [
      new Paragraph({
        alignment: opts.align,
        spacing: { after: 0 },
        children: [new TextRun({ text: String(text), font: "Arial", size: 18, color: opts.color ?? S.navy, bold: opts.bold })]
      })
    ]
  });
}

function statusCell(text, width) {
  return cell(text, width, { fill: statusFill(text), color: S.white, bold: true, align: AlignmentType.CENTER });
}

function table(headers, rows, widths, statusCols = []) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ children: headers.map((h, i) => cell(h, widths[i], { fill: S.navy, color: S.white, bold: true })) }),
      ...rows.map((row) => new TableRow({
        children: row.map((value, i) => statusCols.includes(i) ? statusCell(value, widths[i]) : cell(value, widths[i]))
      }))
    ]
  });
}

function numbered(items) {
  return items.map((item) => new Paragraph({
    numbering: { reference: "nums", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text: item, font: "Arial", size: 18, color: S.navy })]
  }));
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20, color: S.navy } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: "Arial", color: S.navy }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: "Arial", color: S.navy }, paragraph: { spacing: { before: 180, after: 140 }, outlineLevel: 1 } }
    ]
  },
  numbering: {
    config: [{ reference: "nums", levels: [{ level: 0, format: "decimal", text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: {
      default: new Header({
        children: [new Paragraph({
          spacing: { after: 120 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: S.green, space: 1 } },
          children: [
            new TextRun({ text: "Illumio PCE Security Assessment", font: "Arial", size: 18, color: S.navy, bold: true }),
            new TextRun({ text: "\tConfidential", font: "Arial", size: 16, color: S.red, italics: true })
          ]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: S.grayLight, space: 1 } },
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "Page ", font: "Arial", size: 16, color: S.gray }), new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: S.gray })]
        })]
      })
    },
    children: [
      P("ILLUMIO PCE ENVIRONMENT SECURITY ASSESSMENT", { size: 32, bold: true, alignment: AlignmentType.CENTER, after: 200, before: 400 }),
      P("Policy Status, Enforcement Readiness and Segmentation Roadmap", { size: 24, color: S.gray, alignment: AlignmentType.CENTER, after: 180 }),
      P(`Assessment Date: ${data.meta.generated_on}`, { size: 18, alignment: AlignmentType.CENTER, after: 60 }),
      P("Classification: Confidential", { size: 18, color: S.red, alignment: AlignmentType.CENTER, after: 320 }),
      P("", { pageBreakBefore: true }),

      H("1. Executive Summary", HeadingLevel.HEADING_1),
      table(
        ["Workloads", "Apps", "Compliance", "Coverage"],
        [[data.summary.total_workloads, data.summary.total_apps, `${data.summary.compliance_score}%`, `${data.summary.policy_coverage_percent}%`]],
        [2340, 2340, 2340, 2340]
      ),
      P("The Illumio demo environment currently presents a critical segmentation posture. Compliance scored 25.0 percent, explicit policy coverage is only 20.0 percent, there are no ringfence rulesets, and two bridge nodes still provide viable lateral movement paths across otherwise separate app groups."),
      P("The most material risks are concentrated in remote administration flows, incomplete governance of management and telemetry ports, and unmanaged traffic touching both internet-facing and imaging services.", { after: 180 }),

      H("2. Environment Overview", HeadingLevel.HEADING_1),
      table(
        ["Metric", "Value", "Metric", "Value"],
        [
          ["Total workloads", data.summary.total_workloads, "Applications", data.summary.total_apps],
          ["Rulesets", data.summary.total_rulesets, "Ringfence rulesets", data.summary.ringfence_rulesets],
          ["Bridge nodes", data.summary.bridge_nodes, "Mixed app groups", data.summary.mixed_enforcement_apps],
          ["Unmanaged source flows", data.summary.unmanaged_source_flows, "Unmanaged destination flows", data.summary.unmanaged_destination_flows]
        ],
        [2340, 2340, 2340, 2340]
      ),
      P("Mixed enforcement applications create governance and troubleshooting risk because the same app and env tuple behaves differently under policy.", { after: 100 }),
      table(
        ["Application (Env)", "Modes", "Risk"],
        data.enforcement.mixed_groups.map((x) => [`${x.app} (${x.env})`, Object.entries(x.modes).map(([k, v]) => `${k}:${v}`).join(", "), "CRITICAL"]),
        [3600, 3600, 2160],
        [2]
      ),

      H("3. Security Status and Compliance Findings", HeadingLevel.HEADING_1),
      table(
        ["Check", "Status", "Detail"],
        data.compliance.findings.map((x) => [`${x.id} ${x.name}`, x.status, x.detail]),
        [2640, 1440, 5280],
        [1]
      ),
      P("Label hygiene observations:", { bold: true, after: 60 }),
      ...numbered(data.label_hygiene.issues),
      P("Existing policy is sparse. Only two rulesets exist, none are ringfence rulesets, and four draft changes remain unprovisioned.", { after: 140 }),

      H("4. Lateral Movement Risk Analysis", HeadingLevel.HEADING_1),
      table(
        ["Bridge Node", "Reachable Apps", "Direct Out", "Direct In", "Severity"],
        data.lateral_movement.bridges.map((x) => [`${x.app} (${x.env})`, x.reachable_apps, x.direct_connections_out, x.direct_connections_in, x.severity.toUpperCase()]),
        [3120, 1440, 1200, 1200, 2400],
        [4]
      ),
      P("Top reachability ranking:", { bold: true, after: 60 }),
      table(
        ["Application (Env)", "Reachable Apps", "Bridge"],
        data.lateral_movement.top_reachability.map((x) => [`${x.app} (${x.env})`, x.reachable_apps, x.bridge ? "CRITICAL" : "LOW"]),
        [4560, 1920, 2880],
        [2]
      ),

      H("5. Infrastructure Services Classification", HeadingLevel.HEADING_1),
      table(
        ["Application (Env)", "Score", "Tier", "Pattern", "Notes"],
        data.infrastructure_services.map((x) => [`${x.app} (${x.env})`, x.score, x.tier, x.pattern, x.notes]),
        [2520, 900, 1620, 1260, 3060]
      ),

      H("6. High-Risk Port Exposure", HeadingLevel.HEADING_1),
      table(
        ["Source", "Destination", "Port", "Connections", "Decision", "Severity"],
        data.high_risk_ports.map((x) => [x.source, x.destination, `${x.port}/${x.proto}`, x.connections, x.decision, x.severity.toUpperCase()]),
        [1980, 1980, 960, 1140, 1560, 1740],
        [5]
      ),
      P("The remote administration pattern is the clearest risk cluster. Endpoint and VDI traffic reaches privileged infrastructure and business systems over SSH and RDP, while SMB and RPC remain broadly allowed into AD.", { after: 140 }),

      H("7. Unmanaged Traffic Analysis", HeadingLevel.HEADING_1),
      table(
        ["Unmanaged Source IP", "Destination", "Port", "Connections", "Type"],
        data.unmanaged_traffic.sources.map((x) => [x.ip, x.destination, x.port, x.connections, x.type]),
        [2160, 2880, 900, 1200, 2220]
      ),
      P("Unmanaged destinations observed from managed workloads:", { bold: true, after: 60 }),
      table(
        ["Managed Source", "Destination IP", "Port", "Connections", "Type"],
        data.unmanaged_traffic.destinations.map((x) => [x.source, x.ip, x.port, x.connections, x.type]),
        [2160, 2520, 900, 1200, 2580]
      ),

      H("8. Segmentation and Enforcement Roadmap", HeadingLevel.HEADING_1),
      ...data.roadmap.flatMap((x) => [P(`${x.phase} | ${x.title}`, { bold: true, color: S.teal, after: 50 }), ...numbered(x.actions)]),

      H("9. Immediate Action Items", HeadingLevel.HEADING_1),
      table(
        ["Action", "Impact", "Effort", "Priority"],
        data.immediate_actions.map((x) => [x.action, x.impact, x.effort, x.priority]),
        [2820, 3720, 1020, 1800],
        [3]
      ),

      H("10. Summary", HeadingLevel.HEADING_1),
      P("Three findings stand out above the rest. First, vdi (users) and assetmgmt (prod) are bridge nodes and should be ringfenced immediately. Second, remote administration traffic over SSH and RDP is still overly broad and not sufficiently codified. Third, unmanaged traffic continues to touch both business applications and imaging systems, leaving meaningful blind spots."),
      P("The near-term objective should be to reduce attacker pathing, stabilize high-risk admin and telemetry flows with explicit policy, and improve label governance so the environment can move toward fuller enforcement with lower operational risk.", { after: 80 })
    ]
  }]
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  process.stdout.write(outPath);
});
