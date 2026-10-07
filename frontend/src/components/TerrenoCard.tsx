import { ChevronRight, MapPin } from 'lucide-react'
import { area } from '../format'
import type { Terreno } from '../types'

const ANCHO = 92
const ALTO = 64

/** Recorte satelital compuesto por 2x2 teselas con el contorno del terreno. */
function Miniatura({ m }: { m: Terreno['miniatura'] }) {
  const [cx, cy] = m.centro_px
  return (
    <div className="terreno-img" role="img" aria-label="Vista satelital del terreno">
      <div className="miniatura-bloque" style={{ left: ANCHO / 2 - cx, top: ALTO / 2 - cy }}>
        {m.teselas.map((t) => (
          <img key={t.url} src={t.url} alt="" style={{ left: t.x, top: t.y }} draggable={false} />
        ))}
        {m.contorno_px.length >= 3 && (
          <svg width="512" height="512">
            <polygon
              points={m.contorno_px.map((p) => p.join(',')).join(' ')}
              fill="rgba(45, 212, 191, 0.3)"
              stroke="#5eead4"
              strokeWidth="2"
            />
          </svg>
        )}
      </div>
    </div>
  )
}

interface Props {
  terreno: Terreno | null
  cargando: boolean
  onEnfocar: () => void
}

export default function TerrenoCard({ terreno, cargando, onEnfocar }: Props) {
  if (!terreno) {
    return (
      <div className="terreno-card">
        <div className="terreno-img skeleton" />
        <div className="terreno-info">
          <span className="terreno-label">Terreno seleccionado</span>
          <div className="skeleton linea" style={{ width: '80%' }} />
          <div className="skeleton linea" style={{ width: '55%' }} />
        </div>
      </div>
    )
  }

  return (
    <button
      className={`terreno-card${cargando ? ' atenuado' : ''}`}
      onClick={onEnfocar}
      title="Centrar el mapa en el terreno"
    >
      <Miniatura m={terreno.miniatura} />
      <div className="terreno-info">
        <span className="terreno-label">Terreno seleccionado</span>
        <strong className="terreno-dir" title={terreno.direccion_completa}>
          {terreno.nombre ? `${terreno.nombre} · ` : ''}
          {terreno.direccion}
        </strong>
        <span className="terreno-meta">
          {terreno.area_m2 != null ? (
            <>
              Área: <b>{area(terreno.area_m2)}</b>
            </>
          ) : (
            <span className="sin-dato">
              <MapPin size={13} /> Sin polígono: elige una cancha o dibuja el terreno
            </span>
          )}
          <span className="sep">|</span>
          Uso actual: <span>{terreno.uso_actual === 'Sin datos' ? 'Por verificar' : terreno.uso_actual}</span>
        </span>
      </div>
      <ChevronRight size={20} className="terreno-chevron" />
    </button>
  )
}
