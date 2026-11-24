import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import Carregando from '../components/Carregando'
import EstadoVazio from '../components/EstadoVazio'
import LinhaRegistro from '../components/LinhaRegistro'
import MensagemErro from '../components/MensagemErro'

const STATUS = [['', 'Todos'], ['OK', 'OK'], ['CORRIGIDO', 'Corrigidos'], ['DESCARTADO', 'Descartados'], ['PENDENTE', 'Pendentes']]

export default function Registros({ loteId }) {
  const [status, setStatus] = useState('')
  const [processo, setProcesso] = useState('')
  const [estado, setEstado] = useState({ carregando: true })

  const carregar = useCallback(async () => {
    setEstado({ carregando: true })
    try {
      const dados = await api.registros(loteId, { status, processo })
      setEstado({ registros: dados.registros })
    } catch (erro) {
      setEstado({ erro })
    }
  }, [loteId, status, processo])

  useEffect(() => {
    const espera = setTimeout(carregar, 250)
    return () => clearTimeout(espera)
  }, [carregar])

  return (
    <section>
      <h2>Registros</h2>
      <div className="filtros" role="search">
        <label>Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS.map(([valor, rotulo]) => <option key={valor} value={valor}>{rotulo}</option>)}
          </select>
        </label>
        <label>Processo
          <input type="search" placeholder="Ex.: 0023456" value={processo} onChange={(e) => setProcesso(e.target.value)} />
        </label>
      </div>
      {estado.carregando && <Carregando />}
      <MensagemErro erro={estado.erro} onTentarDeNovo={carregar} />
      {estado.registros?.length === 0 && <EstadoVazio titulo="Nenhum registro encontrado">Mude o filtro ou a busca.</EstadoVazio>}
      {estado.registros?.length > 0 && (
        <div className="rolagem">
          <table className="tabela">
            <thead><tr><th>Registro</th><th>Chave</th><th>Status</th><th>O que aconteceu</th><th>Antes → depois</th></tr></thead>
            <tbody>{estado.registros.map((r) => <LinhaRegistro key={r.id} registro={r} />)}</tbody>
          </table>
        </div>
      )}
    </section>
  )
}
