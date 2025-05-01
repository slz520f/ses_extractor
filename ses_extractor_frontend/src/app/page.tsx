'use client';

import { useState } from 'react';

export default function HomePage() {
  const [loading, setLoading] = useState(false); // ログインボタンの読み込み状態
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    try {
      // const response = await fetch('http://localhost:8000/auth/login', {
      const response = await fetch('https://ses-extractor.onrender.com/auth/login', {
        method: 'GET',
      });

      if (response.ok) {
        const { redirect_url } = await response.json();
        // ログインコールバックページへリダイレクト
        window.location.href = redirect_url;
      } else {
        throw new Error('ログインURLの取得に失敗しました');
      }
    } catch (error) {
      console.error('ログイン失敗', error);
      setError('ログインに失敗しました。再試行してください');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      <h1 className="text-3xl font-bold mb-4">SES案件管理システム</h1>
      <button
        onClick={handleLogin}
        className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        disabled={loading}
      >
        {loading ? 'ログイン中...' : 'Googleアカウントでログイン'}
      </button>
      {error && <p className="mt-4 text-red-500">{error}</p>}
    </div>
  );
}