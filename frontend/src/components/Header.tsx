import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  Bell,
  ChartColumn,
  ChevronDown,
  FileText,
  Heart,
  House,
  LoaderCircle,
  MapPin,
  Search,
} from 'lucide-react'
import { buscarDireccion } from '../api'
import type { ResultadoBusqueda } from '../types'

function Logo() {
  return (
    <div className="logo">
      <svg viewBox="0 0 40 40" width="38" height="38" aria-hidden="true">
        <path d="M20 3 35 11.5 20 20 5 11.5Z" fill="#2bb3a8" />
        <path d="M5 11.5 20 20v16.5L5 28Z" fill="#0f6e78" />
        <path d="M35 11.5 20 20v16.5L35 28Z" fill="#14476b" />
        <path d="M20 3 27.5 7.25 20 11.5 12.5 7.25Z" fill="#7fdcd2" />
      </svg>
      <div>
        <div className="logo-nombre">
          Pred<span>IA</span>
        </div>
        <div className="logo-sub">Terrenos con mayor potencial</div>
      </div>
    </div>
  )
}

interface Props {
  onSeleccionar: (lat: number, lon: number) => void
}

export default function Header({ onSeleccionar }: Props) {
  const [q, setQ] = useState('')
  const [resultados, setResultados] = useState<ResultadoBusqueda[] | null>(null)
  const [buscando, setBuscando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Nominatim no permite autocompletado: se busca solo al presionar Enter
  async function buscar(e: FormEvent) {
    e.preventDefault()
    if (q.trim().length < 3) return
    setBuscando(true)
    setError(null)
    try {
      setResultados(await buscarDireccion(q.trim()))
    } catch (err) {
      setError((err as Error).message)
      setResultados([])
    } finally {
      setBuscando(false)
    }
  }

  function elegir(r: ResultadoBusqueda) {
    setResultados(null)
    setQ(r.titulo)
    onSeleccionar(r.lat, r.lon)
  }

  return (
    <header className="header">
      <Logo />
      <nav className="nav">
        <button className="nav-item activo">
          <House size={17} /> Explorar
        </button>
        <button className="nav-item" disabled title="Próximamente">
          <ChartColumn size={17} /> Análisis
        </button>
        <button className="nav-item" disabled title="Próximamente">
          <FileText size={17} /> Reportes
        </button>
        <button className="nav-item" disabled title="Próximamente">
          <Heart size={17} /> Favoritos
        </button>
      </nav>

      <form className="buscador" onSubmit={buscar} role="search">
        {buscando ? <LoaderCircle size={17} className="girar" /> : <Search size={17} />}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onBlur={() => setTimeout(() => setResultados(null), 200)}
          placeholder="Buscar dirección, distrito o referencia..."
          aria-label="Buscar dirección"
        />
        {resultados && (
          <ul className="buscador-resultados">
            {error && <li className="vacio">{error}</li>}
            {!error && resultados.length === 0 && <li className="vacio">Sin resultados en Lima</li>}
            {resultados.map((r) => (
              <li key={`${r.lat},${r.lon}`}>
                <button type="button" onMouseDown={() => elegir(r)}>
                  <MapPin size={15} />
                  <span>
                    <strong>{r.titulo}</strong>
                    <small>{r.detalle}</small>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </form>

      <button className="icono-btn campana" aria-label="Notificaciones">
        <Bell size={20} />
        <span className="punto-rojo" />
      </button>
      <div className="usuario">
        <span className="avatar">JS</span>
        <span className="usuario-nombre">Juan Silva</span>
        <ChevronDown size={16} />
      </div>
    </header>
  )
}
