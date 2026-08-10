/**
 * 语音波形动画组件（占位）。
 */

interface AudioWaveProps {
  isActive?: boolean;
}

export default function AudioWave({ isActive = false }: AudioWaveProps) {
  if (!isActive) return null;

  return (
    <div className="flex items-center justify-center space-x-1 h-8" aria-hidden="true">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="w-1 bg-primary-500 rounded-full animate-bounce"
          style={{
            height: `${Math.random() * 24 + 8}px`,
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
    </div>
  );
}
