/**
 * 语音按钮组件（核心交互，占位）。
 */

interface VoiceButtonProps {
  onClick?: () => void;
  isListening?: boolean;
  disabled?: boolean;
}

export default function VoiceButton({ onClick, isListening = false, disabled = false }: VoiceButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        w-20 h-20 rounded-full flex items-center justify-center
        text-white text-2xl font-bold
        transition-all duration-200
        ${isListening ? 'bg-red-500 animate-pulse' : 'bg-primary-600 hover:bg-primary-700'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
      aria-label={isListening ? '停止录音' : '开始语音输入'}
    >
        {isListening ? '●' : '🎤'}
    </button>
  );
}
