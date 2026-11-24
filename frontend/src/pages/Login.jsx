import { useState } from 'react'
import { api } from '../api/client'

export default function Login({ onEntrar }) {
  const [usuario, setUsuario] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(evento) {
    evento.preventDefault()
    setEnviando(true)
    setErro('')
    try {
      const dados = await api.entrar(usuario, senha)
      onEntrar(dados.usuario)
    } catch (e) {
      setErro(e.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="login">
      <form className="cartao login__form" onSubmit={enviar}>
        <h1>Validador de precatórios</h1>
        <p className="texto-suave">Entre para validar os arquivos do tribunal.</p>
        <label>Usuário<input value={usuario} onChange={(e) => setUsuario(e.target.value)} autoComplete="username" required /></label>
        <label>Senha<input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" required /></label>
        {erro && <p className="erro-campo" role="alert">{erro}</p>}
        <button className="botao botao--primario" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        <p className="texto-suave texto-pequeno">Demonstração com dados fictícios.</p>
      </form>
    </main>
  )
}
