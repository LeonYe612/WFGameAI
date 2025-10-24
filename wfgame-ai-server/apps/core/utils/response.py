from django.http import JsonResponse
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import viewsets

VALID_JSON_RESPONSE_ATTR = "_valid_json_response"


class ApiResponseIntent:
    """
    用于在 get_serializer_class 中通过 api_response(code, data=SerializerClass) 传递定制 code/msg
    而不直接返回 JsonResponse（避免 DRF 流程中断）。
    """
    def __init__(self, code=0, msg="ok", serializer_class=None):
        self.code = code
        self.msg = msg
        self.serializer_class = serializer_class

def api_response(code=0, data=None, msg="ok"):
    # 特殊用法：当 data 是“类”（常见于 get_serializer_class 想传递 Serializer 类）时，
    # 返回一个意图对象，由自定义 ViewSet 捕获并处理。
    if isinstance(data, type):
        return ApiResponseIntent(code=code, msg=msg, serializer_class=data)
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



class CustomResponseModelViewSet(viewsets.ModelViewSet):
    """
    自定义的 ModelViewSet，覆盖 finalize_response 以统一返回格式为
    {
        "code": 0,          # 整数，0 表示成功，非 0 表示失败
        "msg": "ok",       # 字符串，描述信息
        "data": {...}      # 具体数据，任意类型
    }
    直接用当前类替换原来的 ViewSet 即可生效。
    """

    # 统一默认 code/msg，可在子类中覆盖
    DEFAULT_CODE = 0
    DEFAULT_MSG = "ok"
    # 按 action 覆盖 code/msg，例如：{"list": {"code": 123, "msg": "列表成功"}}
    ACTION_RESPONSE_META = {}

    def _resolve_code_msg(self):
        """按 action 解析 code/msg，未配置时使用默认值。"""
        try:
            # 优先使用本次请求的强制覆盖（来自 ApiResponseIntent）
            forced_code = getattr(self, '_forced_code', None)
            forced_msg = getattr(self, '_forced_msg', None)
            if forced_code is not None or forced_msg is not None:
                return forced_code if forced_code is not None else 0, forced_msg if forced_msg is not None else 'ok'
            meta = getattr(self, 'ACTION_RESPONSE_META', {}) or {}
            default_code = getattr(self, 'DEFAULT_CODE', 0)
            default_msg = getattr(self, 'DEFAULT_MSG', 'ok')
            action = getattr(self, 'action', None)
            override = meta.get(action, {}) if action else {}
            code = override.get('code', default_code)
            msg = override.get('msg', default_msg)
            return code, msg
        except Exception:
            # 任意异常回退默认
            return 0, 'ok'

    # 覆盖 DRF 的 get_serializer，使其支持 ApiResponseIntent 作为 get_serializer_class 的返回值
    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        # 支持：在 get_serializer_class 中 return api_response(code=..., msg=..., data=SerializerClass)
        if isinstance(serializer_class, ApiResponseIntent):
            self._forced_code = serializer_class.code
            self._forced_msg = serializer_class.msg
            serializer_class = serializer_class.serializer_class
        # 只允许返回“序列化器类”，其余类型一律报错，避免 'Response' object is not callable
        if not isinstance(serializer_class, type):
            raise TypeError(
                "get_serializer_class() 必须返回序列化器类，或使用 api_response(code=..., msg=..., data=SerializerClass) 进行临时覆盖。"
            )
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        # 1) 已经是 api_response(JsonResponse) 并带标记，直接返回
        if getattr(response, VALID_JSON_RESPONSE_ATTR, False):
            return response

        # 2) DRF Response：统一转换成 JsonResponse(api_response)
        if isinstance(response, Response):
            data = response.data
            if isinstance(data, dict) and set(data.keys()) >= {"code", "msg", "data"}:
                code = data.get("code", 0)
                msg = data.get("msg", "ok")
                payload = data.get("data")
            else:
                code, msg = self._resolve_code_msg()
                payload = data
            return api_response(code=code, msg=msg, data=payload)

        # 3) 其他 HttpResponse（含 JSON 或文本），统一转换
        try:
            content = None
            if hasattr(response, "content"):
                # bytes -> str
                try:
                    content = response.content
                    if isinstance(content, bytes):
                        content = content.decode("utf-8", errors="ignore")
                except Exception:
                    content = None

            if content is not None:
                import json
                try:
                    parsed = json.loads(content)
                except Exception:
                    parsed = content  # 非 JSON 文本，直接作为 data 返回

                if isinstance(parsed, dict) and set(parsed.keys()) >= {"code", "msg", "data"}:
                    code = parsed.get("code", 0)
                    msg = parsed.get("msg", "ok")
                    payload = parsed.get("data")
                else:
                    code, msg = self._resolve_code_msg()
                    payload = parsed
                return api_response(code=code, msg=msg, data=payload)
        except Exception:
            # 任何异常都回退到父类默认处理
            return super().finalize_response(request, response, *args, **kwargs)

        # 4) 若既不是 DRF Response，也无 content 可用，回退默认处理
        return super().finalize_response(request, response, *args, **kwargs)

class CommonPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'size'
    max_page_size = 500

    def get_paginated_response(self, data):
        return api_response(
            data={
                'page': self.page.number,
                'size': self.page.paginator.per_page,
                'total': self.page.paginator.count,
                'items': data
            }
        )

    def format_page_data(self, items):
        return {
            'page': self.page.number,
            'size': self.page.paginator.per_page,
            'total': self.page.paginator.count,
            'items': items
        }

    def empty_response(self):
        return api_response(
            data={
                'page': 1,
                'size': self.page_size,
                'total': 0,
                'items': []
            }
        )

    def paginate_response(self, queryset, request, view=None, serializer_class=None, serializer_kwargs=None, raise_exception=True):
        if serializer_kwargs is None:
            serializer_kwargs = {}
        try:
            page = self.paginate_queryset(queryset, request, view=view)
            page = page or []
            if serializer_class is not None:
                serializer = serializer_class(page, **serializer_kwargs)
                return self.get_paginated_response(serializer.data)
            else:
                return self.get_paginated_response(page)
        except Exception as e:
            # 页码超出范围时根据情况返回空数据或抛出异常
            if raise_exception:
                return api_response(code=500, msg=str(e))
            else:
                return self.empty_response()
