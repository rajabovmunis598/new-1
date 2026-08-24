import csv
from datetime import date, datetime
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone


CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe_value(value):
    """Serialize a value while preventing spreadsheet formula execution."""
    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    text = str(value)
    if text.startswith(CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


def csv_export_response(filename_prefix, headers, rows):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"{filename_prefix}-{timezone.localdate().isoformat()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"

    # The BOM keeps Tajik/Cyrillic text readable in common spreadsheet apps.
    response.write("\ufeff")
    writer = csv.writer(response, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(csv_safe_value(value) for value in row)
    return response
