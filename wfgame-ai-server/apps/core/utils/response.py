from django.http import JsonResponse

VALID_JSON_RESPONSE_ATTR = "_valid_json_response"


def api_response(code=0, data=None, msg="ok"):
    res = JsonResponse(
        {
            "code": code,
            "msg": msg,
            "data": data
        },
        json_dumps_params={
            "ensure_ascii": False,
        }
    )
    setattr(res, VALID_JSON_RESPONSE_ATTR, True)
    return res