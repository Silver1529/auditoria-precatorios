import { render, screen } from '@testing-library/react'
import BannerEnvio from './BannerEnvio'

describe('BannerEnvio', () => {
  it('fica vermelho com pendência e mostra o motivo', () => {
    render(<BannerEnvio liberado={false} motivo="Envio bloqueado: 9 pendências e 3 erros" />)
    const banner = screen.getByRole('alert')
    expect(banner).toHaveClass('banner--bloqueado')
    expect(banner).toHaveTextContent('Envio bloqueado: 9 pendências e 3 erros')
  })

  it('fica verde sem pendência', () => {
    render(<BannerEnvio liberado motivo="" />)
    const banner = screen.getByRole('status')
    expect(banner).toHaveClass('banner--liberado')
    expect(banner).toHaveTextContent('Tudo validado, envio liberado')
  })
})
