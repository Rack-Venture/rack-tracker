import style from './SectionContainer.module.css'

/**
 * 섹션 공통 레이아웃 컴포넌트. `<section>` 태그로 렌더링.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children
 * @param {string} [props.id] - 섹션 id (앵커 링크용)
 * @param {string} [props.heading] - 섹션 제목
 * @param {string} [props.description] - 섹션 설명
 */
export default function SectionContainer({ children, id, heading, description }) {
    return (
        <section id={id} className={style.sectionContainer}>
            {(heading || description) && (
                <div className={style.sectionIntro}>
                    {heading && <h2 className={style.sectionHeading}>{heading}</h2>}
                    {description && <p className={style.sectionDescription}>{description}</p>}
                </div>
            )}
            {children}
        </section>
    )
}
