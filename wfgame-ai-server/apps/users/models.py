from django.contrib.auth.models import AbstractUser
from django.db import models
from typing import Literal, Optional, TypedDict, List

class TeamInfo(TypedDict):
    id: int
    name: list[str]


class AuthUser(AbstractUser):
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="手机号"
    )
    chinese_name = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="中文名"
    )
    sso_user_id = models.IntegerField(
        blank=True, null=True, verbose_name="SSO用户ID", unique=True
    )
    active_team_id = models.IntegerField(
        default=0, blank=True, null=True, verbose_name="当前激活团队ID"
    )
    joined_teams = models.JSONField(
        default=list, blank=True, verbose_name="已加入团队列表"
    )
    is_sso_admin = models.BooleanField(
        default=False, verbose_name="是否为SSO平台管理员"
    )
    sso_permissions = models.JSONField(
        default=dict, blank=True, verbose_name="SSO权限信息"
    )
    sso_routes = models.JSONField(
        default=list, blank=True, verbose_name="SSO路由信息"
    )

    def has_sso_perm(
            self, 
            perm_code: str, 
            scope: Literal["all", "menu", "api", "action", "link"] = "all"
        ) -> bool:
        """
        检查用户是否具有指定的SSO权限
        :param perm_code: 权限代码
        :param scope: 权限范围和SSO类型保持一致
        可选值: "all" (所有)、"menu" (菜单), "api" (接口), "action" (操作), "link" (外链)
        :return: True 如果用户具有该权限, 否则 False
        说明:
        - 如果用户是超级管理员或SSO管理员, 则自动具有所有权限
        - 如果scope为"all", 则在所有权限中检查
        - 如果scope指定具体类型, 则仅在对应范围内查找权限
        - 如果scope值无效, 则抛出ValueError异常
        sso_permissions字段示例:
        {
            "team_1": {
                "menu": ["/pages/index_template.html"],
                "api": ["api1", "api2"],
                "action": ["add", "edit"],
                "link": ["http://example.com"]
            }
            "team_2": {
                "page": ["view_reports"],
                "api": []
            }
        }
        """
        if self.is_superuser or self.is_sso_admin:
            return True
        curr_team_key = f"team_{self.active_team_id}"
        curr_team_perms = self.sso_permissions.get(curr_team_key, {
            "menu": [],
            "api": [],
            "action": [],
            "link": []
        })

        if scope == "all":
            all_perms = set()
            for perms in curr_team_perms.values():
                all_perms.update(perms)
            return perm_code in all_perms
        else:
            scoped_perms = curr_team_perms.get(scope, [])
            return perm_code in scoped_perms

    def get_team_info(self, team_id: int) -> Optional[TeamInfo]:
        """
        根据团队ID递归查找团队信息, 并返回包含完整name路径的TeamInfo
        """
        def _find_team(teams, path):
            for team in teams:
                curr_path = path + [team.get("name")]
                if team.get("id") == team_id:
                    return {"id": team_id, "name": curr_path}
                children = team.get("children")
                if children:
                    result = _find_team(children, curr_path)
                    if result:
                        return result
            return None

        joined_teams = self.joined_teams or []
        return _find_team(joined_teams, [])

    def get_default_team_info(self) -> Optional[TeamInfo]:
        """
        获取用户的默认团队信息, 即第一个 genre = 2 的团队
        """
        joined_teams = self.joined_teams or []
        def _find_default_team(teams, path):
            for team in teams:
                curr_path = path + [team.get("name")]
                if team.get("genre") == 2:
                    return {"id": team.get("id"), "name": curr_path}
                children = team.get("children")
                if children:
                    result = _find_default_team(children, curr_path)
                    if result:
                        return result
            return None
        return _find_default_team(joined_teams, [])

    def get_active_team_perms(self, scope: Literal["all", "menu", "api", "action", "link"] = "all") -> List[str]:
        """
        获取用户当前激活团队的指定范围权限列表
        :param scope: 权限范围
        可选值: "all" (所有)、"menu" (菜单), "api" (接口), "action" (操作), "link" (外链)
        :return: 权限代码列表
        说明:
        - 如果用户是超级管理员或SSO管理员, 则返回 ["*"] 表示所有权限
        - 如果scope为"all", 则返回所有权限的合集
        - 如果scope指定具体类型, 则仅返回对应范围内的权限列表
        - 如果scope值无效, 则抛出ValueError异常
        """
        if self.is_superuser or self.is_sso_admin:
            return ["*"]
        curr_team_key = f"team_{self.active_team_id}"
        curr_team_perms = self.sso_permissions.get(curr_team_key, {
            "menu": [],
            "api": [],
            "action": [],
            "link": []
        })

        if scope == "all":
            all_perms = set()
            for perms in curr_team_perms.values():
                all_perms.update(perms)
            return list(all_perms)
        elif scope in curr_team_perms:
            return curr_team_perms.get(scope, [])
        else:
            raise ValueError(f"Invalid scope value: {scope}")

    def get_active_team_menu_perms(self) -> List[str]:
        """
        获取用户当前激活团队的菜单权限
        """
        if self.is_superuser or self.is_sso_admin:
            return ["*"]
        curr_team_key = f"team_{self.active_team_id}"
        return self.sso_permissions.get(curr_team_key, {}).get("menu", [])


    class Meta:
        db_table = "auth_user"
        verbose_name = "用户"
        verbose_name_plural = "用户"
