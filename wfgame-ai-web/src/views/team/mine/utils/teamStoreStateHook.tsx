import { computed, watch } from "vue";
import { useTeamStoreHook } from "@/store/modules/team";
import { onActivated, onDeactivated, onMounted } from "vue";

export function useTeamGlobalState() {
  const activeTeamFullName = computed(() => {
    // console.log("activeTeamFullName", useTeamStoreHook()?.teamFullNames);
    return useTeamStoreHook()?.teamFullNames.join(" • ");
  });

  const activeTeamName = computed(() => {
    return useTeamStoreHook()?.teamName;
  });

  const activeTeamId = computed(() => {
    return useTeamStoreHook()?.teamId;
  });

  const mineTeamOptions = computed(() => {
    return useTeamStoreHook()?.mineTeamOptions;
  });

  const allTeamOptions = computed(() => {
    return useTeamStoreHook()?.allTeamOptions;
  });

  const refreshLoading = computed(() => {
    return useTeamStoreHook()?.refreshLoading;
  });

  const initWatchTeamId = (
    watchFunc: Function,
    immediate = true,
    onMountedFunc?: Function
  ) => {
    let unwatch = null; // 用于存储 watch 的取消方法
    // const instance = getCurrentInstance();
    // const componentName = instance?.type.name;

    if (onMountedFunc) {
      onMounted(() => {
        typeof onMountedFunc === "function" && onMountedFunc();
      });
    }

    onActivated(() => {
      // console.log(`【${componentName}】组件 onActivated: 添加 watcher`);
      unwatch = watch(
        () => useTeamStoreHook()?.teamId,
        (newValue, oldValue) => {
          if (newValue && newValue != oldValue) {
            // console.log(
            //   `【${componentName}】组件捕捉到 teamId 变化:`,
            //   newValue
            // );
            typeof watchFunc === "function" && watchFunc(newValue, oldValue);
          }
        },
        { immediate: immediate }
      );
    });

    onDeactivated(() => {
      // console.log(`【${componentName}】组件 onDeactivated: 移除 watcher`);
      unwatch && unwatch(); // 取消 watch
    });
  };

  const switchTeam = (teamId = 0) => {
    if (teamId && teamId != activeTeamId.value) {
      useTeamStoreHook()?.switchTeam(teamId);
    }
  };

  const refreshTeamOptions = (type = "mine", callback?: Function) => {
    useTeamStoreHook()?.refreshTeamOptions(type, callback);
  };

  return {
    activeTeamFullName,
    activeTeamName,
    activeTeamId,
    mineTeamOptions,
    allTeamOptions,
    refreshLoading,
    initWatchTeamId,
    switchTeam,
    refreshTeamOptions
  };
}
