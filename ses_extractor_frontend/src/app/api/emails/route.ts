// // ses_extractor_frontend/src/app/api/emails/route.ts



// ses_extractor_frontend/src/app/api/emails/route.ts
import { NextResponse } from 'next/server';

// 处理POST请求来获取邮件
export async function POST() {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/emails/fetch`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // 如果你有用cookie认证，可以保留
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching mails:', error);
    return NextResponse.json({ error: 'Error fetching mails' }, { status: 500 });
  }
}
