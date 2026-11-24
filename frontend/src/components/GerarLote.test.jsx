import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import GerarLote from './GerarLote'

const bloqueado = {
  envio_liberado: false,
  motivo_bloqueio: 'Envio bloqueado: 9 pendências e 3 erros',
  bloqueios: [{ registro_id: 'pagamentos.json#5', regras: ['PAG-VALOR-AUSENTE'], severidade: 'erro',
    mensagem_usuario: 'O pagamento veio sem valor.', como_corrigir: 'Peça ao tribunal o valor.' }],
}

describe('GerarLote', () => {
  it('fica desabilitado e explica o bloqueio', () => {
    render(<GerarLote resumo={bloqueado} onGerar={() => {}} />)
    expect(screen.getByRole('button', { name: /gerar lote/i })).toBeDisabled()
    expect(screen.getByText(/pagamentos.json#5/)).toBeInTheDocument()
    expect(screen.getByText(/O pagamento veio sem valor/)).toBeInTheDocument()
  })

  it('habilita quando liberado e chama onGerar', async () => {
    const onGerar = vi.fn()
    render(<GerarLote resumo={{ envio_liberado: true, motivo_bloqueio: '', bloqueios: [] }} onGerar={onGerar} />)
    const botao = screen.getByRole('button', { name: /gerar lote/i })
    expect(botao).toBeEnabled()
    await userEvent.click(botao)
    expect(onGerar).toHaveBeenCalled()
  })
})
