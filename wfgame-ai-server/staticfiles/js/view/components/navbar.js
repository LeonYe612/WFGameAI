const { ref, onMounted } = Vue;

console.log("Navbar component loaded");

// 获取 cookie
function getCookie(name) {
  const cookies = document.cookie.split(";");
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split("=");
    if (key === name) return value;
  }
  return null;
}

// 获取用户信息
function getUserInfo() {
  const username = getCookie("username") || "Guest";
  return { username };
}

// 导航菜单项数据
const navItems = [
  { href: "/pages/dashboard_template.html", icon: "fas fa-tachometer-alt", text: "控制台" },
  { href: "/pages/devices.html", icon: "fas fa-mobile-alt", text: "设备管理" },
  { href: "/pages/scripts.html", icon: "fas fa-code", text: "脚本管理" },
  { href: "/pages/ocr_template.html", icon: "fas fa-file-alt", text: "OCR识别" },
  { href: "/pages/tasks_template.html", icon: "fas fa-tasks", text: "任务管理" },
  { href: "/pages/reports_template.html", icon: "fas fa-chart-bar", text: "测试报告" },
  { href: "/pages/data_template.html", icon: "fas fa-database", text: "数据管理" },
  { href: "/pages/settings_template.html", icon: "fas fa-cog", text: "系统设置" },
];

export default {
  name: "Navbar",
  setup() {
    const username = ref("Guest");
    const showLogout = ref(false);

    // 初始化用户信息
    const initUserInfo = () => {
      const info = getUserInfo();
      username.value = info.username;
    };

    // 注销逻辑
    const logout = async () => {
      try {
        const res = await fetch("/api/users/logout/", { method: "GET" });
        if (res.ok) {
          username.value = "Guest";
          alert("用户已注销登录！");
        } else {
          alert("注销失败");
        }
      } catch {
        alert("注销失败");
      }
      showLogout.value = false;
    };

    onMounted(() => {
      initUserInfo();
    });

    return {
      username,
      showLogout,
      logout,
      navItems, // 暴露菜单项
    };
  },
  template: `
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
      <div class="container-fluid">
        <a class="navbar-brand" href="/">WFGame AI</a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item" v-for="item in navItems" :key="item.href">
              <a class="nav-link" :href="item.href">
                <i :class="item.icon"></i> {{ item.text }}
              </a>
            </li>
          </ul>
          <div
            class="user-info"
            :style="{
              width: '120px',
              textAlign: 'center',
              marginLeft: 'auto',
              cursor: 'pointer',
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '40px',
              borderRadius: '8px',
              transition: 'background 0.2s',
              color: username === 'Guest' ? 'orange' : '#19a700ff'
            }"
            @mouseenter="showLogout = true"
            @mouseleave="showLogout = false"
          >
            {{ username }}
            <div
              class="logout-menu"
              v-show="showLogout && username !== 'Guest'"
              style="
                position: absolute;
                top: 100%;
                left: 50%;
                transform: translateX(-50%);
                background: #fff;
                border: 1px solid #ddd;
                border-radius: 6px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 6px 18px;
                z-index: 100;
                font-size: 15px;
                color: #333;
                cursor: pointer;
              "
              @click="logout"
            >
              注销
            </div>
          </div>
        </div>
      </div>
    </nav>
  `,
};
