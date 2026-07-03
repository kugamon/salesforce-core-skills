# Audit Report Template Guide

This is the default report template for the `sf-audit` skill. It
defines brand tokens, colours, CSS classes, Word/Excel styles, and layout
conventions. If the user provides their own template, use that instead —
user-provided templates always take precedence over this default.

---

## 1. Brand Tokens

Default brand tokens for report styling. Replace with your own brand colors as needed.

| Token            | Value     | Use                                                        |
| ---------------- | --------- | ---------------------------------------------------------- |
| `--brand-cyan`   | `#14DDDD` | Accent colour, "Excellent" score pills                     |
| `--brand-blue`   | `#417AE4` | **Primary banner/header colour** — use solid, not gradient |
| `--text-on-blue` | `#FFFFFF` | All text placed on the brand blue background               |
| `--surface`      | `#FFFFFF` | Card / table row background                                |
| `--body-bg`      | `#F4F6F9` | Page background                                            |
| `--border`       | `#E0E4EA` | Card borders, table borders                                |
| `--muted`        | `#6B7280` | Labels, meta text                                          |

> **Design decision:** Use `#417AE4` as a flat solid colour for the banner,
> table headers, footer, and numbered bullets. Do **not** use gradients —
> solid blue was chosen for clarity and print compatibility.

### Severity / Score colours

| Level             | Condition | Badge background | Badge text / border |
| ----------------- | --------- | ---------------- | ------------------- |
| Excellent         | ≥ 80 %    | `#E8FBF9`        | `#14DDDD`           |
| Good              | 70 – 79 % | `#E9F7EF`        | `#27AE60`           |
| Acceptable        | 60 – 69 % | `#FEF3CD`        | `#F39C12`           |
| Needs Improvement | 40 – 59 % | `#FEF9E7`        | `#E67E22`           |
| Critical          | < 40 %    | `#FDE8E8`        | `#E74C3C`           |

**Finding severity left-border colours** (same palette, findings panel):

| Type     | Left border | Badge bg  | Badge text |
| -------- | ----------- | --------- | ---------- |
| Critical | `#E74C3C`   | `#FDE8E8` | `#E74C3C`  |
| Warning  | `#E67E22`   | `#FEF3CD` | `#E67E22`  |
| Info     | `#417AE4`   | `#EBF1FB` | `#417AE4`  |
| Positive | `#27AE60`   | `#E9F7EF` | `#27AE60`  |

> Positive findings use **green** (`#27AE60`), the same as the "Good" domain
> score colour — not cyan. This keeps the severity palette internally consistent.

Score-to-rating lookup for overall org score (0–100):

| Score    | Rating            |
| -------- | ----------------- |
| 80 – 100 | Excellent         |
| 70 – 79  | Good              |
| 60 – 69  | Acceptable        |
| 40 – 59  | Needs Improvement |
| < 40     | Critical          |

---

## 2. HTML Report

### Banner structure

No logo in the banner — the report is about the customer org, not the Salesforce MCP server.
The org name, ID, instance, and date serve as the identity anchor.

```html
<div class="banner">
  <div class="banner-text">
    <div class="banner-title">Salesforce Org Audit Report</div>
    <div class="banner-subtitle">{ORG_NAME} · Org ID: {ORG_ID} · Instance: {INSTANCE} · {DATE}</div>
  </div>
  <div class="banner-score">
    <div class="banner-score-value">{SCORE}</div>
    <div class="banner-score-label">out of 100</div>
    <div class="banner-score-rating">{RATING}</div>
  </div>
</div>
```

### Core CSS (copy verbatim into `<style>`)

```css
/* ── the Salesforce MCP server brand tokens ── */
:root {
  --brand-blue: #417ae4;
  --brand-cyan: #14dddd;
}

.banner {
  background: #417ae4; /* solid — no gradient */
  padding: 28px 40px 32px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.banner-text {
  flex: 1;
}
.banner-title {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.3px;
}
.banner-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 4px;
}
.banner-score {
  text-align: right;
  flex-shrink: 0;
}
.banner-score-value {
  font-size: 48px;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}
.banner-score-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.75);
  margin-top: 4px;
}
.banner-score-rating {
  display: inline-block;
  margin-top: 6px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 20px;
  padding: 2px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

/* Table headers — solid brand blue */
thead th {
  background: #417ae4;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  padding: 10px 14px;
  text-align: left;
}

/* Numbered recommendation bullets */
.rec-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #417ae4;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* Findings — left-border severity strip */
.finding {
  border-left: 4px solid;
  border-radius: 6px;
  padding: 12px 16px;
}
.finding.critical {
  border-left-color: #e74c3c;
}
.finding.warning {
  border-left-color: #e67e22;
}
.finding.info {
  border-left-color: #417ae4;
}
.finding.positive {
  border-left-color: #27ae60;
} /* green, same as "Good" score */

.finding.critical .finding-badge {
  background: #fde8e8;
  color: #e74c3c;
}
.finding.warning .finding-badge {
  background: #fef3cd;
  color: #e67e22;
}
.finding.info .finding-badge {
  background: #ebf1fb;
  color: #417ae4;
}
.finding.positive .finding-badge {
  background: #e9f7ef;
  color: #27ae60;
}

/* Footer */
.footer {
  background: #417ae4; /* solid — no gradient */
  padding: 20px 40px;
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}
```

### Footer

```html
<div class="footer">
  Generated by <a href="" style="color:#fff">the Salesforce MCP server</a>
  Audit Engine &nbsp;·&nbsp; {DATE} &nbsp;·&nbsp; Org: {ORG_NAME} ({ORG_ID})
</div>
```

---

## 3. Word Document (docx-js)

> **Note:** This section documents patterns for JavaScript-based generators
> using `docx-js`. The bundled Python generator (`scripts/generate_reports.py`)
> uses `python-docx` — see the script source for python-docx equivalents.

### Page setup (always explicit — docx-js defaults to A4)

```javascript
properties: {
  page: {
    size: { width: 12240, height: 15840 }, // US Letter, DXA
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1-inch margins
  }
}
```

### Heading colours

```javascript
// Heading 1 — brand blue
{ id: "Heading1", run: { size: 36, bold: true, font: "Arial", color: "417AE4" },
  paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } }

// Heading 2 — dark slate
{ id: "Heading2", run: { size: 28, bold: true, font: "Arial", color: "2C3E50" },
  paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } }
```

### Table header cells — solid brand blue

```javascript
// ⚠ Always use ShadingType.CLEAR (not SOLID) to prevent black backgrounds
new TableCell({
  shading: { fill: '417AE4', type: ShadingType.CLEAR },
  children: [
    new Paragraph({
      children: [
        new TextRun({
          text: 'Column Header',
          bold: true,
          color: 'FFFFFF',
          font: 'Arial',
          size: 20,
        }),
      ],
    }),
  ],
});
```

### Dual-width tables (required — without this tables break on some platforms)

```javascript
new Table({
  width: { size: 9360, type: WidthType.DXA }, // full content width (1-inch margins)
  columnWidths: [col1, col2, col3],            // must sum to 9360
  rows: [ new TableRow({ children: [
    new TableCell({ width: { size: col1, type: WidthType.DXA }, ... })
  ]}) ]
})
```

### Score colour helper (JavaScript)

```javascript
function scoreColor(score, max) {
  const pct = (score / max) * 100;
  if (pct >= 80) return '14DDDD'; // Excellent — cyan
  if (pct >= 70) return '27AE60'; // Good — green
  if (pct >= 60) return 'F39C12'; // Acceptable — amber
  if (pct >= 40) return 'E67E22'; // Needs Improvement — orange
  return 'E74C3C'; // Critical — red
}
```

### Validation

After generating the DOCX, always validate:

```bash
python /path/to/docx-skill/scripts/office/validate.py output.docx
```

---

## 4. Excel Workbook (openpyxl)

### Header row style — solid brand blue

```python
from openpyxl.styles import PatternFill, Font, Alignment

HEADER_FILL = PatternFill("solid", fgColor="417AE4")   # solid brand blue
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Arial", size=11)

def apply_header(cell, value):
    cell.value = value
    cell.fill  = HEADER_FILL
    cell.font  = HEADER_FONT
    cell.alignment = Alignment(horizontal="left", vertical="center")
```

### Score cell colours

```python
FILLS = {
    "Excellent"   : PatternFill("solid", fgColor="E8FBF9"),
    "Good"        : PatternFill("solid", fgColor="E9F7EF"),
    "Acceptable"  : PatternFill("solid", fgColor="FEF3CD"),
    "Warning"     : PatternFill("solid", fgColor="FEF9E7"),
    "Critical"    : PatternFill("solid", fgColor="FDE8E8"),
}
FONTS = {
    "Excellent"   : Font(color="14DDDD", bold=True, name="Arial", size=11),
    "Good"        : Font(color="27AE60", bold=True, name="Arial", size=11),
    "Acceptable"  : Font(color="F39C12", bold=True, name="Arial", size=11),
    "Warning"     : Font(color="E67E22", bold=True, name="Arial", size=11),
    "Critical"    : Font(color="E74C3C", bold=True, name="Arial", size=11),
}
```

### Auto-width columns

```python
for col in ws.columns:
    max_len = max((len(str(c.value or "")) for c in col), default=10)
    ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
```

### Sheet tab colour

```python
ws.sheet_properties.tabColor = "417AE4"
```

---

## 5. File Naming & Output Structure

```
audit_output/
  Salesforce_Org_Audit_Report.html    ← self-contained HTML
  Salesforce_Org_Audit_Report.docx    ← Word document
  Salesforce_Org_Audit_Scores.xlsx    ← Excel workbook
```

For multi-org audits, prefix with the org name:

```
audit_output/
  Acme_Corp_Org_Audit_Report.html
  Acme_Corp_Org_Audit_Report.docx
  Acme_Corp_Org_Audit_Scores.xlsx
```

---

## 6. Placeholders Reference

| Placeholder      | Source                                         |
| ---------------- | ---------------------------------------------- |
| `{ORG_NAME}`     | `org_init` response → org name            |
| `{ORG_ID}`       | `org_init` response → org ID              |
| `{INSTANCE}`     | `org_init` response → instance            |
| `{DATE}`         | System date at time of audit run               |
| `{SCORE}`        | Computed weighted org health score (0–100)     |
| `{RATING}`       | Score-to-rating lookup (see Section 1)         |
| `{RATING_COLOR}` | Severity colour for the rating (see Section 1) |
