import { Building2, Car, ChartColumn, Database, House, Info, Users } from 'lucide-react'

const SECCIONES = [
  { id: 'resumen', label: 'Resumen', icon: House },
  { id: 'conectividad', label: 'Conectividad', icon: Car },
  { id: 'equipamiento', label: 'Equipamiento', icon: Building2 },
  { id: 'desarrollo', label: 'Desarrollo futuro', icon: ChartColumn },
  { id: 'percepcion', label: 'Percepción', icon: Users },
  { id: 'mercado', label: 'Mercado', icon: Database },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div>
        <h2>Ubicación y entorno</h2>
        <p className="sidebar-sub">
          Analiza el contexto de tu terreno para una mejor toma de decisiones.
        </p>
        <nav className="sidebar-menu">
          {SECCIONES.map(({ id, label, icon: Icon }) => {
            const activo = id === 'conectividad'
            return (
              <button
                key={id}
                className={`sidebar-item${activo ? ' activo' : ''}`}
                disabled={!activo}
                title={activo ? undefined : 'Próximamente'}
                aria-current={activo ? 'page' : undefined}
              >
                <Icon size={20} />
                {label}
              </button>
            )
          })}
        </nav>
      </div>

      <div className="sidebar-info">
        <div className="sidebar-info-titulo">
          <span className="info-icono">
            <Info size={16} />
          </span>
          <strong>Conoce el entorno, identifica oportunidades.</strong>
        </div>
        <p>La información del entorno te permite evaluar mejor el potencial de tu terreno.</p>
      </div>
    </aside>
  )
}
