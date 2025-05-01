//ses_extractor_frontend/src/app/api/auth/route.ts
import {  NextResponse } from 'next/server';
// 你的 Google OAuth2 的设置
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!;
const REDIRECT_URI = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI!; // 登录成功后返回的地址
const SCOPES = [
  'https://www.googleapis.com/auth/userinfo.email',
  'https://www.googleapis.com/auth/userinfo.profile',
  'https://www.googleapis.com/auth/gmail.readonly',
];

// 处理GET请求
export async function GET() {
  const state = Math.random().toString(36).substring(7); // 生成一个随机state防止CSRF攻击
  const oauthUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');

  oauthUrl.searchParams.set('client_id', CLIENT_ID);
  oauthUrl.searchParams.set('redirect_uri', REDIRECT_URI);
  oauthUrl.searchParams.set('response_type', 'code');
  oauthUrl.searchParams.set('scope', SCOPES.join(' '));
  oauthUrl.searchParams.set('access_type', 'offline');
  oauthUrl.searchParams.set('prompt', 'consent');
  oauthUrl.searchParams.set('state', state);

  return NextResponse.redirect(oauthUrl.toString());
}