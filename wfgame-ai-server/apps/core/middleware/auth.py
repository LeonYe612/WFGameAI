from django.shortcuts import redirect
from django.conf import settings
from apps.users.models import AuthUser
from apps.core.utils.jwt_helper import decode_token
from apps.core.utils.response import api_response
from apps.core.utils.context_vars import current_user

class AuthenticationMiddleware:
    """
    自定义认证中间件
    """

    # 不需要认证的路径列表
    NO_AUTH = {
        "/api/users/login",
        "/api/users/login-by-ticket",
        "/api/users/refresh-token",
        "/pages/no_permission",
        "/pages/index_template.html",
    }

    SSO_WEB_HOST = settings.CFG.get("auth", "sso_web_host")
    ENABLE_PAGE_AUTH = settings.CFG.getboolean("auth", "enable_page_auth", fallback=True)
    ENABLE_API_AUTH = settings.CFG.getboolean("auth", "enable_api_auth", fallback=False)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.rstrip("/")
        if path in self.NO_AUTH:
            return self.get_response(request)

        # 🙍‍♂️ 用户认证：支持两种认证方式
        # 1. JWT 机制（通过 Authorization 请求头传递 Bearer Token）
        # 2. 默认的 Django Session & Cookie 机制
        user: AuthUser = getattr(request, "user", None)
        if not user.username:
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload, error = decode_token(token)
                if error:
                    return api_response(code=401, msg=error)
                username = payload.get("username")
                if not username:
                    return api_response(code=401, msg="Token中缺少用户名")
                user = AuthUser.objects.filter(username=username).first()
                if not user:
                    return api_response(code=401, msg="用户不存在")

        if not user.username:
            # 重定向到SSO平台的登录页面
            return redirect(self.format_sso_login_url(request))
        else:
            setattr(request, "_user", user)  # 确保 request.user 可用
            # 设置当前用户到上下文变量，并获取一个token（用于后续重置）
            user_token = current_user.set(user)
            # 将token保存在request上以便在process_response中清理
            request._current_user_token = user_token

        # 🔒 权限认证
        # a. /pages/ 开头的请求，菜单权限认证
        # b. /api/ 开头的请求，接口权限认证
        # c. 其他请求，忽略权限认证
        curr_path = request.path_info
        if curr_path.startswith("/pages/"):
            if not self.ENABLE_PAGE_AUTH:
                return self.get_response(request)
            # 菜单权限认证
            if not user.has_sso_perm(curr_path, scope="menu"):
                return redirect(f"/pages/no_permission?from={curr_path}")
        elif curr_path.startswith("/api/"):
            if not self.ENABLE_API_AUTH:
                return self.get_response(request)
            if not user.has_sso_perm(curr_path, scope="api"):
                return api_response(code=403, msg="无权限访问该接口, 请联系管理员授权")
        else:
            # 其他静态资源等请求，不进行权限认证
            return self.get_response(request)

        response =  self.get_response(request)
        # 清理 current_user
        if hasattr(request, "_current_user_token"):
            current_user.reset(request._current_user_token)

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        在视图函数调用前进行认证检查
        """
        pass

    def format_sso_login_url(self, request):
        """
        生成SSO登录URL
        """
        # api/users/login?next={当前请求完整URL}
        curr_url = request.build_absolute_uri()
        login_url = request.build_absolute_uri(f"/api/users/login?next={curr_url}")

        # 兼容配置末尾没有斜杠的情况
        if not self.SSO_WEB_HOST.endswith("/"):
            self.SSO_WEB_HOST += "/"

        # 完整 sso 登录 URL
        sso_url = f"{self.SSO_WEB_HOST}?redirect={login_url}#/sso-login"
        return sso_url
