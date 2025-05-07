/*
  ✅ Chakra UI 置換版
  - Input、Button、Select、Skeleton などのコンポーネントを置き換えました
  - 機能ロジックとテーブル構造はそのまま保持
*/

'use client'

import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { useState, useEffect, useCallback } from 'react'

import {
  Box,
  Button,
  Flex,
  Input,

  Skeleton,
  Table,
  VStack,
  HStack,
} from '@chakra-ui/react'

type Email = {
  received_at: string
  subject: string
  sender_email: string
  project_description: string
  required_skills: string[]
  optional_skills: string[]
  location: string
  unit_price: string
}

export function EmailTable({ emails, onEmailClick }: { emails: Email[], onEmailClick?: (email: Email) => void }) {
  const [globalFilter, setGlobalFilter] = useState('')
  const [selectedLocation, setSelectedLocation] = useState('')
  const [unitPriceRange, setUnitPriceRange] = useState({ min: '', max: '' })
  const [selectedSkill, setSelectedSkill] = useState<string[]>(['all'])
  const [filteredEmails, setFilteredEmails] = useState<Email[]>(emails)
  const [loading, setLoading] = useState(true)

  

  const handleFilter = useCallback(() => {
    const result = emails.filter((email) => {
      const matchesKeyword =
        globalFilter === '' ||
        Object.values(email).some((val) =>
          typeof val === 'string'
            ? val.toLowerCase().includes(globalFilter.toLowerCase())
            : Array.isArray(val)
            ? val.join(', ').toLowerCase().includes(globalFilter.toLowerCase())
            : false
        )

      const matchesLocation =
        (selectedLocation || '') === '' || (email.location || '').toLowerCase().includes((selectedLocation || '').toLowerCase());
      

      const matchesUnitPrice =
        (unitPriceRange.min === '' || parseInt(email.unit_price) >= parseInt(unitPriceRange.min)) &&
        (unitPriceRange.max === '' || parseInt(email.unit_price) <= parseInt(unitPriceRange.max))

      const matchesSkill =
        selectedSkill.includes('all') ||
        (Array.isArray(email.required_skills) && email.required_skills.some(skill => selectedSkill.includes(skill))) ||
        (Array.isArray(email.optional_skills) && email.optional_skills.some(skill => selectedSkill.includes(skill)))

      return matchesKeyword && matchesLocation && matchesUnitPrice && matchesSkill
    })

    setFilteredEmails(result)
  }, [ emails,globalFilter, selectedLocation, unitPriceRange, selectedSkill])


  

  const handleReset = () => {
    setGlobalFilter('')
    setSelectedLocation('')
    setUnitPriceRange({ min: '', max: '' })
    setSelectedSkill(['all'])
    setTimeout(() => handleFilter(), 0)
  }

  const skills = [
    'JavaScript',
    'TypeScript',
    'React',
    'Next.js',
    'Python',
    'Django',
    'Java',
    'Spring Boot',
    'AWS',
    'Docker',
    'Kubernetes',
    'PostgreSQL',
    'MySQL',
    'Git',
    'Linux',
  ]

  const columns: ColumnDef<Email>[] = [
    {
      accessorKey: 'received_at',
      header: () => '日付',
      cell: (row) => new Date(row.getValue() as string).toLocaleString(),
    },
    { accessorKey: 'subject', header: () => '件名' },
    { accessorKey: 'sender_email', header: () => '送信者' },
    { accessorKey: 'project_description', header: () => 'プロジェクト詳細' },
    {
      accessorKey: 'required_skills',
      header: () => '必須スキル',
      cell: ({ row }) => Array.isArray(row.getValue('required_skills') as string[]) ? (row.getValue('required_skills') as string[]).join(', ') : '-',
    },
    {
      accessorKey: 'optional_skills',
      header: () => '尚可スキル',
      cell: ({ row }) => Array.isArray(row.getValue('optional_skills') as string[]) ? (row.getValue('optional_skills') as string[]).join(', ') : '-',
    },
    { accessorKey: 'location', header: () => '勤務地' },
    { accessorKey: 'unit_price', header: () => '単価' },
  ]

  const table = useReactTable({
    data: filteredEmails,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: 30, // ✅ ここで指定
      },
    },
  })

  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 2000)
    return () => clearTimeout(timeout)
  }, [])

  return (
    <VStack align="stretch" mt={4}>
      <Box fontSize="xl" fontWeight="bold" mb={2}>
        最近14日間のメール（{filteredEmails.length}件）
      </Box>
      <Flex wrap="wrap" gap={4}>
        <Input
          placeholder="メールのキーワードを検索..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          maxW="300px"
          bg="whiteAlpha.800"
          borderColor="teal.400"
          _hover={{ borderColor: "teal.500" }}
          _focus={{ borderColor: "teal.600" }}
        />
        
        <Input
          placeholder="場所を入力"
          value={selectedLocation}
          onChange={(e) => setSelectedLocation(e.target.value)}
          maxW="200px"
          bg="whiteAlpha.800"
          borderColor="teal.300"
        />
  
        <HStack >
          <Input
            placeholder="最低単価"
            value={unitPriceRange.min}
            onChange={(e) =>
              setUnitPriceRange({ ...unitPriceRange, min: e.target.value })
            }
            maxW="100px"
            bg="whiteAlpha.800"
            borderColor="teal.300"
          />
          <Input
            placeholder="最高単価"
            value={unitPriceRange.max}
            onChange={(e) =>
              setUnitPriceRange({ ...unitPriceRange, max: e.target.value })
            }
            maxW="100px"
            bg="whiteAlpha.800"
            borderColor="teal.300"
          />
        </HStack>
  
        <select
          value={selectedSkill[0]}
          onChange={(e) => setSelectedSkill([e.target.value])}
          className="bg-whiteAlpha.800 border-teal-300 border p-2 max-w-[200px]"
        >
          <option value="all">全てのスキル</option>
          {skills.map((skill, i) => (
            <option key={i} value={skill}>
              {skill}
            </option>
          ))}
        </select>
  
        <Button
          colorScheme="teal"
          onClick={handleFilter}
          bg="teal.500"
          _hover={{ bg: "teal.600" }}
          _active={{ bg: "teal.700" }}
          width="auto"
          height="44px"
        >
          検索
        </Button>
    
        <Button
          variant="outline"
          colorScheme="teal"
          bg="teal.500"
          _hover={{ bg: "teal.600" }}
          _active={{ bg: "teal.700" }}
          onClick={handleReset}
          width="auto"
          height="44px"
        >
          すべてのページに戻る
        </Button>
      </Flex>
    
      <Box
        borderWidth="1px"
        borderRadius="md"
        overflowX="auto"
        className="rounded-lg shadow-md border border-gray-200 w-full"
      >
        <Table.Root variant="outline" size="sm" tableLayout="auto" className="w-full table-auto">
          <Table.Header>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Row key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <Table.ColumnHeader
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    cursor="pointer"
                    className="px-4 py-1 bg-teal-100 hover:bg-teal-200 text-sm"
                    style={{ width: "150px" }}
                  >
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === 'asc'
                      ? ' ↑'
                      : header.column.getIsSorted() === 'desc'
                      ? ' ↓'
                      : ''}
                  </Table.ColumnHeader>
                ))}
              </Table.Row>
            ))}
          </Table.Header>
          <Table.Body minH="300px">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <Table.Row key={i}>
                    {columns.map((_, j) => (
                      <Table.Cell key={j}>
                        <Skeleton height="4" />
                      </Table.Cell>
                    ))}
                  </Table.Row>
                ))
              : table.getRowModel().rows.map((row) => (
                  <Table.Row key={row.id}>
                    {row.getVisibleCells().map((cell) => (
                      <Table.Cell
                        key={cell.id}
                        className="whitespace-nowrap overflow-hidden text-ellipsis max-w-[150px] h-[50px] px-4 py-2 cursor-pointer"
                        style={{ width: "150px" }}
                        onClick={() => onEmailClick && onEmailClick(row.original)}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </Table.Cell>
                    ))}
                  </Table.Row>
                ))}
          </Table.Body>
        </Table.Root>
      </Box>
      <Flex justify="space-between" align="center" mt={4}>
        <Button
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
          colorScheme="teal"
          variant="outline"
          _disabled={{ opacity: 0.5, cursor: 'not-allowed' }}
        >
          前へ
        </Button>
  
        <Box>
          ページ {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
        </Box>
  
        <Button
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
          colorScheme="teal"
          variant="outline"
          _disabled={{ opacity: 0.5, cursor: 'not-allowed' }}
        >
          次へ
        </Button>
      </Flex>
    </VStack>
  )
  
}