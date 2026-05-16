from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from controller import analysis, health, jobs, rack_motion, results, synthesis

app = FastAPI(title="Motion Analysis Backend")
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(rack_motion.router)
app.include_router(results.router)
app.include_router(synthesis.router)
