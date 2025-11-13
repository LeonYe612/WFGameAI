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

declare const require: any;

// 优先读取环境变量，否则用默认值
function getEnvInt(key: string, def: number): number {
  if (typeof process !== "undefined" && process.env && process.env[key]) {
    const v = process.env[key].replace(/\s/g, "");
    if (/^\d+$/.test(v)) return parseInt(v, 10);
    // 支持 2*1024 这种表达式
    try {
      // 使用 Function 代替 eval，语法相同但更显式
      const n = Function(`return (${v})`)();
      if (typeof n === "number" && !isNaN(n)) return n;
    } catch (e) {
      // 明确处理解析错误：刻意忽略无效表达式（可在开发环境打印以便排查）
      if (
        typeof process !== "undefined" &&
        process.env &&
        process.env.NODE_ENV !== "production"
      ) {
        console.warn(
          `getEnvInt: unable to parse "${key}"="${process.env[key]}", use default ${def}`,
          e
        );
      }
    }
  }
  return def;
}

const DEFAULT_CHUNK_KB = getEnvInt("VITE_ZSTD_CHUNK_KB", 1024); // 1MB
const DEFAULT_THRESHOLD_KB = getEnvInt("VITE_ZSTD_THRESHOLD_KB", 10240); // 10MB

function toU8(buf: Uint8Array | ArrayBuffer): Uint8Array {
  return buf instanceof Uint8Array ? buf : new Uint8Array(buf);
}

function isOomError(err: unknown): boolean {
  const s = String(err || "").toLowerCase();
  return (
    s.includes("oom") ||
    s.includes("out of memory") ||
    s.includes("cannot enlarge memory") ||
    s.includes("abort")
  );
}

function findZstdFrameOffsets(buf: Uint8Array): number[] {
  const magic = [0x28, 0xb5, 0x2f, 0xfd];
  const out: number[] = [];
  for (let i = 0; i + 3 < buf.length; i++) {
    if (
      buf[i] === magic[0] &&
      buf[i + 1] === magic[1] &&
      buf[i + 2] === magic[2] &&
      buf[i + 3] === magic[3]
    ) {
      out.push(i);
    }
  }
  if (out.length === 0) out.push(0);
  return out;
}

interface ZstdApi {
  compress: (input: Uint8Array) => Uint8Array;
  decompress: (input: Uint8Array) => Uint8Array;
}

async function initZstd(): Promise<ZstdApi> {
  const m = require("zstd-codec");
  const ZstdCodec = m.ZstdCodec || m.Zstd || m;
  if (!ZstdCodec || typeof ZstdCodec.run !== "function") {
    throw new Error("未找到 zstd-codec（或缺少 ZstdCodec.run）");
  }
  return new Promise<ZstdApi>((resolve, reject) => {
    try {
      ZstdCodec.run((zstd: any) => {
        // 优先 Simple 实例
        if (zstd.Simple) {
          try {
            const inst = new zstd.Simple();
            if (
              typeof inst.compress === "function" &&
              typeof inst.decompress === "function"
            ) {
              return resolve({
                compress: inst.compress.bind(inst),
                decompress: inst.decompress.bind(inst)
              });
            }
          } catch { }
        }
        // 兜底直接用 zstd
        if (
          typeof zstd.compress === "function" &&
          typeof zstd.decompress === "function"
        ) {
          return resolve({
            compress: zstd.compress,
            decompress: zstd.decompress
          });
        }
        reject(new Error("zstd 运行时未提供可用的压缩/解压 API"));
      });
    } catch (e) {
      reject(e);
    }
  });
}

export async function zstdDecompressWasm(
  data: Uint8Array,
  opts?: { thresholdKB?: number }
): Promise<Uint8Array> {
  const { decompress } = await initZstd();
  const thresholdKB =
    opts && typeof opts.thresholdKB === "number"
      ? opts.thresholdKB
      : DEFAULT_THRESHOLD_KB;
  const thresholdBytes = Math.max(1, Math.floor(thresholdKB * 1024));
  const needSplit = data.length > thresholdBytes;
  if (!needSplit) {
    try {
      return toU8(decompress(data));
    } catch (e) {
      if (!isOomError(e)) throw e;
      // OOM -> split by frames
    }
  }
  const offsets = findZstdFrameOffsets(data);
  if (offsets.length === 1 && !needSplit) {
    return toU8(decompress(data));
  }
  const pieces: Uint8Array[] = [];
  for (let i = 0; i < offsets.length; i++) {
    const start = offsets[i];
    const end = i + 1 < offsets.length ? offsets[i + 1] : data.length;
    const frame = data.subarray(start, end);
    const out = decompress(frame);
    pieces.push(toU8(out));
  }
  const total = pieces.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let w = 0;
  for (const p of pieces) {
    out.set(p, w);
    w += p.length;
  }
  return out;
}

export async function zstdCompressWasm(
  data: Uint8Array,
  opts?: { chunkKB?: number }
): Promise<Uint8Array> {
  const { compress } = await initZstd();
  const startKB = Math.max(1, (opts && opts.chunkKB) || DEFAULT_CHUNK_KB);
  console.log(`zstdCompressWasm: startKB=${startKB}KB`);
  const thresholdBytes = DEFAULT_THRESHOLD_KB * 1024;
  const shouldChunk = data.length > thresholdBytes;
  if (!shouldChunk) {
    try {
      return toU8(compress(data));
    } catch (e) {
      if (!isOomError(e)) throw e;
    }
  }
  let curKB = startKB;
  const minKB = 64;
  const compressWithKB = (kb: number): Uint8Array => {
    const chunkSize = kb * 1024;
    const frames: Uint8Array[] = [];
    for (let off = 0; off < data.length; off += chunkSize) {
      const chunk = data.subarray(off, Math.min(off + chunkSize, data.length));
      frames.push(compress(chunk));
    }
    const total = frames.reduce((n, f) => n + f.length, 0);
    const out = new Uint8Array(total);
    let w = 0;
    for (const f of frames) {
      out.set(f, w);
      w += f.length;
    }
    return out;
  };
  try {
    return compressWithKB(curKB);
  } catch (e) {
    if (!isOomError(e)) throw e;
  }
  while (curKB > minKB) {
    curKB = Math.max(minKB, Math.floor(curKB / 2));
    try {
      return compressWithKB(curKB);
    } catch (e) {
      if (!isOomError(e)) throw e;
      if (curKB === minKB) break;
    }
  }
  throw new Error("WASM 压缩内存不足，建议减小输入或改用原生 CLI/服务端压缩");
}
