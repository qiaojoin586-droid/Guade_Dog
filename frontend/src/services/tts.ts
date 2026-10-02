/**
 * 浏览器语音播报（Web Speech Synthesis）。
 *
 * 为什么不走讯飞 TTS：语音交互必须低延迟，且播报内容和识别必须串行，
 * 浏览器内置播报不依赖网络与密钥，演示阶段最稳。
 */

let cachedVoice: SpeechSynthesisVoice | null = null;

function pickChineseVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null;
  if (cachedVoice) return cachedVoice;
  const voices = window.speechSynthesis.getVoices();
  const zh = voices.find((v) => v.lang.toLowerCase().startsWith('zh'));
  if (zh) cachedVoice = zh;
  return cachedVoice;
}

/** 预加载语音列表（部分浏览器首次 getVoices 为空，需要等 voiceschanged）。 */
export function warmUpVoices(): void {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  pickChineseVoice();
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = null;
    pickChineseVoice();
  };
}

/** 是否支持语音播报。 */
export function isSpeechSynthesisSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * 播报一段文字，返回的 Promise 在播报结束（或失败）时 resolve。
 * 调用前会取消上一条播报，避免叠音。
 */
export function speak(text: string): Promise<void> {
  return new Promise((resolve) => {
    const content = text.trim();
    if (!content || !isSpeechSynthesisSupported()) {
      resolve();
      return;
    }

    const synth = window.speechSynthesis;
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(content);
    utterance.lang = 'zh-CN';
    utterance.rate = 0.95;
    utterance.pitch = 1;
    utterance.volume = 1;

    const voice = pickChineseVoice();
    if (voice) utterance.voice = voice;

    let finished = false;
    let started = false;
    let timer = 0;
    let startGuard = 0;

    const finish = () => {
      if (finished) return;
      finished = true;
      window.clearTimeout(timer);
      window.clearTimeout(startGuard);
      resolve();
    };

    utterance.onstart = () => {
      started = true;
    };
    utterance.onend = finish;
    utterance.onerror = finish;

    // 自动播放策略可能静默拦截播报：2 秒还没开始就当作失败，避免流程卡死
    startGuard = window.setTimeout(() => {
      if (!started) {
        try {
          synth.cancel();
        } catch {
          // 忽略
        }
        finish();
      }
    }, 2_000);

    // 兜底：极少数环境不触发 onend，按文本长度估算上限
    timer = window.setTimeout(finish, Math.min(30_000, 3_000 + content.length * 220));

    try {
      synth.speak(utterance);
    } catch {
      finish();
    }
  });
}

/** 立即停止播报。 */
export function stopSpeaking(): void {
  if (!isSpeechSynthesisSupported()) return;
  window.speechSynthesis.cancel();
}
