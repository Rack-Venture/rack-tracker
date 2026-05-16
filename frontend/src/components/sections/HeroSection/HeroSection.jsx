import Button from '../../Button/Button';
import style from './HeroSection.module.css';
import overlay from '../../../assets/images/Overlay.svg'
import LogoGithub from '../../../assets/images/Logo_github.svg'
import { focusCoreDemo } from '../../../utils/focusCoreDemo.js'

export default function HeroSection(){
    return(
        <section className={style.sectionContainer}>
            <img className={style.overlay} src={overlay} alt="" />
            <p className={style.eyebrow}>
                BIOMECHANICS · POSE ESTIMATION
            </p>
            <h1 className={style.headline}>
            Future of Biomechanics Analysis, <br/>
            <span>Start with MVP v1</span>
            </h1>
            <p className={style.subheading}>
            Combine MediaPipe skeleton extraction and LLM feedback. <br/>
            Experience precise movement interpretation beyond simple recording.
            </p>
            <div className={style.actions}>
                <Button
                    width='17.4rem'
                    height='5.8rem'
                    label='Start Demo'
                    fontSize='var(--font-size-md)'
                    onClick={focusCoreDemo}
                />
                <Button
                    width='17.4rem'
                    height='5.8rem'
                    label='GitHub'
                    theme='negative'
                    fontSize='var(--font-size-md)'
                    icon={LogoGithub}
                    href='https://github.com/rack-labs/rack-tracker/tree/develop/poseLandmarker_Python'
                />
            </div>
        </section>
    )
}
