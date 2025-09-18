export interface CaseQueueItem {
  /** 用例基础ID */
  case_base_id: number;
  /** 当前版本号 */
  version: number;
  /** 已选择版本号 */
  selectedVersion?: number;
  /** 用例名称 */
  name: string;
  /** 可用版本列表 */
  version_list: number[];
  /** 执行账号 */
  account: string;
  /** 账号密码 */
  password: string;
  /** 账号昵称 */
  nick_name: string;
  /** 身份令牌 */
  token?: string;
  /** 所属串行块的位置索引 */
  block_index: number;
  /** 块内Item的位置索引 */
  inner_index: number;
  /** 用户标识(账号后缀) */
  uid?: number;
  /** 辅助操作 */
  checked?: boolean;
  /** 背景色 */
  color?: string;
  /** emoji 表情 */
  emoji?: string;
  // 报告中的辅助展示字段
  result?: string;
  report_id?: number;
  run_status?: number;
}

export interface AccountOption {
  uid: number;
  color: string;
  emoji: string;
  bg?: string;
}

const emojiCategories = {
  mammals: [
    "🐀",
    "🐵",
    "🐒",
    "🦍",
    "🦧",
    "🐶",
    "🐕",
    "🦮",
    "🐕‍🦺",
    "🐩",
    "🐺",
    "🦊",
    "🦝",
    "🐱",
    "🐈",
    "🦁",
    "🐯",
    "🐅",
    "🐆",
    "🐴",
    "🐎",
    "🦄",
    "🦓",
    "🦌",
    "🐮",
    "🐂",
    "🐃",
    "🐄",
    "🐷",
    "🐖",
    "🐗",
    "🐽",
    "🐏",
    "🐑",
    "🐐",
    "🐪",
    "🐫",
    "🦙",
    "🦒",
    "🐘",
    "🦏",
    "🦛",
    "🐭",
    "🐁",
    "🐹",
    "🐰",
    "🐇",
    "🐿️",
    "🦔",
    "🦇",
    "🐻",
    "🐨",
    "🐼",
    "🦥",
    "🦦",
    "🦨",
    "🦘",
    "🦡",
    "🐾"
  ],
  birds: [
    "🦃",
    "🐔",
    "🐓",
    "🐣",
    "🐤",
    "🐥",
    "🐦",
    "🐧",
    "🕊️",
    "🦅",
    "🦆",
    "🦢",
    "🦉",
    "🦩",
    "🦚",
    "🦜"
  ],
  amphibians: ["🐸"],
  reptiles: ["🐊", "🐢", "🦎", "🐍", "🐲", "🐉", "🦕", "🦖"],
  marineAnimals: ["🐳", "🐋", "🐬", "🐟", "🐠", "🐡", "🦈", "🐙", "🐚", "🪸"],
  insects: [
    "🐌",
    "🦋",
    "🐛",
    "🐜",
    "🐝",
    "🐞",
    "🦗",
    "🕷️",
    "🕸️",
    "🦂",
    "🦟",
    "🦠"
  ],
  flowers: ["💐", "🌸", "💮", "🏵️", "🌹", "🥀", "🌺", "🌻", "🌼", "🌷"],
  plants: [
    "🌱",
    "🌲",
    "🌳",
    "🌴",
    "🌵",
    "🌾",
    "🌿",
    "☘️",
    "🍀",
    "🍁",
    "🍂",
    "🍃",
    "🍄"
  ]
};

// 扁平化所有 emoji 的版本（如果需要单个数组）
const allEmojis = [
  ...emojiCategories.mammals,
  ...emojiCategories.birds,
  ...emojiCategories.amphibians,
  ...emojiCategories.reptiles,
  ...emojiCategories.marineAnimals,
  ...emojiCategories.insects,
  ...emojiCategories.flowers,
  ...emojiCategories.plants
];

/**
 * 根据索引生成固定的 emoji 表情
 * @param index 输入索引号
 * @returns 对应的 emoji 表情
 */
export function getEmojiByIndex(index: number): string {
  // 使用模运算确保索引在范围内
  return allEmojis[index % allEmojis.length];
}

/**
 * 根据索引生成高区分度的十六进制颜色代码
 * @param index 输入索引号
 * @returns 十六进制颜色代码（如 #F349D6）
 */
export function getColorByIndex(index: number): string {
  // 分阶段黄金角度（120°基础角度 + 指数补偿）
  const PHI = (1 + Math.sqrt(5)) / 2; // 黄金比例
  const baseAngle = 120 * (1 + Math.log(index + 1) / PHI);
  const hue = (index * baseAngle) % 360;

  // 饱和度阶梯控制（固定五个饱和度级别）
  const saturationLevels = [80, 85, 90, 95, 100];
  const saturation = saturationLevels[index % 5];

  // 亮度振荡算法（正弦波叠加）
  const baseLightness = 50;
  const lightnessVariation = 15 * Math.sin((index * Math.PI) / 3);
  const lightness = baseLightness + lightnessVariation;

  return hslToHex(hue, saturation, lightness);
}

// 保持原有hslToHex函数不变
/**
 * 将 HSL 颜色转换为十六进制
 * @param h 色相（0-360）
 * @param s 饱和度（0-100）
 * @param l 亮度（0-100）
 * @returns 十六进制颜色代码
 */
function hslToHex(h: number, s: number, l: number): string {
  // 转换 HSL 到 RGB
  s /= 100;
  l /= 100;

  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;

  let r = 0,
    g = 0,
    b = 0;

  if (h >= 0 && h < 60) {
    r = c;
    g = x;
    b = 0;
  } else if (h >= 60 && h < 120) {
    r = x;
    g = c;
    b = 0;
  } else if (h >= 120 && h < 180) {
    r = 0;
    g = c;
    b = x;
  } else if (h >= 180 && h < 240) {
    r = 0;
    g = x;
    b = c;
  } else if (h >= 240 && h < 300) {
    r = x;
    g = 0;
    b = c;
  } else if (h >= 300 && h < 360) {
    r = c;
    g = 0;
    b = x;
  }

  // 转换为 0-255 范围
  r = Math.round((r + m) * 255);
  g = Math.round((g + m) * 255);
  b = Math.round((b + m) * 255);

  // 转换为十六进制
  return `#${((1 << 24) + (r << 16) + (g << 8) + b)
    .toString(16)
    .slice(1)
    .toUpperCase()}`;
}

export interface MenuClickEvent {
  label: string;
}

export interface assetItem {
  name: string; // 文件名
  url: string; // 文件链接
}
