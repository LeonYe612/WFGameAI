import { http } from "@/utils/http";
import { baseUrlApi, ApiResult } from "./utils";

/** 获取当前用户参与的团队列表 */
export const listMineTeam = () => {
  return http.request<ApiResult>("get", baseUrlApi("/users/mine-teams"));
};

/** 切换团队 */
export const switchTeam = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/users/switch-team"), {
    data
  });
};

// ================================================================

/** 查询团队列表 */
export const listTeam = () => {
  return http.request<ApiResult>("get", baseUrlApi("/sys/teams/list"));
};

/** 添加/修改团队 */
export const editTeam = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/sys/teams/edit"), {
    data
  });
};

/** 删除团队 */
export const delTeam = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/sys/teams/del"), {
    data
  });
};

/** 查询用户当前激活团队的成员列表 */
export const listMember = () => {
  return http.request<ApiResult>("get", baseUrlApi("/teams/members/list"));
};

/** 添加/移除团队成员 */
export const manageMember = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/teams/members/manage"), {
    data
  });
};

/** 向团队成员委任角色 */
export const assignMember = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/teams/members/assign"), {
    data
  });
};

/** 拷贝某个团队的所有成员 */
export const copyMember = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/teams/members/copy"), {
    data
  });
};

/** 获取当前用户激活团队的简要信息 */
export const briefCurrentTeam = () => {
  return http.request<ApiResult>("get", baseUrlApi("/teams/current/brief"));
};

/** 获取当前用户参与的团队列表 */
export const listMineActiveTeam = () => {
  return http.request<ApiResult>(
    "get",
    baseUrlApi("/teams/manage/mine/active")
  );
};

/** 查询当前激活团队的环境配置信息 */
export const getTeamConfig = () => {
  return http.request<ApiResult>("get", baseUrlApi("/teams/manage/config"));
};

/** 切换团队 */
export const editTeamConfig = (data?: object) => {
  return http.request<ApiResult>("post", baseUrlApi("/teams/manage/config"), {
    data
  });
};

/** 测试团队配置 */
export const testTeamConfig = (data?: object) => {
  return http.request<ApiResult>(
    "post",
    baseUrlApi("/teams/manage/test-config"),
    {
      data
    }
  );
};

/** 查询团队的数据统计 */
export const statisticsTeam = () => {
  return http.request<ApiResult>("get", baseUrlApi("/teams/statistics"));
};
