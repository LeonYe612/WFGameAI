import { computed, onUnmounted, watch } from "vue";
import { useTeamStoreHook } from "@/store/modules/team";
import { onDeactivated, onMounted } from "vue";

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

  // const initWatchTeamId = (
  //   watchFunc: Function,
  //   immediate = true,
  //   onMountedFunc?: Function
  // ) => {
  //   debugger;
  //   let unwatch = null; // 用于存储 watch 的取消方法
  //   // const instance = getCurrentInstance();
  //   // const componentName = instance?.type.name;

  //   if (onMountedFunc && typeof onMountedFunc === "function") {
  //     onMounted(() => {
  //       onMountedFunc();
  //     });
  //   }

  //   onActivated(() => {
  //     console.log(`组件 onActivated: 添加 teamId Watcher`);
  //     unwatch = watch(
  //       () => useTeamStoreHook()?.teamId,
  //       (newValue, oldValue) => {
  //         if (newValue && newValue != oldValue) {
  //           console.log(`组件捕捉到 teamId 变化:`, newValue);
  //           typeof watchFunc === "function" && watchFunc(newValue, oldValue);
  //         }
  //       },
  //       { immediate: immediate }
  //     );
  //   });

  //   onDeactivated(() => {
  //     console.log(`组件 onDeactivated: 移除 teamId Watcher`);
  //     unwatch && unwatch(); // 取消 watch
  //   });
  // };

  const initWatchTeamId = (
    watchFunc: Function,
    immediate = true,
    onMountedFunc?: Function
  ) => {
    let unwatch = null; // 用于存储 watch 的取消方法
    if (onMountedFunc && typeof onMountedFunc === "function") {
      onMounted(() => {
        onMountedFunc();
      });
    }

    onMounted(() => {
      console.log(`组件 onMounted: 添加 teamId Watcher`);
      // 直接返回 watch，让组件自己管理生命周期
      unwatch = watch(
        () => useTeamStoreHook()?.teamId,
        (newValue, oldValue) => {
          if (newValue && newValue != oldValue) {
            // console.log(`组件捕捉到 teamId 变化:`, newValue);
            typeof watchFunc === "function" && watchFunc(newValue, oldValue);
          }
        },
        { immediate: immediate }
      );
    });

    onUnmounted(() => {
      console.log(`组件 onUnmounted: 移除 teamId Watcher`);
      unwatch && unwatch(); // 组件卸载时取消 watch
    });

    onDeactivated(() => {
      console.log(`组件 onDeactivated: 移除 teamId Watcher`);
      unwatch && unwatch(); // 组件停用时取消 watch
    });

    return unwatch;
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
