import { render, screen } from '@testing-library/react'
import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  it.each([
    ['OK', 'OK'],
    ['CORRIGIDO', 'Corrigido'],
    ['DESCARTADO', 'Descartado'],
    ['PENDENTE', 'Pendente'],
  ])('mostra texto e ícone além da cor para %s', (status, texto) => {
    const { container } = render(<StatusBadge status={status} />)
    expect(screen.getByText(texto)).toBeInTheDocument()
    const icone = container.querySelector('[data-icone]')
    expect(icone).not.toBeNull()
    expect(icone).toHaveAttribute('aria-hidden', 'true')
    expect(container.firstChild).toHaveClass('badge', `badge--${status.toLowerCase()}`)
  })
})
