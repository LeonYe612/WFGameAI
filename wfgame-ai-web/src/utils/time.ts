import daysj from "dayjs";

/** 返回格式化的时间，如果出错返回一个默认值 */
// export const TimeDefault = (
//   dateString: string,
//   format?: string,
//   defaultString?: string
// ) => {
//   if (!defaultString) {
//     defaultString = "/";
//   }
//   if (dateString == undefined || dateString == "") {
//     return defaultString;
//   }
//   if (!format) {
//     format = "YYYY-MM-DD";
//   }

//   try {
//     const date = new Date(dateString);
//     const year = date.getFullYear();
//     const month = (date.getMonth() + 1).toString().padStart(2, "0");
//     const day = date.getDate().toString().padStart(2, "0");
//     const hours = date.getHours().toString().padStart(2, "0");
//     const minutes = date.getMinutes().toString().padStart(2, "0");
//     const seconds = date.getSeconds().toString().padStart(2, "0");
//     return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
//   } catch (error) {
//     console.error(error);
//     return defaultString;
//   }
// };

/** 返回格式化的时间，如果出错返回一个默认值 */
export const TimeDefault = (
  date: string,
  format?: string,
  defaultString?: string
) => {
  if (!defaultString) {
    defaultString = "/";
  }
  if (date == undefined || date == "") {
    return defaultString;
  }
  if (!format) {
    format = "YYYY-MM-DD HH:mm:ss";
  }

  const t = daysj(new Date(date));
  if (t.year() == 1 || t.year() == 0) {
    return defaultString;
  }
  return t.format(format);
};

/** 格式化时间戳或Date对象为指定格式的日期字符串 */
export const formatDateTime = (
  dateInput: number | Date,
  format = "YYYY-MM-DD HH:mm:ss"
): string => {
  let date: Date;

  if (typeof dateInput === "number") {
    // 判断是10位时间戳（秒）还是13位时间戳（毫秒）
    date =
      dateInput > 9_999_999_999
        ? new Date(dateInput)
        : new Date(dateInput * 1000);
  } else {
    date = dateInput;
  }

  return daysj(date).format(format);
};

export const formatTimestamp = (ts: number): string => {
  // 10位时间戳（秒）转毫秒（13位）
  const date = ts > 9_999_999_999 ? new Date(ts) : new Date(ts * 1000);

  // 提取日期组件
  const year = date.getFullYear() % 100; // 取年份后两位
  const month = date.getMonth() + 1; // 月份从0开始，需+1
  const day = date.getDate();
  const hours = date.getHours();
  const minutes = date.getMinutes();

  // 格式化为两位数并拼接字符串
  return [
    String(day).padStart(2, "0"),
    String(month).padStart(2, "0"),
    String(year).padStart(2, "0"),
    String(hours).padStart(2, "0"),
    String(minutes).padStart(2, "0")
  ].join("");
};
