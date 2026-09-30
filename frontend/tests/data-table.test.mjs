import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseDataMatrix, dataToCsv } from '../src/views/ui-automation/test-cases/dataTable.js'
test('keeps account leading zeros, blanks and punctuation', () => {
  const data = parseDataMatrix([['username', 'password'], ['001', 'a,"b\nc'], ['002', ''], ['', '']])
  assert.equal(data.rows.length, 2)
  assert.equal(data.rows[0].username, '001')
  assert.equal(data.rows[1].password, '')
  assert.equal(dataToCsv(data.columns, data.rows), '"username","password"\r\n"001","a,""b\nc"\r\n"002",""')
})
test('rejects duplicate/invalid headers, mismatched width and row limits', () => {
  for (const matrix of [[['username', 'username'], ['a', 'b']], [['bad-name'], ['x']], [['a'], ['x', 'y']], [['a']], [['a'], ...Array(1001).fill(['x'])]]) {
    assert.throws(() => parseDataMatrix(matrix))
  }
})
