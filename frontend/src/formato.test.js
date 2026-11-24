import { formatarData, formatarMoeda } from './formato'

describe('formato', () => {
  it('formata dinheiro em pt-BR a partir do texto da API, sem perder centavos', () => {
    expect(formatarMoeda('30500.00')).toMatch(/R\$\s30\.500,00/)
    expect(formatarMoeda('-200.00')).toMatch(/-R\$\s200,00/)
    expect(formatarMoeda('9999999999999.99')).toMatch(/9\.999\.999\.999\.999,99/)
    expect(formatarMoeda(null)).toBe('—')
  })

  it('formata data ISO sem passar por fuso', () => {
    expect(formatarData('2026-12-31')).toBe('31/12/2026')
    expect(formatarData(null)).toBe('—')
  })
})
