import Button from '../../Button/Button';
import styles from './MainHeader.module.css';
import Logo from '../../../assets/images/Logo_SMU.svg'
import { focusCoreDemo } from '../../../utils/focusCoreDemo.js'


export default function MainHeader(){
    return(
        <div className={styles.headerContainer}>
            <div className={styles.signature}>
                <a href='https://www.smu.ac.kr/kor/index.do' className='SMU'><img className={styles.logo} src={Logo} alt="Sangmyung university" /></a>
                <a href='/'><h2 className={styles.teamName}>RACKLABS</h2></a>
                <a href='/'><p className={styles.productName}>MVP V1</p></a>
            </div>
            <nav>
                <ul className={styles.nav}>
                    <li>
                        <a
                            href='#coreDemo'
                            onClick={(event) => {
                                event.preventDefault()
                                focusCoreDemo()
                            }}
                        >
                            Core Demo
                        </a>
                    </li>
                    <li><a href='#liveSyncStudio'>Live View</a></li>
                    <li><a href='#dataInsight'>Data Insight</a></li>
                    <li><a href='#technicalPipeline'>Pipeline</a></li>
                </ul>
            </nav>
            <Button
                width='13.2rem'
                height='3.6rem'
                label='Contact Expert'
                fontSize='var(--font-size-sm)'
                onClick={() => window.open('https://github.com/lhk0721', '_blank')}
            />
            
        </div>
    )
}
