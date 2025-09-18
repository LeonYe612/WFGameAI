import{p as H,d as M}from"./index-8ca571cf.js";import{s as T}from"./scripts-e54598c6.js";import{s as W}from"./request-d2ecd641.js";import{l as A,r as h,$ as E,z as d,N as L,h as b,q as V,H as t,k as i,y as s,A as r,x as C,v as k,O as P,j as N,F as G,m as K,aF as p,ah as Q,ai as X,_ as Y}from"./index-e046f3d2.js";import{s as Z}from"./rules-926a8b3c.js";const u=m=>(Q("data-v-94951a10"),m=m(),X(),m),ee={class:"script-create-content"},te={class:"flex items-center"},se=u(()=>i("span",{class:"font-medium"},"脚本信息",-1)),ae={class:"grid grid-cols-1 md:grid-cols-2 gap-4"},oe={class:"flex items-center justify-between"},le=u(()=>i("span",{class:"font-medium"},"脚本模板",-1)),ne={class:"flex space-x-2"},ie=u(()=>i("div",{class:"text-sm text-gray-600 mb-3"}," 选择一个模板快速开始，或者直接编辑下方的JSON内容 ",-1)),de={class:"flex items-center justify-between"},re=u(()=>i("span",{class:"font-medium"},"脚本内容",-1)),ce={class:"flex space-x-2"},pe={class:"flex justify-between items-center text-sm text-gray-500"},ue=u(()=>i("span",{class:"text-blue-500"},[i("i",{class:"el-icon-info mr-1"}),r(" 请确保JSON格式正确 ")],-1)),me={class:"flex justify-end space-x-2"},O=`{
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
}`,_e=A({name:"ScriptCreateDialog",__name:"scriptCreateDialog",props:{categories:{}},emits:["created"],setup(m,{expose:J,emit:j}){const _=h(!1),n=h(!1),f=h(),a=E({filename:"",category:"",description:"",content:""}),D=()=>{S(),_.value=!0},S=()=>{var l;Object.assign(a,{filename:"",category:"",description:"",content:O}),(l=f.value)==null||l.resetFields()},F=()=>{try{const l=JSON.parse(a.content);a.content=JSON.stringify(l,null,2),p("JSON格式化成功",{type:"success"})}catch{p("JSON格式错误，无法格式化",{type:"error"})}},z=async()=>{if(f.value)try{await f.value.validate();try{JSON.parse(a.content)}catch{p("JSON格式错误，请检查语法",{type:"error"});return}let l=a.filename.trim();l.endsWith(".json")||(l+=".json"),await W({apiFunc:T,apiParams:[l,a.content],enableSucceedMsg:!0,succeedMsgContent:"脚本创建成功！",onBeforeRequest:()=>{n.value=!0},onSucceed:()=>{j("created"),g()},onFailed:()=>{p("脚本创建失败",{type:"error"})},onCompleted:()=>{n.value=!1}})}catch(l){console.error("表单验证失败:",l)}},g=()=>{_.value=!1,S()},v=l=>{let e="";switch(l){case"click":e=`{
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
}`;break;default:e=O}a.content=e,p(`已应用${l}模板`,{type:"success"})};return J({showDialog:D}),(l,e)=>{const $=d("el-icon"),x=d("el-input"),y=d("el-form-item"),B=d("el-option"),R=d("el-select"),w=d("el-card"),c=d("el-button"),U=d("el-form"),I=d("el-dialog"),q=L("loading");return b(),V(I,{modelValue:_.value,"onUpdate:modelValue":e[8]||(e[8]=o=>_.value=o),title:"新建脚本",width:"90%",draggable:!0,onClose:g},{footer:t(()=>[i("div",me,[s(c,{onClick:g,disabled:n.value},{default:t(()=>[r(" 取消 ")]),_:1},8,["disabled"]),s(c,{type:"primary",icon:k(H),loading:n.value,onClick:z},{default:t(()=>[r(C(n.value?"创建中...":"创建脚本"),1)]),_:1},8,["icon","loading"])])]),default:t(()=>[P((b(),N("div",ee,[s(U,{ref_key:"formRef",ref:f,model:a,rules:k(Z),"label-width":"100px",class:"create-form"},{default:t(()=>[s(w,{shadow:"never",class:"border mb-4"},{header:t(()=>[i("div",te,[s($,{class:"mr-2"},{default:t(()=>[s(k(M))]),_:1}),se])]),default:t(()=>[i("div",ae,[s(y,{label:"脚本名称",prop:"filename"},{default:t(()=>[s(x,{modelValue:a.filename,"onUpdate:modelValue":e[0]||(e[0]=o=>a.filename=o),placeholder:"请输入脚本名称",disabled:n.value},{suffix:t(()=>[r(".json")]),_:1},8,["modelValue","disabled"])]),_:1}),s(y,{label:"脚本分类",prop:"category"},{default:t(()=>[s(R,{modelValue:a.category,"onUpdate:modelValue":e[1]||(e[1]=o=>a.category=o),placeholder:"请选择分类（可选）",style:{width:"100%"},clearable:"",disabled:n.value},{default:t(()=>[(b(!0),N(G,null,K(l.categories,o=>(b(),V(B,{key:o.id,label:o.name,value:o.id},null,8,["label","value"]))),128))]),_:1},8,["modelValue","disabled"])]),_:1})]),s(y,{label:"脚本描述",prop:"description"},{default:t(()=>[s(x,{modelValue:a.description,"onUpdate:modelValue":e[2]||(e[2]=o=>a.description=o),type:"textarea",rows:2,placeholder:"请输入脚本描述（可选）",disabled:n.value},null,8,["modelValue","disabled"])]),_:1})]),_:1}),s(w,{shadow:"never",class:"border mb-4"},{header:t(()=>[i("div",oe,[le,i("div",ne,[s(c,{size:"small",type:"primary",onClick:e[3]||(e[3]=o=>v("click")),disabled:n.value},{default:t(()=>[r(" 点击模板 ")]),_:1},8,["disabled"]),s(c,{size:"small",type:"success",onClick:e[4]||(e[4]=o=>v("input")),disabled:n.value},{default:t(()=>[r(" 输入模板 ")]),_:1},8,["disabled"]),s(c,{size:"small",type:"warning",onClick:e[5]||(e[5]=o=>v("swipe")),disabled:n.value},{default:t(()=>[r(" 滑动模板 ")]),_:1},8,["disabled"]),s(c,{size:"small",type:"info",onClick:e[6]||(e[6]=o=>v("wait")),disabled:n.value},{default:t(()=>[r(" 等待模板 ")]),_:1},8,["disabled"])])])]),default:t(()=>[ie]),_:1}),s(w,{shadow:"never",class:"border"},{header:t(()=>[i("div",de,[re,i("div",ce,[s(c,{size:"small",type:"info",onClick:F,disabled:n.value},{default:t(()=>[r(" 格式化JSON ")]),_:1},8,["disabled"])])])]),default:t(()=>[s(y,{prop:"content"},{default:t(()=>[s(x,{modelValue:a.content,"onUpdate:modelValue":e[7]||(e[7]=o=>a.content=o),type:"textarea",rows:20,placeholder:"请输入脚本内容（JSON格式）",class:"font-mono",disabled:n.value},null,8,["modelValue","disabled"])]),_:1}),i("div",pe,[i("span",null,"字符数: "+C(a.content.length),1),ue])]),_:1})]),_:1},8,["model","rules"])])),[[q,n.value]])]),_:1},8,["modelValue"])}}});const xe=Y(_e,[["__scopeId","data-v-94951a10"]]);export{xe as default};
