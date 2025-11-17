import { io, Socket } from "socket.io-client";

// 房间级 socket 缓存与事件多路复用
const ROOM_SOCKET_CACHE: Record<string, Socket> = {};
const ROOM_EVENT_HANDLERS: Record<string, Record<string, Set<Function>>> = {};

export function connectSocket(
    { room }: { room: string },
    options?: {
        onReplay?: (imgBase64: string) => void;
        onDisconnect?: () => void;
        onConnect?: () => void;
        onError?: (err: any) => void;
        onSysMsg?: (msg: string, payload: any) => void;
        onStep?: (payload: any) => void;
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
    socket.on("replay", payload => {
        if (payload && (payload.data || typeof payload === "string")) {
            const img = payload.data || payload;
            triggerRoomHandlers(room, "replay", img);
        }
    });
    socket.on("sysMsg", payload => triggerRoomHandlers(room, "sysMsg", payload));
    socket.on(
        "replay_step",
        payload => triggerRoomHandlers(room, "replay_step", payload?.data || payload)
    );
    // 兼容后端直接以事件名推送（非 sysMsg 封装）的任务进度/状态事件
    const sysWrap = (evt: string) => (payload: any) =>
        triggerRoomHandlers(room, "sysMsg", { event: evt, data: payload?.data || payload });
    socket.on("task_progress", sysWrap("task_progress"));
    socket.on("task_status", sysWrap("task_status"));
    socket.on("task_finished", sysWrap("task_finished"));
    if (optionsCopy) attachRoomHandlers(socket, room, optionsCopy);
    return socket;
}

function attachRoomHandlers(socket: Socket, room: string, options: {
    onReplay?: (imgBase64: string) => void;
    onDisconnect?: () => void;
    onConnect?: () => void;
    onError?: (err: any) => void;
    onSysMsg?: (msg: string, payload: any) => void;
    onStep?: (payload: any) => void;
}): void {
    const map = (ROOM_EVENT_HANDLERS[room] = ROOM_EVENT_HANDLERS[room] || {});
    const register = (evt: string, fn: Function | undefined) => {
        if (!fn) return;
        map[evt] = map[evt] || new Set();
        map[evt].add(fn);
    };
    register("replay", options.onReplay);
    register(
        "sysMsg",
        (payload: any) => options.onSysMsg?.(payload?.msg || "", payload)
    );
    register("replay_step", options.onStep);
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
