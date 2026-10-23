"""Doctor-authorized, synthetic patient PDF report rendering."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .clinical_rules import ClinicalRuleResult
from .patients import PatientDetail, ReviewNote
from .prediction_service import AkiPredictionResult

INK = colors.HexColor("#102923")
FOREST = colors.HexColor("#0b5147")
MINT = colors.HexColor("#dff4df")
MAGENTA = colors.HexColor("#a62b62")
LINE = colors.HexColor("#b9d2c8")


def _latest_value(detail: PatientDetail, test_name: str) -> str:
    values = [event for event in detail.ehr_history if event.event_type == "laboratory" and event.data.get("test_name") == test_name]
    if not values:
        return "Unavailable"
    event = max(values, key=lambda item: item.event_time)
    unit = str(event.data.get("unit", "")).strip()
    return f"{event.data.get('value')} {unit}".strip()


def _ehr_series(detail: PatientDetail, test_name: str) -> list[float]:
    events = sorted(
        (event for event in detail.ehr_history if event.event_type == "laboratory" and event.data.get("test_name") == test_name),
        key=lambda item: item.event_time,
    )
    return [float(event.data["value"]) for event in events if isinstance(event.data.get("value"), (int, float))]


def _iot_series(detail: PatientDetail, measurement_type: str, field: str) -> list[float]:
    observations = sorted(
        (item for item in detail.iot_observations if item.measurement_type == measurement_type),
        key=lambda item: item.observed_at,
    )
    return [float(item.data[field]) for item in observations if isinstance(item.data.get(field), (int, float))]


def _trend_chart(title: str, values: list[float], unit: str, stroke: colors.Color) -> Drawing:
    drawing = Drawing(80 * mm, 47 * mm)
    drawing.add(String(4 * mm, 42 * mm, title, fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
    drawing.add(String(4 * mm, 38 * mm, unit, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#557069")))
    if len(values) < 2:
        drawing.add(String(4 * mm, 20 * mm, "Insufficient observations for a trend", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#557069")))
        return drawing

    plot = LinePlot()
    plot.x = 12 * mm
    plot.y = 8 * mm
    plot.width = 63 * mm
    plot.height = 27 * mm
    plot.data = [[(index, value) for index, value in enumerate(values)]]
    plot.lines[0].strokeColor = stroke
    plot.lines[0].strokeWidth = 2
    plot.lines[0].symbol = None
    plot.xValueAxis.valueMin = 0
    plot.xValueAxis.valueMax = max(1, len(values) - 1)
    plot.xValueAxis.valueSteps = [0, max(1, len(values) - 1)]
    plot.xValueAxis.labelTextFormat = lambda value: "First" if value == 0 else "Latest"
    spread = max(values) - min(values)
    padding = max(spread * 0.18, max(abs(value) for value in values) * 0.05, 0.1)
    plot.yValueAxis.valueMin = min(values) - padding
    plot.yValueAxis.valueMax = max(values) + padding
    plot.yValueAxis.labels.fontSize = 6.5
    plot.xValueAxis.labels.fontSize = 6.5
    plot.yValueAxis.strokeColor = LINE
    plot.xValueAxis.strokeColor = LINE
    drawing.add(plot)
    return drawing


def build_patient_report(
    detail: PatientDetail,
    rule: ClinicalRuleResult | None,
    prediction: AkiPredictionResult | None,
    notes: list[ReviewNote],
) -> bytes:
    """Return a branded, non-clinical PDF for one synthetic patient."""
    stream = BytesIO()
    document = SimpleDocTemplate(stream, pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleTB", parent=styles["Title"], textColor=INK, fontSize=25, leading=29, alignment=0, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="HeadingTB", parent=styles["Heading2"], textColor=FOREST, fontSize=14, leading=18, spaceBefore=5 * mm, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="BodyTB", parent=styles["BodyText"], textColor=INK, fontSize=9.5, leading=14))
    styles.add(ParagraphStyle(name="SmallTB", parent=styles["BodyText"], textColor=colors.HexColor("#557069"), fontSize=8, leading=11))
    styles.add(ParagraphStyle(name="RightTB", parent=styles["SmallTB"], alignment=TA_RIGHT))

    logo_path = Path(__file__).resolve().parents[2] / "TwinBean LOGO.png"
    logo = Image(str(logo_path), width=25 * mm, height=25 * mm, kind="proportional") if logo_path.exists() else Paragraph("<b>TwinBean</b>", styles["HeadingTB"])
    header = Table([[logo, Paragraph("<b>TwinBean</b><br/>Kidney digital twin", styles["BodyTB"]), Paragraph("SYNTHETIC RESEARCH REPORT<br/>NOT FOR CLINICAL USE", styles["RightTB"])]], colWidths=[28 * mm, 80 * mm, 65 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.8, LINE), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))

    patient = detail.patient
    risk = f"{prediction.probability * 100:.1f}%" if prediction and prediction.status == "available" else "Risk unavailable"
    rule_status = rule.status.replace("_", " ").title() if rule else "No stored rule result"
    generated = prediction.generated_at.strftime("%d %b %Y, %H:%M UTC") if prediction and prediction.generated_at else "Not available"
    facts = Table([
        ["Age", str(patient.age), "Sex", patient.sex or "Not specified", "CKD stage", patient.ckd_stage],
        ["Latest creatinine", _latest_value(detail, "creatinine"), "Latest eGFR", _latest_value(detail, "egfr"), "Records", str(len(detail.ehr_history) + len(detail.iot_observations))],
    ], colWidths=[25 * mm, 31 * mm, 20 * mm, 31 * mm, 23 * mm, 36 * mm])
    facts.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), MINT), ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"), ("FONTNAME", (4, 0), (4, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("PADDING", (0, 0), (-1, -1), 6)]))

    evidence = Table([
        [Paragraph("<b>Current clinical rule</b>", styles["BodyTB"]), Paragraph("<b>Future 24-hour AKI prediction</b>", styles["BodyTB"])],
        [Paragraph(rule_status, styles["HeadingTB"]), Paragraph(risk, styles["HeadingTB"])],
        [Paragraph(rule.limitation if rule else "No stored rule evidence is available.", styles["SmallTB"]), Paragraph(f"Generated: {generated}", styles["SmallTB"])],
    ], colWidths=[83 * mm, 83 * mm])
    evidence.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef7f2")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))

    story = [header, Spacer(1, 8 * mm), Paragraph(patient.display_name, styles["TitleTB"]), Paragraph(patient.ckd_context or "Synthetic CKD patient record.", styles["BodyTB"]), Spacer(1, 5 * mm), facts, Spacer(1, 5 * mm), evidence]
    story += [Paragraph("Separate evidence streams", styles["HeadingTB"]), Paragraph(f"Synthetic EHR events: <b>{len(detail.ehr_history)}</b> &nbsp;&nbsp; Simulated medical-IoT observations: <b>{len(detail.iot_observations)}</b>. These streams are summarized separately and prediction inputs are limited to observations at or before the prediction cutoff.", styles["BodyTB"])]

    creatinine = _ehr_series(detail, "creatinine")
    egfr = _ehr_series(detail, "egfr")
    systolic = _iot_series(detail, "blood_pressure", "systolic")
    weight = _iot_series(detail, "weight_kg", "value")
    story.append(Paragraph("Patient trends", styles["HeadingTB"]))
    story.append(Paragraph("Longitudinal synthetic EHR and simulated IoT measurements are plotted separately. Horizontal position runs from the first to latest available observation.", styles["SmallTB"]))
    charts = Table([
        [_trend_chart("Creatinine trend", creatinine, "mg/dL - synthetic EHR", FOREST), _trend_chart("eGFR trend", egfr, "mL/min/1.73m2 - synthetic EHR", colors.HexColor("#2f6f9f"))],
        [_trend_chart("Systolic blood pressure", systolic, "mmHg - simulated medical-IoT", MAGENTA), _trend_chart("Weight trend", weight, "kg - simulated medical-IoT", colors.HexColor("#8b6b16"))],
    ], colWidths=[83 * mm, 83 * mm])
    charts.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0.4, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fbf8")), ("PADDING", (0, 0), (-1, -1), 3)]))
    story.append(charts)

    story.append(Paragraph("SHAP model explanation", styles["HeadingTB"]))
    if prediction and prediction.status == "available" and prediction.attributions:
        shap_rows = [["Feature", "Input", "Influence (raw margin)"]]
        for item in sorted(prediction.attributions, key=lambda value: abs(value.shap_margin), reverse=True):
            shap_rows.append([item.feature.replace("_", " ").title(), f"{item.value:g}", f"{item.shap_margin:+.5f}"])
        shap_table = Table(shap_rows, colWidths=[85 * mm, 35 * mm, 46 * mm], repeatRows=1)
        shap_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), FOREST), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.35, LINE), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("PADDING", (0, 0), (-1, -1), 5), ("ALIGN", (1, 1), (-1, -1), "RIGHT")]))
        story += [shap_table, Paragraph("Positive values move this model output toward higher predicted risk; negative values move it lower. SHAP is explanatory, not causal, and does not provide treatment guidance.", styles["SmallTB"])]
    else:
        story.append(Paragraph("No explanation is shown because no valid prediction is available; missing predictions are never represented as zero risk.", styles["BodyTB"]))

    story.append(Paragraph("Doctor review notes", styles["HeadingTB"]))
    if notes:
        for note in notes:
            story.append(KeepTogether([Paragraph(note.text, styles["BodyTB"]), Paragraph(note.created_at.strftime("%d %b %Y, %H:%M UTC") + " - doctor review", styles["SmallTB"]), Spacer(1, 2 * mm)]))
    else:
        story.append(Paragraph("No doctor review notes have been recorded.", styles["BodyTB"]))

    story += [Spacer(1, 6 * mm), Paragraph("This report contains synthetic data only. It is a research prototype output and is not clinical validation, diagnosis, or treatment guidance.", ParagraphStyle(name="DisclaimerTB", parent=styles["SmallTB"], textColor=MAGENTA, borderColor=MAGENTA, borderWidth=0.6, borderPadding=7))]
    document.build(story)
    return stream.getvalue()
