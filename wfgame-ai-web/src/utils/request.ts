import { ApiResult } from "@/api/utils";
import { AxiosError } from "axios";
import { message } from "./message";
import { ElNotification } from "element-plus";

// 此函数弃用，使用下方的 superRequest 函数
export const requestHook = async (fn: Promise<ApiResult>) => {
  try {
    const { code, msg, data } = await fn;
    if (code !== 0) {
      message(msg, { type: "error" });
      return;
    }
    return { code: code, msg: msg, data: data };
  } catch (e) {
    if ((e as AxiosError)?.response?.status !== 200) {
      const msg = e.response?.data?.msg ?? e;
      message(msg, { type: "error" });
    } else {
      message(e, { type: "error" });
    }
    return {
      code: -1,
      msg: "error",
      data: null
    };
  }
};
export const extractApiUrlFromApiFunction = (fn: Function) => {
  const fnString = fn.toString();
  const match = fnString.match(/baseUrlApi\("(.*?)"\)/);
  if (match && match[1]) {
    return match[1]; // 返回匹配到的参数值
  } else {
    return ""; // 如果未匹配到，返回 null 或者其他指定的值
  }
};

export const superRequest = async (props: {
  apiFunc: Function;
  apiParams?: Object;
  onBeforeRequest?: Function; // 发送请求前回调函数
  onSucceed?: Function; // 请求成功回调函数
  onFailed?: Function; // 请求失败回调函数
  onCompleted?: Function; // 请求完成回调函数
  enableSucceedMsg?: Boolean; // 开启请求成功消息通知
  succeedMsgContent?: String; // 成功消息通知内容
  enableFailedMsg?: Boolean; // 开启请求失败消息通知
  enableErrorMsg?: Boolean; // 开启请求失败消息通知
}) => {
  // 设置默认值
  const {
    apiParams = {},
    enableSucceedMsg = false, // 默认为 false
    succeedMsgContent = "操作成功", // 默认消息内容为 'Success'
    enableFailedMsg = true,
    enableErrorMsg = true
  } = props;
  // 响应内容
  let response;
  typeof props.onBeforeRequest === "function" && props.onBeforeRequest();
  try {
    const {
      code = -1,
      msg = "error",
      data = null
    } = await props.apiFunc(apiParams);
    if (code === 0) {
      // ===== a. 请求成功 ======
      response = { code: code, msg: msg, data: data };
      if (enableSucceedMsg) {
        message(`${succeedMsgContent}`, { type: "success" });
      }
      typeof props.onSucceed === "function" && props.onSucceed(response.data);
      return response;
    } else {
      // ===== b. 请求失败 ======
      response = { code: code, msg: msg, data: data };
      typeof props.onFailed === "function" &&
        props.onFailed(response.data, response.msg);
      if (enableFailedMsg) {
        message(response.msg, { type: "error" });
        // ElNotification({
        //   title: `请求失败啦！🤡`,
        //   dangerouslyUseHTMLString: true,
        //   message: `
        //   <h4>🔸 错误代码</h4>
        //   <div><i>code：${response.code}</i></div>
        //   <h4>🔸 错误信息</h4>
        //   <div><i>${response.msg}</i></div>
        //   <h4>🔸 接口函数</h4>
        //   <div><i>${props.apiFunc.name}</i></div>
        //   <h4>🔸 接口路由</h4>
        //   <div><i>${extractApiUrlFromApiFunction(props.apiFunc)}</i></div>
        //   <h4>🔸 请求参数</h4>
        //   <div><i>${JSON.stringify(apiParams)}</i></div>
        //   `,
        //   type: "error"
        // });
      }
      return response;
    }
  } catch (e) {
    // ===== c. 请求异常 ======
    let errorMsg;
    if ((e as AxiosError)?.response?.status !== 200) {
      // 接口请求异常
      errorMsg = e.response?.data?.msg ?? e;
    } else {
      // 代码执行异常
      errorMsg = e;
    }
    response = { code: -1, msg: "error", data: null };
    if (enableErrorMsg) {
      ElNotification({
        title: `请求出错啦！😡`,
        dangerouslyUseHTMLString: true,
        message: `
          <h4>🔸 错误代码</h4>
          <div><i>code：${response.code}</i></div>
          <h4>🔸 错误信息</h4>
          <div><i>${errorMsg}</i></div>
          <h4>🔸 接口函数</h4>
          <div><i>${props.apiFunc.name}</i></div>
          <h4>🔸 接口路由</h4>
          <div><i>${extractApiUrlFromApiFunction(props.apiFunc)}</i></div>
          <h4>🔸 请求参数</h4>
          <div><i>${JSON.stringify(apiParams)}</i></div>
          `,
        type: "error"
      });
    }
    return response;
  } finally {
    typeof props.onCompleted === "function" && props.onCompleted(response);
  }
};
