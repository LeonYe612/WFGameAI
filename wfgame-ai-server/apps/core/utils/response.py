from django.http import JsonResponse
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

VALID_JSON_RESPONSE_ATTR = "_valid_json_response"


def api_response(code=0, data=None, msg="ok"):
    # res = JsonResponse(
    #     {
    #         "code": code,
    #         "msg": msg,
    #         "data": data
    #     },
    #     json_dumps_params={
    #         "ensure_ascii": False,
    #     }
    # )
    res = Response(
        {
            "code": code,
            "msg": msg,
            "data": data
        },
        status=200
    )
    setattr(res, VALID_JSON_RESPONSE_ATTR, True)
    return res


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

    def paginate_response(self, queryset, request, view=None, serializer_class=None, serializer_kwargs=None, raise_exception=False):
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

