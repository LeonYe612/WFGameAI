import { io, Socket } from "socket.io-client";

/**
 * 创建socket连接，支持断连重连、异常显示、事件监听
 * @param {object} param0
 * @param {string} param0.room 房间号
 * @param {object} [options] 事件回调配置
 * @returns {Socket}
 */
export function connectSocket(
  { room }: { room: string },
  options?: {
    onReplay?: (imgBase64: string) => void;
    onDisconnect?: () => void;
    onConnect?: () => void;
    onError?: (err: any) => void;
    onSysMsg?: (msg: string, payload: any) => void;
  }
) {
  // 复制一份options，确保闭包独立
  const optionsCopy = options ? { ...options } : undefined;
  const socket: Socket = io("ws://127.0.0.1:13838", {
    transports: ["websocket"],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    timeout: 8000
  });
  socket.on("connect", () => {
    socket.emit("join", { room });
    optionsCopy?.onConnect && optionsCopy.onConnect();
  });
  socket.on("disconnect", () => {
    optionsCopy?.onDisconnect && optionsCopy.onDisconnect();
  });
  socket.on("connect_error", err => {
    optionsCopy?.onError && optionsCopy.onError(err);
  });
  socket.on("reconnect_attempt", () => {
    // 可选：重连提示
  });
  socket.on("reconnect_failed", () => {
    optionsCopy?.onError && optionsCopy.onError("重连失败");
  });
  // 监听后端推送的replay事件（图片base64）
  socket.on("replay", payload => {
    // payload.data 为base64图片
    if (payload) {
      if (optionsCopy && typeof optionsCopy.onReplay === "function") {
        optionsCopy.onReplay(`${payload.data}`);
      }
    }
  });
  // 监听系统消息
  socket.on("sysMsg", payload => {
    if (optionsCopy?.onSysMsg) {
      optionsCopy.onSysMsg(payload?.msg || "", payload);
    }
  });
  return socket;
}
