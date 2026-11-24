import { useState } from 'react'
import { api } from '../api/client'
import Marca from '../components/Marca'

export default function Login({ onEntrar, loginLivre }) {
  const [usuario, setUsuario] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setErro('')
    try {
      onEntrar(await api.entrar(usuario, senha))
    } catch (e) {
      setErro(e.message)
      setEnviando(false)
    }
  }

  return (
    <div className="login">
      <section className="login__apresentacao">
        <Marca />
        <h1 className="login__titulo">Confira o que o tribunal enviou antes de importar.</h1>
        <ul className="login__garantias">
          <li>Nenhum pagamento some sem motivo.</li>
          <li>Nada é enviado enquanto houver dúvida.</li>
          <li>Cada decisão fica registrada com nome e justificativa.</li>
        </ul>
        <div className="login__carimbo" aria-hidden="true">Conferido</div>
      </section>

      <main className="login__painel">
        <form className="login__form" onSubmit={enviar}>
          <h2>Entrar</h2>
          <label>Usuário
            <input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username"
              placeholder={loginLivre ? 'Seu nome' : ''} required autoFocus />
          </label>
          <label>Senha
            <input type="password" value={senha} onChange={(e) => setSenha(e.target.value)}
              autoComplete="current-password" required />
          </label>
          {erro && <p className="erro-campo" role="alert">{erro}</p>}
          <button className="botao botao--primario botao--largo" disabled={enviando}>
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>
          {loginLivre && (
            <p className="login__demo">
              <strong>Modo demonstração.</strong> Entre com o seu nome e qualquer senha.
              Os processos e valores são fictícios.
            </p>
          )}
        </form>
      </main>
    </div>
  )
}
