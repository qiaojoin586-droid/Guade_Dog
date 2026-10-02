/**
 * 常驻语音控制条（全局唯一入口）。
 *
 * 盲人用户只需要操作这里：点一下开始聆听，用说话完成导航、识别、求救、地址管理。
 * 右侧红色按钮用于模拟“手机剧烈抖动”，触发 SOS 流程。
 */

import { useVoiceControl } from '../voice/VoiceControlProvider';

export default function VoiceDock() {
  const {
    supported,
    mode,
    listening,
    busy,
    transcript,
    reply,
    error,
    sosPending,
    startListening,
    stopListening,
    simulateShake,
  } = useVoiceControl();

  const statusText = !supported
    ? '当前浏览器不支持语音输入'
    : busy
      ? '正在处理…'
      : mode === 'server'
        ? listening
          ? '正在录音，说完再点一下'
          : '录音识别模式，点麦克风开始'
        : listening
          ? '正在聆听，请说话'
          : '语音已暂停，点麦克风继续';

  const micLabel = listening
    ? mode === 'server'
      ? '结束录音并识别'
      : '停止语音控制'
    : mode === 'server'
      ? '开始录音'
      : '开始语音控制';

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 px-2 pb-2 sm:px-3 sm:pb-3 pointer-events-none">
      <section
        className="pointer-events-auto mx-auto max-w-3xl rounded-2xl sm:rounded-3xl bg-[#0a1628]/95 text-white shadow-2xl border border-white/10 px-3 sm:px-5 py-3 sm:py-4 backdrop-blur"
        aria-label="语音控制面板"
      >
        <div className="flex items-center gap-2 sm:gap-4">
          {/* 麦克风 */}
          <button
            type="button"
            onClick={listening ? stopListening : startListening}
            aria-pressed={listening}
            aria-label={micLabel}
            className={`w-14 h-14 sm:w-20 sm:h-20 flex-shrink-0 rounded-full flex items-center justify-center transition-all
              focus:outline-none focus:ring-4 focus:ring-white/60
              ${listening ? 'bg-red-500 animate-pulse' : 'bg-[#2f7cf6] hover:bg-[#1f6ae0]'}`}
          >
            <svg className="w-7 h-7 sm:w-10 sm:h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </button>

          {/* 状态与文本 */}
          <div className="flex-1 min-w-0">
            <p className="text-sm sm:text-lg font-bold truncate" aria-live="polite">
              {statusText}
            </p>
            <p className="text-xs sm:text-base text-blue-100 truncate" title={transcript}>
              {transcript ? `我说：${transcript}` : '试试说：我要去公司'}
            </p>
            <p className="text-xs sm:text-base text-white/90 line-clamp-1 sm:line-clamp-2" aria-live="assertive">
              {reply ? `助手：${reply}` : ''}
            </p>
          </div>

          {/* 模拟剧烈抖动 */}
          <button
            type="button"
            onClick={simulateShake}
            className={`flex-shrink-0 px-3 sm:px-4 py-2.5 sm:py-4 rounded-xl sm:rounded-2xl text-sm sm:text-base font-bold leading-tight
              focus:outline-none focus:ring-4 focus:ring-red-300
              ${sosPending ? 'bg-red-600 animate-pulse' : 'bg-red-500 hover:bg-red-600'}`}
            aria-label="模拟手机剧烈抖动，触发紧急求救"
          >
            剧烈抖动
            <span className="block text-[10px] sm:text-sm font-normal">（模拟求救）</span>
          </button>
        </div>

        {sosPending && (
          <p className="mt-2 sm:mt-3 rounded-xl bg-red-500/20 px-3 sm:px-4 py-2 text-sm sm:text-base text-red-100" role="alert">
            正在确认是否需要求救：10 秒内说“不需要”可取消，不回答将自动求救。
          </p>
        )}

        {error && (
          <p className="mt-2 sm:mt-3 rounded-xl bg-yellow-400/20 px-3 sm:px-4 py-2 text-sm sm:text-base text-yellow-100" role="alert">
            {error}
          </p>
        )}
      </section>
    </div>
  );
}
