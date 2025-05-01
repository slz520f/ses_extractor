// components/ApiKeyInput.tsx
'use client';
import { useState, useEffect } from 'react';

export default function ApiKeyInput() {
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key');
    if (savedKey) setApiKey(savedKey);
  }, []);

  const handleSave = () => {
    localStorage.setItem('gemini_api_key', apiKey);
    alert('✅ API Key 已保存');
  };

  return (
    <div className="flex items-center space-x-2 mt-4 mb-4">
      <label className="text-sm font-medium text-gray-700">Gemini API Key：</label>
      <input
        type="password"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        className="w-80 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="ここに入力してください"
      />
      <button
        onClick={handleSave}
        className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition shadow"
      >
        保存
      </button>
    </div>
  )
}  
