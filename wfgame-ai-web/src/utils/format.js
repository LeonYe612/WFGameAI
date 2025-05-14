/**
 * 格式化工具函数
 * @file src/utils/format.js
 * @author WFGame AI Team
 * @date 2024-05-15
 */

/**
 * 格式化日期
 * @param {string|Date} date - 日期字符串或Date对象
 * @param {string} [format='yyyy-MM-dd HH:mm:ss'] - 输出格式
 * @returns {string} 格式化后的日期字符串
 */
export function formatDate(date, format = 'yyyy-MM-dd HH:mm:ss') {
  if (!date) return '';
  
  let dateObj;
  if (typeof date === 'string') {
    // 将字符串转换为日期对象
    dateObj = new Date(date);
    
    // 检查是否为有效日期
    if (isNaN(dateObj.getTime())) {
      console.warn('Invalid date:', date);
      return date;
    }
  } else if (date instanceof Date) {
    dateObj = date;
  } else {
    console.warn('Invalid date type:', typeof date);
    return String(date);
  }
  
  const o = {
    'M+': dateObj.getMonth() + 1, // 月份
    'd+': dateObj.getDate(), // 日
    'H+': dateObj.getHours(), // 小时
    'h+': dateObj.getHours() % 12 || 12, // 12小时制
    'm+': dateObj.getMinutes(), // 分
    's+': dateObj.getSeconds(), // 秒
    'q+': Math.floor((dateObj.getMonth() + 3) / 3), // 季度
    'S': dateObj.getMilliseconds() // 毫秒
  };
  
  if (/(y+)/.test(format)) {
    format = format.replace(RegExp.$1, (dateObj.getFullYear() + '').substr(4 - RegExp.$1.length));
  }
  
  for (let k in o) {
    if (new RegExp('(' + k + ')').test(format)) {
      format = format.replace(
        RegExp.$1,
        RegExp.$1.length === 1 ? o[k] : ('00' + o[k]).substr(('' + o[k]).length)
      );
    }
  }
  
  return format;
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节大小
 * @param {number} [decimals=2] - 小数位数
 * @returns {string} 格式化后的文件大小
 */
export function formatFileSize(bytes, decimals = 2) {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * 格式化时长（秒转为时分秒）
 * @param {number} seconds - 秒数
 * @returns {string} 格式化后的时长
 */
export function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '';
  
  seconds = Math.floor(seconds);
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  
  if (hours > 0) {
    return `${hours}小时${minutes}分${remainingSeconds}秒`;
  } else if (minutes > 0) {
    return `${minutes}分${remainingSeconds}秒`;
  } else {
    return `${remainingSeconds}秒`;
  }
}

/**
 * 截断文本
 * @param {string} text - 原始文本
 * @param {number} [length=20] - 最大长度
 * @param {string} [suffix='...'] - 省略后缀
 * @returns {string} 处理后的文本
 */
export function truncateText(text, length = 20, suffix = '...') {
  if (!text) return '';
  
  text = String(text);
  
  if (text.length <= length) return text;
  
  return text.substring(0, length) + suffix;
} 