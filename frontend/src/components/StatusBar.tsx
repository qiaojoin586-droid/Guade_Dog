/**
 * 状态栏组件（占位）。
 */

export default function StatusBar() {
  return (
    <div className="w-full bg-primary-50 px-4 py-2 flex items-center justify-between text-sm">
      <span className="text-gray-600">导盲AI</span>
      <span className="text-gray-400">就绪</span>
    </div>
  );
}
