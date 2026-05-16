import style from './MetricsList.module.css'

export default function MetricsList({metrics}){

    return(
        <ul className={style.listContainer}>
            {metrics && metrics.map((metric) => {
                return(
                    <li 
                        key={metric.metric}
                        className={style.metric}
                    >
                        <span className={style.label}>
                            {metric.label}
                        </span>
                        <span className={`${style.value} ${style[metric.type]}`}>
                            {metric.value}
                        </span>
                    </li>
                )
            })}
        </ul>
    )
}