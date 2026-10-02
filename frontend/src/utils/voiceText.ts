/**
 * 语音文本处理：中文数字转阿拉伯数字、口语清洗、是/否判断。
 */

const CN_DIGITS: Record<string, string> = {
  零: '0',
  '〇': '0',
  '○': '0',
  洞: '0',
  一: '1',
  幺: '1',
  壹: '1',
  二: '2',
  两: '2',
  贰: '2',
  三: '3',
  叁: '3',
  四: '4',
  肆: '4',
  五: '5',
  伍: '5',
  六: '6',
  陆: '6',
  七: '7',
  柒: '7',
  八: '8',
  捌: '8',
  九: '9',
  玖: '9',
};

/** 从一段话里抽取数字（手机号、验证码常用：一三八零零一三八零零零）。 */
export function extractDigits(text: string): string {
  let out = '';
  for (const ch of text) {
    if (ch >= '0' && ch <= '9') {
      out += ch;
      continue;
    }
    const mapped = CN_DIGITS[ch];
    if (mapped) out += mapped;
  }
  return out;
}

/** 去掉首尾空白与句尾标点。 */
export function normalizeUtterance(text: string): string {
  return text.replace(/^[\s，。！？、；：]+/, '').replace(/[\s，。！？、；：]+$/, '').trim();
}

/** 是否是“不需要求救”这类否定回答。 */
export function isNegativeReply(text: string): boolean {
  const t = text.replace(/\s/g, '');
  return /不需要|不用|不要|取消|没事|我很好|没有危险|停止求救/.test(t);
}

/** 是否是“需要求救”这类肯定回答。 */
export function isPositiveReply(text: string): boolean {
  const t = text.replace(/\s/g, '');
  if (isNegativeReply(t)) return false;
  return /需要|快点|救我|救命|是的|要的|赶紧/.test(t);
}

/** 播报用：把手机号拆成更易听的节奏（138 0013 8000）。 */
export function formatPhoneForSpeech(phone: string): string {
  if (phone.length !== 11) return phone;
  return `${phone.slice(0, 3)}，${phone.slice(3, 7)}，${phone.slice(7)}`;
}
