'use client';

import { useEmailAuth } from '@/hooks/useEmailAuth';
import { fetchEmails, parseAndSaveAllEmails, fetchRecentEmails } from '@/services/emailService';
import {EmailTable} from '@/components/EmailTable';
import { useEffect, useState, useRef } from 'react';

import {Button,CloseButton,Drawer,Portal,DrawerBody,DrawerHeader,DrawerFooter,DrawerContent,DrawerTitle,DrawerBackdrop,DrawerPositioner,DrawerCloseTrigger,DrawerActionTrigger,} from "@chakra-ui/react";
interface Email {
  sender_email: string;
  subject: string;
  received_at: string;
  project_description: string;
  required_skills: string[];
  optional_skills: string[];
  location: string;
  unit_price: string;
}



export default function CallbackPage() {
  const { loading, error, userEmail, accessToken } = useEmailAuth();
  const [emails, setEmails] = useState<Email[]>([]);
  const [parsedEmails, setParsedEmails] = useState<Email[]>([]);
  const [recentEmails, setRecentEmails] = useState<Email[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);  
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [fetchedEmailCount, setFetchedEmailCount] = useState<number | null>(null);
  const [parsedEmailCount, setParsedEmailCount] = useState<number | null>(null);


  const handleFetchEmails = async () => {
    if (!accessToken) return;
    const result = await fetchEmails(accessToken);
    const count = result.messages?.length || 0;
    setEmails(result.messages || []);
    setFetchedEmailCount(count);  // 👈 更新数量
  };

  const handleParseAndSaveAllEmails = async () => {
    if (!accessToken) return;
    setIsProcessing(true);
    const result = await parseAndSaveAllEmails(accessToken);
    const parsedCount = result.parsedEmails?.length || 0;
    setParsedEmails(result.parsedEmails || []);
    setParsedEmailCount(parsedCount);  // 👈 更新数量
    
    // 重新加载解析后的 recentEmails
    const recent = await fetchRecentEmails(accessToken);
    setRecentEmails(recent.emails || []);
    setIsProcessing(false);
  };
  // ref for programmatically opening drawer
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);

  const handleEmailClick = (email: any) => {
    setSelectedEmail(email);
    drawerTriggerRef.current?.click(); // simulate click to open drawer
  };


  useEffect(() => {
    const loadRecentEmails = async () => {
      if (!accessToken) return;
      const result = await fetchRecentEmails(accessToken);
      setRecentEmails(result.emails || []);
    };
    loadRecentEmails();
  }, [accessToken]);

  if (loading) return <p>正在登录...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="flex flex-col items-center justify-start min-h-screen py-10 bg-gray-100 text-gray-800 w-full">
      <p className="text-2xl font-semibold mb-4">欢迎，{userEmail}</p>
      <div className="space-x-4 mb-6">
        <button
          onClick={handleFetchEmails}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow transition"
        >
          找邮件
        </button>
        <button
          onClick={handleParseAndSaveAllEmails}
          className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg shadow transition"
          disabled={isProcessing}
        >
          {isProcessing ? '处理中...' : '解析并保存所有邮件'}
        </button>
        <div className="mt-2 text-sm text-gray-700 space-y-1">
          {fetchedEmailCount !== null && (
            <p>找到 {fetchedEmailCount} 封邮件</p>
          )}
          {parsedEmailCount !== null && (
            <p>成功解析并保存 {parsedEmailCount} 封邮件</p>
          )}
        </div>

      </div>

     

      <div className="w-full ">
        {recentEmails.length > 0 ? (
          <EmailTable emails={recentEmails} onEmailClick={handleEmailClick}/>
        ) : (
          <p className="text-gray-500 text-center">没有找到最近5天的邮件</p>
        )}
      </div>
      {/* Drawer 用于显示邮件详细信息 */}
      <Drawer.Root placement="end">
        {/* 用于程序控制 drawer 打开 */}
        <Drawer.Trigger asChild>
          <button ref={drawerTriggerRef} className="hidden" />
        </Drawer.Trigger>

        <Portal>
          <DrawerBackdrop />
          <DrawerPositioner>
            <DrawerContent>
              <DrawerHeader>
                <DrawerTitle>邮件详情</DrawerTitle>
              </DrawerHeader>
              <DrawerBody>
                {selectedEmail ? (
                  <div className="space-y-2">
                    <p><strong>发件人：</strong>{selectedEmail.sender_email}</p>
                    <p><strong>主题：</strong>{selectedEmail.subject}</p>
                    <p><strong>日期：</strong>{selectedEmail.received_at}</p>
                    <div>
                      <strong>案件内容：</strong>
                      <p>{selectedEmail.project_description}</p>
                    </div>
                    <p><strong>必須スキル：</strong>{selectedEmail.required_skills.join(', ')}</p>
                    <p><strong>尚可スキル：</strong>{selectedEmail.optional_skills.join(', ')}</p>
                    <p><strong>勤務地：</strong>{selectedEmail.location}</p>
                    <p><strong>単価：</strong>{selectedEmail.unit_price}</p>
                  </div>
                ) : (
                  <p>加载中...</p>
                )}
              </DrawerBody>
              <DrawerFooter className="flex justify-end space-x-2">
                <DrawerActionTrigger asChild>
                  <Button variant="outline">关闭</Button>
                </DrawerActionTrigger>
                <Button colorScheme="blue">保存</Button>
              </DrawerFooter>
              <DrawerCloseTrigger asChild>
                <CloseButton size="sm" className="absolute top-4 right-4" />
              </DrawerCloseTrigger>
            </DrawerContent>
          </DrawerPositioner>
        </Portal>
      </Drawer.Root>
    </div>

  );
}
