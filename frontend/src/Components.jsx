import style from './Components.module.css'
import Button from './components/Button/Button';
import Panel from './components/Panel/Panel';
import ArrowUp from './assets/images/ArrowUp.png'

export default function components(){
    return(
    <div className={style.background}>
        <Button
            
        />
        <Button
            theme='negative'
        />
        <Panel
            icon={ArrowUp}
            label='Analysis Settings'
        >
            Lorem ipsum dolor sit amet consectetur adipisicing elit. Repellat autem pariatur sapiente unde, veritatis, culpa eum, repudiandae magni tempore ipsam quam delectus commodi modi expedita ex iusto nostrum aperiam praesentium!
        </Panel>
    </div>
    )
}