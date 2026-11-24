import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import DiffAntesDepois from '../components/DiffAntesDepois'
import EstadoVazio from '../components/EstadoVazio'
import MensagemErro from '../components/MensagemErro'
import Selo from '../components/Selo'
import { formatarData } from '../formato'

// A situação (vencido, atenção, no prazo, pendente) vem pronta da API.
const SITUACOES = {
  vencido: { tom: 'erro', icone: '✕', texto: 'Vencido' },
  atencao: { tom: 'atencao', icone: '!', texto: 'Vence em breve' },
  no_prazo: { tom: 'ok', icone: '✓', texto: 'No prazo' },
  pendente: { tom: 'pendente', icone: '?', texto: 'Pendente' },
}

function dias(n) {
  if (n == null) return '—'
  if (n < 0) return `vencido há ${-n} dia${n === -1 ? '' : 's'}`
  return `${n} dia${n === 1 ? '' : 's'}`
}

export default function Prazos({ loteId }) {
  const [estado, setEstado] = useState({ carregando: true })
  const carregar = useCallback(async () => {
    try {
      setEstado({ dados: await api.prazos(loteId) })
    } catch (erro) {
      setEstado({ erro })
    }
  }, [loteId])
  useEffect(() => { carregar() }, [carregar])

  if (estado.carregando) return <Carregando />
  if (estado.erro) return <MensagemErro erro={estado.erro} onTentarDeNovo={carregar} />
  const { prazos, hoje } = estado.dados
  if (!prazos.length) return <EstadoVazio titulo="Sem datas de apresentação" />
  return (
    <section>
      <h2>Prazos de pagamento</h2>
      <p className="texto-suave">Regra: apresentado até 2 de abril vence em 31/12 do ano seguinte; depois disso, em
        31/12 do ano subsequente. Dias contados a partir de hoje ({formatarData(hoje)}).</p>
      <div className="rolagem">
        <table className="tabela">
          <thead><tr><th>Processo</th><th>Apresentado em</th><th>Prazo no sistema → calculado</th>
            <th className="num">Dias restantes</th><th>Situação</th></tr></thead>
          <tbody>
            {prazos.map((p) => {
              const s = SITUACOES[p.situacao]
              return (
                <tr key={p.registro_id} className={`prazo prazo--${p.situacao}`}>
                  <td><code>{p.processo}</code></td>
                  <td><code>{p.apresentado_em}</code></td>
                  <td>
                    {p.hub_errado
                      ? <><DiffAntesDepois antes={formatarData(p.prazo_hub)} depois={formatarData(p.prazo_calculado)} />{' '}
                          <Selo tom="erro" icone="⚑">sistema errado</Selo></>
                      : formatarData(p.prazo_calculado ?? p.prazo_hub)}
                    {p.pendente_fuso && <p className="aviso aviso--pendente texto-pequeno">
                      <span aria-hidden="true">? </span>{p.mensagem_usuario} <strong>{p.como_corrigir}</strong></p>}
                    {p.hub_errado && <p className="texto-suave texto-pequeno">{p.como_corrigir}</p>}
                  </td>
                  <td className="num">{dias(p.dias_restantes)}</td>
                  <td><Selo tom={s.tom} icone={s.icone}>{s.texto}</Selo></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
