'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function CallbackPage() {
  const router = useRouter();
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [emails, setEmails] = useState<any[]>([]); // 存储获取的邮件
  const [parsedEmails, setParsedEmails] = useState<any[]>([]); // 存储解析的邮件
  const [emailToParse, setEmailToParse] = useState<string | null>(null); // 当前要解析的邮件ID

  useEffect(() => {
    const fetchToken = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const email = urlParams.get('email');
      const accessToken = urlParams.get('access_token');
      const code = urlParams.get('code');

      // 检查 email 和 access_token 是否存在
      if (email && accessToken) {
        setUserEmail(email);
        setAccessToken(accessToken);
        localStorage.setItem('user_email', email);
        localStorage.setItem('access_token', accessToken);
        setLoading(false);
      } else if (code) {
        try {
          // 如果只有 code，向后端请求 token 和用户信息
          const response = await fetch('http://localhost:8000/auth/callback', {
            method: 'POST',
            body: JSON.stringify({ code }),
            headers: {
              'Content-Type': 'application/json',
            },
          });

          if (response.ok) {
            const { access_token, user_email } = await response.json();
            setUserEmail(user_email);
            setAccessToken(access_token);

            // 存储 token 和 email 到 localStorage
            localStorage.setItem('access_token', access_token);
            localStorage.setItem('user_email', user_email);
            setLoading(false);
          } else {
            throw new Error('登录失败');
          }
        } catch (error) {
          console.error('OAuth callback failed', error);
          setError('登录失败，请重试');
          setLoading(false);
        }
      } else {
        setError('授权信息缺失，请重试');
        setLoading(false);
      }
    };

    fetchToken(); // 在 useEffect 中调用异步函数

  }, [router]);

  const handleFetchEmails = async () => {
    if (!accessToken) {
      alert('没有获取到授权信息');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/emails/fetch_emails', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        const emailsData = await response.json();
        setEmails(emailsData.messages);
        alert('邮件获取成功');
      } else {
        throw new Error('获取邮件失败');
      }
    } catch (error) {
      console.error('获取邮件失败:', error);
      alert('获取邮件失败，请重试');
    }
  };

  const handleParseAndSaveAllEmails = async () => {
    if (!accessToken) {
      alert('没有获取到授权信息');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/emails/parse_and_save_all_emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        alert(result.message); // 显示保存结果
        setParsedEmails([]); // 清空解析结果
        setEmails([]); // 清空邮件列表
      } else {
        throw new Error('解析和保存邮件失败');
      }
    } catch (error) {
      console.error('解析和保存邮件失败:', error);
      alert('解析和保存邮件失败，请重试');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen">
      {loading ? (
        <p>正在登录...</p>
      ) : error ? (
        <p style={{ color: 'red' }}>{error}</p>
      ) : (
        <>
          <p>登录成功！</p>
          <p>欢迎，{userEmail}</p>
          <div className="mt-4">
            <button
              onClick={handleFetchEmails}
              className="px-6 py-2 bg-blue-500 text-white rounded mr-2"
            >
              找邮件
            </button>
            <button
              onClick={handleParseAndSaveAllEmails}
              className="px-6 py-2 bg-green-500 text-white rounded mr-2"
            >
              解析并保存所有邮件
            </button>
          </div>

          {/* 显示邮件列表 */}
          <div className="mt-4">
            <h3>邮件列表</h3>
            <ul>
              {emails.map((email: any) => (
                <li key={email.id}>
                  <p>{email.snippet}</p>
                  <button
                    onClick={() => setEmailToParse(email.id)}
                    className="text-blue-500"
                  >
                    选择解析
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* 显示解析后的邮件内容 */}
          {parsedEmails.length > 0 && (
            <div className="mt-4">
              <h3>解析结果</h3>
              <pre>{JSON.stringify(parsedEmails, null, 2)}</pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}
