import Toggle from '../Toggle/Toggle'
import style from './VisualizationSettings.module.css'

export default function VisualizationSettings({ vizConfig, onChange }) {
    const options = [
        ['showSkeleton', 'Show Skeleton'],
        ['showJointLabels', 'Joint Labels'],
        ['showAngleOverlay', 'Angle Overlay'],
        ['showJointLoad', 'Joint Load'],
        ['showIssueMarkers', 'Issue Markers'],
        ['showRepBoundaries', 'Rep Boundaries'],
        ['showEventMarkers', 'Event Markers'],
        ['showPathTrace', 'Motion Path'],
        ['showConfidenceTint', 'Confidence Tint'],
        ['showBarPass', 'Bar Pass'],
        ['showGroundVector', 'Ground Vector'],
        ['showCoP', 'CoP Line'],
    ]

    return (
        <div className={style.container}>
            {options.map(([key, label]) => (
                <Toggle
                    key={key}
                    label={label}
                    checked={Boolean(vizConfig[key])}
                    onChange={(value) => onChange(key, value)}
                />
            ))}
        </div>
    )
}
