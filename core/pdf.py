from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def render_pdf(template_name, context, filename):
    html = render_to_string(template_name, context)
    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        return HttpResponse("Could not generate PDF", status=500)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
