/**
 * 常用地址管理页。
 *
 * 两条入口并存：
 * - 语音：说“添加地址，公司，xxx”“删除公司地址”“查看常用地址”；
 * - 页面：本页表单，方便明眼人协助维护。
 *
 * 数据真实存储在 MySQL（user_addresses 表）。
 */

import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  createAddress,
  deleteAddress,
  listAddresses,
  updateAddress,
  type UserAddress,
} from '../services/addressService';
import { speak } from '../services/tts';
import { useVoiceControl } from '../voice/VoiceControlProvider';

export default function AddressPage() {
  const navigate = useNavigate();
  const { startListening, listening } = useVoiceControl();

  const [items, setItems] = useState<UserAddress[]>([]);
  const [label, setLabel] = useState('');
  const [address, setAddress] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await listAddresses());
    } catch {
      setError('加载常用地址失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const resetForm = () => {
    setLabel('');
    setAddress('');
    setEditingId(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setMessage('');

    if (!label.trim() || !address.trim()) {
      const text = '别名和详细地址都要填写。';
      setError(text);
      void speak(text);
      return;
    }

    setSaving(true);
    try {
      if (editingId !== null) {
        const updated = await updateAddress(editingId, { label: label.trim(), address: address.trim() });
        const text = `已更新${updated.label}的地址。`;
        setMessage(text);
        void speak(text);
      } else {
        const created = await createAddress({ label: label.trim(), address: address.trim() });
        const text = `已保存${created.label}的地址。`;
        setMessage(text);
        void speak(text);
      }
      resetForm();
      await load();
    } catch (err: unknown) {
      const text =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        '保存失败，请稍后重试';
      setError(text);
      void speak(text);
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item: UserAddress) => {
    setEditingId(item.id);
    setLabel(item.label);
    setAddress(item.address);
    setMessage('');
    setError('');
    void speak(`正在修改${item.label}，请说出或输入新的地址。`);
  };

  const handleDelete = async (item: UserAddress) => {
    if (pendingDeleteId !== item.id) {
      setPendingDeleteId(item.id);
      void speak(`再点一次确认删除${item.label}。`);
      return;
    }
    try {
      await deleteAddress(item.id);
      const text = `已删除${item.label}。`;
      setMessage(text);
      setPendingDeleteId(null);
      void speak(text);
      await load();
    } catch {
      const text = '删除失败，请稍后重试';
      setError(text);
      void speak(text);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-40 sm:pb-48">
      <header className="bg-white border-b border-gray-100 px-4 sm:px-6 py-3 sm:py-5 flex items-center gap-3 sm:gap-4">
        <button
          type="button"
          onClick={() => navigate('/app')}
          className="px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-800 text-base sm:text-lg font-semibold
                     focus:outline-none focus:ring-4 focus:ring-gray-300"
          aria-label="返回主页"
        >
          返回
        </button>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">常用地址</h1>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 sm:space-y-8">
        {/* 语音提示 */}
        <section className="rounded-2xl sm:rounded-3xl bg-[#0d2847] text-white p-4 sm:p-6">
          <h2 className="text-xl sm:text-2xl font-bold mb-3">也可以用说的</h2>
          <ul className="space-y-2 text-base sm:text-lg text-blue-100">
            <li>· 添加地址，公司，北京市朝阳区某某路一号</li>
            <li>· 把公司地址改成北京市海淀区某某路二号</li>
            <li>· 删除公司地址</li>
            <li>· 查看常用地址</li>
          </ul>
          <button
            type="button"
            onClick={startListening}
            className={`mt-5 w-full py-4 rounded-2xl text-xl font-bold
              focus:outline-none focus:ring-4 focus:ring-blue-300
              ${listening ? 'bg-red-500 animate-pulse' : 'bg-white text-[#0d2847]'}`}
          >
            {listening ? '正在聆听，请说话' : '点一下开始说话'}
          </button>
        </section>

        {error && (
          <p className="rounded-2xl bg-red-50 border-2 border-red-200 px-5 py-4 text-lg text-red-700" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="rounded-2xl bg-green-50 border-2 border-green-200 px-5 py-4 text-lg text-green-800" role="status">
            {message}
          </p>
        )}

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl sm:rounded-3xl p-4 sm:p-6 space-y-4 sm:space-y-5 shadow-sm">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">
            {editingId !== null ? '修改地址' : '添加地址'}
          </h2>

          <div>
            <label htmlFor="label" className="block text-base sm:text-lg font-semibold text-gray-700 mb-2">
              别名（例如：家、公司、健身房）
            </label>
            <input
              id="label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="家"
              className="w-full px-4 sm:px-5 py-3 sm:py-4 rounded-2xl border-2 border-gray-300 text-lg sm:text-xl
                         focus:outline-none focus:border-[#1a4a8a] focus:ring-4 focus:ring-blue-200"
            />
          </div>

          <div>
            <label htmlFor="address" className="block text-base sm:text-lg font-semibold text-gray-700 mb-2">
              详细地址
            </label>
            <input
              id="address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="北京市朝阳区幸福小区3号楼"
              className="w-full px-4 sm:px-5 py-3 sm:py-4 rounded-2xl border-2 border-gray-300 text-lg sm:text-xl
                         focus:outline-none focus:border-[#1a4a8a] focus:ring-4 focus:ring-blue-200"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-3 sm:py-4 rounded-2xl bg-[#1a4a8a] hover:bg-[#153d75] text-white text-lg sm:text-xl font-bold
                         disabled:opacity-60 focus:outline-none focus:ring-4 focus:ring-blue-300"
            >
              {saving ? '保存中…' : editingId !== null ? '保存修改' : '保存地址'}
            </button>
            {editingId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="px-4 sm:px-6 py-3 sm:py-4 rounded-2xl bg-gray-100 hover:bg-gray-200 text-gray-800 text-lg sm:text-xl font-semibold
                           focus:outline-none focus:ring-4 focus:ring-gray-300"
              >
                取消
              </button>
            )}
          </div>
        </form>

        {/* 列表 */}
        <section className="space-y-4">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">已保存的地址（{items.length}）</h2>

          {loading && <p className="text-lg text-gray-500">加载中…</p>}
          {!loading && items.length === 0 && (
            <p className="text-lg text-gray-500">还没有常用地址，先添加一个吧。</p>
          )}

          {items.map((item) => (
            <article key={item.id} className="bg-white rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-sm space-y-3 sm:space-y-4">
              <div>
                <p className="text-xl sm:text-2xl font-bold text-gray-900">{item.label}</p>
                <p className="text-base sm:text-lg text-gray-600 mt-1 break-words">{item.address}</p>
              </div>
              <div className="flex gap-3 sm:gap-4">
                <button
                  type="button"
                  onClick={() => startEdit(item)}
                  className="flex-1 py-2.5 sm:py-3 rounded-2xl bg-blue-50 hover:bg-blue-100 text-[#1a4a8a] text-base sm:text-lg font-bold
                             focus:outline-none focus:ring-4 focus:ring-blue-200"
                >
                  修改
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(item)}
                  className={`flex-1 py-2.5 sm:py-3 rounded-2xl text-base sm:text-lg font-bold focus:outline-none focus:ring-4 focus:ring-red-200
                    ${pendingDeleteId === item.id ? 'bg-red-600 text-white' : 'bg-red-50 hover:bg-red-100 text-red-700'}`}
                >
                  {pendingDeleteId === item.id ? '确认删除' : '删除'}
                </button>
              </div>
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
