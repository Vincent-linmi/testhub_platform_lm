export const extraActions = ['selectOption', 'check', 'uncheck', 'press']
export const extraAssertions = ['notVisible', 'notExists', 'valueEquals', 'isChecked', 'notChecked', 'isEnabled', 'isDisabled', 'countEquals', 'urlEquals', 'urlContains']
export const needsStepElement = step => !['wait', 'switchTab', 'screenshot'].includes(step.action_type)
  && !(step.action_type === 'assert' && ['urlEquals', 'urlContains'].includes(step.assert_type))
export const needsStepInput = step => ['fill', 'switchTab', 'getText', 'selectOption', 'press'].includes(step.action_type)
  || (step.action_type === 'assert' && step.assert_type === 'hasAttribute')
export const needsExpectedValue = step => step.action_type === 'assert'
  && ['textContains', 'textEquals', 'hasAttribute', 'valueEquals', 'countEquals', 'urlEquals', 'urlContains'].includes(step.assert_type)
export const stepInputLabel = step => step.action_type === 'getText' ? 'runtimeVariableName'
  : step.action_type === 'assert' ? 'attributeName' : 'inputValue'
export const stepInputHint = step => ({
  getText: 'runtimeVariableHint', selectOption: 'selectOptionHint', press: 'pressHint',
  switchTab: 'switchTabPlaceholder', assert: 'attributeHint'
}[step.action_type] || 'inputPlaceholder')
