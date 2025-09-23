<script lang="ts" setup>
import {
  Warning,
  Iphone,
  SuccessFilled,
  WarnTriangleFilled,
  CircleCloseFilled
} from "@element-plus/icons-vue";
import { ReNormalCountTo } from "@/components/ReCountTo";
import { useTeamGlobalState } from "@/views/team/hooks/teamStoreStateHook";
import { ref } from "vue";
import { useRouter } from "vue-router";
// import { superRequest } from "@/utils/request";
// import { statisticsTeam } from "@/api/team";

const router = useRouter();

defineOptions({
  name: "DashboardStatistic"
});

const data = [
  {
    title: "在线设备",
    tip: "在线设备总数",
    value: 0,
    icon: Iphone,
    backgroundColor: "#409EFF", // Element Plus 主蓝色
    textColor: "#FFFFFF",
    footerText: "",
    onClick: () => {
      router.push({ path: "/devices/index" });
    }
  },
  {
    title: "成功测试",
    tip: "测试结果成功的总任务数",
    value: 0,
    icon: SuccessFilled,
    backgroundColor: "#67C23A", // Element Plus 成功绿色
    textColor: "#FFFFFF",
    footerText: "",
    onClick: () => {
      router.push({ path: "/tasks/index" });
    }
  },
  {
    title: "正在执行",
    tip: "执行中的总任务数",
    value: 0,
    icon: WarnTriangleFilled,
    backgroundColor: "#E6A23C", // Element Plus 警告黄色
    textColor: "#FFFFFF",
    footerText: "",
    onClick: () => {
      router.push({ path: "/tasks/index" });
    }
  },
  {
    title: "失败测试",
    tip: "测试结果失败的总任务数",
    value: 0,
    icon: CircleCloseFilled,
    backgroundColor: "#F56C6C", // Element Plus 危险红色
    textColor: "#FFFFFF",
    footerText: "",
    onClick: () => {
      router.push({ path: "/tasks/index" });
    }
  }
];
const dataRef = ref(data);

const fetchData = async () => {
  // await superRequest({
  //   apiFunc: statisticsTeam,
  //   onSucceed: data => {
  //     dataRef.value[0].value = data?.total_cases || 0;
  //     dataRef.value[1].value = data?.total_plans || 0;
  //     dataRef.value[2].value = data?.total_pass_rate || 0;
  //     dataRef.value[3].value = data?.total_send_proto || 0;
  //   }
  // });
};

const { initWatchTeamId } = useTeamGlobalState();
initWatchTeamId(fetchData);
</script>
<template>
  <div class="h-full w-full flex justify-between items-center">
    <div
      v-for="item in dataRef"
      :key="item.title"
      class="statistic-card shadow-lg hover:shadow-xl opacity-100 hover:opacity-90 hover:scale-105 transition-all duration-300"
      :style="`background: ${item.backgroundColor}`"
      @click="item.onClick"
    >
      <!-- 图标区域 -->
      <div class="icon-container">
        <el-icon class="card-icon" size="5vh">
          <component :is="item.icon" />
        </el-icon>
      </div>

      <!-- 标题和提示区域 -->
      <div class="flex justify-center items-center text-white mb-2">
        <span class="card-title">{{ item.title }}</span>
        <el-tooltip effect="dark" :content="item.tip" placement="top">
          <el-icon v-if="item.tip" class="ml-1" size="1.8vh">
            <Warning />
          </el-icon>
        </el-tooltip>
      </div>

      <!-- 数值区域 -->
      <div class="value-container">
        <ReNormalCountTo
          suffix=""
          :duration="1000"
          :color="item.textColor"
          :fontSize="'6vh'"
          :startVal="0"
          :endVal="item.value"
        />
      </div>

      <!-- 底部信息区域 -->
      <div class="statistic-footer" v-if="item.footerText">
        <div class="footer-item">
          <span class="text-gray-300">{{ item.footerText }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.statistic-card {
  height: 86%;
  aspect-ratio: 1.6/1;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  margin: 20px auto;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px 16px;
}

.icon-container {
  flex-shrink: 0;
  margin-top: 8px;
}

.card-icon {
  color: rgba(255, 255, 255, 0.9);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  transition: all 0.3s ease;
}

.statistic-card:hover .card-icon {
  color: rgba(255, 255, 255, 1);
  transform: scale(1.1);
}

.card-title {
  font-size: 2vh;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.value-container {
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.statistic-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.1);
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 1;
}

.statistic-card:hover::before {
  opacity: 1;
}

.statistic-card > * {
  position: relative;
  z-index: 2;
}

.statistic-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-top: 16px;
}

.statistic-footer .footer-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.statistic-footer .footer-item span:last-child {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}
</style>
