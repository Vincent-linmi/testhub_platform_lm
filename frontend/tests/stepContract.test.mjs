import assert from 'node:assert/strict'
import { test } from 'node:test'
import { needsStepElement, needsStepInput, needsExpectedValue, stepInputLabel } from '../src/views/ui-automation/test-cases/stepContract.js'

test('page assertions need no locator while absence and count assertions do', () => {
  for (const assert_type of ['urlEquals', 'urlContains']) assert.equal(needsStepElement({ action_type: 'assert', assert_type }), false)
  for (const assert_type of ['notExists', 'notVisible', 'countEquals']) assert.equal(needsStepElement({ action_type: 'assert', assert_type }), true)
})
test('attribute assertions expose name and value while boolean states need no expected string', () => {
  const attribute = { action_type: 'assert', assert_type: 'hasAttribute' }
  assert.equal(needsStepInput(attribute), true)
  assert.equal(needsExpectedValue(attribute), true)
  assert.equal(stepInputLabel(attribute), 'attributeName')
  assert.equal(needsExpectedValue({ action_type: 'assert', assert_type: 'isDisabled' }), false)
})
test('text extraction exposes an optional variable name instead of a fill value', () => {
  assert.equal(needsStepInput({ action_type: 'getText' }), true)
  assert.equal(stepInputLabel({ action_type: 'getText' }), 'runtimeVariableName')
  for (const action_type of ['selectOption', 'press']) assert.equal(needsStepInput({ action_type }), true)
})

test('runtime reference help renders literally in both supported editor locales', async () => {
  const { createI18n } = await import('vue-i18n')
  for (const locale of ['zh-cn', 'en']) {
    const messages = (await import(`../src/locales/lang/${locale}/ui-automation.js`)).default
    const i18n = createI18n({ legacy: false, locale, messages: { [locale]: messages } })
    assert.ok(i18n.global.t('testCase.runtimeVariableHint', { reference: '${runtime.orderId}' }).includes('${runtime.orderId}'))
  }
})
