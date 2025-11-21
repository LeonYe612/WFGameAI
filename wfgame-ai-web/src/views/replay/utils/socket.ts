import { io, Socket } from "socket.io-client";

// 房间级 socket 缓存与事件多路复用
const ROOM_SOCKET_CACHE: Record<string, Socket> = {};
const ROOM_EVENT_HANDLERS: Record<string, Record<string, Set<Function>>> = {};

export function connectSocket(
    { room }: { room: string },
    options?: {
        onFrame?: (imgBase64: string) => void;
        onDisconnect?: () => void;
        onConnect?: () => void;
        onError?: (err: any) => void;
        onSysMsg?: (msg: string, payload: any) => void;
        onStep?: (payload: any) => void;
        onProgress?: (payload: any) => void;
    }
): Socket {
    const optionsCopy = options ? { ...options } : undefined;
    const { VITE_WSS_URL, VITE_WSS_PORT, VITE_VITE_WSS_URL, VITE_VITE_WSS_PORT } = (import.meta as any).env || {};
    const host = String(VITE_WSS_URL || VITE_VITE_WSS_URL || "").trim();
    const port = String(VITE_WSS_PORT || VITE_VITE_WSS_PORT || "").trim();
    const proto =
        typeof window !== "undefined" && window.location?.protocol === "https:"
            ? "wss"
            : "ws";
    let endpoint = "";
    if (/^wss?:\/\//i.test(host)) {
        endpoint = host;
    } else if (host) {
        endpoint = `${proto}://${host}${port ? `:${port}` : ""}`;
    } else {
        const h = window.location?.hostname || "127.0.0.1";
        const p = window.location?.port ? `:${window.location.port}` : "";
        endpoint = `${proto}://${h}${p}`;
    }
    if (ROOM_SOCKET_CACHE[room]) {
        const existing = ROOM_SOCKET_CACHE[room];
        if (optionsCopy) attachRoomHandlers(existing, room, optionsCopy);
        // 检查缓存的 socket 是否已断开，若是则重连
        if (existing.disconnected) {
            existing.connect();
        } else {
            // 若已连接，确保加入房间并触发 onConnect 回调
            existing.emit("join", { room });
            optionsCopy?.onConnect && optionsCopy.onConnect();
        }
        return existing;
    }
    const socket: Socket = io(endpoint, {
        transports: ["websocket"],
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 1000,
        timeout: 8000
    });
    ROOM_SOCKET_CACHE[room] = socket;
    ROOM_EVENT_HANDLERS[room] = ROOM_EVENT_HANDLERS[room] || {};
    socket.on("connect", () => {
        socket.emit("join", { room });
        optionsCopy?.onConnect && optionsCopy.onConnect();
    });
    socket.on(
        "disconnect",
        () => optionsCopy?.onDisconnect && optionsCopy.onDisconnect()
    );
    socket.on(
        "connect_error",
        err => optionsCopy?.onError && optionsCopy.onError(err)
    );
    socket.on(
        "reconnect_failed",
        () => optionsCopy?.onError && optionsCopy.onError("重连失败")
    );
    // 移除全局 onAny 调试日志

    socket.on("frame", payload => {
        const ts = Date.now();
        let base64Candidate: any = null;
        if (payload && (payload.data || typeof payload === "string")) {
            base64Candidate = payload.data || payload;
        }
        if (typeof base64Candidate === 'string') {
            triggerRoomHandlers(room, "frame", base64Candidate);
        }
    });
    socket.on("sysMsg", payload => {
        triggerRoomHandlers(room, "sysMsg", payload);
    });
    // 直接监听服务端的 progress 事件（HTTP emit: event="progress"）
    socket.on("progress", payload => {
        // 兼容 SocketResponse 包裹或直传 data
        let raw: any = payload;
        if (raw && typeof raw === "object" && "data" in raw && (raw as any).data != null) {
            raw = (raw as any).data;
        }
        triggerRoomHandlers(room, "progress", raw);
    });
    socket.on("step", payload => {
        let raw = payload;
        if (raw && typeof raw === "object" && "data" in raw && raw.data && typeof raw.data === "object") {
            const d = (raw as any).data;
            if ("step_index" in d || "script" in d || "status" in d) {
                raw = d;
            }
        }
        triggerRoomHandlers(room, "step", raw);
    });
    socket.on("error", payload => {
        triggerRoomHandlers(room, "error", payload);
    });
    if (optionsCopy) attachRoomHandlers(socket, room, optionsCopy);
    return socket;
}

function attachRoomHandlers(socket: Socket, room: string, options: {
    onFrame?: (imgBase64: string) => void;
    onDisconnect?: () => void;
    onConnect?: () => void;
    onError?: (err: any) => void;
    onSysMsg?: (msg: string, payload: any) => void;
    onStep?: (payload: any) => void;
    onProgress?: (payload: any) => void;
}): void {
    const map = (ROOM_EVENT_HANDLERS[room] = ROOM_EVENT_HANDLERS[room] || {});
    const register = (evt: string, fn: Function | undefined) => {
        if (!fn) return;
        map[evt] = map[evt] || new Set();
        map[evt].add(fn);
    };
    register("frame", options.onFrame);
    register(
        "sysMsg",
        (payload: any) => options.onSysMsg?.(payload?.msg || "", payload)
    );
    register("step", options.onStep);
    register("progress", options.onProgress);
    register("error", options.onError);
    if (options.onError) {
        socket.off("connect_error", _handleConnectError(room));
        socket.on(
            "connect_error",
            err => options.onError && options.onError(err)
        );
    }
}

function triggerRoomHandlers(room: string, event: string, payload: any): void {
    const map = ROOM_EVENT_HANDLERS[room];
    if (!map) return;
    const set = map[event];
    if (!set) return;
    set.forEach(fn => {
        try {
            fn(payload);
        } catch (e) {
            /* ignore single handler error */
        }
    });
}

function _handleConnectError(room: string) {
    return (err: any) => {
        triggerRoomHandlers(room, "connect_error", err);
    };
}

// 主动释放某个房间的共享连接（可在路由离开或任务结束时调用）
export function releaseRoomSocket(room: string): void {
    const socket = ROOM_SOCKET_CACHE[room];
    if (socket) {
        try {
            socket.emit("leave", { room });
        } catch (e) { /* ignore */ }
        try {
            socket.disconnect();
        } catch (e) { /* ignore */ }
        delete ROOM_SOCKET_CACHE[room];
        delete ROOM_EVENT_HANDLERS[room];
    }
}

// 预连接任务房间：在点击“Start”后、真正调用后端启动接口之前调用，避免错过早期离线/错误事件。
// 使用方式：preconnectReplayTask(taskId, { onStep, onProgress, onSysMsg, ... });
// 若后续页面再挂载同房间组件，会复用底层 socket，不会重复建立。
export function preconnectReplayTask(
    taskId: string | number,
    handlers?: {
        onStep?: (payload: any) => void;
        onProgress?: (payload: any) => void;
        onSysMsg?: (msg: string, payload: any) => void;
        onError?: (err: any) => void;
    }
): Socket {
    const room = `replay_task_${String(taskId)}`;
    // 仅注册所需处理器；连接成功后立即 join 房间。
    return connectSocket({ room }, {
        onStep: handlers?.onStep,
        onProgress: handlers?.onProgress,
        onSysMsg: handlers?.onSysMsg,
        onError: handlers?.onError,
        onConnect: () => {/* noop */ },
        onDisconnect: () => {/* noop */ }
    });
}
