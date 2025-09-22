import{p as I,d as M}from"./index-ccf167da.js";import{s as P}from"./scripts-d29b0ea0.js";import{s as T}from"./request-2aeceb02.js";import{m as W,r as x,a0 as A,A as r,O as H,j as _,u as V,I as t,l as i,z as s,B as d,y as C,x as w,P as L,k as S,F as G,p as K,aE as u,_ as Q}from"./index-fbbdd03e.js";import{s as X}from"./rules-318443ef.js";const Y={class:"script-create-content"},Z={class:"flex items-center"},h={class:"grid grid-cols-1 md:grid-cols-2 gap-4"},ee={class:"flex items-center justify-between"},te={class:"flex space-x-2"},se={class:"flex items-center justify-between"},le={class:"flex space-x-2"},oe={class:"flex justify-between items-center text-sm text-gray-500"},ae={class:"flex justify-end space-x-2"},N=`{
  "name": "新建脚本",
  "version": "1.0",
  "description": "请描述脚本功能",
  "steps": [
    {
      "action": "click",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "description": "点击坐标(100, 100)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`,ne=W({name:"ScriptCreateDialog",__name:"scriptCreateDialog",props:{categories:{}},emits:["created"],setup(ie,{expose:O,emit:J}){const j=J,c=x(!1),n=x(!1),m=x(),l=A({filename:"",category:"",description:"",content:""}),D=()=>{k(),c.value=!0},k=()=>{var a;Object.assign(l,{filename:"",category:"",description:"",content:N}),(a=m.value)==null||a.resetFields()},F=()=>{try{const a=JSON.parse(l.content);l.content=JSON.stringify(a,null,2),u("JSON格式化成功",{type:"success"})}catch{u("JSON格式错误，无法格式化",{type:"error"})}},z=async()=>{if(m.value)try{await m.value.validate();try{JSON.parse(l.content)}catch{u("JSON格式错误，请检查语法",{type:"error"});return}let a=l.filename.trim();a.endsWith(".json")||(a+=".json"),await T({apiFunc:P,apiParams:[a,l.content],enableSucceedMsg:!0,succeedMsgContent:"脚本创建成功！",onBeforeRequest:()=>{n.value=!0},onSucceed:()=>{j("created"),y()},onFailed:()=>{u("脚本创建失败",{type:"error"})},onCompleted:()=>{n.value=!1}})}catch(a){console.error("表单验证失败:",a)}},y=()=>{c.value=!1,k()},f=a=>{let e="";switch(a){case"click":e=`{
  "name": "点击脚本",
  "version": "1.0",
  "description": "点击指定坐标的脚本",
  "steps": [
    {
      "action": "click",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "description": "点击坐标(100, 100)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;break;case"input":e=`{
  "name": "输入脚本",
  "version": "1.0",
  "description": "输入文本的脚本",
  "steps": [
    {
      "action": "input",
      "target": {
        "type": "coordinate",
        "x": 100,
        "y": 100
      },
      "text": "Hello World",
      "description": "在坐标(100, 100)输入文本"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;break;case"swipe":e=`{
  "name": "滑动脚本",
  "version": "1.0",
  "description": "滑动操作的脚本",
  "steps": [
    {
      "action": "swipe",
      "start": {
        "x": 100,
        "y": 100
      },
      "end": {
        "x": 200,
        "y": 200
      },
      "duration": 1000,
      "description": "从(100, 100)滑动到(200, 200)"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;break;case"wait":e=`{
  "name": "等待脚本",
  "version": "1.0",
  "description": "等待指定时间的脚本",
  "steps": [
    {
      "action": "wait",
      "duration": 3000,
      "description": "等待3秒"
    }
  ],
  "settings": {
    "delay": 1000,
    "timeout": 30000
  }
}`;break;default:e=N}l.content=e,u(`已应用${a}模板`,{type:"success"})};return O({showDialog:D}),(a,e)=>{const B=r("el-icon"),b=r("el-input"),v=r("el-form-item"),R=r("el-option"),U=r("el-select"),g=r("el-card"),p=r("el-button"),$=r("el-form"),q=r("el-dialog"),E=H("loading");return _(),V(q,{modelValue:c.value,"onUpdate:modelValue":e[8]||(e[8]=o=>c.value=o),title:"新建脚本",width:"90%",draggable:!0,onClose:y},{footer:t(()=>[i("div",ae,[s(p,{onClick:y,disabled:n.value},{default:t(()=>[...e[20]||(e[20]=[d(" 取消 ",-1)])]),_:1},8,["disabled"]),s(p,{type:"primary",icon:w(I),loading:n.value,onClick:z},{default:t(()=>[d(C(n.value?"创建中...":"创建脚本"),1)]),_:1},8,["icon","loading"])])]),default:t(()=>[L((_(),S("div",Y,[s($,{ref_key:"formRef",ref:m,model:l,rules:w(X),"label-width":"100px",class:"create-form"},{default:t(()=>[s(g,{shadow:"never",class:"border mb-4"},{header:t(()=>[i("div",Z,[s(B,{class:"mr-2"},{default:t(()=>[s(w(M))]),_:1}),e[9]||(e[9]=i("span",{class:"font-medium"},"脚本信息",-1))])]),default:t(()=>[i("div",h,[s(v,{label:"脚本名称",prop:"filename"},{default:t(()=>[s(b,{modelValue:l.filename,"onUpdate:modelValue":e[0]||(e[0]=o=>l.filename=o),placeholder:"请输入脚本名称",disabled:n.value},{suffix:t(()=>[...e[10]||(e[10]=[d(".json",-1)])]),_:1},8,["modelValue","disabled"])]),_:1}),s(v,{label:"脚本分类",prop:"category"},{default:t(()=>[s(U,{modelValue:l.category,"onUpdate:modelValue":e[1]||(e[1]=o=>l.category=o),placeholder:"请选择分类（可选）",style:{width:"100%"},clearable:"",disabled:n.value},{default:t(()=>[(_(!0),S(G,null,K(a.categories,o=>(_(),V(R,{key:o.id,label:o.name,value:o.id},null,8,["label","value"]))),128))]),_:1},8,["modelValue","disabled"])]),_:1})]),s(v,{label:"脚本描述",prop:"description"},{default:t(()=>[s(b,{modelValue:l.description,"onUpdate:modelValue":e[2]||(e[2]=o=>l.description=o),type:"textarea",rows:2,placeholder:"请输入脚本描述（可选）",disabled:n.value},null,8,["modelValue","disabled"])]),_:1})]),_:1}),s(g,{shadow:"never",class:"border mb-4"},{header:t(()=>[i("div",ee,[e[15]||(e[15]=i("span",{class:"font-medium"},"脚本模板",-1)),i("div",te,[s(p,{size:"small",type:"primary",onClick:e[3]||(e[3]=o=>f("click")),disabled:n.value},{default:t(()=>[...e[11]||(e[11]=[d(" 点击模板 ",-1)])]),_:1},8,["disabled"]),s(p,{size:"small",type:"success",onClick:e[4]||(e[4]=o=>f("input")),disabled:n.value},{default:t(()=>[...e[12]||(e[12]=[d(" 输入模板 ",-1)])]),_:1},8,["disabled"]),s(p,{size:"small",type:"warning",onClick:e[5]||(e[5]=o=>f("swipe")),disabled:n.value},{default:t(()=>[...e[13]||(e[13]=[d(" 滑动模板 ",-1)])]),_:1},8,["disabled"]),s(p,{size:"small",type:"info",onClick:e[6]||(e[6]=o=>f("wait")),disabled:n.value},{default:t(()=>[...e[14]||(e[14]=[d(" 等待模板 ",-1)])]),_:1},8,["disabled"])])])]),default:t(()=>[e[16]||(e[16]=i("div",{class:"text-sm text-gray-600 mb-3"}," 选择一个模板快速开始，或者直接编辑下方的JSON内容 ",-1))]),_:1}),s(g,{shadow:"never",class:"border"},{header:t(()=>[i("div",se,[e[18]||(e[18]=i("span",{class:"font-medium"},"脚本内容",-1)),i("div",le,[s(p,{size:"small",type:"info",onClick:F,disabled:n.value},{default:t(()=>[...e[17]||(e[17]=[d(" 格式化JSON ",-1)])]),_:1},8,["disabled"])])])]),default:t(()=>[s(v,{prop:"content"},{default:t(()=>[s(b,{modelValue:l.content,"onUpdate:modelValue":e[7]||(e[7]=o=>l.content=o),type:"textarea",rows:20,placeholder:"请输入脚本内容（JSON格式）",class:"font-mono",disabled:n.value},null,8,["modelValue","disabled"])]),_:1}),i("div",oe,[i("span",null,"字符数: "+C(l.content.length),1),e[19]||(e[19]=i("span",{class:"text-blue-500"},[i("i",{class:"el-icon-info mr-1"}),d(" 请确保JSON格式正确 ")],-1))])]),_:1})]),_:1},8,["model","rules"])])),[[E,n.value]])]),_:1},8,["modelValue"])}}});const me=Q(ne,[["__scopeId","data-v-94951a10"]]);export{me as default};
