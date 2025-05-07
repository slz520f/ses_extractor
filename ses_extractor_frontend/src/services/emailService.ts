// ses_extractor_frontend/src/services/emailService.ts
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://ses-extractor.onrender.com' 
  : 'http://localhost:8000';


// any 型を具体的な型に置き換え
interface RawEmailResponse {
  success: boolean;
  data: {
    body: string;
    headers: Record<string, string>;
    raw_json?: any; // 必要に応じてさらに詳細な型を定義
  };
}
  
// OAuth2トークンとJWTを取得
export const fetchTokenWithCode = async (code: string) => {
  const response = await fetch(`${API_BASE_URL}/auth/callback`, {
    method: 'POST',
    body: JSON.stringify({ code }),
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) throw new Error('ログインに失敗しました');
  const data = await response.json();
  // バックエンドからjwt_tokenフィールドが返されることを想定
  return data.jwt_token; // JWTのみ返す
};

export const fetchEmails = async (jwtToken: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/emails/fetch_emails`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${jwtToken}` },
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error("APIエラー詳細:", {
        status: response.status,
        statusText: response.statusText,
        errorData,
      });
      throw new Error(`メール取得失敗: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error("リクエスト失敗詳細:", error);
    throw error;
  }
};

// 直近14日間のメールを取得
export const fetchRecentEmails = async (jwtToken: string) => {
  const response = await fetch(`${API_BASE_URL}/emails/recent`, {
    method: 'GET',
    headers: { 
      Authorization: `Bearer ${jwtToken}`, 
      'Content-Type': 'application/json' 
    },
  });
  if (!response.ok) throw new Error('直近14日間のメール取得に失敗');
  return response.json();
};

// 全てのメールを解析して保存
export const parseAndSaveAllEmails = async (jwtToken: string) => {
  let apiKey: string | null = null;
  if (typeof window !== 'undefined') {
    apiKey = localStorage.getItem('gemini_api_key');
  }
  const response = await fetch(`${API_BASE_URL}/emails/parse_and_save_all_emails`, {
    method: 'POST',
    body: JSON.stringify({ apiKey }),
    headers: { 
      Authorization: `Bearer ${jwtToken}`, 
      'Content-Type': 'application/json' 
    },
  });
  if (!response.ok) throw new Error('メールの解析と保存に失敗');
  return response.json();
};

export const getRawEmail = async (rawEmailId: number, jwtToken: string,): Promise<RawEmailResponse> => {
  const url = `${API_BASE_URL}/emails/get_raw_email/${rawEmailId}`;
  
  try {
    console.log('生メールリクエスト中、URL:', url); // デバッグログ
    const response = await fetch(url, {
      method: 'GET',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${jwtToken}` ,
      },
    });

    console.log('レスポンス受信、ステータスコード:', response.status); // デバッグログ
    
    if (!response.ok) {
      let errorDetails = '';
      try {
        errorDetails = await response.text();
        console.error('エラー詳細:', errorDetails); // デバッグログ
      } catch (e) {
        console.error('エラーレスポンスの解析失敗:', e); // デバッグログ
      }
      throw new Error(`サーバーエラー (${response.status}): ${errorDetails || '詳細なエラー情報なし'}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API呼び出しエラー詳細:', {
      url,
      error,
      timestamp: new Date().toISOString()
    }); // 詳細エラーログ
    throw error;
  }
};