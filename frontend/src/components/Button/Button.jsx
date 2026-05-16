import styles from './Button.module.css';

/**
 * 공통 버튼 컴포넌트
 *
 * @param {Object} props
 * @param {Function} props.onClick - 클릭 이벤트 핸들러
 * @param {'positive'|'negative'} [props.theme='positive'] - 버튼 테마 (긍정/부정)
 * @param {string} [props.width='17.4rem'] - 버튼 너비 (CSS 값)
 * @param {string} [props.height='5.8rem'] - 버튼 높이 (CSS 값)
 * @param {string} [props.label='Button'] - 버튼 텍스트
 * @param {string} [props.fontSize='var(--font-size-md)'] - 버튼 폰트 크기 (CSS 값)
 * @returns {JSX.Element}
 */

export default function Button({
    onClick,
    theme = 'positive',
    width = '17.4rem',
    height = '5.8rem',
    label = 'Button',
    fontSize = 'var(--font-size-md)',
    disabled = false,
    icon,
    href,
}){
    const className = `${styles.button} ${theme === 'positive' ? styles.positive : styles.negative} ${disabled ? styles.disabled : ''}`;
    const style = { '--btn-width': width, '--btn-height': height, '--btn-font-size': fontSize };
    const content = (
        <>
            {icon && <img src={icon} alt="" style={{ height: '1.6rem', width: 'auto', marginRight: '0.8rem' }} />}
            {label}
        </>
    );

    if (href) {
        return (
            <a href={href} target="_blank" rel="noopener noreferrer" className={className} style={style}>
                {content}
            </a>
        );
    }

    return (
        <button
            type='button'
            onClick={onClick}
            disabled={disabled}
            className={className}
            style={style}
        >
            {content}
        </button>
    )
}