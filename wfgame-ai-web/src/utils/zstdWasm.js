"use strict";
/*
  安装命令：
  npm install zstd-codec
  或
  yarn add zstd-codec
  或
  pnpm add zstd-codec
  pnpm add -D typescript @types/node
  注意：zstd-codec 体积较大，约 1.5MB（gzipped），请根据实际场景斟酌使用。

  对外 API（全部中文注释）
  - zstdCompressWasm(data: Uint8Array, opts?): Promise<Uint8Array>
    压缩：默认当数据>10240KB 或整块压缩 OOM 时，自动按分片（多帧）压缩；opts.chunkKB 可自定义分片大小，默认 1024KB。
      - opts.chunkKB 压缩分片大小（KB），默认 1MB（1024KB）
  - zstdDecompressWasm(data: Uint8Array, opts?): Promise<Uint8Array>
    解压：默认尝试整帧，若数据>10240KB 或 OOM，则自动按帧分片解压并拼接。opts.thresholdKB 可自定义阈值。
      - opts.thresholdKB 解压分片阈值（KB），默认 10MB（10240KB）

  说明
  - 依赖 zstd-codec（WASM 实现），不使用系统 CLI，可在浏览器/Node 中使用。
  - 解压未提供真实“流式”接口，这里采用“按帧切分”的方式以降低峰值内存需求。
  - 压缩支持按分片生成多帧，在二进制层面进行拼接，以降低 OOM 风险。

  实例
  // 压缩 Uint8Array 数据，分片 512KB
  const out1 = await zstdCompressWasm(u8, { chunkKB: 512 });

  // 解压 Uint8Array zst 数据，阈值 8MB
  const out2 = await zstdDecompressWasm(u8zst, { thresholdKB: 8192 });

  // 不传 opts 时，均为默认策略（压缩分片 1024KB，解压阈值 10MB）
  const out3 = await zstdCompressWasm(u8);
  const out4 = await zstdDecompressWasm(u8zst);
*/
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.zstdDecompressWasm = zstdDecompressWasm;
exports.zstdCompressWasm = zstdCompressWasm;
// 优先读取环境变量，否则用默认值
function getEnvInt(key, def) {
    if (typeof process !== "undefined" && process.env && process.env[key]) {
        var v = process.env[key].replace(/\s/g, "");
        if (/^\d+$/.test(v))
            return parseInt(v, 10);
        // 支持 2*1024 这种表达式
        try {
            // 使用 Function 代替 eval，语法相同但更显式
            var n = Function("return (".concat(v, ")"))();
            if (typeof n === "number" && !isNaN(n))
                return n;
        }
        catch (e) {
            // 明确处理解析错误：刻意忽略无效表达式（可在开发环境打印以便排查）
            if (typeof process !== "undefined" &&
                process.env &&
                process.env.NODE_ENV !== "production") {
                console.warn("getEnvInt: unable to parse \"".concat(key, "\"=\"").concat(process.env[key], "\", use default ").concat(def), e);
            }
        }
    }
    return def;
}
var DEFAULT_CHUNK_KB = getEnvInt("ZSTD_CHUNK_KB", 1024); // 1MB
var DEFAULT_THRESHOLD_KB = getEnvInt("ZSTD_THRESHOLD_KB", 10240); // 10MB
function toU8(buf) {
    return buf instanceof Uint8Array ? buf : new Uint8Array(buf);
}
function isOomError(err) {
    var s = String(err || "").toLowerCase();
    return (s.includes("oom") ||
        s.includes("out of memory") ||
        s.includes("cannot enlarge memory") ||
        s.includes("abort"));
}
function findZstdFrameOffsets(buf) {
    var magic = [0x28, 0xb5, 0x2f, 0xfd];
    var out = [];
    for (var i = 0; i + 3 < buf.length; i++) {
        if (buf[i] === magic[0] &&
            buf[i + 1] === magic[1] &&
            buf[i + 2] === magic[2] &&
            buf[i + 3] === magic[3]) {
            out.push(i);
        }
    }
    if (out.length === 0)
        out.push(0);
    return out;
}
function initZstd() {
    return __awaiter(this, void 0, void 0, function () {
        var m, ZstdCodec;
        return __generator(this, function (_a) {
            m = require("zstd-codec");
            ZstdCodec = m.ZstdCodec || m.Zstd || m;
            if (!ZstdCodec || typeof ZstdCodec.run !== "function") {
                throw new Error("未找到 zstd-codec（或缺少 ZstdCodec.run）");
            }
            return [2 /*return*/, new Promise(function (resolve, reject) {
                    try {
                        ZstdCodec.run(function (zstd) {
                            // 优先 Simple 实例
                            if (zstd.Simple) {
                                try {
                                    var inst = new zstd.Simple();
                                    if (typeof inst.compress === "function" &&
                                        typeof inst.decompress === "function") {
                                        return resolve({
                                            compress: inst.compress.bind(inst),
                                            decompress: inst.decompress.bind(inst)
                                        });
                                    }
                                }
                                catch (_a) { }
                            }
                            // 兜底直接用 zstd
                            if (typeof zstd.compress === "function" &&
                                typeof zstd.decompress === "function") {
                                return resolve({
                                    compress: zstd.compress,
                                    decompress: zstd.decompress
                                });
                            }
                            reject(new Error("zstd 运行时未提供可用的压缩/解压 API"));
                        });
                    }
                    catch (e) {
                        reject(e);
                    }
                })];
        });
    });
}
function zstdDecompressWasm(data, opts) {
    return __awaiter(this, void 0, void 0, function () {
        var decompress, thresholdKB, thresholdBytes, needSplit, offsets, pieces, i, start, end, frame, out_1, total, out, w, _i, pieces_1, p;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, initZstd()];
                case 1:
                    decompress = (_a.sent()).decompress;
                    thresholdKB = opts && typeof opts.thresholdKB === "number"
                        ? opts.thresholdKB
                        : DEFAULT_THRESHOLD_KB;
                    thresholdBytes = Math.max(1, Math.floor(thresholdKB * 1024));
                    needSplit = data.length > thresholdBytes;
                    if (!needSplit) {
                        try {
                            return [2 /*return*/, toU8(decompress(data))];
                        }
                        catch (e) {
                            if (!isOomError(e))
                                throw e;
                            // OOM -> split by frames
                        }
                    }
                    offsets = findZstdFrameOffsets(data);
                    if (offsets.length === 1 && !needSplit) {
                        return [2 /*return*/, toU8(decompress(data))];
                    }
                    pieces = [];
                    for (i = 0; i < offsets.length; i++) {
                        start = offsets[i];
                        end = i + 1 < offsets.length ? offsets[i + 1] : data.length;
                        frame = data.subarray(start, end);
                        out_1 = decompress(frame);
                        pieces.push(toU8(out_1));
                    }
                    total = pieces.reduce(function (n, p) { return n + p.length; }, 0);
                    out = new Uint8Array(total);
                    w = 0;
                    for (_i = 0, pieces_1 = pieces; _i < pieces_1.length; _i++) {
                        p = pieces_1[_i];
                        out.set(p, w);
                        w += p.length;
                    }
                    return [2 /*return*/, out];
            }
        });
    });
}
function zstdCompressWasm(data, opts) {
    return __awaiter(this, void 0, void 0, function () {
        var compress, startKB, thresholdBytes, shouldChunk, curKB, minKB, compressWithKB;
        return __generator(this, function (_a) {
            switch (_a.label) {
                case 0: return [4 /*yield*/, initZstd()];
                case 1:
                    compress = (_a.sent()).compress;
                    startKB = Math.max(1, (opts && opts.chunkKB) || DEFAULT_CHUNK_KB);
                    console.log("zstdCompressWasm: startKB=".concat(startKB, "KB"));
                    thresholdBytes = DEFAULT_THRESHOLD_KB * 1024;
                    shouldChunk = data.length > thresholdBytes;
                    if (!shouldChunk) {
                        try {
                            return [2 /*return*/, toU8(compress(data))];
                        }
                        catch (e) {
                            if (!isOomError(e))
                                throw e;
                        }
                    }
                    curKB = startKB;
                    minKB = 64;
                    compressWithKB = function (kb) {
                        var chunkSize = kb * 1024;
                        var frames = [];
                        for (var off = 0; off < data.length; off += chunkSize) {
                            var chunk = data.subarray(off, Math.min(off + chunkSize, data.length));
                            frames.push(compress(chunk));
                        }
                        var total = frames.reduce(function (n, f) { return n + f.length; }, 0);
                        var out = new Uint8Array(total);
                        var w = 0;
                        for (var _i = 0, frames_1 = frames; _i < frames_1.length; _i++) {
                            var f = frames_1[_i];
                            out.set(f, w);
                            w += f.length;
                        }
                        return out;
                    };
                    try {
                        return [2 /*return*/, compressWithKB(curKB)];
                    }
                    catch (e) {
                        if (!isOomError(e))
                            throw e;
                    }
                    while (curKB > minKB) {
                        curKB = Math.max(minKB, Math.floor(curKB / 2));
                        try {
                            return [2 /*return*/, compressWithKB(curKB)];
                        }
                        catch (e) {
                            if (!isOomError(e))
                                throw e;
                            if (curKB === minKB)
                                break;
                        }
                    }
                    throw new Error("WASM 压缩内存不足，建议减小输入或改用原生 CLI/服务端压缩");
            }
        });
    });
}
