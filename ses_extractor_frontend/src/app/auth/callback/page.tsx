//ses_extractor_frontend/src/app/auth/callback/page.tsx
'use client';

import { useEmailAuth } from '@/hooks/useEmailAuth';
import { fetchEmails, parseAndSaveAllEmails, fetchRecentEmails } from '@/services/emailService';
import { EmailTable } from '@/components/EmailTable';
import { useEffect, useState, useRef } from 'react';
import {
  Button, CloseButton, Drawer, Portal, DrawerBody, DrawerHeader, DrawerFooter, DrawerContent, DrawerTitle,
  DrawerBackdrop, DrawerPositioner, DrawerCloseTrigger, DrawerActionTrigger,
  Progress, Box, Text, VStack
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
  const [fetchProgress, setFetchProgress] = useState(0);
  const [parseProgress, setParseProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const retryTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const [isLoadingEmails, setIsLoadingEmails] = useState(false);

  // 计算下次获取时间
  const calculateNextFetchTime = () => {
    const now = new Date();
    const nextHour = new Date(now);
    nextHour.setHours(nextHour.getHours() + 1);
    nextHour.setMinutes(0);
    nextHour.setSeconds(0);
    return nextHour.toLocaleTimeString();
  };

  // 检查是否需要自动获取邮件
  const checkAutoFetch = () => {
    const now = new Date();
    const nextFetch = new Date(now);
    nextFetch.setHours(nextFetch.getHours() + 1);
    nextFetch.setMinutes(0);
    nextFetch.setSeconds(0);
    if (now >= nextFetch) {
      handleManualTrigger();
    }
  };

  // 设置定时器，每分钟检查一次时间
  useEffect(() => {
    const timer = setInterval(() => {
      setNextFetchTime(calculateNextFetchTime());
      checkAutoFetch();
    }, 60000);
    
    return () => clearInterval(timer);
  }, []);

  // 获取邮件函数 - 已优化进度条
  const handleFetchEmails = async () => {
    if (!accessToken) return;
    
    try {
      setFetchProgress(0);
      // 模拟进度动画
      for (let i = 0; i <= 90; i += 10) {
        await new Promise(resolve => setTimeout(resolve, 200));
        setFetchProgress(i);
      }

      const result = await fetchEmails(accessToken);
      const newFetchedCount = result.emails?.length || 0;
      
      // 完成进度
      setFetchProgress(100);
      await new Promise(resolve => setTimeout(resolve, 200));

      // 更新邮件计数
      if (previousFetchedEmailCount !== null) {
        const newEmailsCount = newFetchedCount - previousFetchedEmailCount;
        setFetchedEmailCount(Math.max(0, newEmailsCount));
      } else {
        setFetchedEmailCount(newFetchedCount);
      }

      setPreviousFetchedEmailCount(newFetchedCount);
      
      // 获取后自动加载最新邮件
      await loadRecentEmails();
      
    } catch (error) {
      console.error("获取邮件失败:", error);
      setFetchProgress(0);
      toast({
        title: '获取失败',
        description: '获取邮件时出错',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // 修改解析邮件的函数
  const handleParseAndSaveAllEmails = async () => {
    if (!accessToken || !fetchedEmailCount) return;

    setIsProcessing(true);
    setParseProgress(0);
    setParsedEmailCount(0);
    setLogs([]);

    try {
      let successCount = 0;
      
      // 添加完成状态标记
      let isCompleted = false;

      // 平滑进度更新函数
      const updateProgress = async (target: number) => {
        while (parseProgress < target && !isCompleted) {
          setParseProgress(prev => Math.min(prev + 2, target));
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      };

      // 实际解析任务
      const parseTask = async () => {
        try {
          const result = await parseAndSaveAllEmails(accessToken);
          const parsedCount = result.parsedCount || result.parsedEmails?.length || 0;
          successCount = parsedCount;
          
          // 确保最终进度为100%
          setParseProgress(100);
          setParsedEmailCount(parsedCount);
          
          // 更新日志
          if (Array.isArray(result.parsedEmails)) {
            setLogs(prev => [...prev, ...result.parsedEmails.map((e:Email) => e.subject)]);
          }

          // 标记完成
          isCompleted = true;
          
          return result;
        } catch (err) {
          throw err;
        }
      };

      // 并行执行进度更新和解析任务
      await Promise.all([
        updateProgress(95), // 留5%给完成动画
        parseTask()
      ]);

      // 最终完成动画
      await updateProgress(100);

      toast({
        title: '解析完成',
        description: `成功解析并保存 ${successCount} 封邮件`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });

      // 重新加载邮件列表
      await loadRecentEmails();

    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '解析邮件失败';
      toast({
        title: '错误',
        description: errorMessage,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setParseProgress(0);
    } finally {
      setIsProcessing(false);
    }
  };

  // 加载最新邮件 - 已优化
  const loadRecentEmails = async () => {
    if (!accessToken) return;
    
    setIsLoadingEmails(true);
    try {
      const result = await fetchRecentEmails(accessToken);
      // 使用函数式更新确保状态正确
      setRecentEmails(prev => {
        const newEmails = result.emails || [];
        // 去重逻辑
        const uniqueEmails = newEmails.filter(
          (email:Email, index:number, self:Email[]) =>
            index === self.findIndex(e => e.subject === email.subject)
        );
        return [...uniqueEmails];
      });
    } catch (error) {
      console.error("加载邮件失败:", error);
    } finally {
      setIsLoadingEmails(false);
    }
  };

  // 手动立即触发
  const handleManualTrigger = async () => {
    await handleFetchEmails();
    await handleParseAndSaveAllEmails();
    setNextFetchTime(calculateNextFetchTime());
  };

  // 点击邮件显示详情
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);
  const handleEmailClick = (email: Email) => {
    setSelectedEmail(email);
    drawerTriggerRef.current?.click();
  };

  // 初始化加载
  useEffect(() => {
    const initLoad = async () => {
      await loadRecentEmails();
      setNextFetchTime(calculateNextFetchTime());
    };
    initLoad();
  }, [accessToken]);

  // 加载状态显示
  if (loading) return <p>ログイン中...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="flex flex-col min-h-screen bg-gray-100 text-gray-800 w-full">
      {/* 欢迎标题 */}
      <p className="text-xl font-semibold">ようこそ、{userEmail}</p>
      
      {/* 操作行 */}
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
            disabled={isProcessing}
          >
            メールを探す
          </button>
  
          <div className="px-3 py-2 bg-white rounded shadow-md">
            <ApiKeyInput />
          </div>
  
          <button
            onClick={handleParseAndSaveAllEmails}
            className="px-4 py-2 text-sm bg-green-600 hover:bg-green-700 text-white rounded shadow min-w-[160px]"
            disabled={isProcessing || !fetchedEmailCount}
          >
            {isProcessing ? '処理中...' : 'すべてのメールを解析'}
          </button>
        </div>
      </div>
  
      {/* 状态栏 */}
      <div className="text-sm text-gray-700 space-y-1 p-4">
        {/* 获取进度条 */}
        {fetchProgress > 0 && fetchProgress < 100 && (
          <Box>
            <Text>メール取得進捗: {fetchProgress}%</Text>
            <Progress.Root value={fetchProgress} size="sm" colorScheme="blue" />
          </Box>
        )}
        
        {/* 解析进度条 */}
        {parseProgress > 0 && (
          <Box>
            <Text>解析進捗: {parseProgress}%</Text>
            <Progress.Root value={parseProgress} size="sm" colorScheme="green" />
          </Box>
        )}
        
        {/* 邮件数量信息 */}
        <VStack align="start" >
          {fetchedEmailCount !== null && (
            <Text>
              {fetchedEmailCount > 0 
                ? `${fetchedEmailCount} 通の新しいメールが見つかりました`
                : '新しいメールはありません'}
            </Text>
          )}
          
          {parsedEmailCount !== null && (
            <Text color="green.600">
              すでに存在したデータ以外{parsedEmailCount} 通のメールを正常に解析して保存しました
            </Text>
          )}
        </VStack>
        
        {/* 日志显示 */}
        {logs.length > 0 && (
          <Box mt={2} p={2} bg="gray.50" borderRadius="md" maxH="200px" overflowY="auto">
            {logs.map((log, index) => (
              <Text key={index} fontSize="sm">{log}</Text>
            ))}
          </Box>
        )}
      </div>
  
      {/* 邮件列表区域 */}
      <div className="w-full flex-1 px-4 overflow-auto">
        {isLoadingEmails ? (
          <Box textAlign="center" py={10}>
            <Text>加载中...</Text>
          </Box>
        ) : recentEmails.length > 0 ? (
          <EmailTable emails={recentEmails} onEmailClick={handleEmailClick} />
        ) : (
          <Text className="text-gray-500 text-center" py={10}>
            最近14日間のメールは見つかりませんでした
          </Text>
        )}
      </div>
  
      {/* 邮件详情抽屉 */}
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
      
      {/* 全局加载指示器 */}
      {(isProcessing || isLoadingEmails) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full">
            <Text mb={4}>
              {isProcessing ? '处理中...' : '加载邮件中...'} 
              {parseProgress > 0 && ` (${parseProgress}%)`}
            </Text>
            {parseProgress > 0 && (
              <Progress.Root value={parseProgress} size="sm" colorScheme="blue" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}