export function validateColumns(columns) {
  if (!columns.length || columns.length > 100 || columns.some(column => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(column))) {
    throw new Error('请填写 1–100 个有效列名：字母或下划线开头，只能包含字母、数字和下划线')
  }
  if (new Set(columns).size !== columns.length) throw new Error('列名不能重复')
}

export function parseDataMatrix(matrix) {
  if (!matrix.length) throw new Error('文件为空，请将列名放在第一行')
  const columns = matrix[0].map(value => String(value).trim())
  validateColumns(columns)
  const body = matrix.slice(1).filter(row => row.some(value => value !== '' && value != null))
  if (!body.length || body.length > 1000) throw new Error('请导入 1–1000 行数据')
  if (body.some(row => row.slice(columns.length).some(value => value !== '' && value != null))) throw new Error('数据列超过表头列数，请检查文件')
  return { columns, rows: body.map(row => Object.fromEntries(columns.map((column, index) => [column, String(row[index] ?? '')]))) }
}

export function dataToCsv(columns, rows) {
  const escape = value => `"${String(value ?? '').replaceAll('"', '""')}"`
  return [columns, ...rows.map(row => columns.map(column => row[column]))].map(row => row.map(escape).join(',')).join('\r\n')
}
