import { useCallback, useState } from 'react'
import style from './AnalysisDashboard.module.css'
import Panel from '../../Panel/Panel.jsx'
import SectionContainer from '../../SectionContainer/SectionContainer.jsx'
import LlmFeedback from '../../LlmFeedback/LlmFeedback.jsx'
import RawSkeletonJson from '../../RawSkeletonJson/RawSkeletonJson.jsx'
import Button from '../../Button/Button.jsx'
import { getTimeseriesSeries } from '../../../features/analysis-session/adapters.js'

function formatValue(value, unit = '') {
    if (value == null || value === '') return 'n/a'
    if (typeof value === 'number') {
        const rounded = Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2)
        return `${rounded}${unit}`
    }
    return `${value}${unit}`
}

function Placeholder({ text }) {
    return (
        <article className={`${style.feedbackSurface} ${style.placeholder}`}>
            <span className={style.placeholderIcon}>—</span>
            <span>{text}</span>
        </article>
    )
}

function FeedbackSurface({ children }) {
    return (
        <article className={style.feedbackSurface}>
            {children}
        </article>
    )
}

export default function AnalysisDashboard({ analysisSession }) {
    const { result, skeletonPage, benchmarkDetails, jobMeta, downloadRawSkeleton } = analysisSession
    const [skeletonDownloadError, setSkeletonDownloadError] = useState('')
    const [isDownloadingSkeleton, setIsDownloadingSkeleton] = useState(false)
    const timeseriesSeries = result ? getTimeseriesSeries(result.timeseries).slice(0, 8) : []
    const summary = result?.summary ?? {}
    const kpis = result?.kpis ?? []
    const repSegments = result?.repSegments ?? []
    const issues = result?.issues ?? []
    const llmView = result?.llmView ?? {
        overallComment: 'LLM feedback unavailable.',
        highlights: [],
        corrections: [],
        coachCue: 'No coach cue was returned for this session.',
    }
    const benchmarkView = result?.benchmarkView ?? null
    const canDownloadSkeleton = Boolean(skeletonPage && jobMeta.jobId && !isDownloadingSkeleton)

    const handleSkeletonDownload = useCallback(async () => {
        if (!jobMeta.jobId) return

        setSkeletonDownloadError('')
        setIsDownloadingSkeleton(true)

        try {
            await downloadRawSkeleton(jobMeta.jobId)
        } catch (error) {
            setSkeletonDownloadError(error?.message ?? 'Failed to download raw skeleton JSON.')
        } finally {
            setIsDownloadingSkeleton(false)
        }
    }, [downloadRawSkeleton, jobMeta.jobId])

    return (
        <SectionContainer
            id='dataInsight'
            heading='ANALYSIS DASHBOARD'
            description='Turn analysis, LLM feedback, and benchmark payloads into readable session diagnostics.'
        >
            <div className={style.contents}>
                <Panel label='SESSION SUMMARY'>
                    {result ? (
                        <FeedbackSurface>
                            <dl className={style.detailList}>
                                {[
                                    { label: 'Exercise', value: summary.exerciseType ?? 'squat' },
                                    { label: 'Reps', value: formatValue(summary.repCount) },
                                    { label: 'Duration', value: formatValue(summary.durationMs ? summary.durationMs / 1000 : null, 's') },
                                    { label: 'Source FPS', value: formatValue(summary.sourceFps) },
                                    { label: 'Sampled FPS', value: formatValue(summary.sampledFps ?? skeletonPage?.fps) },
                                    { label: 'Detection Ratio', value: formatValue(summary.detectionRatio != null ? summary.detectionRatio * 100 : null, '%') },
                                    { label: 'Bar Placement', value: summary.barPlacementResolved ?? summary.barPlacementMode ?? 'n/a' },
                                    { label: 'Total System Mass', value: formatValue(summary.totalSystemMassKg, 'kg') },
                                ].map((item) => (
                                    <div key={item.label} className={style.detailRow}>
                                        <dt>{item.label}</dt>
                                        <dd>{item.value}</dd>
                                    </div>
                                ))}
                            </dl>
                        </FeedbackSurface>
                    ) : (
                        <Placeholder text='Run analysis to populate the session summary.' />
                    )}
                </Panel>

                <Panel label='BIOMECHANICS KPIS'>
                    {kpis.length ? (
                        <FeedbackSurface>
                            {kpis.map((kpi) => (
                                <article key={kpi.key ?? kpi.label} className={style.listBlock}>
                                    <div className={style.rowHeader}>
                                        <strong className={style.itemTitle}>{kpi.label ?? kpi.key}</strong>
                                        <span className={style.itemValue}>{formatValue(kpi.value, kpi.unit ?? '')}</span>
                                    </div>
                                    {kpi.description && <p>{kpi.description}</p>}
                                    {kpi.personalContext && <small>{kpi.personalContext}</small>}
                                </article>
                            ))}
                        </FeedbackSurface>
                    ) : (
                        result
                            ? <Placeholder text='No KPI payload was returned.' />
                            : <Placeholder text='Run analysis to populate biomechanics KPIs.' />
                    )}
                </Panel>

                <Panel label='REP BREAKDOWN'>
                    {repSegments.length ? (
                        <FeedbackSurface>
                            {repSegments.map((rep) => (
                                <article key={rep.repIndex ?? `${rep.startMs}-${rep.endMs}`} className={style.listBlock}>
                                    <div className={style.rowHeader}>
                                        <strong className={style.itemTitle}>Rep {rep.repIndex ?? '?'}</strong>
                                        <span className={style.itemValue}>Depth {formatValue(rep.depthAngleDeg, 'deg')}</span>
                                    </div>
                                    <p>
                                        Start {formatValue(rep.startMs / 1000, 's')} / Bottom {formatValue(rep.bottomMs / 1000, 's')} / End {formatValue(rep.endMs / 1000, 's')}
                                    </p>
                                </article>
                            ))}
                        </FeedbackSurface>
                    ) : (
                        result
                            ? <Placeholder text='No rep segment data returned.' />
                            : <Placeholder text='Run analysis to populate rep breakdown.' />
                    )}
                </Panel>

                <Panel label='MOVEMENT ISSUES'>
                    {issues.length ? (
                        <FeedbackSurface>
                            {issues.map((issue, index) => (
                                <article key={`${issue.code}-${index}`} className={style.listBlock}>
                                    <div className={style.rowHeader}>
                                        <strong className={style.itemTitle}>{issue.code ?? 'issue'}</strong>
                                        <span className={style.severityBadge} data-severity={issue.severity ?? 'info'}>{issue.severity ?? 'info'}</span>
                                    </div>
                                    <p>{issue.message ?? 'No issue message returned.'}</p>
                                    <small>
                                        rep {issue.repIndex ?? 'n/a'} at {formatValue(issue.timestampMs != null ? issue.timestampMs / 1000 : null, 's')}
                                    </small>
                                </article>
                            ))}
                        </FeedbackSurface>
                    ) : (
                        result
                            ? <Placeholder text='No movement issues were returned.' />
                            : <Placeholder text='Run analysis to populate movement issues.' />
                    )}
                </Panel>

                <Panel label='LLM FEEDBACK'>
                    {result ? (
                        <LlmFeedback
                            feedbackText={[
                                llmView.overallComment,
                                '',
                                'Highlights',
                                ...(llmView.highlights.length ? llmView.highlights.map(item => `- ${item}`) : ['- No highlight list returned.']),
                                '',
                                'Corrections',
                                ...(llmView.corrections.length ? llmView.corrections.map(item => `- ${item}`) : ['- No correction list returned.']),
                                '',
                                `Coach cue: ${llmView.coachCue}`,
                            ].join('\n')}
                        />
                    ) : (
                        <Placeholder text='Run analysis to populate LLM feedback.' />
                    )}
                </Panel>

                <Panel label='TIMESERIES DIAGNOSTICS'>
                    {timeseriesSeries.length ? (
                        <FeedbackSurface>
                            {timeseriesSeries.map((series) => {
                                const nums = series.values.filter(v => typeof v === 'number' && isFinite(v))
                                const seriesMin = nums.length ? nums.reduce((a, b) => a < b ? a : b) : null
                                const seriesMax = nums.length ? nums.reduce((a, b) => a > b ? a : b) : null
                                return (
                                    <article key={series.key} className={style.listBlock}>
                                        <div className={style.rowHeader}>
                                            <strong className={style.itemTitle}>{series.label}</strong>
                                            <span className={style.itemValue}>{series.values.length} pts</span>
                                        </div>
                                        <small>
                                            min {formatValue(seriesMin)} / max {formatValue(seriesMax)}
                                        </small>
                                    </article>
                                )
                            })}
                        </FeedbackSurface>
                    ) : (
                        result
                            ? <Placeholder text='No timeseries block was returned.' />
                            : <Placeholder text='Run analysis to populate timeseries diagnostics.' />
                    )}
                </Panel>

                <Panel label='BENCHMARK'>
                    {benchmarkDetails || benchmarkView ? (
                        <FeedbackSurface>
                            <dl className={style.detailList}>
                                {[
                                    { label: 'Requested Delegate', value: benchmarkView?.requestedDelegate ?? 'n/a' },
                                    { label: 'Actual Delegate', value: benchmarkView?.actualDelegate ?? 'n/a' },
                                    { label: 'Delegate Fallback', value: benchmarkView?.delegateFallbackApplied ? 'yes' : 'no' },
                                    { label: 'Total Elapsed', value: formatValue(benchmarkView?.totalElapsedMs != null ? benchmarkView.totalElapsedMs / 1000 : null, 's') },
                                    { label: 'Pose Detected Ratio', value: formatValue(benchmarkView?.poseDetectedRatio != null ? benchmarkView.poseDetectedRatio * 100 : null, '%') },
                                    { label: 'Avg Visibility', value: formatValue(benchmarkView?.avgVisibility) },
                                ].map((item) => (
                                    <div key={item.label} className={style.detailRow}>
                                        <dt>{item.label}</dt>
                                        <dd>{item.value}</dd>
                                    </div>
                                ))}
                            </dl>
                        </FeedbackSurface>
                    ) : (
                        result
                            ? <Placeholder text='Benchmark payload unavailable. The dashboard falls back to analysis and feedback blocks.' />
                            : <Placeholder text='Run analysis to populate benchmark details.' />
                    )}
                </Panel>

                <Panel
                    label='RAW SKELETON JSON'
                    headerSuffix={(
                        <Button
                            onClick={handleSkeletonDownload}
                            disabled={!canDownloadSkeleton}
                            theme='negative'
                            width='9.6rem'
                            height='3.2rem'
                            fontSize='var(--font-size-xm)'
                            label={isDownloadingSkeleton ? 'DOWNLOADING...' : 'DOWNLOAD'}
                        />
                    )}
                >
                    {skeletonPage ? (
                        <>
                            {skeletonDownloadError ? <p className={style.downloadError}>{skeletonDownloadError}</p> : null}
                            <RawSkeletonJson skeletonJson={skeletonPage.raw} />
                        </>
                    ) : (
                        <>
                            {result
                                ? <Placeholder text='Skeleton payload missing. The overlay requires /skeleton and cannot be reconstructed from /result alone.' />
                                : <Placeholder text='Run analysis to populate the raw skeleton page.' />
                            }
                        </>
                    )}
                </Panel>
            </div>
        </SectionContainer>
    )
}
