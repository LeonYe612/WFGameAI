import{aE as u,ad as m}from"./index-fbbdd03e.js";const h=e=>{const a=e.toString().match(/baseUrlApi\("(.*?)"\)/);return a&&a[1]?a[1]:""},v=async e=>{var s,o,c;const{apiParams:r={},enableSucceedMsg:a=!1,succeedMsgContent:l="操作成功",enableFailedMsg:f=!0,enableErrorMsg:g=!0}=e;let t;typeof e.onBeforeRequest=="function"&&e.onBeforeRequest();try{const{code:i=-1,msg:n="error",data:d=null}=await e.apiFunc(r);return i===0?(t={code:i,msg:n,data:d},a&&u(`${l}`,{type:"success"}),typeof e.onSucceed=="function"&&e.onSucceed(t.data),t):(t={code:i,msg:n,data:d},typeof e.onFailed=="function"&&e.onFailed(t.data,t.msg),f&&u(t.msg,{type:"error"}),t)}catch(i){let n;return((s=i==null?void 0:i.response)==null?void 0:s.status)!==200?n=((c=(o=i.response)==null?void 0:o.data)==null?void 0:c.msg)??i:n=i,t={code:-1,msg:"error",data:null},g&&m({title:"请求出错啦！😡",dangerouslyUseHTMLString:!0,message:`
          <h4>🔸 错误代码</h4>
          <div><i>code：${t.code}</i></div>
          <h4>🔸 错误信息</h4>
          <div><i>${n}</i></div>
          <h4>🔸 接口函数</h4>
          <div><i>${e.apiFunc.name}</i></div>
          <h4>🔸 接口路由</h4>
          <div><i>${h(e.apiFunc)}</i></div>
          <h4>🔸 请求参数</h4>
          <div><i>${JSON.stringify(r)}</i></div>
          `,type:"error"}),t}finally{typeof e.onCompleted=="function"&&e.onCompleted(t)}};export{v as s};
