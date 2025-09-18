export const getCookie = (name) => {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [key, value] = cookie.trim().split('=');
      if (key === name) return value;
    }
    return null;
  };

export const getUserInfo = () => {
  const username = getCookie("username") || "Guest";
  return { username };
};

  // 响应注销后的UI更新
export const handleLogoutSuccess = (userDiv) => {
  userDiv.textContent = "Guest";
  userDiv.style.color = "orange";
  alert("用户已注销登录！");
};

export const initUserInfo = () => {
  const userInfo = getUserInfo();
  const navbar = document.querySelector("nav.navbar");
  if (navbar) {
    // 创建用户信息容器
    const userDiv = document.createElement("div");
    userDiv.className = "user-info";
    userDiv.style.width = "120px";
    userDiv.style.textAlign = "center";
    userDiv.style.marginLeft = "auto";
    userDiv.style.cursor = "pointer";
    userDiv.style.position = "relative";
    userDiv.style.display = "flex";
    userDiv.style.alignItems = "center";
    userDiv.style.justifyContent = "center";
    userDiv.style.height = "40px";
    userDiv.style.borderRadius = "8px";
    userDiv.style.transition = "background 0.2s";

    // 设置颜色
    if (userInfo.username === "Guest") {
      userDiv.style.color = "orange";
    } else {
      userDiv.style.color = "#19a700ff"; // 亮绿色
    }
    userDiv.textContent = `${userInfo.username}`;

    // 创建注销菜单
    const menuDiv = document.createElement("div");
    menuDiv.className = "logout-menu";
    menuDiv.style.display = "none";
    menuDiv.style.position = "absolute";
    menuDiv.style.top = "100%";
    menuDiv.style.left = "50%";
    menuDiv.style.transform = "translateX(-50%)";
    menuDiv.style.background = "#fff";
    menuDiv.style.border = "1px solid #ddd";
    menuDiv.style.borderRadius = "6px";
    menuDiv.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)";
    menuDiv.style.padding = "6px 18px";
    menuDiv.style.zIndex = "100";
    menuDiv.style.fontSize = "15px";
    menuDiv.style.color = "#333";

    menuDiv.textContent = "注销";
    menuDiv.style.cursor = "pointer";

    // hover 显示菜单
    userDiv.addEventListener("mouseenter", () => {
      menuDiv.style.display = "block";
      userDiv.style.background = "#f0f0f0";
    });
    userDiv.addEventListener("mouseleave", () => {
      menuDiv.style.display = "none";
      userDiv.style.background = "";
    });

    // 点击注销
    menuDiv.addEventListener("click", () => {
      fetch("/api/users/logout", {
        method: "GET",
      }).then((res) => {
        if (res.ok) {
          handleLogoutSuccess(userDiv);
        } else {
          alert("注销失败");
        }
      });
    });

    userDiv.appendChild(menuDiv);
    navbar.appendChild(userDiv);
  }
};
