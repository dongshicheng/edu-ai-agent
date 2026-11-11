import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from app.models.schemas import SlideSpec


# Color scheme
PRIMARY_COLOR = RGBColor(0x22, 0x5B, 0xA8)  # Deep blue
ACCENT_COLOR = RGBColor(0x3B, 0x82, 0xF6)   # Blue
BG_COLOR = RGBColor(0xFF, 0xFF, 0xFF)
TEXT_COLOR = RGBColor(0x1F, 0x29, 0x37)
SUBTITLE_COLOR = RGBColor(0x64, 0x74, 0x8B)

# Chinese fonts
TITLE_FONT = "Microsoft YaHei"
BODY_FONT = "Microsoft YaHei"


def _set_font(run, name: str, size: int, bold: bool = False, color: RGBColor = TEXT_COLOR):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def _add_cover_slide(prs: Presentation, spec: SlideSpec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

    # Title
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = spec.title
    _set_font(run, TITLE_FONT, 36, bold=True, color=PRIMARY_COLOR)

    # Subtitle
    if spec.bullets:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        run2 = p2.add_run()
        run2.text = spec.bullets[0] if spec.bullets else ""
        _set_font(run2, BODY_FONT, 18, color=SUBTITLE_COLOR)

    # Decorative line
    shape = slide.shapes.add_shape(
        1, Inches(3), Inches(2.3), Inches(4), Pt(3)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = ACCENT_COLOR
    shape.line.fill.background()

    # Notes
    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes


def _add_toc_slide(prs: Presentation, spec: SlideSpec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = spec.title
    _set_font(run, TITLE_FONT, 28, bold=True, color=PRIMARY_COLOR)

    # TOC items
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(8), Inches(4.5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    for i, item in enumerate(spec.bullets):
        p = tf2.add_paragraph() if i > 0 else tf2.paragraphs[0]
        p.space_after = Pt(16)
        run = p.add_run()
        run.text = item
        _set_font(run, BODY_FONT, 20, color=TEXT_COLOR)

    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes


def _add_content_slide(prs: Presentation, spec: SlideSpec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title bar
    shape = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(10), Inches(0.9)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = PRIMARY_COLOR
    shape.line.fill.background()

    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.1), Inches(9), Inches(0.7))
    tf = txBox.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = spec.title
    _set_font(run, TITLE_FONT, 24, bold=True, color=BG_COLOR)

    # Bullet points
    txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.3), Inches(8.4), Inches(5.5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    for i, bullet in enumerate(spec.bullets):
        p = tf2.add_paragraph() if i > 0 else tf2.paragraphs[0]
        p.space_after = Pt(14)
        p.level = 0
        run = p.add_run()
        run.text = f"  {bullet}"
        _set_font(run, BODY_FONT, 18, color=TEXT_COLOR)

    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes


def _add_summary_slide(prs: Presentation, spec: SlideSpec):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title
    txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(1))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = spec.title
    _set_font(run, TITLE_FONT, 28, bold=True, color=PRIMARY_COLOR)

    # Summary points
    txBox2 = slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(8), Inches(5))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    for i, item in enumerate(spec.bullets):
        p = tf2.add_paragraph() if i > 0 else tf2.paragraphs[0]
        p.space_after = Pt(12)
        run = p.add_run()
        run.text = f"  {item}"
        _set_font(run, BODY_FONT, 18, color=TEXT_COLOR)

    if spec.notes:
        slide.notes_slide.notes_text_frame.text = spec.notes


LAYOUT_HANDLERS = {
    "cover": _add_cover_slide,
    "toc": _add_toc_slide,
    "content": _add_content_slide,
    "two_column": _add_content_slide,
    "summary": _add_summary_slide,
    "exercise": _add_content_slide,
}


def generate_pptx(slides: list[SlideSpec], output_path: str) -> str:
    """Generate a PPTX file from slide specifications."""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    for spec in slides:
        handler = LAYOUT_HANDLERS.get(spec.layout, _add_content_slide)
        handler(prs, spec)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    prs.save(output_path)
    return output_path
