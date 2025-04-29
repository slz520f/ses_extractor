'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false); // 登录按钮的加载状态
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/auth/login', {
        method: 'GET',
      });

      if (response.ok) {
        const { redirect_url } = await response.json();
        // 重定向到登录回调页面
        window.location.href = redirect_url;
      } else {
        throw new Error('Failed to fetch login URL');
      }
    } catch (error) {
      console.error('Login failed', error);
      setError('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
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
