


'use client';

import { useEmailAuth } from '@/hooks/useEmailAuth';
import { fetchEmails, parseAndSaveAllEmails, fetchRecentEmails } from '@/services/emailService';
import { EmailTable } from '@/components/EmailTable';
import { useEffect, useState, useRef } from 'react';
import {
  Button, CloseButton, Drawer, Portal, DrawerBody, DrawerHeader, DrawerFooter, DrawerContent, DrawerTitle,
  DrawerBackdrop, DrawerPositioner, DrawerCloseTrigger, DrawerActionTrigger,
  Box, Text, Flex,ProgressRoot,ProgressTrack,ProgressRange
} from "@chakra-ui/react";
import { createStandaloneToast } from '@chakra-ui/toast';
import ApiKeyInput from '@/components/ApiKeyInput';

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
  const [recentEmails, setRecentEmails] = useState<Email[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);  
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [fetchedEmailCount, setFetchedEmailCount] = useState<number | null>(null);
  const [parsedEmailCount, setParsedEmailCount] = useState<number | null>(null);
  const [nextFetchTime, setNextFetchTime] = useState<string>('');
  const { toast } = createStandaloneToast();
  const [previousFetchedEmailCount, setPreviousFetchedEmailCount] = useState<number | null>(null);
  const [fetchProgress, setFetchProgress] = useState(0); // 新增：记录找邮件的进度
  const [parseProgress, setParseProgress] = useState(0); // 新增：记录解析邮件的进度
  const [logs, setLogs] = useState<string[]>([]); 


 
  const retryTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  // 计算下次获取时间
  const calculateNextFetchTime = () => {
    const now = new Date();
    const nextHour = new Date(now);
    nextHour.setHours(nextHour.getHours() + 1);
    nextHour.setMinutes(0);
    nextHour.setSeconds(0);
    return nextHour.toLocaleTimeString();
  };

  useEffect(() => {
    setNextFetchTime(calculateNextFetchTime());
    const timer = setInterval(() => {
      setNextFetchTime(calculateNextFetchTime());
    }, 60000); // 每分钟更新一次
    
    return () => clearInterval(timer);
  }, []);

  const handleFetchEmails = async () => {
    if (!accessToken) return;

    const result = await fetchEmails(accessToken);
  const newFetchedCount = result.emails?.length || 0;

  // 如果有之前获取过邮件的数量，计算新邮件数量
  if (previousFetchedEmailCount !== null) {
    const newEmailsCount = newFetchedCount - previousFetchedEmailCount;
    setFetchedEmailCount(newEmailsCount >= 0 ? newEmailsCount : 0); // 显示新邮件数量
  } else {
    setFetchedEmailCount(newFetchedCount);  // 第一次获取，直接显示所有邮件数量
  }

  // 更新上次获取邮件的数量
  setPreviousFetchedEmailCount(newFetchedCount);
  setFetchProgress(100); // 设置为100表示邮件找完了
};

  // 清除重试定时器
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  const handleParseAndSaveAllEmails = async () => {
    if (!accessToken) return;
    
    setIsProcessing(true);
    setParseProgress(0); // 重置进度条
    setLogs([]); // 重置日志

    
    try {
      const BATCH_SIZE = 20;
      const totalEmails = fetchedEmailCount || 0;
      let processedCount = 0;
      let successCount = 0;
      
      while (processedCount < totalEmails) {
        const batchEnd = Math.min(processedCount + BATCH_SIZE, totalEmails);
      
        
        try {
          const result = await parseAndSaveAllEmails(accessToken);
          const parsedCount = result.parsedEmails?.length || 0;
          successCount += parsedCount;
          processedCount = batchEnd;

          // 更新进度条
          const progress = Math.floor((processedCount / totalEmails) * 100);
          setParseProgress(progress);

          // 检查并更新日志
          const logMessages = result.parsedEmails || [];
          if (Array.isArray(logMessages)) {
            setLogs(prevLogs => [...prevLogs, ...logMessages]);  // 合并日志
          } else {
            console.error("logMessages is not an array", logMessages);
          }
        
          if (result.parsedEmails?.length) {
            setRecentEmails(prev => [...result.parsedEmails, ...prev]);
          }
          
        } catch (err: unknown) {
          if (err instanceof Error && err.message?.includes('API rate limit')) {
           
            await new Promise(resolve => {
              retryTimeoutRef.current = setTimeout(resolve, 30000);
            });
            continue;
          }
          throw err;
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
      
      setParsedEmailCount(successCount);
      toast({
        title: '解析完了',
        description: `${successCount}通のメールを解析・保存しました`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      // 解析完成后重新加载邮件列表
      await loadRecentEmails();
      
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'メールの解析に失敗しました';
      toast({
        title: 'エラー',
        description: errorMessage,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsProcessing(false);
      // setIsModalOpen(false);
    }
  };
  // 加载最新邮件
  const loadRecentEmails = async () => {
    if (!accessToken) return;
    const result = await fetchRecentEmails(accessToken);
    setRecentEmails(result.emails || []);
  };

  // 手动立即触发
  const handleManualTrigger = async () => {
    await handleFetchEmails();
    await handleParseAndSaveAllEmails();
    setNextFetchTime(calculateNextFetchTime()); // 重置时间
  };

  const drawerTriggerRef = useRef<HTMLButtonElement>(null);

  const handleEmailClick = (email: Email) => {
    setSelectedEmail(email);
    drawerTriggerRef.current?.click();
  };

  useEffect(() => {
    const loadRecentEmails = async () => {
      if (!accessToken) return;
      const result = await fetchRecentEmails(accessToken);
      setRecentEmails(result.emails || []);
    };
    loadRecentEmails();
  }, [accessToken]);

  if (loading) return <p>ログイン中...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="flex flex-col min-h-screen bg-gray-100 text-gray-800 w-full">
      <p className="text-xl font-semibold">ようこそ、{userEmail}</p>
  
      {/* === 操作行：分为左右两组按钮 === */}
      <div className="flex items-center justify-between flex-wrap gap-4 bg-white p-4 rounded shadow-md">
  
        {/* 左：次回自動取得時間 + 今すぐ実行 */}
        <div className="flex items-center gap-3 pr-6 border-r border-gray-300">
          <span className="text-sm font-bold text-gray-700">次回自動取得時間:</span>
          <span className="text-md text-blue-600">{nextFetchTime}</span>
          <button
            onClick={handleManualTrigger}
            className="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded shadow min-w-[120px]"
            disabled={isProcessing}
          >
            今すぐ実行
          </button>
        </div>
  
        {/* 右：其他操作按钮 */}
        <div className="flex items-center flex-wrap gap-3">
          <button
            onClick={handleFetchEmails}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded shadow min-w-[120px]"
          >
            メールを探す
          </button>
  
          <div className="px-3 py-2 bg-white rounded shadow-md">
            <ApiKeyInput />
          </div>
  
          <button
            onClick={handleParseAndSaveAllEmails}
            className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 text-white rounded shadow min-w-[160px]"
            disabled={isProcessing}
          >
            {isProcessing ? '処理中...' : 'すべてのメールを解析'}
          </button>
        </div>
      </div>
  
      {/* === 状态栏 === */}
      <div className="text-sm text-gray-700 space-y-1 p-4">
        {fetchProgress < 100 && (
          <div>
            <p>メール取得進捗: {fetchProgress}%</p>
            <div className="w-60 h-2 bg-gray-200 rounded">
              <div
                className="h-full bg-blue-500 rounded"
                style={{ width: `${fetchProgress}%` }}
              ></div>
            </div>
          </div>
        )}
  
        {parseProgress < 100 && (
          <div>
            <p>解析進捗: {parseProgress}%</p>
            <div className="w-60 h-2 bg-gray-200 rounded">
              <div
                className="h-full bg-green-500 rounded"
                style={{ width: `${parseProgress}%` }}
              ></div>
            </div>
          </div>
        )}
        {/* 日志显示 */}
          <div className="logs">
            {logs.map((log, index) => (
              <p key={index}>{log}</p>
            ))}
          </div>
  
        {fetchedEmailCount !== null && fetchedEmailCount > 0 && (
          <p>{fetchedEmailCount} 通の新しいメールが見つかりました</p>
        )}
  
        {fetchedEmailCount !== null && fetchedEmailCount === 0 && (
          <p>新しいメールはありません</p>
        )}
  
        {parsedEmailCount !== null && (
          <p>{parsedEmailCount} 通のメールを正常に解析して保存しました</p>
        )}
      </div>
  
      {/* === メール一覧表示区域（可滚动） === */}
      <div className="w-full flex-1 px-4 overflow-auto">
        {recentEmails.length > 0 ? (
          <EmailTable emails={recentEmails} onEmailClick={handleEmailClick} />
        ) : (
          <p className="text-gray-500 text-center">
            最近14日間のメールは見つかりませんでした
          </p>
        )}
      </div>
  
      {/* === Drawer: メール詳細表示 === */}
      <Drawer.Root placement="end">
        <Drawer.Trigger asChild>
          <button ref={drawerTriggerRef} className="hidden" />
        </Drawer.Trigger>
  
        <Portal>
          <DrawerBackdrop />
          <DrawerPositioner>
            <DrawerContent>
              <DrawerHeader>
                <DrawerTitle>メールの詳細</DrawerTitle>
              </DrawerHeader>
              <DrawerBody>
                {selectedEmail ? (
                  <div className="space-y-2">
                    <p><strong>送信者：</strong>{selectedEmail.sender_email}</p>
                    <p><strong>件名：</strong>{selectedEmail.subject}</p>
                    <p><strong>日付：</strong>{selectedEmail.received_at}</p>
                    <div>
                      <strong>案件内容：</strong>
                      <p>{selectedEmail.project_description}</p>
                    </div>
                    <p><strong>必須スキル：</strong>{Array.isArray(selectedEmail.required_skills) ? selectedEmail.required_skills.join(', ') : '-'}</p>
                    <p><strong>尚可スキル：</strong>{Array.isArray(selectedEmail.optional_skills) ? selectedEmail.optional_skills.join(', ') : '-'}</p>
                    <p><strong>勤務地：</strong>{selectedEmail.location}</p>
                    <p><strong>単価：</strong>{selectedEmail.unit_price}</p>
                  </div>
                ) : (
                  <p>読み込み中...</p>
                )}
              </DrawerBody>
              <DrawerFooter className="flex justify-end space-x-2">
                <DrawerActionTrigger asChild>
                  <Button variant="outline">閉じる</Button>
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
  )
}  