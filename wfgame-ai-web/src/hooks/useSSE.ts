import { ref, onUnmounted, readonly } from "vue";
import { message } from "@/utils/message";

// 定义事件处理函数的类型
type EventHandler<T = any> = (data: T) => void;

// 定义所有事件监听器的集合类型
// 键是事件名 (如 'message', 'broadcast')，值是该事件的处理函数数组
type Listeners = {
  [event: string]: EventHandler[];
};

// 连接状态的枚举
export enum SSEState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSED = 2
}

export enum ServerEvent {
  MESSAGE = "message", // 私信消息
  BROADCAST = "broadcast", // 广播消息
  CONNECTION_ESTABLISHED = "connection_established", // 连接建立确认
  HEARTBEAT = "heartbeat", // 心跳
  NOTIFICATION = "notification" // 通用弹窗消息
}

// --- 模块级变量，确保全局只有一个 EventSource 实例和监听器集合 ---

// EventSource 实例的引用
let eventSource: EventSource | null = null;

// 所有组件注册的事件监听器
const listeners: Listeners = {};

// 待处理的事件监听器，用于在 SSE 连接建立前缓存
const pendingListeners = new Set<string>();

// 响应式的连接状态
const connectionState = ref<SSEState>(SSEState.CLOSED);

// SSE 连接的 URL，请根据你的项目配置修改
const SSE_URL = "/api/notifications/stream/";

/**
 * 初始化并管理全局唯一的 SSE 连接。
 * 这个函数只应在应用的主入口（如 App.vue）调用一次。
 */
const connect = () => {
  // 如果已经连接或正在连接，则不执行任何操作
  if (eventSource && eventSource.readyState !== EventSource.CLOSED) {
    return;
  }

  try {
    eventSource = new EventSource(SSE_URL, { withCredentials: true });
    connectionState.value = SSEState.CONNECTING;

    eventSource.onopen = () => {
      connectionState.value = SSEState.OPEN;
      console.log("SSE connection established.");
    };

    eventSource.onerror = error => {
      console.error("SSE connection error:", error);
      connectionState.value = SSEState.CLOSED;
      eventSource?.close(); // 关闭实例，稍后可能会自动重连
      message("⚠️ 与服务端的 SSE 通信出现错误，请检查网络或稍后重试。", {
        type: "error"
      });
    };

    // 这个 onmessage 用于捕获所有没有 'event:' 字段的默认消息
    // 在我们的后端实现中，这个通常不会被用到，但最好有
    eventSource.onmessage = event => {
      console.log("Received default SSE message:", event.data);
    };

    // 监听后端发送的 'connection_established' 事件
    eventSource.addEventListener(ServerEvent.CONNECTION_ESTABLISHED, _event => {
      message("🔔 与服务端的 SSE 通信已连接！", { type: "success" });
      // 连接成功后，处理所有在连接前注册的事件
      pendingListeners.forEach(eventName => {
        addServerEventListener(eventName);
      });
      pendingListeners.clear(); // 清空待处理列表
    });

    // 监听后端发送的 'heartbeat' 事件
    eventSource.addEventListener(ServerEvent.HEARTBEAT, () => {
      // console.log('SSE heartbeat received.'); // 通常不需要打印心跳日志
    });
  } catch (error) {
    console.error("Failed to create EventSource:", error);
    connectionState.value = SSEState.CLOSED;
  }
};

/**
 * 关闭 SSE 连接并清空所有监听器。
 */
const disconnect = () => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
    connectionState.value = SSEState.CLOSED;
    // 清空所有事件的监听器数组
    Object.keys(listeners).forEach(event => {
      listeners[event] = [];
    });
    console.log("SSE connection closed.");
  }
};

/**
 * 动态地为 EventSource 实例添加事件监听器。
 * @param eventName 事件名称
 */
const addServerEventListener = (eventName: string) => {
  // 如果 EventSource 实例存在并且连接已打开，则直接添加监听器
  if (eventSource && eventSource.readyState === EventSource.OPEN) {
    eventSource.addEventListener(eventName, event => {
      // 检查该事件是否有注册的处理器
      if (listeners[eventName] && listeners[eventName].length > 0) {
        try {
          // 后端发送的数据是 JSON 字符串，需要解析
          const data = JSON.parse((event as MessageEvent).data);
          // 调用所有为该事件注册的处理函数
          listeners[eventName].forEach(handler => handler(data));
        } catch (e) {
          console.error(`Error parsing SSE data for event '${eventName}':`, e);
        }
      }
    });
  } else {
    // 否则，将事件名加入待处理队列
    pendingListeners.add(eventName);
  }
};

/**
 * Vue Composable - 用于在组件中使用 SSE。
 * @returns on: 用于注册事件监听器的函数
 * @returns connectionState: 只读的连接状态
 */
export function useSSE() {
  /**
   * 注册一个事件监听器。
   * @param event 事件名称 (例如 'message', 'broadcast')
   * @param handler 事件处理函数
   */
  const on = <T>(event: string, handler: EventHandler<T>) => {
    // 如果这是第一次监听此事件，为 EventSource 创建一个 addEventListener
    if (!listeners[event]) {
      listeners[event] = [];
      addServerEventListener(event);
    }
    listeners[event].push(handler);

    // 当组件卸载时，自动移除这个监听器，防止内存泄漏
    onUnmounted(() => {
      off(event, handler);
    });
  };

  /**
   * 移除一个事件监听器。
   * @param event 事件名称
   * @param handler 事件处理函数
   */
  const off = <T>(event: string, handler: EventHandler<T>) => {
    if (listeners[event]) {
      const index = listeners[event].indexOf(handler);
      if (index > -1) {
        listeners[event].splice(index, 1);
      }
    }
  };

  return {
    on,
    connectionState: readonly(connectionState) // 提供只读的状态
  };
}

// 导出连接和断开函数，以便在应用根组件中控制
export { connect, disconnect };
