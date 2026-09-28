import csv
import io
from datetime import date, datetime
from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from academics.models import Program
from journal.models import AcademicYear
from .models import AdmissionImportBatch, Applicant, Application, ApplicationStatusHistory


MAX_IMPORT_ROWS = 2000
MAX_IMPORT_BYTES = 5 * 1024 * 1024
REQUIRED_COLUMNS = (
    "application_number", "first_name", "last_name", "birth_date", "email", "phone",
    "program_code", "academic_year",
)
HEADER_ALIASES = {
    "application_number": {"application_number", "номер_заявки", "рақами_ариза"},
    "first_name": {"first_name", "имя", "ном"},
    "last_name": {"last_name", "фамилия", "насаб"},
    "middle_name": {"middle_name", "отчество", "номи_падар"},
    "birth_date": {"birth_date", "дата_рождения", "санаи_таваллуд"},
    "email": {"email", "почта"},
    "phone": {"phone", "телефон"},
    "national_id": {"national_id", "номер_документа", "рақами_ҳуҷҷат"},
    "address": {"address", "адрес", "суроға"},
    "program_code": {"program_code", "код_программы", "рамзи_барнома"},
    "academic_year": {"academic_year", "учебный_год", "соли_таҳсил"},
}


def _canonical_header(value):
    normalized = str(value or "").strip().lower().replace(" ", "_")
    for canonical, aliases in HEADER_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized


def _read_rows(uploaded_file):
    if uploaded_file.size > MAX_IMPORT_BYTES:
        raise ValidationError({"file": "The file exceeds the 5 MB limit."})
    suffix = Path(uploaded_file.name).suffix.lower()
    content = uploaded_file.read()
    if suffix == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError({"file": "CSV must use UTF-8 encoding."}) from exc
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return list(csv.reader(io.StringIO(text), dialect))
    if suffix != ".xlsx":
        raise ValidationError({"file": "Upload an .xlsx or UTF-8 .csv file."})
    try:
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        worksheet = workbook.active
        rows = [list(row) for row in worksheet.iter_rows(values_only=True)]
        workbook.close()
        return rows
    except Exception as exc:
        raise ValidationError({"file": "The Excel workbook could not be read."}) from exc


def _date_value(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            continue
    return ""


def _error(field, code, message):
    return {"field": field, "code": code, "message": message}


def build_import_preview(uploaded_file, user):
    matrix = _read_rows(uploaded_file)
    if not matrix:
        raise ValidationError({"file": "The file is empty."})
    headers = [_canonical_header(value) for value in matrix[0]]
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise ValidationError({"columns": missing})
    if len(matrix) - 1 > MAX_IMPORT_ROWS:
        raise ValidationError({"file": f"The file contains more than {MAX_IMPORT_ROWS} rows."})

    programs = {item.code.lower(): item for item in Program.objects.all()}
    years = {item.name.lower(): item for item in AcademicYear.objects.all()}
    existing_emails = {value.lower() for value in Applicant.objects.values_list("email", flat=True)}
    existing_ids = {value for value in Applicant.objects.exclude(national_id="").values_list("national_id", flat=True)}
    existing_numbers = set(Application.objects.values_list("application_number", flat=True))
    seen_emails, seen_ids, seen_numbers = set(), set(), set()
    result = []

    for excel_row, values in enumerate(matrix[1:], start=2):
        if all(value in (None, "") for value in values):
            continue
        raw = {header: values[index] if index < len(values) else "" for index, header in enumerate(headers)}
        row = {
            "application_number": str(raw.get("application_number") or "").strip(),
            "first_name": str(raw.get("first_name") or "").strip(),
            "last_name": str(raw.get("last_name") or "").strip(),
            "middle_name": str(raw.get("middle_name") or "").strip(),
            "birth_date": _date_value(raw.get("birth_date")),
            "email": str(raw.get("email") or "").strip().lower(),
            "phone": str(raw.get("phone") or "").strip(),
            "national_id": str(raw.get("national_id") or "").strip(),
            "address": str(raw.get("address") or "").strip(),
            "program_code": str(raw.get("program_code") or "").strip(),
            "academic_year": str(raw.get("academic_year") or "").strip(),
        }
        errors = []
        for field in REQUIRED_COLUMNS:
            if not row[field]:
                errors.append(_error(field, "required", "Required value is missing."))
        if row["email"]:
            try:
                validate_email(row["email"])
            except DjangoValidationError:
                errors.append(_error("email", "invalid", "Email address is invalid."))
        if raw.get("birth_date") and not row["birth_date"]:
            errors.append(_error("birth_date", "invalid", "Use YYYY-MM-DD or DD.MM.YYYY."))
        if row["program_code"].lower() not in programs:
            errors.append(_error("program_code", "unknown", "Programme code was not found."))
        if row["academic_year"].lower() not in years:
            errors.append(_error("academic_year", "unknown", "Academic year was not found."))
        if row["email"] in existing_emails or row["email"] in seen_emails:
            errors.append(_error("email", "duplicate", "Applicant email is duplicated."))
        if row["application_number"] in existing_numbers or row["application_number"] in seen_numbers:
            errors.append(_error("application_number", "duplicate", "Application number is duplicated."))
        if row["national_id"] and (row["national_id"] in existing_ids or row["national_id"] in seen_ids):
            errors.append(_error("national_id", "duplicate", "Document number is duplicated."))
        seen_emails.add(row["email"])
        seen_numbers.add(row["application_number"])
        if row["national_id"]:
            seen_ids.add(row["national_id"])
        result.append({"row": excel_row, "data": row, "errors": errors})

    batch = AdmissionImportBatch.objects.create(
        file_name=Path(uploaded_file.name).name,
        rows=result,
        row_count=len(result),
        valid_count=sum(not item["errors"] for item in result),
        error_count=sum(bool(item["errors"]) for item in result),
        created_by=user,
    )
    return batch


@transaction.atomic
def commit_import_batch(batch, user):
    batch = AdmissionImportBatch.objects.select_for_update().get(pk=batch.pk)
    if batch.status == AdmissionImportBatch.Status.COMMITTED:
        return batch, True
    if batch.error_count:
        raise ValidationError({"batch": "Resolve every preview error before importing."})
    programs = {item.code.lower(): item for item in Program.objects.all()}
    years = {item.name.lower(): item for item in AcademicYear.objects.all()}
    try:
        for item in batch.rows:
            data = item["data"]
            applicant = Applicant.objects.create(
                first_name=data["first_name"], last_name=data["last_name"], middle_name=data["middle_name"],
                birth_date=data["birth_date"], email=data["email"], phone=data["phone"],
                national_id=data["national_id"], address=data["address"],
            )
            application = Application.objects.create(
                applicant=applicant,
                program=programs[data["program_code"].lower()],
                academic_year=years[data["academic_year"].lower()],
                application_number=data["application_number"],
                source="excel_import",
            )
            ApplicationStatusHistory.objects.create(
                application=application, from_status="", to_status=application.status,
                reason=f"Imported from {batch.file_name}", author=user,
            )
    except (IntegrityError, KeyError) as exc:
        raise ValidationError({"batch": "Data changed after preview. Create a new preview and try again."}) from exc
    batch.status = AdmissionImportBatch.Status.COMMITTED
    batch.committed_at = timezone.now()
    batch.save(update_fields=("status", "committed_at"))
    return batch, False
