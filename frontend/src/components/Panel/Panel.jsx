import style from './Panel.module.css'

/**
 * 아이콘과 레이블로 구성된 헤더와 콘텐츠 영역을 가진 패널 컴포넌트.
 *
 * @param {Object} props
 * @param {string} [props.icon] - 헤더에 표시할 아이콘 이미지 경로. 없으면 아이콘 미표시.
 * @param {string} props.label - 헤더에 표시할 패널 제목 텍스트.
 * @param {React.ReactNode} props.children - 패널 본문에 렌더링할 자식 요소.
 * @returns {JSX.Element}
 */
export default function Panel({icon, label, headerPrefix, headerSuffix, children, id, tabIndex, containerClassName = '', bodyClassName = ''}){
    return (
        <div className={`${style.panelContainer} ${containerClassName}`.trim()} id={id} tabIndex={tabIndex}>
            <div className={style.panelHeader}>
                {headerPrefix && <div className={style.headerPrefix}>{headerPrefix}</div>}
                {icon && <img 
                    src={icon}
                    alt={label}
                    className={style.icon}            
                />}
                <h3 className={style.panelLable}>{label}</h3>
                {headerSuffix && <div className={style.headerSuffix}>{headerSuffix}</div>}
            </div>
            <div className={`${style.panelBody} ${bodyClassName}`.trim()}>
                {children}
            </div>
        </div>
    )
}
