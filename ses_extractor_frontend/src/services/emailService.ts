// services/emailService.ts

export const fetchTokenWithCode = async (code: string) => {
    const response = await fetch('http://localhost:8000/auth/callback', {
      method: 'POST',
      body: JSON.stringify({ code }),
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) throw new Error('登录失败');
    return response.json();
  };
  
  export const fetchEmails = async (accessToken: string) => {
    const response = await fetch('http://localhost:8000/emails/fetch_emails', {
      method: 'GET',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) throw new Error('获取邮件失败');
    return response.json();
  };
  
  export const parseAndSaveAllEmails = async (accessToken: string) => {
    const response = await fetch('http://localhost:8000/emails/parse_and_save_all_emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('解析和保存邮件失败');
    return response.json();
  };
  
  export const fetchRecentEmails = async (accessToken: string) => {
    const response = await fetch('http://localhost:8000/emails/recent', {
      method: 'GET',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('获取近5天邮件失败');
    return response.json();
  };
  