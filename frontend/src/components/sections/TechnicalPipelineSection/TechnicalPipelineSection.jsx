import style from './TechnicalPipelineSection.module.css'
import SectionContainer from '../../SectionContainer/SectionContainer'
import LogoFastAPI from '../../../assets/images/Logo_FastAPI.svg'
import LogoOpenCV from '../../../assets/images/Logo_OpenCV.svg'
import LogoMediaPipe from '../../../assets/images/Logo_MediaPipe.svg'
import LogoPython from '../../../assets/images/Logo_Python.svg'
import LogoNumPy from '../../../assets/images/Logo_NumPy.svg'
import LogoClaude from '../../../assets/images/Logo_Claude.svg'

const PIPELINE_STEPS = [
    {
        number: '01',
        tag: 'FastAPI',
        tagColor: '#0D93F2',
        name: 'Job Creation',
        description: 'The client uploads a source video to POST /jobs and receives a jobId for async polling.',
    },
    {
        number: '02',
        tag: 'OpenCV',
        tagColor: '#22C55E',
        name: 'Frame Sampling',
        description: 'The backend decodes the source video, samples frames, and keeps frameIndex plus timestampMs aligned.',
    },
    {
        number: '03',
        tag: 'MediaPipe',
        tagColor: '#00F2FF',
        name: 'Pose Extraction',
        description: 'BlazePose VIDEO inference extracts landmarks and per-frame pose visibility from the sampled frames.',
    },
    {
        number: '04',
        tag: 'Python',
        tagColor: '#F59E0B',
        name: 'Skeleton Assembly',
        description: 'Skeleton pages are exposed as /jobs/{jobId}/skeleton so the viewer can sync overlay data with the original file.',
    },
    {
        number: '05',
        tag: 'NumPy',
        tagColor: '#F97316',
        name: 'Biomechanics Analysis',
        description: 'Angles, rep segments, issues, events, and dashboard metrics are computed into the analysis block.',
    },
    {
        number: '06',
        tag: 'LLM',
        tagColor: '#A855F7',
        name: 'Feedback Packaging',
        description: 'LLM feedback and benchmark diagnostics are attached after analysis so the dashboard can render coaching output.',
    },
]

const ARCHITECTURE_LAYERS = [
    {
        index: '1',
        name: 'Client Input',
        files: 'App + Core Demo',
        description: 'Collect video and analysis settings, then start one async job per run.',
    },
    {
        index: '2',
        name: 'Async Job API',
        files: '/jobs',
        description: 'Create a job once, then track the run through polling instead of a blocking response.',
    },
    {
        index: '3',
        name: 'Status Polling',
        files: '/jobs/{jobId}',
        description: 'Expose backend progress so the UI can report queued, extracting, analyzing, computing, generating_feedback, and completed stages.',
    },
    {
        index: '4',
        name: 'Data Retrieval',
        files: '/result /skeleton /benchmark',
        description: 'Fetch analysis blocks separately after completion so each surface can hydrate from the right payload.',
    },
]

const ASYNC_JOB_STAGES = [
    {
        status: 'POST /jobs',
        ratio: 'create',
        detail: 'Returns a jobId immediately after the upload request is accepted.',
    },
    {
        status: 'GET /jobs/{jobId}',
        ratio: 'poll',
        detail: 'Reports status and progress while extraction, analysis, and feedback generation are still running.',
    },
    {
        status: 'GET /jobs/{jobId}/result',
        ratio: 'result',
        detail: 'Delivers the analysis, llmFeedback, and summary-level payload after completion.',
    },
    {
        status: 'GET /jobs/{jobId}/skeleton',
        ratio: 'viewer',
        detail: 'Streams paged skeleton data for the synchronized overlay viewer.',
    },
    {
        status: 'GET /jobs/{jobId}/benchmark',
        ratio: 'diag',
        detail: 'Adds optional runtime diagnostics without blocking the main result contract.',
    },
]

const API_ENDPOINTS = [
    { method: 'POST', path: '/jobs', description: 'Create an async job from uploaded form data.' },
    { method: 'GET', path: '/jobs/{jobId}', description: 'Poll job status and progress.' },
    { method: 'GET', path: '/jobs/{jobId}/result', description: 'Read final analysis and LLM payloads.' },
    { method: 'GET', path: '/jobs/{jobId}/skeleton', description: 'Read paged skeleton frames for viewer sync.' },
    { method: 'GET', path: '/jobs/{jobId}/benchmark', description: 'Read benchmark and quality diagnostics.' },
    { method: 'GET', path: '/jobs/{jobId}/skeleton/download', description: 'Download the raw skeleton JSON file.' },
]

const PAYLOAD_BLOCKS = [
    {
        label: 'analysis',
        color: '#22C55E',
        endpoint: '/jobs/{jobId}/result',
        consumer: 'Analysis Dashboard',
        text: 'Primary dashboard block with summary, KPIs, rep segments, issues, events, and timeseries data.',
        fields: [
            { key: 'summary', type: 'object' },
            { key: 'kpis', type: 'KPI[]' },
            { key: 'repSegments', type: 'Segment[]' },
            { key: 'issues', type: 'Issue[]' },
            { key: 'events', type: 'Event[]' },
            { key: 'timeseries', type: 'object' },
        ],
    },
    {
        label: 'llmFeedback',
        color: '#A855F7',
        endpoint: '/jobs/{jobId}/result',
        consumer: 'LLM Feedback Panel',
        text: 'Coaching-oriented text payload rendered into overall comments, highlights, corrections, and cues.',
        fields: [
            { key: 'overallComment', type: 'string' },
            { key: 'highlights', type: 'string[]' },
            { key: 'corrections', type: 'string[]' },
            { key: 'coachCue', type: 'string' },
        ],
    },
    {
        label: 'skeleton',
        color: '#00F2FF',
        endpoint: '/jobs/{jobId}/skeleton',
        consumer: 'Skeleton Viewer',
        text: 'Viewer-oriented frame sequence used for timeline sync and landmark overlay instead of dashboard prose.',
        fields: [
            { key: 'frames', type: 'Frame[]' },
            { key: 'videoInfo', type: 'object' },
            { key: 'totalFrames', type: 'number' },
            { key: 'offset', type: 'number' },
            { key: 'limit', type: 'number' },
        ],
    },
    {
        label: 'benchmark',
        color: '#F59E0B',
        endpoint: '/jobs/{jobId}/benchmark',
        consumer: 'Diagnostics Panel',
        text: 'Optional diagnostic payload for delegate selection, timing summary, and quality indicators.',
        fields: [
            { key: 'run', type: 'object' },
            { key: 'timingSummary', type: 'object' },
            { key: 'qualitySummary', type: 'object' },
        ],
    },
]

const SVG_BONES = [
    [70, 34, 38, 52], [70, 34, 102, 52],
    [38, 52, 102, 52],
    [38, 52, 26, 92], [26, 92, 18, 126],
    [102, 52, 114, 92], [114, 92, 122, 126],
    [38, 52, 50, 148], [102, 52, 90, 148],
    [50, 148, 90, 148],
    [50, 148, 46, 196], [46, 196, 42, 236],
    [90, 148, 94, 196], [94, 196, 98, 236],
]

const SVG_LANDMARKS = [
    [11, 38, 52, 'upper'], [12, 102, 52, 'upper'],
    [13, 26, 92, 'upper'], [14, 114, 92, 'upper'],
    [15, 18, 126, 'upper'], [16, 122, 126, 'upper'],
    [23, 50, 148, 'lower'], [24, 90, 148, 'lower'],
    [25, 46, 196, 'lower'], [26, 94, 196, 'lower'],
    [27, 42, 236, 'lower'], [28, 98, 236, 'lower'],
]

const LANDMARK_GROUPS = [
    {
        group: 'Face',
        color: '#6B7280',
        range: '0 – 10',
        total: 11,
        used: false,
        note: 'Not used in biomechanics analysis',
        active: [],
    },
    {
        group: 'Upper Body',
        color: '#00F2FF',
        range: '11 – 22',
        total: 12,
        used: true,
        note: 'Shoulders, elbows, and wrists',
        active: [
            { id: 11, name: 'L Shoulder' }, { id: 12, name: 'R Shoulder' },
            { id: 13, name: 'L Elbow' }, { id: 14, name: 'R Elbow' },
            { id: 15, name: 'L Wrist' }, { id: 16, name: 'R Wrist' },
        ],
    },
    {
        group: 'Lower Body',
        color: '#22C55E',
        range: '23 – 32',
        total: 10,
        used: true,
        note: 'Hips, knees, and ankles',
        active: [
            { id: 23, name: 'L Hip' }, { id: 24, name: 'R Hip' },
            { id: 25, name: 'L Knee' }, { id: 26, name: 'R Knee' },
            { id: 27, name: 'L Ankle' }, { id: 28, name: 'R Ankle' },
        ],
    },
]

const ANALYSIS_METRICS_GROUPS = [
    {
        category: 'Joint Angles',
        color: '#00F2FF',
        metrics: [
            { name: 'Knee Angle', landmarks: '25–26', range: '0°–180°', note: 'Primary rep detection trigger' },
            { name: 'Hip Flexion', landmarks: '23–24', range: '0°–120°', note: 'Depth and form assessment' },
            { name: 'Spine Inclination', landmarks: '11–23', range: '0°–90°', note: 'Postural alignment indicator' },
            { name: 'Elbow Angle', landmarks: '13–14', range: '0°–160°', note: 'Upper-body push/pull ROM' },
            { name: 'Shoulder Angle', landmarks: '11–12', range: '0°–180°', note: 'Overhead and lateral form cue' },
        ],
    },
    {
        category: 'Rep Detection',
        color: '#22C55E',
        metrics: [
            { name: 'Rep Count', landmarks: null, range: 'int', note: 'Angle inflection point cycle count' },
            { name: 'Phase Duration', landmarks: null, range: 'ms', note: 'Per-rep eccentric and concentric time' },
            { name: 'Tempo Ratio', landmarks: null, range: 'float', note: 'Eccentric-to-concentric split ratio' },
            { name: 'Rep Segments', landmarks: null, range: 'Segment[]', note: 'Start/end timestamps per rep' },
        ],
    },
    {
        category: 'Quality Signals',
        color: '#F59E0B',
        metrics: [
            { name: 'Visibility Score', landmarks: 'all', range: '0.0–1.0', note: 'Per-landmark confidence from MediaPipe' },
            { name: 'Symmetry Index', landmarks: 'bilateral', range: '0.0–1.0', note: 'Left/right angle deviation ratio' },
            { name: 'Frame Coverage', landmarks: 'all', range: '%', note: 'Ratio of high-confidence frames in clip' },
        ],
    },
]

const BACKEND_ARCH_LAYERS = [
    {
        tech: 'uv',
        color: '#DE5FE9',
        layer: 'Package & Environment',
        responsibility: 'Dependency management',
        files: ['pyproject.toml', 'uv.lock', '.python-version'],
        description: 'All Python 3.12 dependencies are declared in pyproject.toml. uv sync reproduces the .venv from uv.lock deterministically — no pip, no manual installs. Switching hardware or CI always starts from the same locked set.',
    },
    {
        tech: 'FastAPI',
        color: '#0D93F2',
        layer: 'HTTP & Routing',
        responsibility: 'API surface · no business logic',
        files: ['app.py', 'controller/jobs.py', 'controller/results.py', 'controller/analysis.py'],
        description: 'app.py mounts CORS and GZip middleware then includes all routers. Controllers translate HTTP shape into service calls and return responses — no business logic or state lives in the controller layer.',
    },
    {
        tech: 'asyncio',
        color: '#94A3B8',
        layer: 'Async Job Orchestration',
        responsibility: 'Job lifecycle · stage tracking',
        files: ['service/job_manager.py'],
        description: 'JobManager.run_job() sequences the full pipeline in a single asyncio task per upload. It advances job status (queued → extracting → analyzing → feedback → done) so the polling endpoint can report real progress without blocking.',
    },
    {
        tech: 'OpenCV',
        color: '#22C55E',
        layer: 'Frame Sampling',
        responsibility: 'Video → ExtractedFrame[]',
        files: ['adapter/opencv_adapter.py', 'service/video_reader.py'],
        description: 'OpenCvAdapter wraps cv2 behind an interface that the service layer imports instead of cv2 directly. VideoReaderService drives it at a target FPS and emits ExtractedFrame objects carrying a stable frameIndex and timestampMs that all downstream steps align to.',
    },
    {
        tech: 'MediaPipe',
        color: '#00F2FF',
        layer: 'Pose Inference',
        responsibility: 'Frames → PoseFrameResult[]',
        files: ['adapter/mediapipe_adapter.py', 'service/pose_inference.py'],
        description: 'MediaPipeAdapter wraps the BlazePose landmarker task. PoseInferenceService runs VIDEO mode over the sampled frame sequence and serializes 33 named landmark points with normalized x/y/z and per-landmark visibility and presence scores per frame.',
    },
    {
        tech: 'NumPy',
        color: '#F59E0B',
        layer: 'Data Analysis',
        responsibility: 'Landmarks → metrics · no ML',
        files: ['service/analysis_pipeline.py', 'service/analysis_features.py', 'service/analysis_reps.py', 'service/analysis_kpis.py', 'service/analysis_issues.py'],
        description: 'Pure-math biomechanics pipeline orchestrated by AnalysisPipelineService: preprocess → body profile → joint features → CoP → rep segmentation → KPIs → personal thresholds → events → issues. No external ML models — only geometry and NumPy arithmetic.',
    },
    {
        tech: 'LLM',
        color: '#A855F7',
        layer: 'LLM Feedback',
        responsibility: 'Analysis → coaching text',
        files: ['service/llm_feedback.py', 'service/llm_prompt_payload.py'],
        description: 'LlmPromptPayloadService trims the full analysis dict to a minimal JSON payload before the API call. LlmFeedbackService passes it to claude-* via the anthropic SDK and parses the structured JSON response. If LLM_FEEDBACK_ENABLED=false, a rule-based fallback runs instead.',
    },
]

const tagLogoMap = {
    FastAPI: LogoFastAPI,
    OpenCV: LogoOpenCV,
    MediaPipe: LogoMediaPipe,
    Python: LogoPython,
    NumPy: LogoNumPy,
    LLM: LogoClaude,
}

export default function TechnicalPipelineSection() {
    return (
        <div className={style.sectionWrapper}>
            <SectionContainer id="technicalPipeline">
                <div className={style.intro}>
                    <span className={style.introLabel}>Architecture</span>
                    <h2 className={style.introHeading}>Technical Pipeline</h2>
                    <p className={style.introDescription}>
                        This section describes the real async contract used by the frontend: create a job,
                        poll status, then hydrate result, skeleton, and benchmark payloads from dedicated endpoints.
                    </p>
                </div>

                <div className={style.pipelinePanel}>
                    <h3 className={style.panelHeading}>Backend Processing Pipeline</h3>
                    <div className={style.pipelineTrack}>
                        {PIPELINE_STEPS.map((step, index) => (
                            <div key={step.number} className={style.pipelineTrackStep} style={{ '--tag-color': step.tagColor }}>
                                <div className={style.pipelineTrackTop}>
                                    {index > 0 && <div className={style.pipelineTrackLine} />}
                                    <div className={style.pipelineTrackNode}>
                                        {tagLogoMap[step.tag] && (
                                            <img src={tagLogoMap[step.tag]} alt={step.tag} className={style.pipelineTrackLogo} />
                                        )}
                                    </div>
                                    {index < PIPELINE_STEPS.length - 1 && <div className={style.pipelineTrackLine} />}
                                </div>
                                <div className={style.pipelineTrackCard}>
                                    <div className={style.pipelineTrackCardHeader}>
                                        <span className={style.pipelineTrackNum}>{step.number}</span>
                                        <span className={style.stepTag}>{step.tag}</span>
                                    </div>
                                    <h4 className={style.pipelineTrackName}>{step.name}</h4>
                                    <p className={style.pipelineTrackDesc}>{step.description}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className={style.backendArchPanel}>
                    <div className={style.backendArchHeader}>
                        <h3 className={style.panelHeading}>Backend Architecture Layers</h3>
                        <p className={style.panelDescription}>
                            Each responsibility is isolated to its own layer. uv locks the environment, FastAPI owns the HTTP surface, adapters wrap external libs, services run the pipeline, and the LLM call is a final isolated step.
                        </p>
                    </div>
                    <div className={style.backendArchRows}>
                        {BACKEND_ARCH_LAYERS.map((layer, index) => (
                            <div
                                key={layer.tech}
                                className={style.backendArchRow}
                                style={{ '--arch-color': layer.color }}
                            >
                                <div className={style.backendArchRowAccent} />
                                <div className={style.backendArchRowContent}>
                                    <div className={style.backendArchRowLeft}>
                                        <div className={style.backendArchRowMeta}>
                                            <span className={style.backendArchTechBadge}>{layer.tech}</span>
                                            <span className={style.backendArchLayerName}>{layer.layer}</span>
                                        </div>
                                        <span className={style.backendArchResponsibility}>{layer.responsibility}</span>
                                        <div className={style.backendArchFiles}>
                                            {layer.files.map(f => (
                                                <code key={f} className={style.backendArchFile}>{f}</code>
                                            ))}
                                        </div>
                                    </div>
                                    <p className={style.backendArchDesc}>{layer.description}</p>
                                </div>
                                {index < BACKEND_ARCH_LAYERS.length - 1 && (
                                    <div className={style.backendArchConnector}>
                                        <svg width="12" height="16" viewBox="0 0 12 16" fill="none" aria-hidden="true">
                                            <path d="M6 0V12M6 12L2 8M6 12L10 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                        </svg>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                <div className={style.bottomPanels}>
                    <div className={style.panel}>
                        <h3 className={style.panelHeading}>Frontend Architecture Layers</h3>
                        <div className={style.layerStack}>
                            {ARCHITECTURE_LAYERS.map((layer, index) => {
                                const colors = ['#0D93F2', '#22C55E', '#00F2FF', '#F59E0B']
                                const isLast = index === ARCHITECTURE_LAYERS.length - 1
                                return (
                                    <div key={layer.index} className={style.layerRow} style={{ '--layer-color': colors[index] }}>
                                        <div className={style.layerRowTrack}>
                                            <div className={style.layerRowNode} />
                                            {!isLast && <div className={style.layerRowLine} />}
                                        </div>
                                        <div className={`${style.layerRowBody} ${isLast ? style.layerRowBodyLast : ''}`}>
                                            <div className={style.layerRowHeader}>
                                                <div className={style.layerRowMeta}>
                                                    <span className={style.layerRowNum}>
                                                        {String(layer.index).padStart(2, '0')}
                                                    </span>
                                                    <span className={style.layerRowName}>{layer.name}</span>
                                                </div>
                                                <code className={style.layerFiles}>{layer.files}</code>
                                            </div>
                                            <p className={style.layerRowDesc}>{layer.description}</p>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    <div className={style.panel}>
                        <h3 className={style.panelHeading}>Frontend-Backend End-to-End API Endpoints</h3>
                        <div className={style.apiEndpoints}>
                            {API_ENDPOINTS.map((endpoint) => (
                                <div key={endpoint.path} className={style.apiEndpoint}>
                                    <span className={style.apiMethod}>{endpoint.method}</span>
                                    <div className={style.apiText}>
                                        <code className={style.apiPath}>{endpoint.path}</code>
                                        <span className={style.apiDescription}>{endpoint.description}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className={style.asyncJobPanel}>
                    <div className={style.asyncJobHeader}>
                        <h3 className={style.asyncJobHeading}>Frontend Async Job Model</h3>
                        <p className={style.asyncJobDesc}>
                            The UI does not wait for one long blocking response. It opens a job, polls the status endpoint,
                            then reads specialized payloads after completion so the viewer and dashboard can hydrate independently.
                        </p>
                    </div>
                    <div className={style.asyncJobDiagram}>
                        <div className={style.asyncPhase}>
                            <div className={style.asyncPhaseHeader}>
                                <span className={style.asyncPhaseNum}>01</span>
                                <span className={style.asyncPhaseTitle}>Create</span>
                            </div>
                            <div className={style.asyncPhaseBody}>
                                <div className={style.asyncEndpointRow}>
                                    <span className={`${style.asyncMethod} ${style.asyncMethodPost}`}>POST</span>
                                    <code className={style.asyncEndpointPath}>/jobs</code>
                                </div>
                                <div className={style.asyncReturnTag}>
                                    <span className={style.asyncReturnArrow}>↳</span>
                                    <span className={style.asyncReturnText}>returns <code>jobId</code> immediately</span>
                                </div>
                                <p className={style.asyncPhaseDesc}>Upload is non-blocking. The job is queued and the ID is returned right away.</p>
                            </div>
                        </div>

                        <div className={style.asyncConnector} aria-hidden="true">
                            <svg width="40" height="16" viewBox="0 0 40 16" fill="none">
                                <path d="M0 8H36M36 8L28 2M36 8L28 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>

                        <div className={style.asyncPhase}>
                            <div className={style.asyncPhaseHeader}>
                                <span className={style.asyncPhaseNum}>02</span>
                                <span className={style.asyncPhaseTitle}>Poll</span>
                            </div>
                            <div className={style.asyncPhaseBody}>
                                <div className={style.asyncEndpointRow}>
                                    <span className={`${style.asyncMethod} ${style.asyncMethodGet}`}>GET</span>
                                    <code className={style.asyncEndpointPath}>{'/jobs/{jobId}'}</code>
                                </div>
                                <div className={style.statusFlow}>
                                    {['queued', 'extracting', 'analyzing', 'computing', 'generating_feedback', 'completed'].map((status, i, arr) => (
                                        <span key={status} className={style.statusFlowItem}>
                                            <span className={`${style.statusPill} ${status === 'completed' ? style.statusPillDone : ''}`}>
                                                {status}
                                            </span>
                                            {i < arr.length - 1 && <span className={style.statusFlowArrow}>↓</span>}
                                        </span>
                                    ))}
                                </div>
                                <p className={style.asyncPhaseDesc}>Backend reports progress per stage until the job reaches done.</p>
                            </div>
                        </div>

                        <div className={style.asyncConnector} aria-hidden="true">
                            <svg width="40" height="16" viewBox="0 0 40 16" fill="none">
                                <path d="M0 8H36M36 8L28 2M36 8L28 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                            </svg>
                        </div>

                        <div className={`${style.asyncPhase} ${style.asyncPhaseRetrieve}`}>
                            <div className={style.asyncPhaseHeader}>
                                <span className={style.asyncPhaseNum}>03</span>
                                <span className={style.asyncPhaseTitle}>Retrieve</span>
                                <span className={style.asyncParallelBadge}>parallel</span>
                            </div>
                            <div className={style.asyncRetrieveGrid}>
                                {[
                                    { path: '/result', label: 'analysis · llmFeedback', color: '#22C55E' },
                                    { path: '/skeleton', label: 'frame overlay · viewer sync', color: '#00F2FF' },
                                    { path: '/benchmark', label: 'quality diagnostics', color: '#F59E0B' },
                                ].map((item) => (
                                    <div key={item.path} className={style.asyncRetrieveItem} style={{ '--retrieve-color': item.color }}>
                                        <div className={style.asyncEndpointRow}>
                                            <span className={`${style.asyncMethod} ${style.asyncMethodGet}`}>GET</span>
                                            <code className={style.asyncEndpointPath}>{`/jobs/{jobId}${item.path}`}</code>
                                        </div>
                                        <span className={style.asyncRetrieveLabel}>{item.label}</span>
                                    </div>
                                ))}
                            </div>
                            <p className={style.asyncPhaseDesc}>Each surface fetches only the payload it needs after the job completes.</p>
                        </div>
                    </div>
                </div>

                <div className={style.hypothesesPanel}>
                    <div className={style.hypothesesHeader}>
                        <h3 className={style.hypothesesHeading}>Payload Contract</h3>
                        <p className={style.hypothesesSubtext}>
                            Each surface hydrates from a dedicated payload after the job completes.
                        </p>
                    </div>
                    <div className={style.hypothesesGrid}>
                        {PAYLOAD_BLOCKS.map((block) => (
                            <div key={block.label} className={style.contractCard} style={{ '--block-color': block.color }}>
                                <div className={style.contractCardTop}>
                                    <div className={style.contractKeyRow}>
                                        <span className={style.contractBrace}>{'{}'}</span>
                                        <code className={style.contractLabel}>{block.label}</code>
                                        <span className={style.contractType}>object</span>
                                    </div>
                                    <div className={style.contractEndpointRow}>
                                        <span className={`${style.asyncMethod} ${style.asyncMethodGet}`}>GET</span>
                                        <code className={style.contractEndpoint}>{block.endpoint}</code>
                                    </div>
                                </div>
                                <p className={style.hypothesisText}>{block.text}</p>
                                <div className={style.contractSchema}>
                                    {block.fields.map((field) => (
                                        <div key={field.key} className={style.contractSchemaRow}>
                                            <code className={style.contractSchemaKey}>{field.key}</code>
                                            <span className={style.contractSchemaType}>{field.type}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className={style.contractConsumer}>
                                    <span className={style.contractConsumerArrow}>→</span>
                                    <span className={style.contractConsumerName}>{block.consumer}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
                <div className={style.landmarkMetricsGrid}>
                    {/* Pose Landmark Map */}
                    <div className={style.panel}>
                        <h3 className={style.panelHeading}>Pose Landmark Map</h3>
                        <p className={style.panelDescription}>
                            BlazePose VIDEO mode extracts 33 landmarks per frame. 12 body joints are active in biomechanics analysis; face landmarks are captured but unused.
                        </p>
                        <div className={style.landmarkBody}>
                            <div className={style.landmarkSvgWrap}>
                                <svg viewBox="0 0 140 250" className={style.landmarkSvg} aria-hidden="true">
                                    <circle cx="70" cy="18" r="14"
                                        fill="rgba(255,255,255,0.04)"
                                        stroke="rgba(255,255,255,0.18)"
                                        strokeWidth="1.2"
                                    />
                                    {SVG_BONES.map(([x1, y1, x2, y2], i) => (
                                        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                                            stroke="rgba(255,255,255,0.14)"
                                            strokeWidth="1.5"
                                            strokeLinecap="round"
                                        />
                                    ))}
                                    {SVG_LANDMARKS.map(([id, x, y, group]) => {
                                        const color = group === 'upper' ? '#00F2FF' : '#22C55E'
                                        const fill = group === 'upper' ? 'rgba(0,242,255,0.15)' : 'rgba(34,197,94,0.15)'
                                        return (
                                            <g key={id}>
                                                <circle cx={x} cy={y} r="5.5" fill={fill} stroke={color} strokeWidth="1.5" />
                                                <circle cx={x} cy={y} r="2" fill={color} />
                                            </g>
                                        )
                                    })}
                                </svg>
                            </div>
                            <div className={style.landmarkGroups}>
                                {LANDMARK_GROUPS.map(grp => (
                                    <div key={grp.group} className={style.landmarkGroupCard} style={{ '--grp-color': grp.color }}>
                                        <div className={style.landmarkGroupHeader}>
                                            <span className={style.landmarkGroupDot} />
                                            <span className={style.landmarkGroupName}>{grp.group}</span>
                                            <code className={style.landmarkGroupRange}>{grp.range}</code>
                                            <span className={grp.used ? style.landmarkUsedBadge : style.landmarkUnusedBadge}>
                                                {grp.used ? 'active' : 'inactive'}
                                            </span>
                                        </div>
                                        <p className={style.landmarkGroupNote}>{grp.note}</p>
                                        {grp.active.length > 0 && (
                                            <div className={style.landmarkChips}>
                                                {grp.active.map(lm => (
                                                    <span key={lm.id} className={style.landmarkChip}>
                                                        <code className={style.landmarkChipId}>{lm.id}</code>
                                                        <span className={style.landmarkChipName}>{lm.name}</span>
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Analysis Metrics */}
                    <div className={style.panel}>
                        <h3 className={style.panelHeading}>Analysis Metrics</h3>
                        <p className={style.panelDescription}>
                            Metrics derived per frame and aggregated across the full clip into the analysis block.
                        </p>
                        <div className={style.metricsCategories}>
                            {ANALYSIS_METRICS_GROUPS.map(group => (
                                <div key={group.category} className={style.metricsCategory} style={{ '--cat-color': group.color }}>
                                    <div className={style.metricsCategoryHeader}>
                                        <span className={style.metricsCategoryDot} />
                                        <span className={style.metricsCategoryTitle}>{group.category}</span>
                                        <span className={style.metricsCategoryCount}>{group.metrics.length}</span>
                                    </div>
                                    <div className={style.metricsItemList}>
                                        {group.metrics.map(metric => (
                                            <div key={metric.name} className={style.metricsItem}>
                                                <div className={style.metricsItemLeft}>
                                                    <span className={style.metricsItemName}>{metric.name}</span>
                                                    <span className={style.metricsItemNote}>{metric.note}</span>
                                                </div>
                                                <div className={style.metricsItemRight}>
                                                    {metric.landmarks && (
                                                        <code className={style.metricsItemLandmarks}>{metric.landmarks}</code>
                                                    )}
                                                    <span className={style.metricsItemRange}>{metric.range}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </SectionContainer>
        </div>
    )
}
