import { useEffect, useRef, useState } from 'react'
import { Bus, Check, ChevronDown } from 'lucide-react'
import { COLORES_VIA, COLOR_TRANSPORTE, ETIQUETAS_VIA } from '../format'
import type { Capas, ClaseVia } from '../types'

const CLASES: ClaseVia[] = ['expresa', 'arterial', 'colectora', 'local']

interface Props {
  capas: Capas
  onCambiar: (capas: Capas) => void
}

function Casilla({ marcado }: { marcado: boolean }) {
  return <span className={`casilla${marcado ? ' marcada' : ''}`}>{marcado && <Check size={13} strokeWidth={3} />}</span>
}

export default function FiltrosVias({ capas, onCambiar }: Props) {
  const [abierto, setAbierto] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const transporte = capas.paraderos || capas.estaciones

  useEffect(() => {
    if (!abierto) return
    const cerrar = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener('mousedown', cerrar)
    return () => document.removeEventListener('mousedown', cerrar)
  }, [abierto])

  return (
    <div className="filtros">
      {CLASES.map((c) => (
        <label key={c} className="filtro">
          <input
            type="checkbox"
            checked={capas[c]}
            onChange={() => onCambiar({ ...capas, [c]: !capas[c] })}
          />
          <Casilla marcado={capas[c]} />
          <span className="chip-color" style={{ background: COLORES_VIA[c] }} />
          {ETIQUETAS_VIA[c]}
        </label>
      ))}

      <div className="filtro filtro-transporte" ref={ref}>
        <label className="filtro">
          <input
            type="checkbox"
            checked={transporte}
            onChange={() => onCambiar({ ...capas, paraderos: !transporte, estaciones: !transporte })}
          />
          <Casilla marcado={transporte} />
          <span className="chip-bus" style={{ color: COLOR_TRANSPORTE }}>
            <Bus size={16} />
          </span>
          Transporte
        </label>
        <button
          className="desplegar"
          onClick={() => setAbierto(!abierto)}
          aria-label="Opciones de transporte"
          aria-expanded={abierto}
        >
          <ChevronDown size={16} />
        </button>
        {abierto && (
          <div className="menu-transporte">
            <label className="filtro">
              <input
                type="checkbox"
                checked={capas.paraderos}
                onChange={() => onCambiar({ ...capas, paraderos: !capas.paraderos })}
              />
              <Casilla marcado={capas.paraderos} />
              Paraderos de bus
            </label>
            <label className="filtro">
              <input
                type="checkbox"
                checked={capas.estaciones}
                onChange={() => onCambiar({ ...capas, estaciones: !capas.estaciones })}
              />
              <Casilla marcado={capas.estaciones} />
              Estaciones (Metro / Metropolitano)
            </label>
          </div>
        )}
      </div>
    </div>
  )
}
