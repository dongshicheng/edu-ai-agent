import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from app.models.schemas import DocSpec


def _add_heading(doc: Document, text: str, level: int = 1):
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.name = "Microsoft YaHei"


def _add_paragraph(doc: Document, text: str, bold: bool = False, indent: bool = False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(12)
    run.bold = bold
    if indent:
        p.paragraph_format.first_line_indent = Inches(0.3)


def generate_docx(spec: DocSpec, output_path: str) -> str:
    """Generate a DOCX lesson plan from DocSpec."""
    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Microsoft YaHei"
    font.size = Pt(12)

    # Title
    title = doc.add_heading(spec.title, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.name = "Microsoft YaHei"

    # Basic info table
    table = doc.add_table(rows=3, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    cells = table.rows[0].cells
    cells[0].text = "学科"
    cells[1].text = spec.subject
    cells[2].text = "年级"
    cells[3].text = spec.grade_level

    cells = table.rows[1].cells
    cells[0].text = "课题"
    cells[1].text = spec.title
    cells[2].text = "课时"
    cells[3].text = spec.duration

    cells = table.rows[2].cells
    cells[0].text = "课型"
    cells[1].text = "新授课"
    cells[2].text = ""
    cells[3].text = ""

    doc.add_paragraph()

    # Teaching objectives
    _add_heading(doc, "一、教学目标", level=1)
    for obj in spec.objectives:
        doc.add_paragraph(obj, style="List Bullet")

    # Key points
    _add_heading(doc, "二、教学重点", level=1)
    for kp in spec.key_points:
        doc.add_paragraph(kp, style="List Bullet")

    # Difficulty points
    _add_heading(doc, "三、教学难点", level=1)
    for dp in spec.difficulty_points:
        doc.add_paragraph(dp, style="List Bullet")

    # Teaching process
    _add_heading(doc, "四、教学过程", level=1)

    if spec.teaching_process:
        # Process table
        proc_table = doc.add_table(rows=1, cols=5)
        proc_table.style = "Table Grid"
        proc_table.alignment = WD_TABLE_ALIGNMENT.CENTER

        headers = ["教学环节", "时间", "教师活动", "学生活动", "设计意图"]
        for i, h in enumerate(headers):
            cell = proc_table.rows[0].cells[i]
            cell.text = h
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    run.bold = True

        for stage in spec.teaching_process:
            row = proc_table.add_row()
            row.cells[0].text = stage.get("stage", "")
            row.cells[1].text = stage.get("duration", "")
            row.cells[2].text = stage.get("teacher_activity", "")
            row.cells[3].text = stage.get("student_activity", "")
            row.cells[4].text = stage.get("design_intent", "")

    doc.add_paragraph()

    # Homework
    _add_heading(doc, "五、作业布置", level=1)
    for hw in spec.homework:
        doc.add_paragraph(hw, style="List Bullet")

    # Reflection
    _add_heading(doc, "六、教学反思", level=1)
    _add_paragraph(doc, spec.reflection or "（课后填写）", indent=True)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    return output_path
