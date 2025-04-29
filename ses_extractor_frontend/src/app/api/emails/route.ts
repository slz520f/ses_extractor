import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    // 调用后端的FastAPI接口
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
