

// // ses_extractor_frontend/src/services/emailService.ts
// // 根据环境变量决定使用哪个API地址
// const API_BASE_URL = process.env.NODE_ENV === 'production' 
//   ? 'https://ses-extractor.onrender.com' 
//   : 'http://localhost:8000';

// export const fetchTokenWithCode = async (code: string) => {
//   const response = await fetch(`${API_BASE_URL}/auth/callback`, {
//     method: 'POST',
//     body: JSON.stringify({ code }),
//     headers: {
//       'Content-Type': 'application/json',
//     },
//   });
//   if (!response.ok) throw new Error('登录失败');
//   return response.json();
// };

// export const fetchEmails = async (accessToken: string) => {
//   const response = await fetch(`${API_BASE_URL}/emails/fetch_emails`, {
//     method: 'GET',
//     headers: { Authorization: `Bearer ${accessToken}` },
//   });
//   if (!response.ok) throw new Error('获取邮件失败');
//   return response.json();
// };

// export const parseAndSaveAllEmails = async (accessToken: string) => {
//   const response = await fetch(`${API_BASE_URL}/emails/parse_and_save_all_emails`, {
//     method: 'POST',
//     headers: { 
//       Authorization: `Bearer ${accessToken}`, 
//       'Content-Type': 'application/json' 
//     },
//   });
//   if (!response.ok) throw new Error('解析和保存邮件失败');
//   return response.json();
// };

// export const fetchRecentEmails = async (accessToken: string) => {
//   const response = await fetch(`${API_BASE_URL}/emails/recent`, {
//     method: 'GET',
//     headers: { 
//       Authorization: `Bearer ${accessToken}`, 
//       'Content-Type': 'application/json' 
//     },
//   });
//   if (!response.ok) throw new Error('获取近14天邮件失败');
//   return response.json();
// };



// ses_extractor_frontend/src/services/emailService.ts
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://ses-extractor.onrender.com' 
  : 'http://localhost:8000';

// 获取OAuth2令牌
export const fetchTokenWithCode = async (code: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/callback`, {
    method: 'POST',
    body: JSON.stringify({ code }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error('登录失败');
  return response.json();
};

// 获取所有邮件
export const fetchEmails = async (accessToken: string) => {
  const response = await fetch(`${API_BASE_URL}/emails/fetch_emails`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new Error('获取邮件失败');
  return response.json();
};

// 获取近14天的邮件
export const fetchRecentEmails = async (accessToken: string) => {
  const response = await fetch(`${API_BASE_URL}/emails/recent`, {
    method: 'GET',
    headers: { 
      Authorization: `Bearer ${accessToken}`, 
      'Content-Type': 'application/json' 
    },
  });
  if (!response.ok) throw new Error('获取近14天邮件失败');
  return response.json();
};

// 解析并保存所有邮件
export const parseAndSaveAllEmails = async (accessToken: string) => {
  const response = await fetch(`${API_BASE_URL}/emails/parse_and_save_all_emails`, {
    method: 'POST',
    headers: { 
      Authorization: `Bearer ${accessToken}`, 
      'Content-Type': 'application/json' 
    },
  });
  if (!response.ok) throw new Error('解析和保存邮件失败');
  return response.json();
};
