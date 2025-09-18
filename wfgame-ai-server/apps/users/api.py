from typing import Tuple, Optional
from django.shortcuts import redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login as django_login

import requests
import logging
from django.conf import settings
from .models import AuthUser
from apps.core.utils.response import api_response
from apps.core.utils.jwt_helper import decode_token, generate_access_token, generate_refresh_token


logger = logging.getLogger(__name__)

def verify_sso_ticket(ticket) -> Tuple[Optional[dict], str]:
    """
    使用 SSO 票据验证用户身份
    验证成功返回用户信息，失败返回错误信息
    需要在 settings.CFG 中配置 SSO 服务器地址
    """
    sso_api_host = settings.CFG.get("auth", "sso_api_host")
    if not sso_api_host.endswith("/"):
        sso_api_host += "/"
    sso_verify_url = f"{sso_api_host}v1/sso/verify"

    try:
        response = requests.post(sso_verify_url, json={"ticket": ticket}, timeout=5)
        if response.status_code != 200:
            return None, f"无法连接到SSO服务器, 状态码: {response.status_code}"
        res = response.json()
        if res.get("code") != 0:
            return None, res.get("msg", "SSO Ticket 验证失败")
        return res.get("data"), ""
    except requests.RequestException as e:
        logger.error(f"请求SSO服务器异常: {str(e)}")
        return None, "请求SSO服务器发生异常"

class LoginByTicketView(APIView):
    """
    使用 sso ticket 换取 jwt access token
    说明：前后端分离架构下，前端 login 页面自动调用此接口换取 token
    """
    def post(self, request):
        ticket = request.data.get("ticket")
        if not ticket:
            return api_response(code=400, msg="缺少 ticket 参数")
        
        # 使用 ticket 去 SSO 服务器获取用户相关信息
        info, error = verify_sso_ticket(ticket)
        if error:
            return api_response(code=400, msg=error)
        
        userinfo = info.get("userInfo", {})
        teaminfo = info.get("teamInfo", {})
        perminfo = info.get("permInfo", {})

        # 将用户信息同步到本地数据库
        username = userinfo.get("username")
        chinese_name = userinfo.get("chinese_name", "")
        is_sso_admin = userinfo.get("is_super_admin", False)
        user, _ = AuthUser.objects.update_or_create(
            username=username,
            defaults={
                "chinese_name": chinese_name,
                "email": userinfo.get("email", ""),
                "phone": userinfo.get("phone", ""),
                "is_sso_admin": is_sso_admin,
                "joined_teams": teaminfo,
                "sso_user_id": userinfo.get("id"),
                "sso_permissions": perminfo,
            },
        )
        # 使用 Django 的认证系统登录用户
        django_login(request, user)

        # 生成 JWT token
        access_token, access_expire = generate_access_token(user)
        refresh_token, _ = generate_refresh_token(user)
        data = {
                "username": username,
                "chineseName": chinese_name,
                "roles": [],
                "perms": user.get_active_team_menu_perms(),
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expires": access_expire.strftime("%Y/%m/%d %H:%M:%S"),
            }
        return api_response(data=data)

class LoginView(APIView):
    """
    用户登录接口
    """

    def get(self, request):
        ticket = request.query_params.get("ticket")
        redirectUrl = request.query_params.get("next", "/")

        if not ticket or not redirectUrl:
            return Response(
                {"detail": "缺少ticket或redirect参数"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 使用 ticket 去 SSO 服务器获取用户相关信息
        info, error = verify_sso_ticket(ticket)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        userinfo = info.get("userInfo", {})
        teaminfo = info.get("teamInfo", {})
        perminfo = info.get("permInfo", {})

        # 将用户信息同步到本地数据库
        username = userinfo.get("username")
        chinese_name = userinfo.get("chinese_name", "")
        user, _ = AuthUser.objects.update_or_create(
            username=username,
            defaults={
                "chinese_name": chinese_name,
                "email": userinfo.get("email", ""),
                "phone": userinfo.get("phone", ""),
                "is_sso_admin": userinfo.get("is_super_admin", False),
                "sso_user_id": userinfo.get("id"),
                "joined_teams": teaminfo,
                "sso_permissions": perminfo,
            },
        )
        # 使用 Django 的认证系统登录用户
        django_login(request, user)

        # 添加设置 cookie
        response = redirect(redirectUrl)
        # 方便前端读取用户名，设置为非 HttpOnly
        response.set_cookie("username", username, httponly=False)

        return response


class LogoutView(APIView):
    """
    用户登出接口
    """

    def get(self, request):
        # 清除用户会话
        request.session.flush()
        return Response({"detail": "已登出"}, status=status.HTTP_200_OK)


class UserInfoView(APIView):
    """
    获取当前登录用户信息接口
    """

    def get(self, request):
        user: AuthUser = self.request._user

        user_data = {
            "id": user.id,
            "username": user.username,
            "chinese_name": user.chinese_name,
            "email": user.email,
            "phone": user.phone,
            "is_sso_admin": user.is_sso_admin,
            "active_team_id": user.active_team_id,
            "joined_teams": user.joined_teams,
        }
        return Response(user_data, status=status.HTTP_200_OK)


class SwitchTeamView(APIView):
    """
    切换当前激活团队接口
    未传递 team_id 参数时，自动尝试将用户切换为加入团队的首个 genre = 2 的团队
    传递 team_id 参数时，检查用户是否已加入该团队，若已加入则切换，否则返回错误
    返回数据格式：
    {
        "code": 0,
        "msg": "团队切换成功",
        "data": {
            "id": "xxxx",
            "name": "xxx",
            "full_name": "xxxx",
        }
    }
    """

    def post(self, request):
        user: AuthUser = getattr(request, "_user")
        team_id = request.data.get("id", 0)
        joined_teams = user.joined_teams or []
        if not joined_teams:
            return api_response(code=400, msg="用户未加入任何团队")
        if team_id:
            team_info = user.get_team_info(team_id)
        else:
            team_info = user.get_default_team_info()

        if not team_info:
            return api_response(code=400, msg="无效的团队ID或用户未加入该团队")

        # 切换当前激活团队
        user.active_team_id = team_info["id"]
        user.save()

        # 返回团队信息
        return api_response(data={
            "id": team_info["id"],
            "name": team_info["name"][-1],
            "full_name": team_info["name"],
            "perms": user.get_active_team_menu_perms(),
        })


class MineTeamView(APIView):
    """
    获取当前用户已加入的团队列表接口
    """

    def get(self, request):
        user: AuthUser = getattr(request, "_user", None)
        teams = user.joined_teams or []
        return api_response(data=teams)

class RefreshTokenView(APIView):
    """
    刷新 accessToken 接口
    """
    def post(self, request):
        refresh_token = request.data.get("refreshToken")
        if not refresh_token:
            return api_response(code=400, msg="缺少 refreshToken 参数")

        payload, error = decode_token(refresh_token)
        if error:
            return api_response(code=401, msg=error)

        if payload.get("type") != "refresh":
            return api_response(code=401, msg="无效的refreshToken类型")

        username = payload.get("username")
        try:
            user = AuthUser.objects.get(username=username)
        except AuthUser.DoesNotExist:
            return api_response(code=404, msg="用户不存在")

        access_token, access_expire = generate_access_token(user)
        result = {
            "accessToken": access_token,
            "expires": access_expire.strftime("%Y/%m/%d %H:%M:%S"),
            "refreshToken": refresh_token,
            "username": username,
            "roles": [],
        }
        return api_response(data=result)


class RoutesView(APIView):
    """
    获取当前用户的路由信息接口
    """
    def get(self, request):
        user: AuthUser = self.request._user
        routes = user.sso_routes or []
        return api_response(data=routes)