import{ae as B,d as v,aI as E,aa as N,s as I,f as P,Z as s,$ as d,h as m,r as b,j as k,k as x,l as i}from"./index-fbbdd03e.js";function z(){const{$storage:t,$config:e}=B(),a=()=>{E().multiTagsCache&&(!t.tags||t.tags.length===0)&&(t.tags=N),t.layout||(t.layout={layout:(e==null?void 0:e.Layout)??"vertical",theme:(e==null?void 0:e.Theme)??"default",darkMode:(e==null?void 0:e.DarkMode)??!1,sidebarStatus:(e==null?void 0:e.SidebarStatus)??!0,epThemeColor:(e==null?void 0:e.EpThemeColor)??"#409EFF"}),t.configure||(t.configure={grey:(e==null?void 0:e.Grey)??!1,weak:(e==null?void 0:e.Weak)??!1,hideTabs:(e==null?void 0:e.HideTabs)??!1,showLogo:(e==null?void 0:e.ShowLogo)??!0,showModel:(e==null?void 0:e.ShowModel)??"smart",multiTagsCache:(e==null?void 0:e.MultiTagsCache)??!1})},n=v(()=>t==null?void 0:t.layout.layout),u=v(()=>t.layout);return{layout:n,layoutTheme:u,initStorage:a}}const j=P({id:"pure-epTheme",state:()=>{var t,e;return{epThemeColor:((t=s().getItem(`${d()}layout`))==null?void 0:t.epThemeColor)??m().EpThemeColor,epTheme:((e=s().getItem(`${d()}layout`))==null?void 0:e.theme)??m().Theme}},getters:{getEpThemeColor(t){return t.epThemeColor},fill(t){return t.epTheme==="light"?"#409eff":t.epTheme==="yellow"?"#d25f00":"#fff"}},actions:{setEpThemeColor(t){const e=s().getItem(`${d()}layout`);this.epTheme=e==null?void 0:e.theme,this.epThemeColor=t,e&&(e.epThemeColor=t,s().setItem(`${d()}layout`,e))}}});function g(){return j(I)}const T={outputDir:"",defaultScopeName:"",includeStyleWithColors:[],extract:!0,themeLinkTagId:"theme-link-tag",themeLinkTagInjectTo:"head",removeCssScopeName:!1,customThemeCssFileName:null,arbitraryMode:!1,defaultPrimaryColor:"",customThemeOutputPath:"C:/Users/Administrator/PycharmProjects/WFGameAI/wfgame-ai-web/node_modules/.pnpm/@pureadmin+theme@3.0.0/node_modules/@pureadmin/theme/setCustomTheme.js",styleTagId:"custom-theme-tagid",InjectDefaultStyleTagToHtml:!0,hueDiffControls:{low:0,high:0},multipleScopeVars:[{scopeName:"layout-theme-default",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #001529 !default;
        $menuHover: #4091f7 !default;
        $subMenuBg: #0f0303 !default;
        $subMenuActiveBg: #4091f7 !default;
        $menuText: rgb(254 254 254 / 65%) !default;
        $sidebarLogo: #002140 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #4091f7 !default;
      `},{scopeName:"layout-theme-light",varsContent:`
        $subMenuActiveText: #409eff !default;
        $menuBg: #fff !default;
        $menuHover: #e0ebf6 !default;
        $subMenuBg: #fff !default;
        $subMenuActiveBg: #e0ebf6 !default;
        $menuText: #7a80b4 !default;
        $sidebarLogo: #fff !default;
        $menuTitleHover: #000 !default;
        $menuActiveBefore: #4091f7 !default;
      `},{scopeName:"layout-theme-dusk",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #2a0608 !default;
        $menuHover: #e13c39 !default;
        $subMenuBg: #000 !default;
        $subMenuActiveBg: #e13c39 !default;
        $menuText: rgb(254 254 254 / 65.1%) !default;
        $sidebarLogo: #42090c !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #e13c39 !default;
      `},{scopeName:"layout-theme-volcano",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #2b0e05 !default;
        $menuHover: #e85f33 !default;
        $subMenuBg: #0f0603 !default;
        $subMenuActiveBg: #e85f33 !default;
        $menuText: rgb(254 254 254 / 65%) !default;
        $sidebarLogo: #441708 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #e85f33 !default;
      `},{scopeName:"layout-theme-yellow",varsContent:`
        $subMenuActiveText: #d25f00 !default;
        $menuBg: #2b2503 !default;
        $menuHover: #f6da4d !default;
        $subMenuBg: #0f0603 !default;
        $subMenuActiveBg: #f6da4d !default;
        $menuText: rgb(254 254 254 / 65%) !default;
        $sidebarLogo: #443b05 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #f6da4d !default;
      `},{scopeName:"layout-theme-mingQing",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #032121 !default;
        $menuHover: #59bfc1 !default;
        $subMenuBg: #000 !default;
        $subMenuActiveBg: #59bfc1 !default;
        $menuText: #7a80b4 !default;
        $sidebarLogo: #053434 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #59bfc1 !default;
      `},{scopeName:"layout-theme-auroraGreen",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #0b1e15 !default;
        $menuHover: #60ac80 !default;
        $subMenuBg: #000 !default;
        $subMenuActiveBg: #60ac80 !default;
        $menuText: #7a80b4 !default;
        $sidebarLogo: #112f21 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #60ac80 !default;
      `},{scopeName:"layout-theme-pink",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #28081a !default;
        $menuHover: #d84493 !default;
        $subMenuBg: #000 !default;
        $subMenuActiveBg: #d84493 !default;
        $menuText: #7a80b4 !default;
        $sidebarLogo: #3f0d29 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #d84493 !default;
      `},{scopeName:"layout-theme-saucePurple",varsContent:`
        $subMenuActiveText: #fff !default;
        $menuBg: #130824 !default;
        $menuHover: #693ac9 !default;
        $subMenuBg: #000 !default;
        $subMenuActiveBg: #693ac9 !default;
        $menuText: #7a80b4 !default;
        $sidebarLogo: #1f0c38 !default;
        $menuTitleHover: #fff !default;
        $menuActiveBefore: #693ac9 !default;
      `}]},_="/static/dist/",D="assets";function A(t){let e=t.replace("#","").match(/../g);for(let a=0;a<3;a++)e[a]=parseInt(e[a],16);return e}function L(t,e,a){let n=[t.toString(16),e.toString(16),a.toString(16)];for(let u=0;u<3;u++)n[u].length==1&&(n[u]=`0${n[u]}`);return`#${n.join("")}`}function F(t,e){let a=A(t);for(let n=0;n<3;n++)a[n]=Math.floor(a[n]*(1-e));return L(a[0],a[1],a[2])}function G(t,e){let a=A(t);for(let n=0;n<3;n++)a[n]=Math.floor((255-a[n])*e+a[n]);return L(a[0],a[1],a[2])}function y(t){return`(^${t}\\s+|\\s+${t}\\s+|\\s+${t}$|^${t}$)`}function C({scopeName:t,multipleScopeVars:e}){const a=Array.isArray(e)&&e.length?e:T.multipleScopeVars;let n=document.documentElement.className;new RegExp(y(t)).test(n)||(a.forEach(u=>{n=n.replace(new RegExp(y(u.scopeName),"g"),` ${t} `)}),document.documentElement.className=n.replace(/(^\s+|\s+$)/g,""))}function M({id:t,href:e}){const a=document.createElement("link");return a.rel="stylesheet",a.href=e,a.id=t,a}function R(t){const e={scopeName:"theme-default",customLinkHref:r=>r,...t},a=e.themeLinkTagId||T.themeLinkTagId;let n=document.getElementById(a);const u=e.customLinkHref(`${_.replace(/\/$/,"")}${`/${D}/${e.scopeName}.css`.replace(/\/+(?=\/)/g,"")}`);if(n){n.id=`${a}_old`;const r=M({id:a,href:u});n.nextSibling?n.parentNode.insertBefore(r,n.nextSibling):n.parentNode.appendChild(r),r.onload=()=>{setTimeout(()=>{n.parentNode.removeChild(n),n=null},60),C(e)};return}n=M({id:a,href:u}),C(e),document[(e.themeLinkTagInjectTo||T.themeLinkTagInjectTo||"").replace("-prepend","")].appendChild(n)}function Z(){var $;const{layoutTheme:t,layout:e}=z(),a=b([{color:"#1b2a47",themeColor:"default"},{color:"#ffffff",themeColor:"light"},{color:"#f5222d",themeColor:"dusk"},{color:"#fa541c",themeColor:"volcano"},{color:"#fadb14",themeColor:"yellow"},{color:"#13c2c2",themeColor:"mingQing"},{color:"#52c41a",themeColor:"auroraGreen"},{color:"#eb2f96",themeColor:"pink"},{color:"#722ed1",themeColor:"saucePurple"}]),{$storage:n}=B(),u=b(($=n==null?void 0:n.layout)==null?void 0:$.darkMode),r=document.documentElement;function c(l=m().Theme??"default"){var o,f;if(t.value.theme=l,R({scopeName:`layout-theme-${l}`}),n.layout={layout:e.value,theme:l,darkMode:u.value,sidebarStatus:(o=n.layout)==null?void 0:o.sidebarStatus,epThemeColor:(f=n.layout)==null?void 0:f.epThemeColor},l==="default"||l==="light")h(m().EpThemeColor);else{const w=a.value.find(S=>S.themeColor===l);h(w.color)}}function p(l,o,f){document.documentElement.style.setProperty(`--el-color-primary-${l}-${o}`,u.value?F(f,o/10):G(f,o/10))}const h=l=>{g().setEpThemeColor(l),document.documentElement.style.setProperty("--el-color-primary",l);for(let o=1;o<=2;o++)p("dark",o,l);for(let o=1;o<=9;o++)p("light",o,l)};function H(){g().epTheme==="light"&&u.value?c("default"):c(g().epTheme),u.value?document.documentElement.classList.add("dark"):document.documentElement.classList.remove("dark")}return{body:r,dataTheme:u,layoutTheme:t,themeColors:a,dataThemeChange:H,setEpThemeColor:h,setLayoutThemeColor:c}}const W={xmlns:"http://www.w3.org/2000/svg",width:"16",height:"16",viewBox:"0 0 24 24"};function O(t,e){return k(),x("svg",W,[...e[0]||(e[0]=[i("path",{fill:"none",d:"M0 0h24v24H0z"},null,-1),i("path",{d:"M12 18a6 6 0 1 1 0-12 6 6 0 0 1 0 12M11 1h2v3h-2zm0 19h2v3h-2zM3.515 4.929l1.414-1.414L7.05 5.636 5.636 7.05zM16.95 18.364l1.414-1.414 2.121 2.121-1.414 1.414zm2.121-14.85 1.414 1.415-2.121 2.121-1.414-1.414 2.121-2.121zM5.636 16.95l1.414 1.414-2.121 2.121-1.414-1.414zM23 11v2h-3v-2zM4 11v2H1v-2z"},null,-1)])])}const q={render:O},Q={xmlns:"http://www.w3.org/2000/svg",width:"16",height:"16",viewBox:"0 0 24 24"};function V(t,e){return k(),x("svg",Q,[...e[0]||(e[0]=[i("path",{fill:"none",d:"M0 0h24v24H0z"},null,-1),i("path",{d:"M11.38 2.019a7.5 7.5 0 1 0 10.6 10.6C21.662 17.854 17.316 22 12.001 22 6.477 22 2 17.523 2 12c0-5.315 4.146-9.661 9.38-9.981"},null,-1)])])}const J={render:V};export{Z as a,J as b,z as c,q as d,R as t,g as u};
