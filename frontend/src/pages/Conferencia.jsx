import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import EstadoVazio from '../components/EstadoVazio'
import MensagemErro from '../components/MensagemErro'
import StatusBadge from '../components/StatusBadge'
import { formatarMoeda } from '../formato'

const ROTULOS = { processo: 'Número do processo', ente: 'Ente devedor', valor_face: 'Valor de face' }
const exibir = (campo, valor) => (valor == null ? '—' : campo === 'valor_face' ? formatarMoeda(valor) : valor)

function CartaoConferencia({ item }) {
  return (
    <article className={`cartao conferencia ${item.status === 'PENDENTE' ? 'conferencia--divergente' : ''}`}>
      <header className="conferencia__topo">
        <code>{item.processo}</code>
        <StatusBadge status={item.status} />
      </header>
      {item.ausente_em && (
        <p className="aviso aviso--erro" role="note">
          <span aria-hidden="true">⚠ </span>
          {item.ausente_em === 'tribunal' ? 'Não está na lista do tribunal.' : 'Não está no nosso sistema (hub).'}
        </p>
      )}
      <table className="tabela tabela--lado-a-lado">
        <thead><tr><th>Campo</th><th>Tribunal</th><th>Nosso sistema</th></tr></thead>
        <tbody>
          {item.campos.map((c) => (
            <tr key={c.campo} className={c.divergente ? 'campo--divergente' : ''}>
              <th scope="row">{ROTULOS[c.campo]}
                {c.divergente && <span className="selo-divergente"><span aria-hidden="true">≠ </span>diferente</span>}
              </th>
              <td>{exibir(c.campo, c.tribunal)}</td>
              <td>{exibir(c.campo, c.hub)}
                {c.so_grafia && <span className="texto-suave texto-pequeno"> (só muda maiúscula, acento ou pontuação: não é divergência)</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>{item.mensagem_usuario}</p>
      {item.como_corrigir && <p className="texto-suave"><strong>Como corrigir:</strong> {item.como_corrigir}</p>}
    </article>
  )
}

export default function Conferencia({ loteId }) {
  const [estado, setEstado] = useState({ carregando: true })
  const carregar = useCallback(async () => {
    try {
      setEstado({ itens: (await api.conferencia(loteId)).conferencia })
    } catch (erro) {
      setEstado({ erro })
    }
  }, [loteId])
  useEffect(() => { carregar() }, [carregar])

  if (estado.carregando) return <Carregando />
  if (estado.erro) return <MensagemErro erro={estado.erro} onTentarDeNovo={carregar} />
  if (!estado.itens.length) return <EstadoVazio titulo="Nada para conferir" />
  const divergentes = estado.itens.filter((i) => i.status === 'PENDENTE').length
  return (
    <section>
      <h2>Conferência tribunal × sistema</h2>
      <p className="texto-suave">{divergentes} de {estado.itens.length} precatórios precisam de atenção.
        Diferenças só de maiúscula, acento ou pontuação não contam como divergência.</p>
      <div className="grade-conferencia">
        {estado.itens.map((item) => <CartaoConferencia key={item.registro_id} item={item} />)}
      </div>
    </section>
  )
}
