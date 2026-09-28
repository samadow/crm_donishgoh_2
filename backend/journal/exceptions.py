from rest_framework.exceptions import APIException


class ConflictError(APIException):
    status_code = 409
    default_detail = "The record was changed by another user. Refresh and try again."
    default_code = "edit_conflict"

