import { useState } from 'react'
import CoreDemoSection from './components/sections/CoreDemoSection/CoreDemoSection.jsx'
import LiveSyncSection from './components/sections/LiveSyncSection/LiveSyncSection.jsx'
import RackMotionStage1Section from './components/sections/RackMotionStage1Section/RackMotionStage1Section.jsx'
import Skeleton3DSynthesisSection from './components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx'
import { useAnalysisSession } from './features/analysis-session/useAnalysisSession.js'
import { useSynthesisSession } from './features/synthesis-session/useSynthesisSession.js'

function App() {
    const sessionA = useAnalysisSession()
    const sessionB = useAnalysisSession()
    const synthesisSession = useSynthesisSession()
    const [synthesisJobId, setSynthesisJobId] = useState(null)
    const [synthesisProgress, setSynthesisProgress] = useState(null)

    return (
        <>
            <CoreDemoSection synthesisSession={synthesisSession} />
            <LiveSyncSection sessionA={sessionA} sessionB={sessionB} />
            <Skeleton3DSynthesisSection
                sessionA={sessionA}
                sessionB={sessionB}
                synthesisSession={synthesisSession}
                onSynthesisJobIdChange={setSynthesisJobId}
                onSynthesisProgressChange={setSynthesisProgress}
            />
            <RackMotionStage1Section
                synthesisJobId={
                    synthesisSession.status === 'completed'
                        ? synthesisSession.jobId
                        : synthesisJobId
                }
            />
        </>
    )
}

export default App
