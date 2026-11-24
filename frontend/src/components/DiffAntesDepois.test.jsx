import { render, screen } from '@testing-library/react'
import DiffAntesDepois from './DiffAntesDepois'

describe('DiffAntesDepois', () => {
  it('mostra o valor antigo riscado e o novo em destaque', () => {
    render(<DiffAntesDepois antes="2.500,50" depois="2500.50" />)
    expect(screen.getByText('2.500,50').tagName).toBe('DEL')
    expect(screen.getByText('2500.50').tagName).toBe('INS')
  })

  it('não mostra nada quando não há mudança', () => {
    const { container } = render(<DiffAntesDepois antes="" depois="" />)
    expect(container).toBeEmptyDOMElement()
  })
})
