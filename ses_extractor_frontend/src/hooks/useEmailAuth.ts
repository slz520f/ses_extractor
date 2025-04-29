// hooks/useEmailAuth.ts

import { useEffect, useState } from 'react';
import { fetchTokenWithCode } from '@/services/emailService';

export const useEmailAuth = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    const fetchToken = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const email = urlParams.get('email');
      const token = urlParams.get('access_token');
      const code = urlParams.get('code');

      if (email && token) {
        setUserEmail(email);
        setAccessToken(token);
        localStorage.setItem('user_email', email);
        localStorage.setItem('access_token', token);
        setLoading(false);
      } else if (code) {
        try {
          const { access_token, user_email } = await fetchTokenWithCode(code);
          setUserEmail(user_email);
          setAccessToken(access_token);
          localStorage.setItem('user_email', user_email);
          localStorage.setItem('access_token', access_token);
          setLoading(false);
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

    fetchToken();
  }, []);

  return { loading, error, userEmail, accessToken };
};
