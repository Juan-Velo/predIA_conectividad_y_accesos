import { ArrowRight, Car, ChevronRight, ClipboardList, Footprints } from 'lucide-react'
import { distancia } from '../format'
import type { Acceso, Observacion, ViaCercana } from '../types'

export function IconoVia() {
  return (
    <svg viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" className="icono-via">
      <path d="M11 4h10l7 24H4Z" fill="currentColor" />
      <path d="M16 7v4M16 14v4M16 21v5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function Skeleton({ filas }: { filas: number }) {
  return (
    <div className="skeleton-lista">
      {Array.from({ length: filas }, (_, i) => (
        <div key={i} className="skeleton linea" style={{ width: `${90 - i * 9}%` }} />
      ))}
    </div>
  )
}

interface RedVialProps {
  vias: ViaCercana[] | null
  seleccionada: number | null
  onSeleccionar: (v: ViaCercana) => void
  onVerMapa: () => void
}

export function RedVialCercana({ vias, seleccionada, onSeleccionar, onVerMapa }: RedVialProps) {
  return (
    <section className="panel">
      <div className="panel-titulo">
        <IconoVia />
        <h3>Red vial cercana</h3>
        <button className="link" onClick={onVerMapa}>
          Ver mapa completo <ArrowRight size={15} />
        </button>
      </div>
      {!vias ? (
        <Skeleton filas={4} />
      ) : vias.length === 0 ? (
        <p className="vacio">No se encontraron vías en el radio de análisis.</p>
      ) : (
        <ul className="lista-vias">
          {vias.map((v) => (
            <li key={v.clase}>
              <button
                className={`via${seleccionada === v.osm_id ? ' seleccionada' : ''}`}
                onClick={() => onSeleccionar(v)}
                title={`${v.nombre_completo} — ver en el mapa`}
              >
                <IconoVia />
                <span className="via-texto">
                  <strong>{v.nombre}</strong>
                  <span className="via-meta">
                    {v.modo === 'caminando' ? <Footprints size={14} /> : <Car size={14} />}
                    {v.frente_al_terreno ? (
                      'Frente al terreno'
                    ) : (
                      <>
                        {distancia(v.distancia_m)}
                        <span className="sep">|</span>
                        {v.estimado && '≈ '}
                        {v.duracion_min} min {v.modo === 'caminando' ? 'caminando' : 'en vehículo'}
                      </>
                    )}
                  </span>
                </span>
                <span className={`pill pill-${v.clase}`}>{v.etiqueta}</span>
                <ChevronRight size={18} className="chevron" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export function Observaciones({ items }: { items: Observacion[] | null }) {
  return (
    <section className="panel">
      <div className="panel-titulo">
        <ClipboardList size={24} className="titulo-icono" />
        <h3>Observaciones</h3>
      </div>
      {!items ? (
        <Skeleton filas={4} />
      ) : (
        <ul className="lista-obs">
          {items.map((o) => (
            <li key={o.texto} title={o.detalle ?? undefined}>
              <span className={`punto punto-${o.tipo}`} />
              <span>
                {o.texto}
                {o.detalle && <small>{o.detalle}</small>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

const FUENTE_ANCHO = {
  osm: 'Ancho registrado en OpenStreetMap',
  carriles: 'Estimado por número de carriles + veredas',
  tipico: 'Valor típico para este tipo de vía en Lima',
}

export function AccesoTerreno({ acceso, cargado }: { acceso: Acceso | null; cargado: boolean }) {
  return (
    <section className="panel">
      <div className="panel-titulo">
        <Car size={24} className="titulo-icono" />
        <h3>Acceso al terreno</h3>
      </div>
      {!cargado ? (
        <Skeleton filas={4} />
      ) : !acceso ? (
        <p className="vacio">No hay vías registradas junto al terreno.</p>
      ) : (
        <dl className="tabla-acceso">
          <dt>Tipo de vía frontal:</dt>
          <dd title={acceso.via_frontal}>
            {acceso.tipo_via_frontal}
            <small> · {acceso.via_frontal}</small>
          </dd>
          <dt>Ancho aproximado:</dt>
          <dd title={FUENTE_ANCHO[acceso.ancho_fuente]}>
            {acceso.ancho_fuente === 'osm' ? '' : '≈ '}
            {acceso.ancho_aprox_m} m
            {acceso.carriles && <small> · {acceso.carriles} carriles</small>}
          </dd>
          <dt>Acceso vehicular:</dt>
          <dd>{acceso.acceso_vehicular}</dd>
          <dt>Transporte público cercano:</dt>
          <dd>{acceso.transporte_publico}</dd>
        </dl>
      )}
    </section>
  )
}
