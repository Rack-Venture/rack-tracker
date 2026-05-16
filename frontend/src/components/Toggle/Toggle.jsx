import style from './Toggle.module.css'

/**
 * on/off 토글 스위치 컴포넌트.
 *
 * @param {Object} props
 * @param {string} props.label - 토글 옆에 표시할 레이블 텍스트.
 * @param {boolean} [props.checked=false] - 현재 토글 상태.
 * @param {Function} [props.onChange] - 상태 변경 시 boolean 값을 인자로 호출.
 * @returns {JSX.Element}
 */
export default function Toggle({ label, checked = false, onChange }) {
    return (
        <label className={style.row}>
            <span className={style.label}>{label}</span>
            <div
                className={`${style.track} ${checked ? style.on : ''}`}
                onClick={() => onChange?.(!checked)}
            >
                <div className={style.thumb} />
            </div>
        </label>
    )
}
