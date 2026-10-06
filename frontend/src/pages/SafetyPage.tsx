/**
 * 安全页面（本期：药品识别 / 健康问答 / 钞票识别）。
 *
 * 拍摄提示：正对药盒/钞票正面，保持光线充足，降低低质量图导致识别失败的概率。
 * 识别结果通过浏览器语音播报（speechSynthesis）。
 */

import { useRef, useState } from 'react';
import { askHealth, recognizeCurrency, recognizeMedicine } from '../services/safetyService';

function speak(text: string) {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'zh-CN';
  window.speechSynthesis.speak(utterance);
}

interface Result {
  text: string;
  isError?: boolean;
}

function ResultBox({ result, loading }: { result: Result | null; loading: boolean }) {
  if (loading) {
    return <p className="mt-3 text-sm text-blue-600">正在识别，请稍候...</p>;
  }
  if (!result) return null;
  return (
    <div className={`mt-3 rounded-lg p-3 text-sm leading-relaxed ${result.isError ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-gray-800'}`}>
      {result.text}
    </div>
  );
}

function Card({
  title,
  desc,
  children,
  color,
}: {
  title: string;
  desc: string;
  children: React.ReactNode;
  color: string;
}) {
  return (
    <div className="rounded-2xl bg-white shadow-sm border border-gray-100 p-5">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-xl ${color} mb-3`}>
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>
      <h2 className="text-lg font-bold text-gray-900">{title}</h2>
      <p className="text-sm text-gray-500 mt-1 mb-4">{desc}</p>
      {children}
    </div>
  );
}

export default function SafetyPage() {
  const [healthQuestion, setHealthQuestion] = useState('');
  const [healthResult, setHealthResult] = useState<Result | null>(null);
  const [medicineResult, setMedicineResult] = useState<Result | null>(null);
  const [currencyResult, setCurrencyResult] = useState<Result | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [medicineLoading, setMedicineLoading] = useState(false);
  const [currencyLoading, setCurrencyLoading] = useState(false);

  const medicineInputRef = useRef<HTMLInputElement>(null);
  const currencyInputRef = useRef<HTMLInputElement>(null);

  const handleHealthAsk = async () => {
    const question = healthQuestion.trim();
    if (!question) return;
    setHealthLoading(true);
    setHealthResult(null);
    try {
      const data = await askHealth(question);
      const text = data.tts_text || data.answer;
      setHealthResult({ text });
      speak(text);
    } catch (err: any) {
      setHealthResult({ text: err.response?.data?.message || '网络错误，请稍后重试', isError: true });
    } finally {
      setHealthLoading(false);
    }
  };

  const handleMedicineFile = async (file: File | undefined) => {
    if (!file) return;
    setMedicineLoading(true);
    setMedicineResult(null);
    try {
      const data = await recognizeMedicine(file);
      setMedicineResult({ text: data.tts_text });
      speak(data.tts_text);
    } catch (err: any) {
      setMedicineResult({ text: err.response?.data?.message || '识别失败，请重试', isError: true });
    } finally {
      setMedicineLoading(false);
      if (medicineInputRef.current) medicineInputRef.current.value = '';
    }
  };

  const handleCurrencyFile = async (file: File | undefined) => {
    if (!file) return;
    setCurrencyLoading(true);
    setCurrencyResult(null);
    try {
      const data = await recognizeCurrency(file);
      setCurrencyResult({ text: data.tts_text });
      speak(data.tts_text);
    } catch (err: any) {
      setCurrencyResult({ text: err.response?.data?.message || '识别失败，请重试', isError: true });
    } finally {
      setCurrencyLoading(false);
      if (currencyInputRef.current) currencyInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 pb-40 sm:pb-44">
      <header className="mb-4 sm:mb-6">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-900">安全助手</h1>
        <p className="text-sm text-gray-500 mt-1">药品识别 · 健康问答 · 钞票识别（识别结果仅供参考）</p>
      </header>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {/* 药品识别 */}
        <Card title="药品识别" desc="拍摄药盒或药瓶，播报药品名称、适应症与用法用量。" color="bg-blue-100 text-blue-600">
          <input
            ref={medicineInputRef}
            type="file"
            accept="image/jpeg,image/png"
            capture="environment"
            className="hidden"
            onChange={(e) => handleMedicineFile(e.target.files?.[0])}
            id="medicine-file"
          />
          <label
            htmlFor="medicine-file"
            className="inline-block w-full text-center rounded-lg bg-blue-600 text-white py-2.5 text-sm font-medium cursor-pointer hover:bg-blue-700"
          >
            {medicineLoading ? '识别中...' : '拍照 / 选择药盒照片'}
          </label>
          <p className="text-xs text-gray-400 mt-2">提示：正对药盒正面，保持光线充足。</p>
          <ResultBox result={medicineResult} loading={medicineLoading} />
        </Card>

        {/* 健康问答 */}
        <Card title="健康问答" desc="语音或文字提问健康问题，AI 给出一般性建议（不诊断）。" color="bg-emerald-100 text-emerald-600">
          <div className="flex gap-2">
            <input
              type="text"
              value={healthQuestion}
              onChange={(e) => setHealthQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleHealthAsk()}
              placeholder="例如：感冒了能吃药吗"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
            />
            <button
              onClick={handleHealthAsk}
              disabled={healthLoading || !healthQuestion.trim()}
              className="rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {healthLoading ? '思考中...' : '提问'}
            </button>
          </div>
          <ResultBox result={healthResult} loading={healthLoading} />
        </Card>

        {/* 钞票识别 */}
        <Card title="钞票识别" desc="拍摄人民币纸币，播报面额；不确定时不会播报具体金额。" color="bg-amber-100 text-amber-600">
          <input
            ref={currencyInputRef}
            type="file"
            accept="image/jpeg,image/png"
            capture="environment"
            className="hidden"
            onChange={(e) => handleCurrencyFile(e.target.files?.[0])}
            id="currency-file"
          />
          <label
            htmlFor="currency-file"
            className="inline-block w-full text-center rounded-lg bg-amber-500 text-white py-2.5 text-sm font-medium cursor-pointer hover:bg-amber-600"
          >
            {currencyLoading ? '识别中...' : '拍照 / 选择纸币照片'}
          </label>
          <p className="text-xs text-gray-400 mt-2">提示：正对钞票正面，保持光线充足。</p>
          <ResultBox result={currencyResult} loading={currencyLoading} />
        </Card>
      </div>
    </div>
  );
}