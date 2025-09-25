"""
OCR模块URL配置
"""

from django.urls import path
from . import api

urlpatterns = [
    # 获取token API
    path("login-by-ticket", api.LoginByTicketView.as_view(), name="users_login_by_ticket"),
    # 刷新 token API
    path("refresh-token", api.RefreshTokenView.as_view(), name="users_refresh_token"),
    # 获取路由
    path("routes", api.RoutesView.as_view(), name="users_routes"),
    # 用户登录 API
    path("login", api.LoginView.as_view(), name="users_login"),
    # 用户登出 API
    path("logout", api.LogoutView.as_view(), name="users_logout"),
    # 用户信息 API
    path("info", api.UserInfoView.as_view(), name="users_info"),
    # 切换团队 API
    path("switch-team", api.SwitchTeamView.as_view(), name="users_switch_team"),
    # 已加入团队列表 API
    path("mine-teams", api.MineTeamView.as_view(), name="users_mine_teams"),
]
