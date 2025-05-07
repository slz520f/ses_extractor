'use client';

import { useEmailAuth } from '@/hooks/useEmailAuth';
import { fetchEmails, parseAndSaveAllEmails, fetchRecentEmails, getRawEmail } from '@/services/emailService';
import { EmailTable } from '@/components/EmailTable';
import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import {
   CloseButton, Drawer, Portal, DrawerBody, DrawerHeader,  DrawerContent, DrawerTitle,
  DrawerBackdrop, DrawerPositioner, DrawerCloseTrigger, 
  Progress, Box, Text, VStack, Code
} from "@chakra-ui/react";
import { createStandaloneToast } from '@chakra-ui/toast';
import ApiKeyInput from '@/components/ApiKeyInput';

interface Email {
  id?: string;
  raw_email_id?: string;
  sender_email: string;
  subject: string;
  received_at: string;
  project_description: string;
  required_skills: string[];
  optional_skills: string[];
  location: string;
  unit_price: string;
}

interface ProcessStatus {
  fetched: number;
  parsed: number;
  logs: string[];
  fetchProgress: number;
  parseProgress: number;
}



export default function CallbackPage() {
  const { loading, error, userEmail, accessToken } = useEmailAuth();
  const [recentEmails, setRecentEmails] = useState<Email[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [rawContent, setRawContent] = useState<string>('');
  const [status, setStatus] = useState<ProcessStatus>({
    fetched: 0,
    parsed: 0,
    logs: [],
    fetchProgress: 0,
    parseProgress: 0
  });
  const [nextFetchTime, setNextFetchTime] = useState<string>('');
  const { toast } = createStandaloneToast();

  const [isLoadingEmails, setIsLoadingEmails] = useState(false);

  // 次回取得時間を計算 (useMemoでメモ化)
  const calculateNextFetchTime = useMemo(() => {
    return () => {
      const now = new Date();
      const nextHour = new Date(now);
      nextHour.setHours(nextHour.getHours() + 1);
      nextHour.setMinutes(0);
      nextHour.setSeconds(0);
      return nextHour.toLocaleTimeString();
    };
  }, []);

  

 


  

  // 最新メール読み込み
  const loadRecentEmails = useCallback(async () => {
    if (!accessToken) return;
    
    setIsLoadingEmails(true);
    try {
      const result = await fetchRecentEmails(accessToken);
      setRecentEmails(()=> {
        const newEmails = result.emails || [];
        // 重複排除
        const uniqueEmails = newEmails.filter(
          (email:Email, index:number, self:Email[]) =>
            index === self.findIndex(e => e.subject === email.subject)
        );
        return [...uniqueEmails];
      });
    } catch (error) {
      console.error("メール読み込み失敗:", error);
    } finally {
      setIsLoadingEmails(false);
    }
  }, [accessToken]);

  // メール取得関数 (useCallbackでメモ化)
  const handleFetchEmails = useCallback(async () => {
    if (!accessToken) return;
    
    try {
      setStatus(current => ({...current, fetchProgress: 0}));
      
      for (let i = 0; i <= 90; i += 10) {
        await new Promise(resolve => setTimeout(resolve, 200));
        setStatus(current => ({...current, fetchProgress: i}));
      }

      const result = await fetchEmails(accessToken);
      const newFetchedCount = result.emails?.length || 0;
      
      setStatus(current => ({
        ...current,
        fetchProgress: 100,
        fetched: newFetchedCount
      }));
      
      await new Promise(resolve => setTimeout(resolve, 200));
      await loadRecentEmails();
      
    } catch (error) {
      console.error("メール取得失敗:", error);
      setStatus(current => ({...current, fetchProgress: 0}));
      toast({
        title: '取得失敗',
        description: 'メール取得中にエラーが発生しました',
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
    }
  }, [accessToken, loadRecentEmails, toast]);

  // メール解析関数
  const handleParseAndSaveAllEmails = useCallback(async () => {
    if (!accessToken || !status.fetched) return;
  
    setIsProcessing(true);
    setStatus(current => ({
      ...current,
      parseProgress: 0,
      parsed: 0,
      logs: []
    }));
  
    try {
      let successCount = 0;
      let isCompleted = false;
  
      const updateProgress = async (target: number) => {
        while (status.parseProgress < target && !isCompleted) {
          setStatus(currentState => ({
            ...currentState,
            parseProgress: Math.min(currentState.parseProgress + 2, target)
          }));
          await new Promise(resolve => setTimeout(resolve, 50));
        }
      };
  
      const parseTask = async () => {
        try {
          const result = await parseAndSaveAllEmails(accessToken);
          const parsedCount = result.parsedCount || result.parsedEmails?.length || 0;
          successCount = parsedCount;
          
          setStatus(current => ({
            ...current,
            parseProgress: 100,
            parsed: parsedCount,
            logs: Array.isArray(result.parsedEmails) 
              ? [...current.logs, ...result.parsedEmails.map((e:Email) => e.subject)]
              : current.logs
          }));
          
          isCompleted = true;
          return result;
        } catch (err) {
          throw err;
        }
      };
  
      await Promise.all([
        updateProgress(95),
        parseTask()
      ]);
  
      await updateProgress(100);
  
      toast({
        title: '解析完了',
        description: `${successCount} 通のメールを正常に解析・保存しました`,
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
  
      await loadRecentEmails();
  
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'メール解析に失敗しました';
      toast({
        title: 'エラー',
        description: errorMessage,
        status: 'error',
        duration: 3000,
        isClosable: true,
      });
      setStatus(current => ({...current, parseProgress: 0}));
    } finally {
      setIsProcessing(false);
    }
  }, [accessToken, status.fetched, status.parseProgress, loadRecentEmails, toast]);

   

// 手動トリガー (useCallbackでメモ化)
const handleManualTrigger = useCallback(async () => {
  await handleFetchEmails();
  await handleParseAndSaveAllEmails();
  setNextFetchTime(calculateNextFetchTime());
}, [handleFetchEmails, handleParseAndSaveAllEmails, calculateNextFetchTime]);

// 自動取得が必要かチェック (useCallbackでメモ化)
const checkAutoFetch = useCallback(() => {
  const now = new Date();
  const nextFetch = new Date(now);
  nextFetch.setHours(nextFetch.getHours() + 1);
  nextFetch.setMinutes(0);
  nextFetch.setSeconds(0);
  if (now >= nextFetch) {
    handleManualTrigger();
  }
}, [handleManualTrigger]);

// タイマー設定（1分ごとに時間チェック）
useEffect(() => {
  const timer = setInterval(() => {
    setNextFetchTime(calculateNextFetchTime());
    checkAutoFetch();
  }, 60000);
  
  return () => clearInterval(timer);
}, [checkAutoFetch, calculateNextFetchTime]);
  

  // メールクリック時の詳細表示
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);
  const handleEmailClick = async (email: Email) => {
    setSelectedEmail(email);
    drawerTriggerRef.current?.click();
  
    if (!email.raw_email_id) {
      setRawContent('生メール内容なし');
      return;
    }
  
    try {
      setIsLoadingEmails(true);
      const response = await getRawEmail(Number(email.raw_email_id), accessToken || '');
      console.log('API响应:', response);
  
      if (response.success && response.data) {
        let displayContent = '';
        const headers = response.data.headers || {};
        
  
        // 添加头部信息
        displayContent += `差出人: ${headers['From'] || '不明'}\n`;
        displayContent += `件名: ${headers['Subject'] || '無題'}\n`;
        displayContent += `日付: ${headers['Date'] || '不明'}\n\n`;
  
        displayContent += response.data.body || '（无正文内容）';
      
  
        setRawContent(displayContent);
      } else {
        setRawContent('取得失敗: データ形式が不正です');
      }
    } catch (error) {
      setRawContent(`エラー: ${error instanceof Error ? error.message : '不明なエラー'}`);
    } finally {
      setIsLoadingEmails(false);
    }
  };
  
  

  // 初期読み込み
  useEffect(() => {
    const initLoad = async () => {
      await loadRecentEmails();
      setNextFetchTime(calculateNextFetchTime());
    };
    initLoad();
  }, [accessToken, loadRecentEmails, calculateNextFetchTime]);

  // ローディング表示
  if (loading) return <p>ログイン中...</p>;
  if (error) return <p style={{ color: 'red' }}>{error}</p>;

  return (
    <div className="flex flex-col min-h-screen bg-gray-100 text-gray-800 w-full">
      {/* ウェルカムタイトル */}
      <p className="text-xl font-semibold">ようこそ、{userEmail}</p>
      
      {/* 操作バー */}
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
  
        {/* 右：その他操作ボタン */}
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
            disabled={isProcessing || !status.fetched}
          >
            {isProcessing ? '処理中...' : 'すべてのメールを解析'}
          </button>
        </div>
      </div>
  
      {/* ステータスバー */}
      <div className="text-sm text-gray-700 space-y-1 p-4">
        {/* 取得プログレスバー */}
        {status.fetchProgress > 0 && status.fetchProgress < 100 && (
          <Box>
            <Text>メール取得進捗: {status.fetchProgress}%</Text>
            <Progress.Root value={status.fetchProgress} size="sm" colorScheme="blue" />
          </Box>
        )}
        
        {/* 解析プログレスバー */}
        {status.parseProgress > 0 && (
          <Box>
            <Text>解析進捗: {status.parseProgress}%</Text>
            <Progress.Root value={status.parseProgress} size="sm" colorScheme="green" />
          </Box>
        )}
        
        {/* メール数情報 */}
        <VStack align="start" >
          {status.fetched > 0 && (
            <Text>
              {status.fetched > 0 
                ? `${status.fetched} 通の新しいメールが見つかりました`
                : '新しいメールはありません'}
            </Text>
          )}
          
          {status.parsed > 0 && (
            <Text color="green.600">
              既存データを除き {status.parsed} 通のメールを正常に解析・保存しました
            </Text>
          )}
        </VStack>
        
        {/* ログ表示 */}
        {status.logs.length > 0 && (
          <Box mt={2} p={2} bg="gray.50" borderRadius="md" maxH="200px" overflowY="auto">
            {status.logs.map((log, index) => (
              <Text key={index} fontSize="sm">{log}</Text>
            ))}
          </Box>
        )}
      </div>
  
      {/* メールリストエリア */}
      <div className="w-full flex-1 px-4 overflow-auto">
        {isLoadingEmails ? (
          <Box textAlign="center" py={10}>
            <Text>読み込み中...</Text>
          </Box>
        ) : recentEmails.length > 0 ? (
          <EmailTable emails={recentEmails} onEmailClick={handleEmailClick} />
        ) : (
          <Text className="text-gray-500 text-center" py={10}>
            最近14日間のメールは見つかりませんでした
          </Text>
        )}
      </div>
  
      {/* メール詳細ドロワー */}
      <Drawer.Root placement="end" size="lg">
        <Drawer.Trigger asChild>
          <button ref={drawerTriggerRef} className="hidden" />
        </Drawer.Trigger>
  
        <Portal>
          <DrawerBackdrop />
          <DrawerPositioner>
            <DrawerContent>
              <DrawerHeader>
                <DrawerTitle>メール詳細</DrawerTitle>
              </DrawerHeader>
              <DrawerBody>
                {selectedEmail ? (
                  <div className="space-y-4">
                    <div>
                      <strong>差出人：</strong>
                      <p>{selectedEmail.sender_email}</p>
                    </div>
                    <div>
                      <strong>件名：</strong>
                      <p>{selectedEmail.subject}</p>
                    </div>
                    <div>
                      <strong>受信日：</strong>
                      <p>{selectedEmail.received_at}</p>
                    </div>
                    <div>
                      <strong>案件内容：</strong>
                      <p>{selectedEmail.project_description}</p>
                    </div>
                    <div>
                      <strong>必須スキル：</strong>
                      <p>{Array.isArray(selectedEmail.required_skills) ? selectedEmail.required_skills.join(', ') : '-'}</p>
                    </div>
                    <div>
                      <strong>尚可スキル：</strong>
                      <p>{Array.isArray(selectedEmail.optional_skills) ? selectedEmail.optional_skills.join(', ') : '-'}</p>
                    </div>
                    <div>
                      <strong>勤務地：</strong>
                      <p>{selectedEmail.location}</p>
                    </div>
                    <div>
                      <strong>単価：</strong>
                      <p>{selectedEmail.unit_price}</p>
                    </div>
                    {rawContent && (
                      <div className="mt-4">
                        <strong>生メール内容：</strong>
                        <Code className="block mt-2 p-4 whitespace-pre-wrap font-mono text-sm bg-gray-100 rounded overflow-auto h-[80vh] border border-gray-300 shadow-inner">
                          {rawContent}
                        </Code>
                      </div>
                    )}
                  </div>
                ) : (
                  <p>読み込み中...</p>
                )}
              </DrawerBody>
              <DrawerCloseTrigger asChild>
                <CloseButton size="sm" className="absolute top-4 right-4" />
              </DrawerCloseTrigger>
            </DrawerContent>
          </DrawerPositioner>
        </Portal>
      </Drawer.Root>
      
      {/* グローバルローディングインジケーター */}
      {(isProcessing || isLoadingEmails) && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full">
            <Text mb={4}>
              {isProcessing ? '処理中...' : 'メール読み込み中...'} 
              {status.parseProgress > 0 && ` (${status.parseProgress}%)`}
            </Text>
            {status.parseProgress > 0 && (
              <Progress.Root value={status.parseProgress} size="sm" colorScheme="blue" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}