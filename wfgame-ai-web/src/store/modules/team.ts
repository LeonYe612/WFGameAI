import { defineStore } from "pinia";
import { store } from "@/store";
import { teamType } from "./types";
import { switchTeam, listMineTeam, listTeam } from "@/api/team";
import { superRequest } from "@/utils/request";
// import { message } from "@/utils/message";
import { initRouter } from "@/router/utils";
import { resetRouter } from "@/router";
import { gmTypeEnum } from "@/utils/enums";
import { useUserStore } from "./user";
import { updateUserKey } from "@/utils/auth";
import { connect } from "@/hooks/useSSE";

const userStore = useUserStore();

export const useTeamStore = defineStore({
  id: "current-team",
  state: (): teamType => ({
    // 用户名
    teamId: 0,
    teamName: "未选择团队",
    teamFullNames: ["未选择团队"],
    mineTeamOptions: [],
    allTeamOptions: [],
    refreshLoading: false,
    animate: false
  }),
  actions: {
    /** 存储团队ID */
    SET_TEAM_ID(teamId: number) {
      this.teamId = teamId;
    },
    /** 存储团队名称 */
    SET_TEAM_NAME(teamName: string) {
      this.teamName = teamName;
    },
    /** 存储全级别名称 */
    SET_TEAM_FULL_NAMES(teamFullNames: Array<string>) {
      this.teamFullNames = teamFullNames;
    },
    /** 获取当前激活队伍的全称 */
    GET_TEAM_FULL_NAMES() {
      return this.teamFullNames?.join(" • ");
    },
    /** 设置当前激活队伍信息 */
    SET_TEAM(data: any) {
      this.teamId = data.id || 0;
      this.teamName = data.name || "未选择团队";
      this.teamFullNames = data.full_name || ["未选择团队"];
      if (data?.perms) {
        // 更新当前团队的权限到用户权限里
        userStore.SET_PERMS(data.perms);
        updateUserKey({ perms: data.perms });
      }
    },
    /** 获取当前激活队伍的 GM 类型 */
    GET_TEAM_GM_TYPE() {
      const fullName = this.GET_TEAM_FULL_NAMES();
      for (const key in gmTypeEnum) {
        if (fullName.includes(gmTypeEnum[key].label)) {
          return gmTypeEnum[key].value;
        }
      }
      return gmTypeEnum.UNKNOWN.value;
    },
    GET_MINE_TEAM_OPTIONS() {
      // 如果this.mineTeamOptions 有值则直接返回，否则调用接口重新获取
      if (this.mineTeamOptions.length > 0) {
        return this.mineTeamOptions;
      } else {
        this.refreshTeamOptions("mine");
      }
    },
    /** 切换团队
     * a. id传递null时，表示后端自动选择团队
     * b. id传递具体值时，表示前端指定团队
     */
    async switchTeam(teamId = 0, refreshRouter = true) {
      await superRequest({
        apiFunc: switchTeam,
        apiParams: { id: teamId },
        onSucceed: (data: any) => {
          // connect();
          this.SET_TEAM(data);
          // 总是消息弹窗提示太烦人，改成动画提醒
          this.animate = true;
          setTimeout(() => {
            this.animate = false;
          }, 1000);
          // 刷新路由: 只有id传递具体值指定切换团队的时候，再进行路由刷新
          if (teamId && refreshRouter) {
            resetRouter();
            initRouter();
            // location.reload();
          }
        }
      });
    },
    /**
     * 刷新[我的团队列表] | [全部团队列表]
     */
    async refreshTeamOptions(type = "mine", callback?: Function) {
      await superRequest({
        apiFunc: type === "mine" ? listMineTeam : listTeam,
        onBeforeRequest: () => {
          this.refreshLoading = true;
        },
        onSucceed: (data: any) => {
          type === "mine"
            ? (this.mineTeamList = data.data)
            : (this.allTeamList = data.data);
          typeof callback === "function" && callback();
        },
        onCompleted: () => {
          this.refreshLoading = false;
        }
      });
      // return new Promise<ApiResult>((resolve, reject) => {
      //   this.refreshLoading = true;
      //   const api = type === "mine" ? listMineTeam : listTeam;
      //   api()
      //     .then(data => {
      //       if (data?.code === 0) {
      //         type === "mine"
      //           ? (this.mineTeamList = data.data)
      //           : (this.allTeamList = data.data);
      //         typeof callback === "function" && callback();
      //         resolve(data);
      //       } else {
      //         throw Error(data.msg);
      //       }
      //     })
      //     .catch(error => {
      //       message(error, { type: "error" });
      //       reject(error);
      //     })
      //     .finally(() => {
      //       this.refreshLoading = false;
      //     });
      // });
    }
  }
});
export function useTeamStoreHook() {
  return useTeamStore(store);
}
