"""One-page (or more) A4 technical spec sheet for a product, built with ReportLab."""
from datetime import date
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from core.content import COMPANY

FONT_DIR = Path(__file__).resolve().parent / 'fonts'
BODY, BOLD, DISPLAY = 'Manrope', 'Manrope-Bold', 'Playfair'

EMERALD = colors.HexColor('#0a3a2c')
EMERALD_LIT = colors.HexColor('#0f5240')
TEXT = colors.HexColor('#08291f')
MUTED = colors.HexColor('#4b695e')
LINE = colors.HexColor('#d5e0da')
MIST = colors.HexColor('#f6f9f7')

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

_fonts_ready = False


def _register_fonts():
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont(BODY, str(FONT_DIR / 'Manrope-Regular.ttf')))
    pdfmetrics.registerFont(TTFont(BOLD, str(FONT_DIR / 'Manrope-Bold.ttf')))
    pdfmetrics.registerFont(TTFont(DISPLAY, str(FONT_DIR / 'PlayfairDisplay-SemiBold.ttf')))
    pdfmetrics.registerFontFamily(BODY, normal=BODY, bold=BOLD, italic=BODY, boldItalic=BOLD)
    _fonts_ready = True


def _styles():
    base = dict(fontName=BODY, fontSize=9.5, leading=13.5, textColor=TEXT)
    return {
        'eyebrow': ParagraphStyle('eyebrow', **{**base, 'fontName': BOLD, 'fontSize': 8,
                                                'textColor': EMERALD_LIT, 'spaceAfter': 3}),
        'title': ParagraphStyle('title', **{**base, 'fontName': DISPLAY, 'fontSize': 24,
                                            'leading': 28, 'spaceAfter': 6}),
        'lead': ParagraphStyle('lead', **{**base, 'fontSize': 11, 'leading': 15.5, 'textColor': MUTED}),
        'h2': ParagraphStyle('h2', **{**base, 'fontName': DISPLAY, 'fontSize': 13, 'leading': 17,
                                      'spaceBefore': 12, 'spaceAfter': 6}),
        'body': ParagraphStyle('body', **base),
        'th': ParagraphStyle('th', **{**base, 'textColor': MUTED}),
        'td': ParagraphStyle('td', **{**base, 'fontName': BOLD}),
        'caption': ParagraphStyle('caption', **{**base, 'fontSize': 8, 'textColor': MUTED, 'leading': 11}),
    }


def _p(text, style):
    return Paragraph(escape(str(text)), style)


def _image(path, max_w, max_h):
    """A flowable scaled to fit the box, or None if the file is missing or unreadable."""
    try:
        img = Image(str(path))
    except (OSError, ValueError):
        return None
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth, img.drawHeight = img.imageWidth * scale, img.imageHeight * scale
    return img


def _file_path(field_file):
    try:
        return field_file.path if field_file else None
    except (NotImplementedError, ValueError):
        return None


def _page_frame(product):
    """Header strip and footer drawn on every page."""
    logo = finders.find('img/logo.png')
    phones = ' · '.join(p['display'] for p in COMPANY['phones'][:2])
    address = f"{COMPANY['street']}, {COMPANY['postal_code']} {COMPANY['city']}"
    site = settings.SITE_URL.replace('https://', '').replace('http://', '')

    def draw(canvas, doc):
        canvas.saveState()
        # Header
        top = PAGE_H - 12 * mm
        if logo:
            canvas.drawImage(logo, MARGIN, top - 11 * mm, height=11 * mm, width=12.3 * mm,
                             preserveAspectRatio=True, mask='auto')
        canvas.setFillColor(TEXT)
        canvas.setFont(BOLD, 10)
        canvas.drawString(MARGIN + 15 * mm, top - 4.5 * mm, COMPANY['legal_name'])
        canvas.setFont(BODY, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN + 15 * mm, top - 9 * mm, COMPANY['tagline'])
        canvas.setFont(BOLD, 8)
        canvas.setFillColor(EMERALD_LIT)
        canvas.drawRightString(PAGE_W - MARGIN, top - 4.5 * mm, 'ТЕХНИЧЕСКА СПЕЦИФИКАЦИЯ')
        canvas.setFont(BODY, 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(PAGE_W - MARGIN, top - 9 * mm, product.name[:70])
        canvas.setStrokeColor(EMERALD)
        canvas.setLineWidth(1.2)
        canvas.line(MARGIN, top - 14 * mm, PAGE_W - MARGIN, top - 14 * mm)

        # Footer
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(.6)
        canvas.line(MARGIN, 17 * mm, PAGE_W - MARGIN, 17 * mm)
        canvas.setFont(BODY, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 12.5 * mm, f'{address} · {phones} · {COMPANY["email"]}')
        canvas.drawString(MARGIN, 8.5 * mm, f'{site}{product.get_absolute_url()}')
        canvas.drawRightString(PAGE_W - MARGIN, 12.5 * mm, f'стр. {doc.page}')
        canvas.drawRightString(PAGE_W - MARGIN, 8.5 * mm, f'Издадена {date.today():%d.%m.%Y} г.')
        canvas.restoreState()

    return draw


def _spec_table(product, st):
    rows = [[_p(k, st['th']), _p(v, st['td'])] for k, v in product.specifications.items()]
    table = Table(rows, colWidths=[CONTENT_W * .4, CONTENT_W * .6])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEABOVE', (0, 0), (-1, 0), 1, TEXT),
        ('LINEBELOW', (0, 0), (-1, -1), .5, LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return table


def _color_table(product, st):
    rows = []
    for c in product.color_list:
        swatch = Table([['']], colWidths=[7 * mm], rowHeights=[5 * mm])
        swatch.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(c['hex']) if c['hex'] else MIST),
            ('BOX', (0, 0), (-1, -1), .5, LINE),
        ]))
        label = escape(c['name']) + (f' — {escape(c["note"])}' if c['note'] else '')
        rows.append([swatch, Paragraph(label, st['body'])])
    table = Table(rows, colWidths=[10 * mm, CONTENT_W - 10 * mm])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return table


def _bullets(items, st):
    return [Paragraph(f'•&nbsp;&nbsp;{escape(i)}', st['body']) for i in items if i.strip()]


def render_spec_sheet(product, images):
    """Return the PDF bytes for `product`; `images` is its list of ProductImage objects."""
    _register_fonts()
    st = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=34 * mm, bottomMargin=24 * mm,
        title=f'{product.name} — техническа спецификация',
        author=COMPANY['legal_name'], subject=product.category.name,
    )

    story = [
        _p(product.category.name.upper(), st['eyebrow']),
        _p(product.name, st['title']),
        _p(product.short_description, st['lead']),
        Spacer(1, 8 * mm),
    ]

    # Photo and drawing side by side when both exist, otherwise one wide.
    pictures = []
    photo = _file_path(images[0].image) if images else None
    drawing = _file_path(product.drawing)
    boxes = [(photo, 'Снимка'), (drawing, 'Чертеж с размери')]
    boxes = [(path, caption) for path, caption in boxes if path]
    if boxes:
        box_w = (CONTENT_W - 6 * mm) / len(boxes) if len(boxes) > 1 else CONTENT_W * .7
        for path, caption in boxes:
            img = _image(path, box_w, 75 * mm if len(boxes) > 1 else 58 * mm)
            if img:
                pictures.append([img, _p(caption, st['caption'])])
    if pictures:
        # A caption only earns its place when it tells the photo from the drawing.
        cells = [[cell[0] for cell in pictures]]
        if len(pictures) > 1:
            cells.append([cell[1] for cell in pictures])
        grid = Table(cells, colWidths=[CONTENT_W / len(pictures)] * len(pictures))
        grid.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ]))
        story += [grid, Spacer(1, 4 * mm)]

    if product.specifications:
        story += [_p('Технически данни', st['h2']), _spec_table(product, st)]

    if product.color_list or product.color_on_request:
        block = [_p('Цветове', st['h2'])]
        if product.color_list:
            block.append(_color_table(product, st))
        if product.color_on_request:
            block.append(_p('Друг цвят — по избор на клиента.', st['body']))
        story.append(KeepTogether(block))

    for heading, items in (('Стандарти и документи', product.standards_list),
                           ('Опции', product.options_list)):
        items = [i for i in items if i.strip()]
        if items:
            story.append(KeepTogether([_p(heading, st['h2']), *_bullets(items, st)]))

    if product.description:
        story.append(_p('За продукта', st['h2']))
        for para in product.description.split('\n\n'):
            if para.strip():
                story += [_p(para.strip(), st['body']), Spacer(1, 2 * mm)]

    story += [
        Spacer(1, 6 * mm),
        Paragraph(
            'За оферта, други размери или цвят: '
            f'<b>{escape(COMPANY["phones"][0]["display"])}</b> · <b>{escape(COMPANY["email"])}</b>',
            st['body']),
    ]

    frame = _page_frame(product)
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()
