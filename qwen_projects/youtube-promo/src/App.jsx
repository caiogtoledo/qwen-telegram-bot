import './App.css'

function App() {
  return (
    <div className="app">
      <main className="container">
        <div className="content">
          <h1>🎬 Caio Toledo Dev</h1>
          <p className="subtitle">Conteúdo de tecnologia para desenvolvedores</p>
          
          <div className="card">
            <h2>Gostou do conteúdo?</h2>
            <p>
              Acesse meu canal no YouTube, deixe seu <strong>like</strong> e 
              <strong> se inscreva</strong> para acompanhar mais vídeos como este!
            </p>
            
            <a 
              href="https://www.youtube.com/@caiotoledodev" 
              target="_blank" 
              rel="noopener noreferrer"
              className="youtube-button"
            >
              <svg className="youtube-icon" viewBox="0 0 24 24" fill="currentColor">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              Acessar Canal
            </a>
          </div>
          
          <div className="actions">
            <div className="action-item">
              <span className="emoji">👍</span>
              <span>Deixe seu like</span>
            </div>
            <div className="action-item">
              <span className="emoji">🔔</span>
              <span>Se inscreva</span>
            </div>
            <div className="action-item">
              <span className="emoji">💬</span>
              <span>Comente</span>
            </div>
          </div>
        </div>
      </main>
      
      <footer className="footer">
        <p>© 2026 Caio Toledo Dev. Todos os direitos reservados.</p>
      </footer>
    </div>
  )
}

export default App
