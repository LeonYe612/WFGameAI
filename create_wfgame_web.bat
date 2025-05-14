@echo off
echo 正在创建WFGame AI自动化测试平台前端资源...

REM 切换到项目根目录
cd /d C:\Users\Administrator\PycharmProjects\WFGameAI

REM 创建主文件夹和子文件夹
mkdir wfgame-ai-web
mkdir wfgame-ai-web\css
mkdir wfgame-ai-web\css\components
mkdir wfgame-ai-web\js
mkdir wfgame-ai-web\js\components
mkdir wfgame-ai-web\js\pages
mkdir wfgame-ai-web\images
mkdir wfgame-ai-web\images\icons
mkdir wfgame-ai-web\images\backgrounds
mkdir wfgame-ai-web\lib
mkdir wfgame-ai-web\lib\bootstrap
mkdir wfgame-ai-web\lib\bootstrap\css
mkdir wfgame-ai-web\lib\bootstrap\js
mkdir wfgame-ai-web\lib\fontawesome
mkdir wfgame-ai-web\lib\fontawesome\css
mkdir wfgame-ai-web\lib\echarts
mkdir wfgame-ai-web\templates
mkdir wfgame-ai-web\pages

REM 创建占位图像文件
echo 占位图像文件 > wfgame-ai-web\images\logo.png
echo 占位图像文件 > wfgame-ai-web\images\avatar.png
echo 占位图像文件 > wfgame-ai-web\images\favicon.ico
echo 占位图像文件 > wfgame-ai-web\images\backgrounds\login-bg.jpg

REM 创建占位库文件
echo 占位库文件 > wfgame-ai-web\lib\bootstrap\css\bootstrap.min.css
echo 占位库文件 > wfgame-ai-web\lib\bootstrap\js\bootstrap.bundle.min.js
echo 占位库文件 > wfgame-ai-web\lib\fontawesome\css\all.min.css
echo 占位库文件 > wfgame-ai-web\lib\echarts\echarts.min.js
echo 占位库文件 > wfgame-ai-web\lib\vue.min.js
echo 占位库文件 > wfgame-ai-web\lib\axios.min.js

REM 创建index.html
echo ^<!DOCTYPE html^> > wfgame-ai-web\index.html
echo ^<html lang="zh-CN"^> >> wfgame-ai-web\index.html
echo ^<head^> >> wfgame-ai-web\index.html
echo     ^<meta charset="UTF-8"^> >> wfgame-ai-web\index.html
echo     ^<meta name="viewport" content="width=device-width, initial-scale=1.0"^> >> wfgame-ai-web\index.html
echo     ^<title^>WFGame AI自动化测试平台^</title^> >> wfgame-ai-web\index.html
echo     ^<link rel="stylesheet" href="lib/bootstrap/css/bootstrap.min.css"^> >> wfgame-ai-web\index.html
echo     ^<link rel="stylesheet" href="lib/fontawesome/css/all.min.css"^> >> wfgame-ai-web\index.html
echo     ^<link rel="stylesheet" href="css/main.css"^> >> wfgame-ai-web\index.html
echo     ^<link rel="icon" href="images/favicon.ico"^> >> wfgame-ai-web\index.html
echo ^</head^> >> wfgame-ai-web\index.html
echo ^<body^> >> wfgame-ai-web\index.html
echo     ^<div id="app"^> >> wfgame-ai-web\index.html
echo         ^<div class="app-loading" v-if="loading"^> >> wfgame-ai-web\index.html
echo             ^<div class="spinner-border text-primary" role="status"^> >> wfgame-ai-web\index.html
echo                 ^<span class="visually-hidden"^>加载中...^</span^> >> wfgame-ai-web\index.html
echo             ^</div^> >> wfgame-ai-web\index.html
echo         ^</div^> >> wfgame-ai-web\index.html
echo         ^<div class="app-container" v-else^> >> wfgame-ai-web\index.html
echo             ^<!-- WFGame AI自动化测试平台主页 --^> >> wfgame-ai-web\index.html
echo             ^<p^>WFGame AI自动化测试平台已成功创建！^</p^> >> wfgame-ai-web\index.html
echo         ^</div^> >> wfgame-ai-web\index.html
echo     ^</div^> >> wfgame-ai-web\index.html
echo     ^<script src="lib/vue.min.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="lib/axios.min.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="lib/bootstrap/js/bootstrap.bundle.min.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="lib/echarts/echarts.min.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="js/pages/dashboard.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="js/api.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="js/router.js"^>^</script^> >> wfgame-ai-web\index.html
echo     ^<script src="js/main.js"^>^</script^> >> wfgame-ai-web\index.html
echo ^</body^> >> wfgame-ai-web\index.html
echo ^</html^> >> wfgame-ai-web\index.html

REM 创建login.html
echo ^<!DOCTYPE html^> > wfgame-ai-web\pages\login.html
echo ^<html lang="zh-CN"^> >> wfgame-ai-web\pages\login.html
echo ^<head^> >> wfgame-ai-web\pages\login.html
echo     ^<meta charset="UTF-8"^> >> wfgame-ai-web\pages\login.html
echo     ^<title^>登录 - WFGame AI自动化测试平台^</title^> >> wfgame-ai-web\pages\login.html
echo ^</head^> >> wfgame-ai-web\pages\login.html
echo ^<body class="login-page"^> >> wfgame-ai-web\pages\login.html
echo     ^<h1^>WFGame AI自动化测试平台登录页^</h1^> >> wfgame-ai-web\pages\login.html
echo ^</body^> >> wfgame-ai-web\pages\login.html
echo ^</html^> >> wfgame-ai-web\pages\login.html

REM 创建CSS文件
echo /* 主样式文件 */ > wfgame-ai-web\css\main.css
echo body { font-family: 'stheitimedium', sans-serif; } >> wfgame-ai-web\css\main.css

echo /* 登录页面样式 */ > wfgame-ai-web\css\login.css
echo body.login-page { background-color: #f5f7fa; } >> wfgame-ai-web\css\login.css

echo /* 仪表盘组件样式 */ > wfgame-ai-web\css\components\dashboard.css
echo .stat-card { display: flex; } >> wfgame-ai-web\css\components\dashboard.css

REM 创建JS文件
echo // 主应用脚本 > wfgame-ai-web\js\main.js
echo const app = new Vue({ el: '#app', data: { loading: false } }); >> wfgame-ai-web\js\main.js

echo // 路由控制脚本 > wfgame-ai-web\js\router.js

echo // API调用服务 > wfgame-ai-web\js\api.js

echo // 仪表盘组件 > wfgame-ai-web\js\pages\dashboard.js
echo const Dashboard = { template: '<div>仪表盘</div>' }; >> wfgame-ai-web\js\pages\dashboard.js

echo 文件和文件夹创建完成！
echo 所有前端资源已创建在目录：C:\Users\Administrator\PycharmProjects\WFGameAI\wfgame-ai-web
echo 请通过浏览器打开index.html查看系统主页