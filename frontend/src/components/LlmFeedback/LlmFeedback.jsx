import style from './LlmFeedback.module.css';

export default function LlmFeedback({ feedbackText }){
    return(
        <article className={style.LlmFeedbackConatiner}>
            <p className={style.feedbackText}>
                {feedbackText}
            </p>
        </article>
    )
}
