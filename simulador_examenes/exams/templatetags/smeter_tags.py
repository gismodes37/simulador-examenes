"""
Template tag para el elemento visual "S-metro" (medidor de intensidad de
senal analogico) usado en las tarjetas de categoria, el examen y los
resultados. Convierte un porcentaje (0-100) en un arco + aguja SVG.

Uso en plantillas:
    {% load smeter_tags %}
    {% smeter pct=78 variant="signal" caption="S9+20" size=220 %}

variant controla el color de la aguja/arco:
    "signal" -> ambar (var(--ra-signal))   — uso general / examen
    "tune"   -> verde (var(--ra-tune))     — aprobado / correcto
    "copper" -> cobre (var(--ra-copper))   — categorias intermedias
    "muted"  -> gris  (var(--ra-ink-muted)) — categorias bajas / sin datos
"""
import math

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_VARIANT_COLORS = {
    "signal": "var(--ra-signal)",
    "tune": "var(--ra-tune)",
    "copper": "var(--ra-copper)",
    "muted": "var(--ra-ink-muted)",
    "alarm": "var(--ra-alarm)",
}

_CX, _CY, _R = 100, 100, 80
_NEEDLE_R = _R - 15
_TRACK_D = f"M 20 {_CY} A {_R} {_R} 0 1 1 180 {_CY}"


def _point_on_arc(pct, radius):
    """pct in [0, 1]. Angle sweeps 180deg (left, S1) -> 0deg (right, S9+)."""
    angle_deg = 180 - (180 * pct)
    angle_rad = math.radians(angle_deg)
    x = _CX + radius * math.cos(angle_rad)
    y = _CY - radius * math.sin(angle_rad)
    return x, y


@register.simple_tag
def smeter(pct, variant="signal", caption="", size=180, ticks=8):
    """Renders an S-meter (analog signal-strength gauge) as inline SVG."""
    try:
        pct_val = max(0.0, min(100.0, float(pct))) / 100
    except (TypeError, ValueError):
        pct_val = 0.0

    color = _VARIANT_COLORS.get(variant, _VARIANT_COLORS["signal"])
    arc_x, arc_y = _point_on_arc(pct_val, _R)
    needle_x, needle_y = _point_on_arc(pct_val, _NEEDLE_R)
    large_arc = 1 if pct_val > 0.5 else 0

    tick_marks = []
    for i in range(ticks + 1):
        t_pct = i / ticks
        x1, y1 = _point_on_arc(t_pct, _R + 4)
        x2, y2 = _point_on_arc(t_pct, _R + 12)
        tick_marks.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="var(--ra-border-strong)" stroke-width="2"/>'
        )

    caption_html = (
        f'<div class="smeter-caption">{caption}</div>' if caption else ""
    )

    signal_arc_d = f"M 20 {_CY} A {_R} {_R} 0 {large_arc} 1 {arc_x:.2f} {arc_y:.2f}"

    svg = f'''<div class="smeter" style="max-width:{size}px; margin:0 auto;">
<svg viewBox="0 0 200 120" role="img" aria-label="Medidor de senal: {pct_val * 100:.0f} por ciento">
<path class="smeter-track" d="{_TRACK_D}"/>
<path d="{signal_arc_d}" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
{''.join(tick_marks)}
<line class="smeter-needle" x1="{_CX}" y1="{_CY}" x2="{needle_x:.2f}" y2="{needle_y:.2f}" stroke="{color}"/>
<circle cx="{_CX}" cy="{_CY}" r="6" fill="{color}"/>
</svg>
{caption_html}
</div>'''
    return mark_safe(svg)
