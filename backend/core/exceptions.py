from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(response.data, dict) and "detail" in response.data:
        message = response.data["detail"]
    else:
        message = "Please check the submitted data."

    response.data = {
        "error": {
            "code": getattr(exc, "default_code", "request_error"),
            "message": message,
            "fields": response.data if isinstance(response.data, dict) else {},
        }
    }
    return response

