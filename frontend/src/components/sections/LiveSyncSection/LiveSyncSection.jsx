import { useState, useRef } from 'react'
import Panel from '../../Panel/Panel.jsx'
import VisualizationSettings from '../../VisualizationSettings/VisualizationSettings.jsx'
import LiveViewPanel from './LiveViewPanel.jsx'
import SectionContainer from '../../SectionContainer/SectionContainer.jsx'
import SettingIcon from '../../../assets/images/icon_setting.png'
import style from './LiveSyncSection.module.css'

function formatTime(s) {
    if (!s || !Number.isFinite(s)) return '0:00.0'
    const m = Math.floor(s / 60)
    const sec = (s % 60).toFixed(1)
    return `${m}:${sec.padStart(4, '0')}`
}

export default function LiveSyncSection({ sessionA, sessionB }) {
    const { vizConfig, updateVizConfig } = sessionA

    const [isPlaying, setIsPlaying] = useState(false)
    const [displayTime, setDisplayTime] = useState(0)
    const [displayDuration, setDisplayDuration] = useState(0)
    const [seekTarget, setSeekTarget] = useState(null)

    const canViewA = sessionA.status === 'completed' && Boolean(sessionA.form.videoFile) && Boolean(sessionA.skeletonPage)
    const canViewB = sessionB.status === 'completed' && Boolean(sessionB.form.videoFile) && Boolean(sessionB.skeletonPage)
    const canPlay  = canViewA || canViewB

    const handleTimeUpdate = (t, d) => {
        setDisplayTime(t)
        if (d > 0) setDisplayDuration(d)
    }

    const handleEnded = () => setIsPlaying(false)

    const handleScrub = (e) => {
        const t = Number(e.target.value)
        setDisplayTime(t)
        setSeekTarget({ time: t })
        setIsPlaying(false)
    }

    const progress = displayDuration > 0 ? (displayTime / displayDuration) * 100 : 0

    return (
        <SectionContainer
            id="liveSyncStudio"
            heading="VISUAL SYNC STUDIO"
            description="Synchronized dual skeleton playback. Adjust the shared visualization settings below to apply to both views."
        >
            {/* ── Dual viewer grid ── */}
            <div className={style.dualGrid}>
                {[
                    { session: sessionA, canView: canViewA, label: 'Live View  A' },
                    { session: sessionB, canView: canViewB, label: 'Live View  B' },
                ].map(({ session, canView, label }) => (
                    <div key={label} className={style.viewerCard}>
                        <div className={style.viewerHeader}>
                            <span
                                className={`${style.liveDot} ${canView ? '' : style.liveDotOff}`}
                                aria-hidden="true"
                            />
                            <span className={style.viewerLabel}>{label}</span>
                        </div>
                        <LiveViewPanel
                            videoFile={session.form.videoFile}
                            skeletonData={session.skeletonPage}
                            vizConfig={vizConfig}
                            barPlacementMode={session.form.barPlacementMode}
                            status={session.status}
                            jobProgress={session.jobMeta.progress}
                            errorMessage={session.userMessage}
                            isPlaying={isPlaying}
                            seekTarget={seekTarget}
                            onTimeUpdate={handleTimeUpdate}
                            onEnded={handleEnded}
                        />
                    </div>
                ))}
            </div>

            {/* ── Synchronized playback bar ── */}
            <div className={style.syncBar}>
                <span className={style.syncLabel}>SYNCHRONIZED PLAYBACK</span>

                <button
                    className={`${style.playBtn} ${isPlaying ? style.playBtnActive : ''}`}
                    onClick={() => setIsPlaying(p => !p)}
                    disabled={!canPlay}
                    aria-label={isPlaying ? 'Pause both' : 'Play both'}
                >
                    {isPlaying ? '■' : '▶'}
                </button>

                <div className={style.scrubWrap}>
                    <input
                        type="range"
                        className={style.scrubber}
                        min={0}
                        max={displayDuration || 1}
                        step={0.033}
                        value={displayTime}
                        onChange={handleScrub}
                        disabled={!canPlay}
                        style={{ '--progress': `${progress}%` }}
                    />
                </div>

                <span className={style.timeDisplay}>
                    {formatTime(displayTime)} / {formatTime(displayDuration)}
                </span>
            </div>

            {/* ── Visualization settings panel ── */}
            <Panel icon={SettingIcon} label="Visualization Panel">
                <VisualizationSettings vizConfig={vizConfig} onChange={updateVizConfig} />
            </Panel>
        </SectionContainer>
    )
}
