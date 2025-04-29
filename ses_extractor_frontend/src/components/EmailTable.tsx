/*
  ✅ Chakra UI 替换版
  - 替换了 Input, Button, Select, Skeleton 等组件
  - 保留了功能逻辑和表格结构
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
import { useState, useEffect, useMemo } from 'react'
import type { ChangeEvent } from 'react'
import {
  Box,
  Button,
  Flex,
  Input,
  Select as ChakraSelect,
  Skeleton,
  Table,
  Text,
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

  useEffect(() => {
    handleFilter()
  }, [emails])

  const handleFilter = () => {
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
        selectedLocation === '' || email.location.toLowerCase().includes(selectedLocation.toLowerCase())

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
  }

  const handleReset = () => {
    setGlobalFilter('')
    setSelectedLocation('')
    setUnitPriceRange({ min: '', max: '' })
    setSelectedSkill(['all'])
    setTimeout(() => handleFilter(), 0)
  }

  const locations = useMemo(() => {
    const locationSet = new Set(emails.map((email) => email.location))
    return Array.from(locationSet)
  }, [emails])

  // const skills = useMemo(() => {
  //   const requiredSkillsSet = new Set(
  //     emails.flatMap((email) => email.required_skills)
  //   )
  //   const optionalSkillsSet = new Set(
  //     emails.flatMap((email) => email.optional_skills)
  //   )
  //   return Array.from(new Set([...requiredSkillsSet, ...optionalSkillsSet]))
  // }, [emails])
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
      header: () => '日期',
      cell: (row) => new Date(row.getValue() as string).toLocaleString(),
    },
    { accessorKey: 'subject', header: () => '主题' },
    { accessorKey: 'sender_email', header: () => '发件人' },
    { accessorKey: 'project_description', header: () => '案件内容' },
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
  })

  useEffect(() => {
    const timeout = setTimeout(() => setLoading(false), 2000)
    return () => clearTimeout(timeout)
  }, [])

  return (
    <VStack align="stretch" mt={4}>
      <Flex wrap="wrap" gap={4}>
        <Input
          placeholder="搜索邮件关键词..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          maxW="300px"
          bg="whiteAlpha.800"
          borderColor="teal.400"
          _hover={{ borderColor: "teal.500" }}
          _focus={{ borderColor: "teal.600" }}
        />
        <Button
          colorScheme="teal"
          onClick={handleFilter}
          bg="teal.500"
          _hover={{ bg: "teal.600" }}
          _active={{ bg: "teal.700" }}
        >
          搜索
        </Button>
  
        <Input
          placeholder="输入地点"
          value={selectedLocation}
          onChange={(e) => setSelectedLocation(e.target.value)}
          maxW="200px"
          bg="whiteAlpha.800"
          borderColor="teal.300"
        />
  
        <HStack>
          <Input
            placeholder="最低单价"
            value={unitPriceRange.min}
            onChange={(e) =>
              setUnitPriceRange({ ...unitPriceRange, min: e.target.value })
            }
            maxW="100px"
            bg="whiteAlpha.800"
            borderColor="teal.300"
          />
          <Input
            placeholder="最高单价"
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
          className="bg-whiteAlpha.800 border-teal-300 border p-2"
        >
          <option value="all">全部技能</option>
          {skills.map((skill, i) => (
            <option key={i} value={skill}>
              {skill}
            </option>
          ))}
        </select>
  
        <Button variant="outline" colorScheme="red" onClick={handleReset}>
          返回所有页面
        </Button>
      </Flex>
  
      <Box
        borderWidth="1px"
        borderRadius="md"
        overflowX="hidden"
        height="500px"
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
                    className="px-4 py-1 bg-teal-100 hover:bg-teal-200 text-sm" // 设置表头固定宽度
                    style={{ width: "150px" }} // 固定表头宽度
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
  
      <Flex justify="space-between" align="center">
        <Button
          onClick={() => table.previousPage()}
          disabled={!table.getCanPreviousPage()}
          variant="outline"
          colorScheme="blue"
        >
          上一页
        </Button>
        <Text>
          页 {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
        </Text>
        <Button
          onClick={() => table.nextPage()}
          disabled={!table.getCanNextPage()}
          variant="outline"
          colorScheme="blue"
        >
          下一页
        </Button>
      </Flex>
    </VStack>
  );
  
  
  
}