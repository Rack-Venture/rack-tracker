import style from './FpsSelector.module.css'

const FPS_OPTIONS = [
    { value: null, label: 'Source FPS', description: 'Use source video fps' },
    { value: 30, label: '30 FPS', description: 'Balanced throughput' },
    { value: 60, label: '60 FPS', description: 'Higher fidelity' },
]

export default function FpsSelector({ value = null, onChange }) {
    return (
        <div className={style.container}>
            <span className={style.label}>Sampling Rate (FPS)</span>
            <div className={style.options}>
                {FPS_OPTIONS.map(option => (
                    <button
                        key={option.label}
                        type="button"
                        className={`${style.option} ${value === option.value ? style.selected : ''}`}
                        onClick={() => onChange?.(option.value)}
                    >
                        <span>{option.label}</span>
                        <small className={style.optionMeta}>{option.description}</small>
                    </button>
                ))}
            </div>
        </div>
    )
}
